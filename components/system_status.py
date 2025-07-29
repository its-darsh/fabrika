import psutil
from components.volume import Volume
from components.common import (
    invoke_repeater,
    bake_progress_bar,
    bake_icon,
    Box,
)


class SystemStatus(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="status-container",
            spacing=4,
            orientation="h",
        )
        self.cpu_progress_bar = bake_progress_bar(
            style_classes="cpu",
            child=bake_icon(icon_name="cpu-symbolic", icon_size=12),
        )
        self.ram_progress_bar = bake_progress_bar(
            style_classes="ram", child=self.cpu_progress_bar
        )

        self.children = self.ram_progress_bar, Volume()
        invoke_repeater(1000, self.update_progress_bars, initial_call=True)

    def update_progress_bars(self):
        cpu_usage: float = psutil.cpu_percent()
        ram_usage: float = psutil.virtual_memory().percent
        self.cpu_progress_bar.value = cpu_usage / 100
        self.ram_progress_bar.value = ram_usage / 100
        self.ram_progress_bar.set_tooltip_text(f"CPU: {cpu_usage}%\nRAM: {ram_usage}%")
        return True
