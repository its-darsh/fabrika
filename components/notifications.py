from .common import (
    Box,
    Label,
    Button,
    FlowBox,
    Overlay,
    Revealer,
    Image,
    ClippingBox,
    Notification,
    Notifications,
    AnimatedScrollable,
    Gtk,
    GdkPixbuf,
    bake_corner,
    cast,
    idle_add,
    invoke_repeater,
    add_style_class_lazy,
    get_children_height_limit,
)

NOTIFICATION_WIDTH = 360
NOTIFICATION_IMAGE_SIZE = 64
NOTIFICATION_TIMEOUT = 10 * 1000  # 10 seconds
NOTIFICATION_BUTTONS_PER_ROW = 2
NOTIFICATION_REVEALER_DURATION = 400  # ms
NOTIFICATIONS_CORNERS_SIZE = 16

DEFAULT_ICONS_THEME = Gtk.IconTheme.get_default()


class LimitBox(Box):
    """A hack for replicating CSS's `max-*` properties"""

    def __init__(self, max_width: int, max_height: int, **kwargs):
        super().__init__(**kwargs)
        self.max_width: int = max_width
        self.max_height: int = max_height

    def do_size_allocate(self, allocation):
        if self.max_width >= 0:
            allocation.width = min(self.max_width, allocation.width)
        if self.max_height >= 0:
            allocation.height = min(self.max_height, allocation.height)
        return Box.do_size_allocate(self, allocation)


class NotificationItem(Box):
    def __init__(self, notification: Notification, **kwargs):
        super().__init__(
            name="notification",
            spacing=8,
            orientation="v",
            size=(NOTIFICATION_WIDTH, -1),
            **kwargs,
        )

        self.notification = notification

        body_container = Box(spacing=4, orientation="h")

        if image_pixbuf := self.notification.image_pixbuf:
            body_container.add(
                ClippingBox(
                    children=(
                        Image(
                            pixbuf=image_pixbuf.scale_simple(
                                NOTIFICATION_IMAGE_SIZE,
                                NOTIFICATION_IMAGE_SIZE,
                                GdkPixbuf.InterpType.BILINEAR,
                            ),
                            v_align="fill",
                            h_align="fill",
                            v_expand=True,
                            h_expand=True,
                        )
                    ),
                    v_align="start",
                    h_align="start",
                    v_expand=False,
                    h_expand=False,
                )
            )
        print()
        body_container.add(
            Box(
                spacing=4,
                orientation="v",
                children=[
                    # a box for holding both the "summary" label and the "close" button
                    Box(
                        orientation="h",
                        children=[
                            Overlay(
                                child=Label(
                                    label=self.notification.summary,
                                    style_classes="summary",
                                    ellipsization="middle",
                                )
                                .build()
                                .set_xalign(0.0)
                                .unwrap(),
                                # notification's source icon
                                overlays=[
                                    Image(
                                        # render app's icon if found
                                        pixbuf=icn.load_icon()
                                        if (
                                            icn := DEFAULT_ICONS_THEME.lookup_icon(
                                                self.notification.app_icon
                                                or self.notification.app_name,
                                                12,
                                                Gtk.IconLookupFlags.FORCE_SIZE,
                                            )
                                        )
                                        is not None
                                        else None,
                                        v_align="start",
                                        h_align="start",
                                    )
                                ],
                            ),
                        ],
                        h_expand=True,
                        v_expand=True,
                        v_align="start",
                    )
                    # add the "close" button
                    .build(
                        lambda box, _: box.pack_end(
                            Button(
                                image=Image(
                                    icon_name="close-symbolic",
                                    icon_size=18,
                                ),
                                v_align="center",
                                h_align="end",
                                on_clicked=lambda *_: self.notification.close(),
                                on_state_flags_changed=lambda btn, *_: (
                                    btn.set_cursor("pointer")
                                    if btn.get_state_flags() & 2
                                    else btn.set_cursor("default"),
                                ),
                            ),
                            False,
                            False,
                            0,
                        )
                    ),
                    Label(
                        label=self.notification.body,
                        style_classes="body",
                        line_wrap="word-char",
                        v_align="start",
                        h_align="start",
                    )
                    .build()
                    .set_xalign(0.0)
                    .unwrap(),
                ],
                h_expand=True,
                v_expand=True,
            )
        )

        self.add(body_container)

        if actions := self.notification.actions:
            self.add(
                FlowBox(
                    spacing=4,
                    row_spacing=4,
                    column_spacing=4,
                    orientation="h",
                    v_expand=True,
                    h_expand=True,
                    children=[
                        Button(
                            h_expand=True,
                            v_expand=True,
                            label=action.label,
                            on_clicked=lambda *_, action=action: action.invoke(),
                            on_state_flags_changed=lambda btn, *_: (
                                btn.set_cursor("pointer")
                                if btn.get_state_flags() & 2
                                else btn.set_cursor("default"),
                            ),
                        )
                        for action in actions
                    ],
                )
                .build()
                .set_max_children_per_line(
                    min(len(actions), NOTIFICATION_BUTTONS_PER_ROW)
                )
                .unwrap()
            )

        # automatically close the notification after the timeout period
        invoke_repeater(
            NOTIFICATION_TIMEOUT,
            self.notification.close,
            "expired",
            initial_call=False,
        )

        add_style_class_lazy(self, "shine")


