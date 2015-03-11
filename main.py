from __future__ import division, absolute_import
import sys
import random
from time import sleep

from kivy.app import App
from kivy.lang import Builder
from kivy.utils import platform
from kivy.lib.osc import oscAPI
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout

try:
    from service.main import servicePort, activityPort, make_sendMsg
except ImportError as e:
    Logger.error("failed to import service-/activityPort from service.main.\nThere is probably a SyntaxError in service.main that buildozer doesn't report.")
    raise e

from spinbox import SpinBox


__version__ = "0.1"


class InitPopup(Popup):
    def on_open(self):
        Clock.schedule_interval(self._query_service, 0.1)
    def _query_service(self, dt):
        Logger.debug("initPopup: send query")
        oscAPI.sendMsg('/get/info/ready', [], port=servicePort)
    def on_dismiss(self):
        Clock.unschedule(self._query_service)        
        return False

class TimelapseWidget(BoxLayout):
    pass

class TimelapseApp(App):
    def build(self):
        Logger.debug("timelapse: build main app")
        self.sendMsg = make_sendMsg(servicePort)
        self.pong_callbacks = []
        self.callbacks = {}
        self.service = None
        self.oscInit()
        self.ensure_service_is_running()
        self.popup = InitPopup()
        Clock.schedule_once(lambda dt: self.popup.open(), 0)
        timelapse_widget = TimelapseWidget()
        timelapse_widget.size_spinner.bind(text=self.set_size)
        return timelapse_widget

    def set_size(self, widget, text):
        Logger.debug("timelapse: set_size: " + text)
        self.sendMsg('/set/picture_size', map(int, text.split("x")))

    def oscInit(self):
        oscAPI.init()
        self.oscId = oscAPI.listen(ipAddr='127.0.0.1', port=activityPort)
        oscAPI.bind(self.oscId, self.receive_pong, '/pong')
        oscAPI.bind(self.oscId, self.receive_info, '/get/info')
        oscAPI.bind(self.oscId, self.receive_info_ready, '/get/info/ready')
        oscAPI.bind(self.oscId, self.receive_picture_sizes, '/get/picture_sizes')
        oscAPI.bind(self.oscId, self.receive_message, '/message')
        Clock.schedule_interval(lambda dt: oscAPI.readQueue(self.oscId), 0.1)

    def ping_service(self):
        self.sendMsg('/ping')

    def set_interval(self, value):
        Logger.info("timelapse: set interval %s" % str(value))
        self.sendMsg('/set/interval', str(value))
        
    def receive_pong(self, *args):
        Logger.info("timelapse: received pong")
        for cb in self.pong_callbacks:
            Logger.debug('timelapse: calling pong callback "%s"' % cb.__name__)
            cb()
        self.pong_callbacks = []

    def ensure_service_is_running(self):
        #self.callbacks[] = lambda : Clock.unschedule(self.start_service)
        #self.pong_callbacks.append(lambda : Clock.unschedule(self.start_service))
        #delay = 0.2
        delay = 0
        Clock.schedule_once(self.start_service, delay)
        #self.ping_service()

    def start_service(self, *args):
        if platform != 'android':
            Logger.warning("timelapse: starting service only works on android."
                           " start manually.")
            return
        from android import AndroidService
        self.service = AndroidService('timelapse service', 'running')
        self.service.start('service started')
        
        
    def disable_config(self):
        self.root.interval_spinbox.disabled = True
        self.root.destination_button.disabled = True

    def enable_config(self):
        self.root.interval_spinbox.disabled = False
        self.root.destination_button.disabled = False

    def start_taking_pictures(self):
        Logger.info("timelapse: start")
        self.root.start_button.disabled = True
        self.disable_config()
        self.sendMsg('/start')
        self.root.stop_button.disabled = False

    def stop_taking_pictures(self):
        Logger.info("timelapse: stop")
        self.root.stop_button.disabled = True
        self.sendMsg('/stop')
        self.enable_config()
        self.root.start_button.disabled = False

    def get_info(self):
        Logger.info("timelapse: get_info")
        self.sendMsg('/get/info')

    def shutdown(self):
        Logger.info("timelapse: shutdown")
        self.sendMsg('/shutdown')
        if self.service:
            self.service.stop()
        self.stop()
        
    def on_pause(self):
        # android activity stopped
        Logger.info("timelapse: on_pasue")
        return True
        
    def on_stop(self):
        # android activity stopped
        Logger.info("timelapse: on_stop")
        self.sendMsg("/shutdown_if_inactive")
        oscAPI.dontListen(self.oscId)
        
    def on_start(self):
        # android activity started
        super(TimelapseApp, self).on_start()
        Logger.info("timelapse: on_start")

    def receive_info(self, message, *args):
        Logger.info("timelapse: received info: %s" % str(message[2]))
        info = eval(message[2])
        self.root.console.text += "\n" + str(info)
        picture_sizes = info['picture_sizes']
        Logger.debug("timelapse: picture_sizes: %s" % str(picture_sizes))
        self.root.size_spinner.values = [("%d x %d" % (size[0], size[1])) for size in picture_sizes]
        Logger.debug("timelapse: spinner_values: %s" % str(self.root.size_spinner.values))

    def receive_info_ready(self, message, *args):
        Logger.info("timelapse: received info ready: %s" % str(message[2]))
        ready = eval(message[2])
        if ready:
            self.popup.dismiss()
            self.sendMsg('/get/info')

    def receive_message(self, message, *args):
        Logger.debug("timelapse: received message: %s" % str(message[2]))

    def receive_picture_sizes(self, message, *args):
        Logger.debug("timelapse: received picture sizes: %s" % str(message[2]))
        sizes = eval(message[2])
        

if __name__ == '__main__':
    Logger.debug("starting timelapse app.")
    TimelapseApp().run()
