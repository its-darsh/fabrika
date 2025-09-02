from .common import (
    Gtk,
    Gdk,
    Playerctl,
    Fabricator,
    Signal,
    SwipeButton,
    Overlay,
    Label,
    Stack,
    Box,
    Builder,
    bake_progress_bar,
    bake_icon,
    idle_add,
    cast,
)


class Player(SwipeButton):
    @Signal
    def focus_request(self): ...

    def __init__(self, player: Playerctl.Player, **kwargs):
        super().__init__(name="player", **kwargs)
        self._player = player
        self._player_handlers: list[int] = []

        self._player.props.player_name

        self._title_label = Label(
            max_chars_width=20,
            ellipsization="end",
            justification="center",
            h_align="start",
            v_align="start",
            style_classes="player-title",
        )

        self._artist_label = Label(
            max_chars_width=20,
            ellipsization="end",
            justification="center",
            h_align="start",
            v_align="start",
            style_classes="player-artist",
        )

        self._metadata_box = Box(
            style_classes="metadata",
            orientation="v",
            children=(self._title_label, self._artist_label),
        )

        self._playback_icon = bake_icon()
        self._next_icon = bake_icon(
            icon_name="media-skip-forward-symbolic",
            style_classes="icon player-control next",
            style="opacity: 0",
            h_align="end",
        )
        self._prev_icon = bake_icon(
            icon_name="media-skip-backward-symbolic",
            style_classes="icon player-control previous",
            style="opacity: 0",
            h_align="start",
        )

        self._progress_bar = bake_progress_bar(value=0.0, child=self._playback_icon)
        self.update_playback_status()

        Fabricator(self.get_player_percentage, 1000).bind(
            "value", "value", self._progress_bar
        )

        self._player.bind(  # type: ignore
            "metadata",
            "tooltip-text",
            self,
            transform_to=lambda _,
            v: f"{self._player.get_title() or 'Unknown'} - {self._player.get_artist() or 'Unknown'}"
            or "Nothing Playing",
        )

        self._player.bind(  # type: ignore
            "metadata",
            "label",
            self._title_label,
            transform_to=lambda _, v: (self._player.get_title() or "Unknown"),
        )

        self._player.bind(  # type: ignore
            "metadata",
            "label",
            self._artist_label,
            transform_to=lambda _, v: (self._player.get_artist() or "Unknown"),
        )

        self._player.notify("metadata")  # type: ignore
        self._player_handlers.extend(
            (
                self._player.connect(
                    "metadata",
                    lambda *_: self._player.notify("metadata"),  # type: ignore
                ),
                self._player.connect("exit", lambda *_: self.close()),
                self._player.connect("playback-status", self.update_playback_status),
            )
        )

        self._controls_menu = Gtk.Menu()
        self._controls_menu.append(
            Builder(
                Gtk.MenuItem(
                    child=Box(  # type: ignore
                        orientation="h",
                        children=(
                            bake_icon(
                                icon_name="media-playlist-repeat-symbolic", icon_size=24
                            ),
                            Label("???").build(
                                lambda lbl, _: (
                                    (
                                        update := lambda *_: lbl.set_label(
                                            "Track"
                                            if (loopstat := player.props.loop_status)
                                            is Playerctl.LoopStatus.TRACK
                                            else "Playlist"
                                            if loopstat is Playerctl.LoopStatus.PLAYLIST
                                            else "None"
                                        )
                                    ),
                                    update(),
                                    player.connect("loop-status", update),
                                )
                            ),
                        ),
                    )
                )
            )
            .connect(
                "button-press-event",
                lambda *_: player.set_loop_status(
                    Playerctl.LoopStatus.NONE
                    if (loopstat := player.props.loop_status)
                    is Playerctl.LoopStatus.TRACK
                    else Playerctl.LoopStatus.PLAYLIST
                    if loopstat is Playerctl.LoopStatus.NONE
                    else Playerctl.LoopStatus.TRACK
                ),
            )
            .unwrap()
        )

        self.children = Box(
            spacing=8,
            orientation="h",
            children=[
                self._progress_bar,
                Overlay(
                    child=self._metadata_box,
                    overlays=[
                        bake_icon(
                            style_classes="player-icon",
                            icon_name=self._player.props.player_name,  # type: ignore
                            h_align="end",
                            v_align="end",
                            icon_size=12,
                        ),
                        self._prev_icon,
                        self._next_icon,
                    ],
                    h_expand=True,
                ).build(
                    lambda ov, _: [
                        ov.set_overlay_pass_through(w, True) for w in ov.overlays
                    ]
                ),
            ],
        )

        idle_add(
            lambda: self.focus_request()
            if self._player.get_property("playback-status")
            is Playerctl.PlaybackStatus.PLAYING
            else None
        )

        # i'm a button. after all
        self.connect(
            "state-flags-changed",
            lambda btn, *_: (
                btn.set_cursor("pointer")
                if btn.get_state_flags() & 2  # type: ignore
                else btn.set_cursor("default"),
            ),
        )
        self.connect("swipe", self.on_swipe)
        self.connect("swipe-end", self.on_swipe_end)

    def on_button_release(self, _, event):
        if event.button == 3:
            self._controls_menu.show_all()
            return self._controls_menu.popup_at_widget(
                self, Gdk.Gravity.NORTH, Gdk.Gravity.SOUTH, event
            )
        return super().on_button_release(_, event)

    def on_swipe(self, __, dx: float, dy: float, *_):
        # TODO: simplify logic
        self.set_cursor("grab")
        self.set_style("transition: unset;")
        self._metadata_box.set_style(f"opacity: {1.0 - round(abs(dx) * 2.0, 3)};")
        if dx > 0:
            self._next_icon.set_style("opacity: 0;")
            self._prev_icon.set_style(f"opacity: {round(dx, 3)};")
            self.set_style(f"margin-left: {round(dx * 50)}px;")
            return
        self._prev_icon.set_style("opacity: 0;")
        self._next_icon.set_style(f"opacity: {round(abs(dx), 3)};")
        return

    def on_swipe_end(self, __, dx: float, dy: float, *_):
        self.set_cursor("default")
        self._prev_icon.set_style("opacity: 0;")
        self._next_icon.set_style("opacity: 0;")
        self._metadata_box.set_style("opacity: 1;")
        self.set_style("transition: margin linear 0.3s; margin-left: inherit;")

        if dx > 0.5:
            self._player.previous()
            return

        if dx < -0.5:
            self._player.next()
            return

        if abs(dx) > 0.1:  # probably a miss-click
            return

        return self._player.play_pause()

    def update_playback_status(self, *_):
        status = cast(Playerctl.PlaybackStatus, self._player.props.playback_status)  # type: ignore
        match status:
            case Playerctl.PlaybackStatus.PLAYING:
                status_icon = "pause"
                self.focus_request()
            case Playerctl.PlaybackStatus.PAUSED:
                status_icon = "start"
            case _:
                status_icon = "stop"

        return self._playback_icon.set_from_icon_name(
            f"media-playback-{status_icon}-symbolic", 16
        )

    def get_player_length(self) -> int:
        return cast(
            int,
            self._player.get_property("metadata").unpack().get("mpris:length"),  # type: ignore
        )

    def get_player_percentage(self, f) -> float:
        if not self._player.props.can_seek:  # type: ignore
            return 0.0
        try:
            return self._player.get_position() / self.get_player_length()
        except Exception:
            return 0.0

    def close(self):
        # cleanup and destroy
        for id in self._player_handlers:
            self._player.handler_disconnect(id)  # type: ignore
        return self.destroy()


