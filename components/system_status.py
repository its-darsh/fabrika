import psutil
from components.volume import Volume
from components.common import (
    invoke_repeater,
    bake_progress_bar,
    Box,
    Label,
    Overlay,
)


class SystemStatus(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="status-container",
            spacing=4,
            orientation="h",
        )
        self.ram_progress_bar = bake_progress_bar(style_classes="ram")
        self.cpu_progress_bar = bake_progress_bar(style_classes="cpu")
        self.progress_bars_overlay = Overlay(
            child=self.ram_progress_bar,
            overlays=[
                self.cpu_progress_bar,
                Label("", style="margin: 0px 6px 0px 0px; font-size: 12px"),
            ],
        )

        self.children = self.progress_bars_overlay, Volume()
        invoke_repeater(1000, self.update_progress_bars, initial_call=True)

    def update_progress_bars(self):
        cpu_usage: float = psutil.cpu_percent()
        ram_usage: float = psutil.virtual_memory().percent
        self.cpu_progress_bar.value = cpu_usage / 100
        self.ram_progress_bar.value = ram_usage / 100
        self.progress_bars_overlay.set_tooltip_text(
            f"CPU: {cpu_usage}%\nRAM: {ram_usage}%"
        )
        return True
