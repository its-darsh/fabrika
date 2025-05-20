"""
example configuration shows how to make a simple
desktop applications launcher, this example doesn't involve
any styling (except a couple of basic style properties)


the purpose of this configuration is to show to to use
the given utils and mainly how using lazy executors might
make the configuration way more faster than it's supposed to be
"""

import re
import urllib.parse
from collections.abc import Iterator
from .common import (
    os,
    mimetypes,
    fuzz,
    fuzzprocess,
    Signal,
    Box,
    Label,
    Button,
    Image,
    Entry,
    DesktopApp,
    AnimatedScrollable,
    invoke_repeater,
    get_desktop_applications,
    exec_shell_command_async,
    exec_shell_command,
    idle_add,
    remove_handler,
    get_children_height_limit,
    GLib,
    Service,
)

WALLPAPERS_PATH = os.path.expanduser("~/Pictures/Wallpapers/")
WALLPAPERS_THUMBNAILS_PATH = os.path.expanduser("~/Pictures/Wallpapers/.thumbnails")
WALLPAPERS_SETTER_COMMAND = os.path.expanduser("~/scripts/set_wallpaper.sh")
WALLPAPERS_THUMBNAILS_SIZE = 256

for path in (WALLPAPERS_PATH, WALLPAPERS_THUMBNAILS_PATH):
    if not os.path.exists(path):
        os.mkdir(path)


class CommandParser:
    def __init__(self, prefixes: tuple[str, ...], default_command: str = "a"):
        self.prefixes = prefixes
        self.default_command = default_command
        self.pattern = rf"^([{''.join(map(re.escape, self.prefixes))}])(\w*)\s*(.*)$"

    def parse(self, string: str) -> tuple[str, str]:
        match = re.match(self.pattern, string.strip())

        if not match:
            return self.default_command, string

        prefix, command, text = match.groups()

        if not command:
            return "wait", text

        return command, text.strip()


class Thread:
    def __init__(self, func, *data, name: str | None = None):
        self.func = func
        self.data = data
        self.stopped = False
        self.gthread = GLib.Thread.new(name, self.wrapper, *data)

    def stop(self):
        self.stopped = True

    def wrapper(self, *data):
        while not self.stopped:
            if not self.func(*data):
                break
        return self.gthread.exit()


class LauncherListsHandler(Service):
    # wingman class for handling queries

    @Signal
    def launched(self) -> None: ...

    @Signal
    def slot_ready(self, button: Button, mode: str) -> None: ...

    @Signal
    def start(self, mode: str) -> None: ...

    @Signal
    def done(self) -> None: ...

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._query_handler: int = 0
        self._query_thread: Thread | None = None
        self._desktop_apps = get_desktop_applications()

    def stop(self):
        if self._query_handler:
            remove_handler(self._query_handler)
            self._query_handler = 0
        if self._query_thread:
            self._query_thread.stop()
            self._query_thread = None
        return

    def query_applications(self, text: str) -> None:
        if not text:
            return self.done()
        self.start("applications")
        filtered_apps: Iterator[DesktopApp] = iter(
            app
            for app, _ in fuzzprocess.extract(
                text,
                self._desktop_apps,
                lambda a: a,
                lambda q, app: fuzz.WRatio(
                    q,
                    (app.display_name or ""),
                ),
            )
        )

        for app in filtered_apps:
            self.slot_ready(
                Button(
                    style_classes="app-slot",
                    child=Box(
                        orientation="h",
                        spacing=12,
                        children=[
                            Image(
                                pixbuf=app.get_icon_pixbuf(), h_align="start", size=32
                            ),
                            Box(
                                orientation="v",
                                children=[
                                    Label(
                                        label=app.display_name or "Unknown",
                                        v_align="start",
                                        h_align="start",
                                        style_classes="app-title",
                                    )
                                ],
                            ).build(
                                lambda box, _: app.description
                                and box.add(
                                    Label(
                                        label=app.description,
                                        max_chars_width=42,
                                        ellipsization="middle",
                                        justification="center",
                                        style_classes="app-description",
                                        v_align="start",
                                        h_align="start",
                                    )
                                )
                            ),
                        ],
                    ),
                    tooltip_text=app.description,
                    on_clicked=lambda *_, app=app: (app.launch(), self.launched()),
                ),
                "applications",
            )

        self.done()

    def query_wallpapers(self, text: str) -> None:
        self.start("wallpapers")
        filtered_walls: Iterator[str] = iter(
            file_full
            for file in os.listdir(WALLPAPERS_PATH)
            if (
                mt := mimetypes.guess_type((file_full := WALLPAPERS_PATH + "/" + file))[
                    0
                ]
            )
            and mt.startswith("image/")
        )

        self._query_handler = idle_add(
            self.bake_next_wallpaper_slot, filtered_walls, pin=True
        )

        return

    def post_wallpaper_cache_check(self, image_path: str, thumbnail_path: str):
        return self.slot_ready(
            Button(
                style_classes="app-slot wallpaper",
                child=Box(h_expand=True, v_expand=True)
                .build()
                .set_style(
                    f"background-image: url('file://{thumbnail_path}');", compile=False
                )
                .unwrap(),
                on_clicked=lambda *_: exec_shell_command_async(
                    f"{WALLPAPERS_SETTER_COMMAND} {image_path}"
                ),
            ),
            "wallpapers",
        )

    def bake_next_wallpaper_slot(self, iterator: Iterator[str]):
        if (image_path := next(iterator, None)) is None:
            idle_add(self.done)
            return False

        image_hash = (exec_shell_command("sha256sum " + image_path) or "").split()[0]
        thumbnail_path = WALLPAPERS_THUMBNAILS_PATH + "/" + image_hash + ".png"

        if not os.path.isfile(thumbnail_path):
            exec_shell_command(
                f"gdk-pixbuf-thumbnailer -s {WALLPAPERS_THUMBNAILS_SIZE} {image_path} {thumbnail_path}",
            )
        self.post_wallpaper_cache_check(image_path, thumbnail_path)
        return True

    def query_google(self, text: str) -> None: ...
    def query_link(self, link: str) -> None: ...


