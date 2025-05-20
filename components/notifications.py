from .common import (
    Box,
    CenterBox,
    Label,
    CustomImage,
    Overlay,
    Button,
    AnimatedScrollable,
    add_style_class_lazy,
    get_children_height_limit,
    invoke_repeater,
    bake_corner,
    cast,
    Notification,
    Notifications,
)
from gi.repository import GdkPixbuf

NOTIFICATION_WIDTH = 360
NOTIFICATION_IMAGE_SIZE = 64
NOTIFICATION_TIMEOUT = 16 * 1000  # 10 seconds
NOTIFICATIONS_CORNERS_SIZE = 16


class NotificationItem(Box):
    def __init__(self, notification: Notification, **kwargs):
        super().__init__(
            size=(NOTIFICATION_WIDTH, -1),
            name="notification",
            spacing=8,
            orientation="v",
            **kwargs,
        )

        self.notification = notification

        body_container = Box(spacing=4, orientation="h")

        if image_pixbuf := self.notification.image_pixbuf:
            body_container.add(
                CustomImage(
                    pixbuf=image_pixbuf.scale_simple(
                        NOTIFICATION_IMAGE_SIZE,
                        NOTIFICATION_IMAGE_SIZE,
                        GdkPixbuf.InterpType.BILINEAR,
                    ),
                    v_expand=False,
                    h_expand=False,
                    v_align="start",
                    h_align="start",
                )
            )

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
                                    ellipsization="middle",
                                )
                                .build()
                                .set_style_classes("summary")
                                .unwrap(),
                                # notification's source icon
                                overlays=CustomImage(
                                    icon_name=(
                                        self.notification.app_icon
                                        or self.notification.app_name
                                    ),
                                    icon_size=12,
                                    v_align="start",
                                    h_align="start",
                                ),
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
                                image=CustomImage(
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
                    ),
                ],
                h_expand=True,
                v_expand=True,
            )
        )

        self.add(body_container)

        if actions := self.notification.actions:
            self.add(
                Box(
                    row_spacing=4,
                    column_spacing=4,
                    spacing=4,
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
            )

        # destroy this widget once the notification is closed
        self.notification.connect(
            "closed",
            lambda *_: (
                parent.remove(self) if (parent := self.get_parent()) else None,  # type: ignore
                self.destroy(),
            ),
        )

        # automatically close the notification after the timeout period
        invoke_repeater(
            NOTIFICATION_TIMEOUT,
            lambda: self.notification.close("expired"),
            initial_call=False,
        )

        add_style_class_lazy(self, "shine")


class NotificationsView(Box):
    def __init__(self, **kwargs):
        super().__init__(visible=False, **kwargs)

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
            children=self.scrolled_window,
            h_expand=True,
            v_expand=True,
        )

        self.notifications = Notifications(
            on_notification_added=lambda _, nid: (
                notif := cast(Notification, self.notifications.notifications.get(nid)),
                self.viewport.add(nfi := NotificationItem(notif)),
                self.viewport.reorder_child(nfi, 0),
            ),
        )

        self.children = (
            Box(
                orientation="v",
                children=Box(
                    children=bake_corner(
                        orientation="top-right",
                        v_expand=True,
                        h_expand=True,
                    ),
                    size=NOTIFICATIONS_CORNERS_SIZE,
                ),
            ),
            Box(
                orientation="v",
                children=[
                    self.overall_container,
                    CenterBox(
                        orientation="h",
                        end_children=Box(
                            children=bake_corner(
                                orientation="top-right",
                                v_expand=True,
                                h_expand=True,
                            ),
                            size=NOTIFICATIONS_CORNERS_SIZE,
                            h_align="end",
                            v_align="end",
                        ),
                    ),
                ],
            ),
        )

        self.viewport.connect("add", self.on_children_change)
        self.viewport.connect("remove", self.on_children_change)
        self.connect("notify::visible", self.on_visiblity_change)

    def on_children_change(self, *_):
        # for fuck's sake don't repeat the same mistake
        # we have two containers to work with
        self.scrolled_window.animate_size(get_children_height_limit(self.viewport, 4))

        return self.hide() if not self.viewport.children else self.show()

    def on_visiblity_change(self, *_):
        self.viewport.remove_style_class("popped")

        if not self.get_visible():
            return

        return invoke_repeater(
            50,
            lambda: self.viewport.add_style_class("popped"),
            initial_call=False,
        )
