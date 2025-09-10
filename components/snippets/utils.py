import cairo
from functools import reduce
from collections.abc import Callable
from typing import TypeVar, Iterable, NamedTuple, cast

from fabric.widgets.box import Box
from fabric.utils import invoke_repeater

from gi.repository import Gtk

T = TypeVar("T")


class Border(NamedTuple):
    top: int
    left: int
    bottom: int
    right: int


class Rectangle(NamedTuple):
    x: float
    y: float
    width: float
    height: float


def get_margin_box_for_widget(
    widget: Gtk.Widget, context: Gtk.StyleContext | None = None
) -> Border:
    return (context or widget.get_style_context()).get_margin(
        widget.get_state_flags()  # type: ignore
    )


def get_content_rect_for_widget(widget: Gtk.Widget) -> Rectangle:
    alloc: Rectangle = widget.get_allocation()  # type: ignore
    margin = get_margin_box_for_widget(widget)

    return Rectangle(
        alloc.x + margin.left,
        alloc.y + margin.top,
        alloc.width - (margin.left + margin.right),
        alloc.height - (margin.top + margin.bottom),
    )


def iter_search(iter: Iterable[T], search_func: Callable[[T], bool]) -> T | None:
    return next((item for item in iter if search_func(item)), None)


def multiply_height_for_child(container: Box, child: Gtk.Widget, n_child: int) -> int:
    spacing: int = container.get_spacing()
    child_height: int = child.get_preferred_size().minimum_size.height  # type: ignore

    height: int = (spacing * (n_child - 1)) + (child_height * n_child)

    return height


def get_children_height_limit(
    viewport: Box,
    max_n_children: int,
    transform_func: Callable[[Gtk.Widget], cairo.RectangleInt] | None = None,
) -> int:
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
            (
                transform_func(children[i])
                if transform_func
                else cast(
                    cairo.RectangleInt,
                    children[i].get_preferred_size().minimum_size,  # type: ignore
                )
            ).height  # type: ignore
            for i in range(children_len)
        ),
    )


def add_style_class_lazy(widget: Gtk.Widget, class_name: str | Iterable[str]) -> int:
    return invoke_repeater(
        50, lambda: widget.add_style_class(class_name), initial_call=False
    )