# TODO: add the whole thing to a revealer that reveals to the left
class NotificationsView(Box):
    def __init__(self, **kwargs):
        super().__init__(orientation="v", visible=False, **kwargs)

        self.viewport = Box(spacing=4, orientation="v")

        self.scrolled_window = AnimatedScrollable(
            min_content_size=(420, 1),
            max_content_size=(420, 480),
            # h_scrollbar_policy="never",
            # v_scrollbar_policy="never",
            child=self.viewport,
            h_expand=True,
            v_expand=True,
        )

        self.overall_container = Box(
            name="notifications",
            orientation="v",
            children=ClippingBox(
                style_classes="notifications-clip", children=self.scrolled_window
            ),
            h_expand=True,
            v_expand=True,
        )

        self.notifications = Notifications(
            on_notification_added=lambda _, notification_id: (
                notification := cast(
                    Notification, self.notifications.notifications.get(notification_id)
                ),
                self.viewport.add(
                    item_rev := Revealer(
                        child=NotificationItem(notification),
                        reveal_child=False,
                        transition_type="slide-down",
                        transition_duration=NOTIFICATION_REVEALER_DURATION,
                    )
                ),
                self.viewport.reorder_child(item_rev, 0),
                # ready to show
                item_rev.reveal(),
                notification.closed.connect(
                    lambda: (
                        item_rev.connect(
                            "notify::child-revealed",
                            lambda: item_rev.destroy()
                            if not item_rev.fully_revealed
                            else None,
                        ),
                        idle_add(item_rev.unreveal),
                    )
                ),
            ),
        )

        # i mean, it's just chef's kiss
        self.children = (
            Box(
                orientation="h",
                children=[
                    Box(
                        orientation="v",
                        spacing=NOTIFICATIONS_CORNERS_SIZE,
                        children=[
                            LimitBox(
                                max_width=NOTIFICATIONS_CORNERS_SIZE,
                                max_height=NOTIFICATIONS_CORNERS_SIZE,
                                children=bake_corner(
                                    orientation="top-right",
                                    v_expand=True,
                                    h_expand=True,
                                ),
                                v_expand=True,
                                size=(NOTIFICATIONS_CORNERS_SIZE, -1),
                            ),
                            Box(
                                h_expand=True,
                                v_expand=True,
                            ),
                        ],
                        h_expand=True,
                        v_expand=True,
                    ),
                    self.overall_container,
                ],
            ),
            Box(
                children=bake_corner(
                    orientation="top-right",
                    v_expand=True,
                    h_expand=True,
                ),
                size=NOTIFICATIONS_CORNERS_SIZE,
                h_align="end",
                v_align="end",
            ),
        )

        self.viewport.connect("add", self.on_children_change)
        self.viewport.connect("remove", self.on_children_change)
        self.connect("notify::visible", self.on_visiblity_change)

    def on_children_change(self, *_):
        # for fuck's sake don't repeat the same mistake
        # we have two containers to work with
        self.scrolled_window.animate_size(
            get_children_height_limit(
                self.viewport,
                4,
                lambda rev: (
                    cast(Revealer, rev).get_child().get_preferred_size().minimum_size  # type: ignore
                ),
            )
        )

        return self.hide() if not self.viewport.children else self.show()

    def on_visiblity_change(self, *_):
        self.viewport.remove_style_class("popped")

        if not self.get_visible():
            return

        return add_style_class_lazy(self.viewport, "popped")
