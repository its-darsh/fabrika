from fabric.audio import Audio
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.scale import Scale, ScaleMark
from fabric.widgets.wayland import WaylandWindow as Window
from components.services.animator import Animator
from fabric.utils import invoke_repeater, remove_handler


class AnimatedScale(Scale):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.animator = (
            Animator(
                bezier_curve=(0.34, 1.56, 0.64, 1.0),
                duration=0.8,
                min_value=self.min_value,
                max_value=self.value,
                tick_widget=self,
                notify_value=lambda p, *_: self.set_value(p.value),
            )
            .build()
            .play()
            .unwrap()
        )

    def animate_value(self, value: float):
        self.animator.pause()
        self.animator.min_value = self.value
        self.animator.max_value = value
        self.animator.play()
        return


class AudioOSDContainer(Box):
    def __init__(self, window: Window, **kwargs):
        super().__init__(**kwargs, spacing=12, name="osd-container")
        self.last_handler: int = 0
        self.window = window
        self.audio = Audio(controller_name="fabric osd")
        self.icon = Image(icon_name="audio-volume-medium-symbolic", icon_size=26)

        self.scale = AnimatedScale(
            marks=(ScaleMark(value=i) for i in range(1, 100, 10)),
            value=70,
            min_value=0,
            max_value=100,
            inverted=False,
            increments=(1, 1),
            orientation=self.get_orientation(),
            on_state_flags_changed=lambda sc, *_: (
                self.unfocus()
                if not (sc.get_state_flags() & 2)  # type: ignore
                else None,
            ),
            on_value_changed=lambda *_: self.audio.speaker
            and (
                self.is_hovered() and self.audio.speaker.set_volume(self.scale.value),
                self.icon.set_from_icon_name(
                    "audio-volume-high-symbolic"
                    if self.audio.speaker.volume >= 80
                    else "audio-volume-low-symbolic"
                    if self.audio.speaker.volume < 50
                    else "audio-volume-medium-symbolic",
                    26,
                ),
            ),
        )

        self.audio.connect(
            "notify::speaker",
            lambda *_: self.audio.speaker
            and self.audio.speaker.build(
                lambda speaker, builder: (
                    speaker.connect(
                        "notify::volume",
                        lambda *_: not self.is_hovered()
                        and (vol := round(self.audio.speaker.volume))
                        and (self.update(), self.scale.animate_value(vol)),
                    ),
                    self.scale.animate_value(speaker.volume),
                )
            ),
        )

        self.children = self.icon, self.scale

    def remove_last_handler(self):
        if self.last_handler:
            remove_handler(self.last_handler)
            self.last_handler = 0
        return

    def update(self, *_):
        self.window.show()
        self.focus()
        self.remove_last_handler()
        self.last_handler = invoke_repeater(1700, self.unfocus, initial_call=False)
        return

    def focus(self, *_):
        self.style_classes = "focused"
        return

    def unfocus(self, *_):
        self.style_classes = ()
        self.remove_last_handler()
        self.last_handler = invoke_repeater(1700, self.unpop, initial_call=False)
        return False

    def unpop(self, *_):
        if not self.is_hovered():
            self.window.hide()
        return False


class OSD(Box):
    def __init__(self, window: Window, **kwargs):
        super().__init__(orientation="h", **kwargs)

        self.items_container = AudioOSDContainer(orientation="h", window=window)

        self.osd_view_window = Box(name="osd", spacing=8, children=self.items_container)

        self.children = self.osd_view_window
