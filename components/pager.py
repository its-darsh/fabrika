import json
from typing import TypedDict
from fabric.hyprland.widgets import get_hyprland_connection
from .common import (
    Gtk,
    Overlay,
    Image,
    Label,
    Fixed,
    Box,
    Corner,
    cast,
)


class PagerClient(TypedDict):
    title: str
    # class: str
    initialClass: str
    initialTitle: str
    at: list[int]
    size: list[int]
    address: str
    mapped: bool
    hidden: bool
    workspace: dict[str, int | str]
    floating: bool
    monitor: int
    pid: int
    xwayland: bool
    pinned: bool
    fullscreen: bool
    fullscreenMode: int
    fakeFullscreen: bool
    grouped: list[str]
    swallowing: str
    focusHistoryID: int


class PagerWorkspace(TypedDict):
    id: int
    size: list[int]
    clients: list[PagerClient]


class Pager(Box):
    def __init__(self, scale_ratio: float, icon_size: int = 28, **kwargs):
        super().__init__(orientation="h", **kwargs)
        self.radius = 32

        def bake_corner(**kwargs):
            return Corner(
                name="corner",
                size=self.radius,
                style_classes="pager-corner",
                **kwargs,
            )

        def bake_corner_box(**kwargs):
            return (
                Box(
                    # style=f"margin-right: {int(self.radius)}px",
                    style_classes="pager-corner-container",
                    children=bake_corner(**kwargs),
                )
                # .build()
                # .set_size_request(-1, self.radius)
                # .unwrap()
            )

        self.connection = get_hyprland_connection()
        self.scale_ratio = scale_ratio

        self.icon_theme = Gtk.IconTheme.get_default()
        self.icon_names = cast(list[str], self.icon_theme.list_icons())
        self.icon_size = icon_size

        self.clients_box = Box(
            name="pager-view",
            spacing=4,
            orientation="h",
        )

        self.children = self.clients_box

        # all aboard...
        if self.connection.ready:
            self.render(None)
        else:
            self.connection.connect("event::ready", self.render)

        for evnt in ("activewindow", "changefloatingmode"):
            self.connection.connect("event::" + evnt, self.render)

    def bake_window_icon(
        self,
        window_class: str,
        fallback_icon: str = "image-missing",
        **kwargs,
    ) -> Image:
        # no need to edit this
        def _baker(icon_name: str | None, **kwgs):
            try:
                pixbuf = self.icon_theme.load_icon(
                    icon_name or fallback_icon,
                    self.icon_size,
                    Gtk.IconLookupFlags.FORCE_SIZE,  # type: ignore
                )
            except Exception:
                pixbuf = self.icon_theme.load_icon(
                    fallback_icon,
                    self.icon_size,
                    Gtk.IconLookupFlags.FORCE_SIZE,  # type: ignore
                )
            return Image(
                pixbuf=pixbuf,
                size=self.icon_size,
                **(kwgs | kwargs),
            )

        return _baker(window_class.lower())

    def fetch_data(self):
        # note: Hyprland window's anchor is not a center point
        # (X, Y) = (0, 0)
        #            -> *______
        #               | aaaa |
        #               | ◕‿‿◕ |
        #               |______|

        workspaces_map: dict[int, PagerWorkspace] = {}
        clients: list[PagerClient] = json.loads(
            self.connection.send_command("j/clients").reply.decode()
        )
        for client in clients:
            client["size"] = [
                round(client["size"][0] / self.scale_ratio),
                round(client["size"][1] / self.scale_ratio),
            ]

            client["at"] = [
                round(client["at"][0] / self.scale_ratio),
                round(client["at"][1] / self.scale_ratio),
            ]

            client_workspace = cast(int, client["workspace"]["id"])

            workspace_root = workspaces_map.get(
                client_workspace,
                PagerWorkspace(
                    {
                        "id": client_workspace,
                        "size": self.get_workspace_size(client_workspace),
                        "clients": [],
                    }
                ),
            )

            workspace_root["clients"].append(client)

            workspaces_map[client_workspace] = workspace_root

        return workspaces_map

    def fetch_data_sorted(self) -> dict[int, PagerWorkspace]:
        unsorted_data = self.fetch_data()
        sorted_data: dict[int, PagerWorkspace] = {}
        for ws_id in sorted(unsorted_data):
            sorted_data[ws_id] = unsorted_data[ws_id]
        return sorted_data

    def get_active_workspace(self) -> int:
        return json.loads(
            self.connection.send_command("j/activeworkspace").reply.decode()
        )["id"]

    def get_workspace_size(self, workspace_id: int) -> list[int]:
        workspace_monitor = [
            m
            for m in json.loads(
                self.connection.send_command("j/monitors").reply.decode()
            )
            if m["name"]
            == [
                ws
                for ws in json.loads(
                    self.connection.send_command("j/workspaces").reply.decode()
                )
                if int(ws["id"]) == workspace_id
            ][0]["monitor"]
        ][0]

        return [
            round(workspace_monitor["width"] / self.scale_ratio),
            round(workspace_monitor["height"] / self.scale_ratio),
        ]

    def render(self, *_):
        if not self.is_visible():
            return

        self.clients_box.children = []
        for workspace_id, workspace in self.fetch_data_sorted().items():
            workspace_label = Label(
                label=str(workspace_id),
                h_align="center",
                v_align="center",
                h_expand=True,
                v_expand=True,
                style_classes="pager-client-label",
            )
            workspace_background = Box(
                children=workspace_label,
                size=workspace["size"],
                style_classes="pager-workspace",
            )
            workspace_overlay = Overlay(child=workspace_background)
            if self.get_active_workspace() == workspace_id:
                workspace_background.add_style_class("active")
                workspace_label.add_style_class("active")

            for client in workspace["clients"]:
                client_box = Box(
                    children=self.bake_window_icon(
                        client["initialClass"],
                        h_align="center",
                        v_align="center",
                        h_expand=True,
                        v_expand=True,
                    ),
                    tooltip_text=client["title"],
                    size=client["size"],
                    style_classes="pager-client",
                )

                fixed = Fixed(size=workspace["size"])
                fixed.put(client_box, *client["at"])
                workspace_overlay.add_overlay(fixed)

            self.clients_box.add(
                Box(orientation="h", children=workspace_overlay),
            )
