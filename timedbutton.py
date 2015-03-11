# Code shamelessly taken from stackoverflow:
# https://stackoverflow.com/a/14080081

import time

from kivy.uix.button import Button
from kivy.clock import Clock

class TimedButton(Button):
    """A simple ``Button`` subclass that produces an event at regular intervals
    when pressed.

    This class, when long-pressed, emits an ``on_time_slice`` event every
    ``time_slice`` milliseconds.

    :param long_press_interval: Defines the minimum time required to consider
                                the press a long-press.
    :type long_press_interval: int
    :param time_slice: The number of milliseconds of each slice.
    :type time_slice: int
    """

    def __init__(self, long_press_interval=550, time_slice=225, **kwargs):
        super(TimedButton, self).__init__(**kwargs)

        self.long_press_interval = long_press_interval
        self.time_slice = time_slice

        self._touch_start = None
        self._long_press_callback = None
        self._slice_callback = None

        self.register_event_type('on_time_slice')
        self.register_event_type('on_long_press')


    def on_state(self, instance, value):
        if value == 'down':
            start_time = time.time()
            self._touch_start = start_time

            def callback(dt):
                self._check_long_press(dt)

            Clock.schedule_once(callback, self.long_press_interval / 1000.0)
            self._long_press_callback = callback
        else:
            end_time = time.time()
            delta = (end_time - (self._touch_start or 0)) * 1000
            Clock.unschedule(self._slice_callback)
            # Fixes the bug of multiple presses causing fast increase
            Clock.unschedule(self._long_press_callback)
            if (self._long_press_callback is not None and
                delta > self.long_press_interval):
                self.dispatch('on_long_press')
            self._touch_start = None
            self._long_press_callback = self._slice_callback = None

    def _check_long_press(self, dt):
        delta = dt * 1000
        if delta > self.long_press_interval and self.state == 'down':
            self.dispatch('on_long_press')
            self._long_press_callback = None

            def slice_callback(dt):
                self.dispatch('on_time_slice')
                return self.state == 'down'

            Clock.schedule_interval(slice_callback, self.time_slice / 1000.0)

            self._slice_callback = slice_callback

    def on_long_press(self):
        pass

    def on_time_slice(self):
        pass