class Players(Stack):
    def __init__(self, **kwargs):
        super().__init__(transition_type="slide-up-down", **kwargs)
        self.add_events("scroll")  # type: ignore
        self._visible_child_index = 0

        self._player_manager = Playerctl.PlayerManager.new()
        self._players: list[Player] = []

        self._player_manager.connect("name-appeared", self.on_player_appeared)
        self._player_manager.connect("player-vanished", self.handle_player_vanished)
        self.connect("scroll-event", self.on_scroll_handler)

        self.initialize_players()

    def initialize_players(self):
        for player_name in self._player_manager.props.player_names:  # type: ignore
            self.on_player_appeared(None, player_name)
        return

    def on_player_appeared(self, _, player_name: Playerctl.PlayerName):
        player_widget = Player(Playerctl.Player.new_from_name(player_name))

        self._players.append(player_widget)
        self.add_named(player_widget, player_name.name)  # type: ignore

        player_widget.focus_request.connect(
            lambda *_: (
                self._players.remove(player_widget),
                self._players.insert(0, player_widget),
                self.set_visible_child(player_widget),
            )
        )

        if self._players:
            self.set_visible_child(self._players[0])

        return

    def handle_player_vanished(self, _, player: Playerctl.Player):
        player_widget = cast(
            Player | None,
            self.get_child_by_name(player.props.player_name),  # type: ignore
        )
        if not player_widget:
            return

        self._players.remove(player_widget)
        self.remove(player_widget)

        return player_widget.close()

    def on_scroll_handler(self, _, event):
        if not self.children:
            return

        # next child in the list or the first child if it's the last already (cycle)
        self._visible_child_index = (
            self._visible_child_index + (-1 if event.direction == 0 else 1)
        ) % len(self.children)

        return self.set_visible_child(self.children[self._visible_child_index])