class Launcher(Box):
    @Signal
    def launched(self): ...

    def __init__(self, **kwargs):
        super().__init__(name="launcher", spacing=4, orientation="v", **kwargs)

        self._arranger_handler: int = 0
        self._all_apps = get_desktop_applications()

        self.viewport = Box(spacing=4, orientation="v")
        self.max_children = 4
        self.command_parser = CommandParser(("!", "?", "/"))
        self.launch_handler = LauncherListsHandler(
            on_start=lambda *_: self.header.add_style_class("shine"),
            on_done=lambda *_: (
                self.post_viewport_arrange(),
                self.header.remove_style_class("shine"),
            ),
            on_slot_ready=lambda _, b, m: self.viewport.add(b),
            on_launched=lambda *_: self.launched(),
        )

        self.header_icon = Image(icon_name="system-search-symbolic")
        self.header_entry = Entry(
            placeholder="Search...",
            style_classe="app-search-entry",
            h_expand=True,
            on_activate=self.on_entry_accept,
            on_changed=self.on_entry_changed,
        )

        self.header = Box(
            style_classes="app-search-header",
            spacing=8,
            orientation="h",
            children=[
                self.header_icon,
                self.header_entry,
            ],
        )

        self.scrolled_window = AnimatedScrollable(
            max_content_size=(280, 320),
            child=self.viewport,
            h_expand=True,
            v_expand=True,
            visible=False,  # no need to have it visible by default
        )

        self.children = self.header, self.scrolled_window

    def on_entry_changed(self, entry: Entry, *_):
        self.launch_handler.stop()
        for old_slot in self.viewport.children:
            self.viewport.remove(old_slot)
            old_slot.destroy()  # type: ignore

        query_data = self.command_parser.parse(entry.get_text())
        command, query_text = query_data

        match command:
            case "a":
                self.header_icon.set_from_icon_name("system-search-symbolic")
                self.launch_handler.query_applications(query_text)
                return
            case "w":
                self.header_icon.set_from_icon_name(
                    "preferences-desktop-wallpaper-symbolic"
                )
                self.launch_handler.query_wallpapers(query_text)
                return
            case "g":
                self.header_icon.set_from_icon_name("google")
                return
            case "l":
                self.header_icon.set_from_icon_name("external-link-symbolic")
                return

        self.header_icon.set_from_icon_name("new-command-alarm")

    def post_viewport_children(self):
        if (
            new_hight := get_children_height_limit(self.viewport, self.max_children)
        ) < 1:
            self.scrolled_window.animate_size(0)
            return False

        self.scrolled_window.show()
        self.scrolled_window.animate_size(new_hight)

        for i, slot in enumerate(self.viewport.children, start=1):
            if i > 8:
                break
            slot.set_style(f"animation-duration: {round(i * 300)}ms;")  # type: ignore
            slot.add_style_class("shine")  # type: ignore

    def post_viewport_arrange(self, *_):
        # keep it from overshooting on every keystroke
        if len(self.viewport.children) < 1:
            self.remove_style_class("overshoot")
        elif "overshoot" not in self.style_classes:
            invoke_repeater(
                50, lambda: self.add_style_class("overshoot"), initial_call=False
            )
        self.post_viewport_children()
        return False

    def on_entry_accept(self, entry: Entry, *_):
        # handle two-phase commands (e.g. web searching and links)
        query_data = self.command_parser.parse(entry.get_text())

        match query_data[0]:
            case "g":
                entry.set_text("")
                self.launched()
                return exec_shell_command_async(
                    f"xdg-open https://www.google.com/search?q={urllib.parse.quote(query_data[1])}"
                )

            case "l":
                entry.set_text("")
                self.launched()
                return exec_shell_command_async(
                    f"xdg-open {('https://' + query_data[1]) if not query_data[1].startswith("http") else query_data[1]}"
                )
        return
