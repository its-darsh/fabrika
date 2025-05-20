from .common import (
    Box,
    Audio,
    Image,
    Overlay,
    EventBox,
    bake_progress_bar,
)


class Volume(Box):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress_bar = bake_progress_bar(style_classes="volume")

        self.volume_icon = Image(icon_name="audio-volume-high-symbolic", icon_size=12)
        self.audio = Audio(notify_speaker=self.on_speaker_changed)

        self.children = EventBox(
            events="scroll",
            child=Overlay(
                child=self.progress_bar,
                overlays=self.volume_icon,
            ),
            on_scroll_event=self.on_scroll,
        )

    def on_scroll(self, _, event):
        match event.direction:
            case 0:
                self.audio.speaker.volume += 10
            case 1:
                self.audio.speaker.volume -= 10
        return

    def set_volume_icon(self, volume: float):
        return self.volume_icon.set_from_icon_name(
            "audio-volume-"
            + (
                "high"
                if volume >= 0.70
                else "medium"
                if volume >= 0.40
                else "low"
                if volume >= 0.1
                else "muted"
            )
            + "-symbolic",
            12,
        )

    def on_speaker_changed(self, *_):
        if not self.audio.speaker:
            return
        volume = self.audio.speaker.volume / 100
        self.progress_bar.value = volume
        self.set_volume_icon(volume)
        return self.audio.speaker.bind(
            "volume",
            "value",
            self.progress_bar,
            lambda _, v: (
                (vol := v / 100),
                self.set_volume_icon(vol),
            )[0],
        )
