from components.common import Fabricator, Label, Box, logger
from gi.repository import GLib
import requests


class Weather(Box):
    CITY = "cairo"
    API_URL = f"https://wttr.in/{CITY}?format=%l+%z+%t+%f+%c+%C"

    def __init__(self, **kwargs):
        super().__init__(name="weather", orientation="h", **kwargs)

        self.weather_fabricator = Fabricator(
            default_value={
                "location": "",
                "time": "",
                "temp": "",
                "feels-like": "",
                "emoji": "",
                "description": "",
            },
            initial_poll=False,
            interval=1000 * 60 * 40,
            poll_from=self.do_fetch_weather,
            on_changed=lambda f, v: logger.debug(
                f"[Weather] fetched new weather data, {v}"
            ),
        )

        GLib.Thread.new("", self.weather_fabricator.start)

        self.children = Box(
            name="weather-inner",
            spacing=16,
            h_expand=True,
            v_expand=True,
            children=(
                Box(
                    orientation="v",
                    v_align="start",
                    h_align="start",
                    h_expand=True,
                    v_expand=True,
                    children=[
                        Box(
                            orientation="v",
                            v_align="start",
                            h_align="start",
                            children=[
                                Label(
                                    label="...",
                                    v_align="start",
                                    h_align="start",
                                    name="weather-location",
                                ).build(self.bind_weather_prop("location")),
                                Label(
                                    label="...",
                                    v_align="start",
                                    h_align="start",
                                    name="weather-time",
                                ).build(self.bind_weather_prop("time")),
                            ],
                        ),
                        Label(
                            label="...",
                            name="weather-description",
                            v_align="end",
                            h_align="start",
                            ellipsization="end",
                            justification="right",
                        ).build(self.bind_weather_prop("description")),
                    ],
                ),
                Box(
                    orientation="v",
                    h_expand=False,
                    v_expand=False,
                    h_align="center",
                    v_align="center",
                    children=[
                        Label(label="...", name="weather-temp").build(
                            self.bind_weather_prop("temp")
                        ),
                        Label(label="...", name="weather-feels-like").build(
                            lambda label, _: self.weather_fabricator.bind(
                                "value",
                                "label",
                                label,
                                transform_to=lambda _,
                                v: f"Feels Like {v["feels-like"]}",
                            )
                        ),
                    ],
                ),
                Label(
                    label="...", h_expand=False, v_expand=False, name="weather-icon"
                ).build(self.bind_weather_prop("emoji")),
            ),
        )

    def do_fetch_weather(self, *_):
        try:
            split_data = requests.get(url=self.API_URL).text.split()
        except Exception as e:
            split_data = [self.CITY, "unknown", "??", "??", "⁉️", str(e)]
        return {
            "location": split_data[0].upper(),
            "time": "Updated " + split_data[1],
            "temp": split_data[2].lstrip("+").rstrip("C"),
            "feels-like": split_data[3].lstrip("+").rstrip("C"),
            "emoji": split_data[4],
            "description": " ".join(split_data[5:]),
        }

    def bind_weather_prop(self, prop_name: str):
        return lambda obj, _: self.weather_fabricator.bind(
            "value",
            "label",
            obj,
            transform_to=lambda _, v: v[prop_name],
        )
