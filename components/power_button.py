from .common import (
    exec_shell_command_async,
    bulk_connect,
    bake_icon,
    partial,
    Signal,
    Widget,
    Revealer,
    Button,
    Stack,
    Label,
    Box,
)


class ScrollButton(Button):
    @Signal
    def entry_dispatched(self, entry_name: str): ...

    def __init__(
        self, entries: dict[str, tuple[Widget | str | None, Widget | None]], **kwargs
    ):
        super().__init__(**kwargs)
        self._locked = True
        self._icons_stack = Stack(transition_type="slide-up-down")
        self._labels_stack = Stack(transition_type="slide-up-down")
        self._labels_lock_stack = Stack(transition_type="slide-up-down")

        self._entries: list[str] = []
        self._current_index: int = -1

        for child, name in (
            (Label(label="Locked"), "locked"),
            (self._labels_stack, "labels"),
        ):
            self._labels_lock_stack.add_named(child, name)

        self._revealer = Revealer(
            transition_type="slide-right", child=self._labels_lock_stack
        )

        self._icons_stack.set_child_visible(True)

        self.children = Box(
            orientation="h", children=(self._icons_stack, self._revealer)
        )

        self.add_events("scroll")
        bulk_connect(
            self,
            {
                "enter-notify-event": lambda *_: self._revealer.set_reveal_child(True),
                "leave-notify-event": lambda *_: self._locked
                and self._revealer.set_reveal_child(False),
                "button-press-event": self.on_button_press_handler,
                "button-release-event": self.on_button_press_handler,
                "scroll-event": self.on_scroll_handler,
            },
        )

        # all aboard...
        for name, args in entries.items():
            self.add_entry(name, *args)

    def on_scroll_handler(self, *_):
        return self.do_cycle_next()  # TODO: implement up and down scrolling

    def on_button_press_handler(self, _, event):
        pressed = int(event.type) == 4
        if pressed and not event.button == 3 and not self._locked:
            return self.entry_dispatched(self._entries[self._current_index])

        self._locked = not pressed
        self._labels_lock_stack.set_visible_child_name(
            "locked" if self._locked else "labels"
        )
        return

    def add_entry(
        self, name: str, label: Widget | str | None = None, icon: Widget | None = None
    ):
        if not name or name in self._entries:
            raise ValueError

        self._entries.append(name)
        self._labels_stack.add_named(
            label if isinstance(label, Widget) else Label(label=label), name
        )
        self._icons_stack.add_named(icon or Box(), name)

    def do_check_invalid_index(self, index: int) -> bool:
        return (index < 0) or (index > (len(self._entries) - 1))

    def do_cycle_next(self):
        self._current_index = self._current_index + 1
        if self.do_check_invalid_index(self._current_index):
            self._current_index = 0  # reset tags

        return self.do_update_current_entry()

    def do_cycle_prev(self):
        self._current_index = self._current_index - 1
        if self.do_check_invalid_index(self._current_index):
            self._current_index = len(self._entries) - 1

        return self.do_update_current_entry()

    def do_update_current_entry(self):
        button_name = self._entries[self._current_index]
        self._icons_stack.set_visible_child_name(button_name)
        self._labels_stack.set_visible_child_name(button_name)
        return True


PowerButton = partial(
    ScrollButton,
    entries={
        "shutdown": (
            "Shutdown",
            bake_icon(name="power-icon", icon_name="system-shutdown-symbolic"),
        ),
        "reboot": (
            "Reboot",
            bake_icon(name="power-icon", icon_name="system-reboot-symbolic"),
        ),
    },
    on_entry_dispatched=lambda btn, entry: exec_shell_command_async(
        f"""
        notify-send "Mayday, Mayday!" "I should be doing the action \\"{entry}\\". However, I'm not programmed enough to do such thing"
        """
    ),
)
