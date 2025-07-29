from fabric import Application
from components.notifications import NotificationsView
from components.palestine_flag import PalestineFlag
from components.system_status import SystemStatus
from components.power_button import PowerButton
from components.dashboard import Dashboard
from components.datetime import DateTime
from components.launcher import Launcher
from components.players import Players
from components.osd import OSD
from components.common import (
    logger,
    truncate,
    bake_corner,
    bulk_replace,
    monitor_file,
    get_relative_path,
    FormattedString,
    ActiveWindow,
    Workspaces,
    SystemTray,
    CenterBox,
    Language,
    Window,
    Overlay,
    Box,
)


class StatusBar(Window):
    def __init__(self, **kwargs):
        super().__init__(
            child=Box(
                orientation="v",
                children=[
                    CenterBox(
                        name="bar-inner",
                        start_children=Box(
                            name="start-container",
                            spacing=4,
                            orientation="h",
                            children=[
                                Workspaces(name="workspaces", spacing=4),
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
                ],
            ),
            visible=False,
            all_visible=False,
            **kwargs,
        )

        self.show_all()


@Application.action()
def apply_style(*args):
    logger.info("[Fabrika] Applying CSS...")

    app.set_stylesheet_from_file(
        get_relative_path("./style/config.css"),
        exposed_functions={
            "relative-path": lambda p: f"url('{get_relative_path(p[1:-1])}');"
        },
    )

    return


@Application.action()
def toggle_launcher():
    launcher.toggle()


if __name__ == "__main__":
    Window.toggle = lambda self: self.set_visible(not self.is_visible())

    bar = StatusBar(
        name="bar", layer="top", anchor="left bottom right", exclusivity="auto"
    )

    corners = Window(
        name="corners",
        layer="top",
        anchor="left bottom right",
        exclusivity="none",
        pass_through=True,
        child=CenterBox(
            start_children=bake_corner(orientation="bottom-left", size=16),
            end_children=bake_corner(orientation="bottom-right", size=16),
        ),
    )

    clock = Window(
        name="clock",
        anchor="top",
        layer="bottom",
        title="fabric-clock",
        margin="220px 0px 0px 0px",
        child=Dashboard(),
        pass_through=True,
        all_visible=True,
        exclusive=False,
    )

    launcher = (
        Window(
            name="fabric-drun",
            title="fabric-drun",
            anchor="top",
            margin="80px 0px 0px 0px",
            keyboard_mode="on-demand",
            child=Launcher(on_launched=lambda *_: launcher.toggle(), size=(460, -1)),
            visible=False,
            all_visible=False,
        )
        .build()
        .add_keybinding("Escape", lambda *_: launcher.toggle())
        .unwrap()
    )

    osd = Window(
        layer="top",
        anchor="bottom",
        margin="0px 0px 8px 0px",
        visible=False,
        all_visible=False,
    ).build(lambda self, _: self.add(OSD(window=self)))

    notifications = Window(
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

    app = Application(
        "fabrika-shell",
        bar,
        osd,
        clock,
        corners,
        launcher,
        notifications,
        open_inspector=False,
    )

    style_monitor = monitor_file(
        get_relative_path("./style/"), apply_style, initial_call=True
    )
    colors_monitor = monitor_file("~/.cache/wal/colors-widgets.css", apply_style)

    app.run()
