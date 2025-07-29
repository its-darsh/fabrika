# ruff: noqa: F401

import os
import gi
import math
import cairo
import fabric
import mimetypes
from typing import cast
from loguru import logger
from typing import Literal
from collections.abc import Iterable
from functools import reduce, partial
from thefuzz import fuzz, process as fuzzprocess

from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.audio.service import Audio
from fabric.widgets.fixed import Fixed
from fabric.widgets.stack import Stack
from fabric.widgets.entry import Entry
from fabric.widgets.image import Image
from fabric.widgets.shapes import Corner
from fabric.widgets.button import Button
from fabric.widgets.widget import Widget
from fabric.widgets.overlay import Overlay
from fabric.widgets.flowbox import FlowBox
from fabric.widgets.eventbox import EventBox
from fabric.widgets.revealer import Revealer
from fabric.widgets.centerbox import CenterBox
from fabric.system_tray.widgets import SystemTray

from components.services.animator import Animator
from fabric.notifications import Notification, Notifications
from fabric import Fabricator, Service, Signal, Property, Builder
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.hyprland.widgets import Workspaces, ActiveWindow, Language
from fabric.utils import (
    FormattedString,
    DesktopApp,
    get_desktop_applications,
    bulk_replace,
    monitor_file,
    invoke_repeater,
    get_relative_path,
    exec_shell_command,
    exec_shell_command_async,
    truncate,
    idle_add,
    remove_handler,
    bulk_connect,
)

gi.require_version("Playerctl", "2.0")
from gi.repository import Playerctl, Gtk, Gdk, Gio, GdkPixbuf, GLib  # noqa: E402


class CustomImage(Image):
    def do_render_rectangle(
        self, cr: cairo.Context, width: int, height: int, radius: int = 0
    ):
        cr.move_to(radius, 0)
        cr.line_to(width - radius, 0)
        cr.arc(width - radius, radius, radius, -(math.pi / 2), 0)
        cr.line_to(width, height - radius)
        cr.arc(width - radius, height - radius, radius, 0, (math.pi / 2))
        cr.line_to(radius, height)
        cr.arc(radius, height - radius, radius, (math.pi / 2), math.pi)
        cr.line_to(0, radius)
        cr.arc(radius, radius, radius, math.pi, (3 * (math.pi / 2)))
        cr.close_path()

    def do_draw(self, cr: cairo.Context):
        context = self.get_style_context()
        width, height = self.get_allocated_width(), self.get_allocated_height()
        cr.save()

        self.do_render_rectangle(
            cr,
            width,
            height,
            cast(int, context.get_property("border-radius", Gtk.StateFlags.NORMAL)),
        )
        cr.clip()
        Image.do_draw(self, cr)

        cr.restore()


bake_progress_bar = partial(
    CircularProgressBar,
    name="progress-bar",
    pie=True,
    size=24,
    start_angle=-90,
    end_angle=270,
)
bake_icon = partial(Image, style_classes="icon", icon_size=16)
bake_corner = partial(Corner, name="corner")
bake_spinner = partial(Box, name="spinner")


class SwipeButton(Button):
    @Signal
    def swipe(self, x: float, y: float, raw_x: int, raw_y: int) -> None: ...
    @Signal
    def swipe_end(self, x: float, y: float, raw_x: int, raw_y: int) -> None: ...

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add_events(("button-press", "button-release", "pointer-motion"))

        self._x_origin = None
        self._y_origin = None
        self._alloc = Gdk.Rectangle()

        self.connect("button-press-event", self.on_button_press)
        self.connect("motion-notify-event", self.on_motion_notify)
        self.connect("button-release-event", self.on_button_release)

    def do_size_allocate(self, allocation: Gdk.Rectangle):
        self._alloc = allocation
        Button.do_size_allocate(self, allocation)
        return

    def do_calculate_distance(
        self, x_origin: int, y_origin: int, x: int, y: int
    ) -> tuple[float, float, int, int]:
        xd = x - x_origin
        yd = y - y_origin
        normalized_xd = xd / float(self._alloc.width)  # type: ignore
        normalized_yd = yd / float(self._alloc.height)  # type: ignore
        return normalized_xd, normalized_yd, xd, yd

    def on_button_press(self, _, event):
        if event.button == 1:
            # NOTE: relative to self's coords
            self._x_origin, self._y_origin = event.x, event.y
        return True

    def on_motion_notify(self, _, event):
        if self._x_origin is None or self._y_origin is None:
            return False

        normalized_dx, normalized_dy, dx, dy = self.do_calculate_distance(
            self._x_origin, self._y_origin, event.x, event.y
        )
        self.swipe(normalized_dx, normalized_dy, dx, dy)
        return True

    def on_button_release(self, _, event):
        if self._x_origin is not None and self._y_origin is not None:
            self.swipe_end(
                *self.do_calculate_distance(
                    self._x_origin, self._y_origin, event.x, event.y
                )
            )

        self._x_origin = None
        self._y_origin = None
        return True


class AnimatedScrollable(ScrolledWindow):
    # would you like to have a good looking scrollable?
    # A. take it and lose on cpu usage
    # B. leave it and make it efficent

    # i take it
    def __init__(
        self,
        bezier_curve: tuple = (0.2, 1, 0.8, 1.0),
        duration: float = 0.3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._last_req = -1
        _, min_height = self.min_content_size
        _, max_height = self.max_content_size

        self.height_animator = Animator(
            bezier_curve=bezier_curve,
            duration=duration,
            tick_widget=self,
            min_value=min_height,
            max_value=max_height,
            notify_value=self.on_animator_change,
        )

    def on_animator_change(self, animator: Animator, *_):
        value = round(animator.value)
        if value < 1:
            self.hide()
        elif not self.is_visible():
            self.show()
        self.set_min_content_height(value)

    def do_animate(
        self,
        from_height: int = 0,
        to_height: int = -1,
    ):
        if to_height == -1:
            return
        self.height_animator.pause()
        self.height_animator.min_value = from_height
        self.height_animator.max_value = to_height
        self.height_animator.play()
        return

    def post_animation(self, animator: Animator, *_):
        if not self._last_req:
            return
        return self.hide()

    def animate_size(self, height: int = -1):
        self._last_req = height
        return self.do_animate(self.min_content_size[1], height)

    def do_get_preferred_height(self):
        value = self.height_animator.value
        value = 0 if value < 0 else value
        return value, value


def multiply_height_for_child(container: Box, child: Gtk.Widget, n_child: int) -> int:
    spacing: int = container.get_spacing()
    child_height: int = child.get_preferred_size().minimum_size.height  # type: ignore

    height: int = (spacing * (n_child - 1)) + (child_height * n_child)

    return height


def get_children_height_limit(viewport: Box, max_n_children: int) -> int:
    spacing: int = viewport.get_spacing()

    children = viewport.children
    children_len = len(viewport.children)

    if children_len < 1:
        return 0

    if children_len > max_n_children:
        children_len = max_n_children

    # calculate the new height
    # ( <the spacing for each child combined, last child doesn't have spacing> ) + ( <the total height of all the children> )
    return (spacing * (children_len - 1)) + reduce(
        lambda x, y: x + y,
        (
            children[i].get_preferred_size().minimum_size.height  # type: ignore
            for i in range(children_len)
        ),
    )


def add_style_class_lazy(widget: Widget, class_name: str | Iterable[str]) -> int:
    return invoke_repeater(
        50, lambda: widget.add_style_class(class_name), initial_call=False
    )
