"""
This is a stand-alone snippet, for updates see its corresponding thread in Fabric's Discord server.

This file is AGPL licensed.
"""

from typing import cast
from fabric import Service, Signal, Property
from gi.repository import GLib, Gtk


class Animator(Service):
    @Signal
    def finished(self) -> None: ...

    @Property(tuple[float, float, float, float], "read-write")
    def bezier_curve(self) -> tuple[float, float, float, float]:
        return self._bezier_curve

    @bezier_curve.setter
    def bezier_curve(self, value: tuple[float, float, float, float]):
        self._bezier_curve = value
        return

    @Property(float, "read-write")
    def value(self):
        return self._value

    @value.setter
    def value(self, value: float):
        self._value = value
        return

    @Property(float, "read-write")
    def max_value(self):
        return self._max_value

    @max_value.setter
    def max_value(self, value: float):
        self._max_value = value
        return

    @Property(float, "read-write")
    def min_value(self):
        return self._min_value

    @min_value.setter
    def min_value(self, value: float):
        self._min_value = value
        return

    @Property(bool, "read-write", default_value=False)
    def playing(self):
        return self._playing

    @playing.setter
    def playing(self, value: bool):
        self._playing = value
        return

    @Property(bool, "read-write", default_value=False)
    def repeat(self):
        return self._repeat

    @Property(bool, "read-write", default_value=False)
    def reverse(self):
        return self._reverse

    @reverse.setter
    def reverse(self, value: bool):
        self._reverse = value
        return

    @repeat.setter
    def repeat(self, value: bool):
        self._repeat = value
        return

    def __init__(
        self,
        bezier_curve: tuple[float, float, float, float],
        duration: float,
        min_value: float = 0.0,
        max_value: float = 1.0,
        repeat: bool = False,
        reverse: bool = False,
        tick_widget: Gtk.Widget | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._bezier_curve = (1, 0, 1, 1)
        self._duration = 5
        self._value = 0.0
        self._min_value = 0.0
        self._max_value = 1.0
        self._repeat = False
        self._reverse = False

        self.bezier_curve = bezier_curve
        self.duration = duration
        self.value = min_value
        self.min_value = min_value
        self.max_value = max_value
        self.repeat = repeat
        self.reverse = reverse

        self.playing = False
        self._start_time = None
        self._tick_handler = None
        self._timeline_pos = 0
        self._tick_widget = tick_widget

    def do_get_time_now(self):
        return GLib.get_monotonic_time() / 1_000_000

    def do_lerp(self, start: float, end: float, time: float) -> float:
        return start + (end - start) * time

    def do_interpolate_cubic_bezier(self, time: float) -> float:
        y_points = (0, self.bezier_curve[1], self.bezier_curve[3], 1)
        return (
            (1 - time) ** 3 * y_points[0]
            + 3 * (1 - time) ** 2 * time * y_points[1]
            + 3 * (1 - time) * time**2 * y_points[2]
            + time**3 * y_points[3]
        )

    def do_ease(self, time: float) -> float:
        return self.do_lerp(
            self.min_value, self.max_value, self.do_interpolate_cubic_bezier(time)
        )

    def do_update_value(self, delta_time: float):
        if not self.playing:
            return

        elapsed_time = delta_time - cast(float, self._start_time)
        progress = elapsed_time / self.duration

        if self.reverse:
            self._timeline_pos = max(0, 1 - progress)
        else:
            self._timeline_pos = min(1, progress)

        self.value = self.do_ease(self._timeline_pos)

        if (self.reverse and self._timeline_pos <= 0) or (
            not self.reverse and self._timeline_pos >= 1
        ):
            if not self.repeat:
                self.value = self.min_value if self.reverse else self.max_value
                self.finished()
                self.pause()
                return
            self.reverse = not self.reverse
            self._start_time = delta_time
            self._timeline_pos = 1 if self.reverse else 0
        return

    def do_handle_tick(self, *_):
        current_time = self.do_get_time_now()
        self.do_update_value(current_time)
        return True

    def do_remove_tick_handlers(self):
        if self._tick_handler:
            if self._tick_widget:
                self._tick_widget.remove_tick_callback(self._tick_handler)
            else:
                GLib.source_remove(self._tick_handler)
        self._tick_handler = None
        return

    def play(self):
        if self.playing:
            return

        self._start_time = self.do_get_time_now()

        if not self._tick_handler:
            if self._tick_widget:
                self._tick_handler = self._tick_widget.add_tick_callback(
                    self.do_handle_tick
                )
            else:
                self._tick_handler = GLib.timeout_add(16, self.do_handle_tick)

        self.playing = True
        return

    def pause(self):
        self.playing = False
        return self.do_remove_tick_handlers()

    def stop(self):
        if not self._tick_handler:
            self._timeline_pos = 0
            self.playing = False
            return
        return self.do_remove_tick_handlers()
