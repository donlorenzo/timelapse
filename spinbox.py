# Code shamelessly taken from stackoverflow:
# https://stackoverflow.com/a/14080081

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.properties import (NumericProperty, ReferenceListProperty)
from timedbutton import TimedButton


class SpinBox(BoxLayout):
    """A widget to show and take numeric inputs from the user.

    :param min_value: Minimum of the range of values.
    :type min_value: int, float
    :param max_value: Maximum of the range of values.
    :type max_value: int, float
    :param step: Step of the selection
    :type step: int, float
    :param value: Initial value selected
    :type value: int, float
    :param editable: Determine if the SpinBox is editable or not
    :type editable: bool
    """

    min_value = NumericProperty(float('-inf'))
    max_value = NumericProperty(float('+inf'))
    step = NumericProperty(1)
    value = NumericProperty(0)
    range = ReferenceListProperty(min_value, max_value, step)

    def __init__(self, btn_size_hint_x=0.2, **kwargs):
        super(SpinBox, self).__init__(orientation='horizontal', **kwargs)

        self.value_label = Label(text=str(self.value))
        self.inc_button = TimedButton(text='+')
        self.dec_button = TimedButton(text='-')

        self.inc_button.bind(on_press=self.on_increment_value)
        self.inc_button.bind(on_time_slice=self.on_increment_value)
        self.dec_button.bind(on_press=self.on_decrement_value)
        self.dec_button.bind(on_time_slice=self.on_decrement_value)

        self.buttons_vbox = BoxLayout(orientation='vertical',
                                      size_hint_x=btn_size_hint_x)
        self.buttons_vbox.add_widget(self.inc_button)
        self.buttons_vbox.add_widget(self.dec_button)

        self.add_widget(self.value_label)
        self.add_widget(self.buttons_vbox)

    def on_increment_value(self, btn_instance):
        if float(self.value) + float(self.step) <= self.max_value:
            self.value += self.step

    def on_decrement_value(self, btn_instance):
        if float(self.value) - float(self.step) >= self.min_value:
            self.value -= self.step

    def on_value(self, instance, value):
        instance.value_label.text = str(value)
