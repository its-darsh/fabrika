from fabric import Application
from components.palestine_flag import PalestineFlag
from components.system_status import SystemStatus
from components.power_button import PowerButton
from components.dashboard import Dashboard
from components.datetime import DateTime
from components.players import Players
from components.common import (
    logger,
    truncate,
    bake_corner,
    bulk_replace,
    monitor_file,
    get_relative_path,
    invoke_repeater,
    remove_handler,
    FormattedString,
    ActiveWindow,
    SystemTray,
    CenterBox,
    Language,
    Overlay,
    Window,
    Box,
)


OSD_ENABLED: bool = True
PAGER_ENABLED: bool = True
LAUNCHER_ENABLED: bool = True
NOTIFICATIONS_ENABLED: bool = True
USE_EXPERIMENTAL_WORKSPACES: bool = True

if USE_EXPERIMENTAL_WORKSPACES:
    from components.snippets.workspaces import Workspaces as Workspaces
else:
    from fabric.hyprland.widgets import HyprlandWorkspaces as Workspaces


class StatusBar(Window):
    def __init__(self, **kwargs):
        super().__init__(
            child=Box(
                orientation="v",
                children=(
                    CenterBox(
                        name="bar-inner",
                        start_children=Box(
                            name="start-container",
                            spacing=4,
                            orientation="h",
                            children=[
                                (
                                    (
                                        (
                                            workspaces := Workspaces()
                                        ).get_inner_workspaces()
                                        if USE_EXPERIMENTAL_WORKSPACES
                                        else (
                                            workspaces := Workspaces(
                                                name="workspaces", spacing=4
                                            )
                                        )
                                    ).build(
                                        lambda wss: wss.connect(
                                            "workspace-activated",
                                            lambda: toggle_pager(),
                                        )
                                        if PAGER_ENABLED
                                        else None
                                    ),
                                    workspaces,
                                )[1],
                                Box(name="players-container", children=Players()),
                            ],
                        ),
                        center_children=Box(
                            name="center-container",
                            spacing=4,
                            orientation="h",
                            children=Overlay(
                                child=ActiveWindow(
                                    name="hyprland-window",
                                    style_classes="title",
                                    formatter=FormattedString(
                                        "{truncate(win_title or 'Desktop', 32)}",
                                        truncate=truncate,
                                    ),
                                ),
                                overlays=ActiveWindow(
                                    name="hyprland-window",
                                    style_classes="class",
                                    formatter=FormattedString(
                                        "{truncate(win_class or '', 32)}",
                                        truncate=truncate,
                                    ),
                                    h_align="start",
                                    v_align="end",
                                    h_expand=False,
                                    v_expand=False,
                                ),
                            ),
                        ),
                        end_children=Box(
                            name="end-container",
                            spacing=4,
                            orientation="h",
                            children=[
                                PalestineFlag(),
                                SystemStatus(),
                                SystemTray(spacing=4, name="system-tray"),
                                DateTime(name="date-time"),
                                Language(
                                    formatter=FormattedString(
                                        "{replace_lang(language)}",
                                        replace_lang=lambda lang: bulk_replace(
                                            lang,
                                            (r".*Eng.*", r".*Ar.*"),
                                            ("ENG", "ARA"),
                                            regex=True,
                                        ),
                                    ),
                                    name="hyprland-language",
                                ),
                                PowerButton(name="power-menu"),
                            ],
                        ),
                    ),
                ),
            ),
            all_visible=True,
            **kwargs,
        )


@Application.action()
def apply_style(*args):
    logger.info("[Fabrika] Applying CSS...")
    return app.set_stylesheet_from_file(
        get_relative_path("./style/config.css"),
        exposed_functions={
            "relative-path": lambda p: f"url('{get_relative_path(p[1:-1])}');"
        },
    )


@(Application.action() if LAUNCHER_ENABLED else lambda *_: ...)
def toggle_launcher():
    launcher.toggle()


@(Application.action() if OSD_ENABLED else lambda *_: ...)
def toggle_osd():
    osd.toggle()


last_pager_handler = None


@(Application.action() if PAGER_ENABLED else lambda *_: ...)
def toggle_pager(interval: int = 1000, auto_hide: bool = True):
    global last_pager_handler

    if last_pager_handler:
        remove_handler(last_pager_handler)
        last_pager_handler = None
    if not launcher.is_visible():
        pager.show()
    if auto_hide:
        last_pager_handler = invoke_repeater(interval, pager.hide, initial_call=False)
    return


bar = StatusBar(name="bar", layer="top", anchor="left bottom right", exclusivity="auto")

corners = Window(
    name="corners",
    layer="top",
    anchor="left bottom right",
    exclusivity="none",
    child=CenterBox(
        start_children=bake_corner(orientation="bottom-left", size=16),
        end_children=bake_corner(orientation="bottom-right", size=16),
    ),
    pass_through=True,
)

clock = Window(
    name="clock",
    title="fabric-clock",
    layer="bottom",
    anchor="top",
    margin="220px 0px 0px 0px",
    exclusivity="none",
    child=Dashboard(),
    pass_through=True,
    all_visible=True,
)

app = Application("fabrika-shell", corners, bar, clock)

if NOTIFICATIONS_ENABLED:
    from components.notifications import NotificationsView

    app.add_window(
        Window(
            layer="top",
            anchor="top right",
            visible=False,
            all_visible=False,
        ).build(
            lambda win, _: win.add(
                NotificationsView().build(
                    lambda notifs, _: notifs.bind("visible", "visible", win)
                )
            )
        )
    )

if LAUNCHER_ENABLED:
    from components.launcher import Launcher

    launcher = (
        Window(
            name="launcher-window",
            title="fabric-launcher",
            anchor="top",
            margin="80px 0px 0px 0px",
            keyboard_mode="on-demand",
            child=Launcher(on_launched=lambda: launcher.toggle(), size=(460, -1)),
            visible=False,
            all_visible=False,
        )
        .build()
        .add_keybinding("Escape", lambda *_: launcher.toggle())
        .unwrap()
    )

    app.add_window(launcher)

if PAGER_ENABLED:
    from components.pager import Pager

    pager = Window(
        name="pager-window",
        title="fabric-pager",
        anchor="top",
        margin="80px 0px 0px 0px",
        child=Pager(),
        visible=False,
        all_visible=False,
        pass_through=True,
    )
    app.add_window(pager)

if OSD_ENABLED:
    from components.osd import OSD

    osd = Window(
        layer="top",
        anchor="bottom",
        margin="0px 0px 8px 0px",
        title="fabric-osd",
        visible=False,
        all_visible=False,
    ).build(lambda win: win.add(OSD(window=win)))
    app.add_window(osd)

style_monitor = monitor_file(
    get_relative_path("./style/"), apply_style, initial_call=True
)
colors_monitor = monitor_file("~/.cache/wal/colors-widgets.css", apply_style)


if __name__ == "__main__":
    app.run()
