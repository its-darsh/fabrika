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
from fabric import Fabricator, Service, Signal, Property, Builder

from fabric.widgets.box import Box
from fabric.widgets.label import Label
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

from components.snippets.clippingbox import ClippingBox
from components.snippets.swipebutton import SwipeButton
from components.snippets.animator import Animator, cubic_bezier, lerp
from components.snippets.animatedscrollable import AnimatedScrollable
from components.snippets.utils import (
    multiply_height_for_child,
    get_children_height_limit,
    add_style_class_lazy,
)


from fabric.audio.service import Audio
from fabric.notifications import Notification, Notifications
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.hyprland.widgets import (
    HyprlandLanguage as Language,
    HyprlandWorkspaces as Workspaces,
    HyprlandActiveWindow as ActiveWindow,
)
from fabric.utils import (
    FormattedString,
    DesktopApp,
    truncate,
    idle_add,
    bulk_replace,
    monitor_file,
    bulk_connect,
    remove_handler,
    invoke_repeater,
    get_relative_path,
    get_desktop_applications,
    exec_shell_command_async,
    exec_shell_command,
)

gi.require_version("Playerctl", "2.0")
from gi.repository import Playerctl, Gtk, Gdk, Gio, GdkPixbuf, GLib  # noqa: E402

bake_progress_bar = partial(
    CircularProgressBar,
    name="progress-bar",
    start_angle=-90,
    end_angle=270,
    pie=True,
    size=24,
)
bake_icon = partial(Image, style_classes="icon", icon_size=16)
bake_corner = partial(Corner, name="corner")
bake_spinner = partial(Box, name="spinner")


# override
Window.toggle = lambda self: self.set_visible(not self.is_visible())  # type: ignore
