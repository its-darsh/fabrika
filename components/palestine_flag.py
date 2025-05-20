from .common import Box, partial


PalestineFlag = partial(
    Box,
    style_classes="palestine-flag",
    tooltip_markup=(
        "<span font_weight='bold' foreground='red' size='x-large'>"
        "STOP GENOCIDE!"
        "</span>"
    ),
    size=(48, -1),
)
