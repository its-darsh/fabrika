from playsound import playsound
import multiprocessing
from .common import (
    Fabricator,
    partial,
    Overlay,
    Widget,
    Label,
    Box,
    Gtk,
    Gdk,
    Animator,
    cubic_bezier,
    get_relative_path,
)
from fabric.widgets.datetime import DateTime as BasicDateTime


ALARM_SOUND_PATH = get_relative_path("./audio/alarm.mp3")


class TimerProgress(Gtk.ProgressBar, Widget):
    def __init__(self, interval: float, **kwargs):
        Gtk.ProgressBar.__init__(self)  # type: ignore
        Widget.__init__(self, **kwargs)

        self._animator = Animator(
            duration=interval,
            timing_function=partial(cubic_bezier, 0, 0, 1, 1),
            tick_widget=self,
            on_finished=self.on_timer_done,
            # TODO: add a way of identifing time left before dingy dongs
            notify_value=lambda a, *_: self.set_fraction(a.value),
        )

        self._animator.play()

    @staticmethod  # BLOCKS MAIN THREAD. RUN IN A THREAD.
    def do_play_alarm_sound():
        for _ in range(16):
            playsound(ALARM_SOUND_PATH, block=True)

    def on_timer_done(self, *_):
        self._animator.pause()

        audio = multiprocessing.get_context("spawn").Process(
            target=self.do_play_alarm_sound
        )
        audio.start()

        def on_notification_interaction(*_):
            audio.terminate()
            self.hide()  # type: ignore
            if p := self.get_parent():
                p.remove(self)  # type: ignore
            return self.destroy()  # type: ignore

        Fabricator(
            stream=True,
            poll_from="dunstify 'Timer' --action='stop,Stop'",  # TODO: move to notify-send
            notify_value=on_notification_interaction,
        )


class DateTime(BasicDateTime):
    def __init__(self, **kwargs):
        self._label = Label()

        super().__init__(**kwargs)

        self._menu = Gtk.Menu()
        self._timers_container = Box(orientation="v", v_align="end", h_expand=True)
        self._container = Overlay(child=self._label, overlays=self._timers_container)

        for label, interval in {
            # "2 Seconds": 2,  # for testing...
            "1 Minute": 60,
            "5 Minutes": 5 * 60,
            "10 Minutes": 10 * 60,
            "15 Minutes": 15 * 60,
            "30 Minutes": 30 * 60,
            "1 Hour": 60 * 60,
            "2 Hours": 2 * 60 * 60,
        }.items():
            menu_item = Gtk.MenuItem.new_with_label(label)
            menu_item.connect("activate", self.do_start_timer, interval)

            self._menu.append(menu_item)

        self.add(self._container)

    def set_label(self, label: str):
        return self._label.set_label(label)

    def get_label(self) -> str:
        return self._label.get_label()

    def do_start_timer(self, menu_item: Gtk.MenuItem, interval: int):
        progress = TimerProgress(
            interval=interval,
            h_expand=True,
            v_align="end",
        )
        progress.show_all()  # type: ignore
        return self._timers_container.add(progress)  # type: ignore

    def do_handle_press(self, _, event, *args):
        match event.button:
            case 1:  # left click
                self.do_cycle_next()
            case 3:  # right click
                self._menu.show_all()  # type: ignore
                self._menu.popup_at_widget(
                    self, Gdk.Gravity.NORTH, Gdk.Gravity.SOUTH, event
                )
        return
