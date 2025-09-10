# Author: Yousef EL-Darsh
# License (SPDX): CC-BY-NC-ND-4.0

import cairo
from typing import Any
from functools import partial
from fabric.widgets.widget import Widget
from fabric.widgets.overlay import Overlay
from fabric.hyprland.widgets import HyprlandWorkspaces, WorkspaceButton
from .utils import Rectangle, get_content_rect_for_widget, iter_search
from .animator import Animator, cubic_bezier, lerp
from gi.repository import Gtk


class TailRail(Gtk.DrawingArea, Widget):
    def __init__(
        self,
        animator_kwargs: dict[str, Any] = {},
        tail_animator_kwargs: dict[str, Any] = {},
        **kwargs,
    ):
        Gtk.DrawingArea.__init__(self)
        Widget.__init__(self, **kwargs)

        self._animator = Animator(
            **{
                "duration": 0.1,
                "timing_function": partial(cubic_bezier, 0.55, 0.79, 0.02, 1.0),
            }
            | animator_kwargs,
            tick_widget=self,
            notify_value=lambda *_: self.queue_draw(),
        )

        self._tail_animator = Animator(
            **{
                "duration": 0.5,
                "timing_function": partial(cubic_bezier, 0.55, 0.79, 0.02, 1.0),
            }
            | tail_animator_kwargs,
            tick_widget=self,
            notify_value=lambda *_: self.queue_draw(),
        )

        self._buffer_box = Rectangle(0, 0, 0, 0)
        self._from_box = Rectangle(0, 0, 0, 0)
        self._to_box = Rectangle(0, 0, 0, 0)

    def animate(self, from_box: Rectangle, to_box: Rectangle):
        self._animator.pause()
        self._tail_animator.pause()

        self._from_box = self._buffer_box
        self._to_box = to_box

        if not (self._from_box.width and self._from_box.height):
            self._from_box = from_box

        self._animator.play()
        self._tail_animator.play()

    def do_realize(self, *_):
        Gtk.DrawingArea.do_realize(self)
        if window := self.get_window():
            window.set_pass_through(True)
        return

    def do_draw(self, cr: cairo.Context):
        cr.save()
        context = self.get_style_context()
        cr.set_antialias(cairo.Antialias.BEST)

        leading_progress = self._animator.value
        trailing_progress = self._tail_animator.value

        # x axis
        left_edge_start = self._from_box.x
        left_edge_end = self._to_box.x
        right_edge_start = self._from_box.x + self._from_box.width
        right_edge_end = self._to_box.x + self._to_box.width

        if self._to_box.x >= self._from_box.x:  # to right
            current_left = lerp(left_edge_start, left_edge_end, trailing_progress)
            current_right = lerp(right_edge_start, right_edge_end, leading_progress)
        else:
            current_left = lerp(left_edge_start, left_edge_end, leading_progress)
            current_right = lerp(right_edge_start, right_edge_end, trailing_progress)

        # y axis
        top_edge_start = self._from_box.y
        top_edge_end = self._to_box.y
        bottom_edge_start = self._from_box.y + self._from_box.height
        bottom_edge_end = self._to_box.y + self._to_box.height

        if self._to_box.y >= self._from_box.y:  # to down
            current_top = lerp(top_edge_start, top_edge_end, trailing_progress)
            current_bottom = lerp(bottom_edge_start, bottom_edge_end, leading_progress)
        else:
            current_top = lerp(top_edge_start, top_edge_end, leading_progress)
            current_bottom = lerp(bottom_edge_start, bottom_edge_end, trailing_progress)

        self._buffer_box = Rectangle(
            current_left,
            current_top,
            current_right - current_left,
            current_bottom - current_top,
        )

        if self._buffer_box.width > 0:
            # cr.rectangle(*self._buffer_box)
            # cr.clip()

            Gtk.render_background(context, cr, *self._buffer_box)
            Gtk.render_frame(context, cr, *self._buffer_box)

        cr.restore()
        return True


class Workspaces(Overlay):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_workspace: WorkspaceButton | None = None
        self._current_workspace: WorkspaceButton | None = None
        self._rail = TailRail(name="tail")
        self._buttons: list[WorkspaceButton] = []

        # for performance, you know
        # it's like we're in the 2000's...
        # no such thing as lexer precomputed optimizations
        active_filter = lambda btn: btn.active
        notify_animator = (
            lambda btn: self.do_set_active_button(btn)
            if (btn := iter_search(self._buttons, active_filter))
            else None
        )

        self._workspaces = HyprlandWorkspaces(
            spacing=4,
            name="workspaces",
            style_classes="experimental",
            buttons_factory=lambda ws_id: (
                ws_btn := WorkspaceButton(ws_id, tooltip_text=str(ws_id))
                .build()
                .connect("map", notify_animator)
                .connect("notify::active", notify_animator)
                .unwrap(),
                self._buttons.append(ws_btn),
            )[0],
        )

        self.add(self._workspaces)
        self.add_overlay(self._rail)
        self.set_overlay_pass_through(self._rail, True)

    def get_inner_workspaces(self) -> HyprlandWorkspaces:
        return self._workspaces

    def get_inner_rail(self) -> TailRail:
        return self._rail

    def do_set_active_button(self, button: WorkspaceButton):
        self._last_workspace = self._current_workspace
        self._current_workspace = button
        if not self._last_workspace:
            self._last_workspace = self._current_workspace
        return self.do_animate()

    def do_animate(self):
        return self._rail.animate(
            get_content_rect_for_widget(self._last_workspace),
            get_content_rect_for_widget(
                next((item for item in self._buttons if item.active), None)
            ),
        )
