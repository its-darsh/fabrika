# Author: Yousef EL-Darsh
# License (SPDX): CC-BY-NC-ND-4.0

from functools import partial
from fabric.widgets.scrolledwindow import ScrolledWindow

from .animator import Animator, cubic_bezier


class AnimatedScrollable(ScrolledWindow):
    # would you like to have a good looking scrollable?
    # A. take it and lose on cpu usage
    # B. leave it and make it efficent

    # i take it
    def __init__(
        self,
        bezier_curve: tuple[float, float, float, float] = (0.2, 1, 0.8, 1.0),
        duration: float = 0.3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._last_req = -1
        _, min_height = self.min_content_size
        _, max_height = self.max_content_size

        self.height_animator = Animator(
            duration=duration,
            timing_function=partial(cubic_bezier, *bezier_curve),
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

    def animate_size(self, height: int = -1):
        self._last_req = height
        return self.do_animate(self.min_content_size[1], height)

    def do_get_preferred_height(self):
        value = self.height_animator.value
        value = 0 if value < 0 else value
        return value, value
