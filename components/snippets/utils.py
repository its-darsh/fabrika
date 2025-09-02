import cairo
from functools import reduce
from typing import Iterable, cast
from collections.abc import Callable
from fabric.widgets.box import Box
from fabric.utils import invoke_repeater

from gi.repository import Gtk

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
