from fabric.widgets.datetime import DateTime
from .common import Box, Label, exec_shell_command
from .weather import Weather


class Dashboard(Box):
    def __init__(self, **kwargs):
        super().__init__(
            orientation="v",
            name="clock-widget",
            children=[
                DateTime(name="date", formatters="%A. %d %B", interval=10000),
                DateTime(name="time", formatters="%I:%M"),
                Label(
                    label=exec_shell_command("hyprctl splash")
                    or "hyprctl is not as bad as you might think. it's just slightly worse."
                ),
                Weather(),
            ],
            **kwargs,
        )
