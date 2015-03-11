from time import sleep
from kivy.lib.osc import oscAPI
from kivy.clock import Clock
from kivy.logger import Logger
from jnius import autoclass, cast, PythonJavaClass, java_method

servicePort = 56279
activityPort = 56278

#MediaRecorder = autoclass('android.media.MediaRecorder')
#AudioSource = autoclass('android.media.MediaRecorder$AudioSource')
#AudioEncoder = autoclass('android.media.MediaRecorder$AudioEncoder')
#VideoSource = autoclass('android.media.MediaRecorder$VideoSource')
#VideoEncoder = autoclass('android.media.MediaRecorder$VideoEncoder')
#OutputFormat = autoclass('android.media.MediaRecorder$OutputFormat')
Camera = autoclass('android.hardware.Camera')
Camera_Parameters = autoclass('android.hardware.Camera$Parameters')
PythonService = autoclass('org.renpy.android.PythonService')
SurfaceTexture = autoclass('android.graphics.SurfaceTexture')
ImageFormat = autoclass('android.graphics.ImageFormat')
FileOutputStream = autoclass('java.io.FileOutputStream')


def make_sendMsg(port):
    def sendMsg(channel, message=None):
        if message is None:
            oscAPI.sendMsg(channel, [], port=port)
        else:
            oscAPI.sendMsg(channel, [str(message)], port=port)
    return sendMsg


class _CameraShutterCallback(PythonJavaClass):
    __javainterfaces__ = ['android.hardware.Camera$ShutterCallback']
    __javacontext__ = 'app'

    def __init__(self, callback):
        super(_CameraShutterCallback, self).__init__()
        self.callback = callback

    @java_method('()V')
    def onShutter(self):
        self.callback()


class _CameraPictureCallback(PythonJavaClass):
    __javainterfaces__ = ['android.hardware.Camera$PictureCallback']
    __javacontext__ = 'app'

    def __init__(self, callback):
        super(_CameraPictureCallback, self).__init__()
        self.callback = callback

    @java_method('([BLandroid/hardware/Camera;)V')
    def onPictureTaken(self, data, camera):
        self.callback(data)


class TimelapseService(object):
    def __init__(self):
        super(TimelapseService, self).__init__()
        Logger.debug("timelapse.service: __init__")
        self.sendMsg = make_sendMsg(activityPort)
        self.cam = None
        self.ready = False
        self.active = False
        self._running = None
        self.filename_cnt = 1
        self.interval = 1
        self.pictures_taken = 0
        self.service = cast('android.app.Service', PythonService.mService)
        self._oscInit()
        self._setup_cam()
        Logger.debug("timelapse.service: __init__ done")
        
    def _oscInit(self):
        oscAPI.init()
        self.oscId = oscAPI.listen(ipAddr="127.0.0.1", port=servicePort)
        oscAPI.bind(self.oscId, self.ping, "/ping")
        oscAPI.bind(self.oscId, self.echo, "/echo")
        oscAPI.bind(self.oscId, self.callback, "/callback")
        oscAPI.bind(self.oscId, self.start, "/start")
        oscAPI.bind(self.oscId, self.stop, "/stop")
        oscAPI.bind(self.oscId, self.shutdown, "/shutdown")
        oscAPI.bind(self.oscId, self.shutdown_if_inactive, "/shutdown_if_inactive")
        oscAPI.bind(self.oscId, self.get_info, "/get/info")
        oscAPI.bind(self.oscId, self.get_info_ready, "/get/info/ready")
        oscAPI.bind(self.oscId, self.set_interval, "/set/interval")
        oscAPI.bind(self.oscId, self.get_picture_sizes, "/get/picture_sizes")

    def _setup_recorder(self):
        self.recorder = MediaRecorder()
        self.recorder.setAudioSource(AudioSource.MIC)
        self.recorder.setVideoSource(VideoSource.DEFAULT)
        self.recorder.setOutputFormat(OutputFormat.MPEG_4)
        self.recorder.setOutputFile("/storage/sdcard0/test.mp4")
        self.recorder.setAudioEncoder(AudioEncoder.DEFAULT)
        self.recorder.setVideoEncoder(VideoEncoder.DEFAULT)
#        self.recorder.setVideoSize(800, 480)
        self.recorder.setVideoFrameRate(30)
        self.recorder.prepare()

    def _setup_cam(self):
        Logger.info("timelapse.service: preparing camera")
        self.cam = Camera.open(0)
        params = self.cam.getParameters()
        Logger.debug("timelapse.service: cam.params.pictureFormat: %s" % params.getPictureFormat())
        Logger.debug("timelapse.service: cam.params.flash: %s" % params.getFlashMode())
        Logger.debug("timelapse.service: cam.params.jpegQuality: %s" % params.getJpegQuality())
        Logger.debug("timelapse.service: cam.params.pictureSize: %dx%d" % (params.getPictureSize().width, params.getPictureSize().height))
        ranges = []
        l = params.getSupportedPreviewFpsRange()
        for i in xrange(l.size()):
            ranges.append(l.get(i))
        Logger.debug("timelapse.service: cam.params.supportedPreviewRanges: %s" % str(ranges))
        sizes = self._get_picture_sizes()
        Logger.debug("timelapse.service: cam.params.supportedPictureSizes: %s" % str(sizes))

        params.setPictureFormat(ImageFormat.JPEG)
        params.setFlashMode(Camera_Parameters.FLASH_MODE_OFF)
        self.cam.setParameters(params)
        self.texture = SurfaceTexture(0)
        Logger.debug("timelapse.service: texture: %s" % str(self.texture))
        self.cam.setPreviewTexture(self.texture)

    def get_next_name(self):
        d = "/storage/sdcard0/foobar/"
        name_template = os.path.join(d, "snap_%04d.jpg")
        while os.path.exists(name_template % self.filename_cnt):
            self.filename_cnt += 1
        return name_template % self.filename_cnt

    def take_picture(self, *args):
        Logger.info("timelapse.service: take_picture")
        if not self.cam:
            Logger.error("timelapse.service: cam not initialized!")
            return
        if not self.ready:
            Logger.error("timelapse.service: cam not ready!")
            return
        self.ready = False
        self.cam.takePicture(_CameraShutterCallback(self.onShutter),
                             None, None,
                             _CameraPictureCallback(self.onPictureTaken))
        Logger.info("timelapse.service: take_picture done")

    def foo(self, *args):
        Logger.info("timelapse.service: foo")
    def bar(self, *args):
        Logger.info("timelapse.service: bar")

    def onShutter(self):
        Logger.info("timelapse.service: onShutter")

    def onPictureTaken(self, data):
        Logger.info("timelapse.service: onPictureTaken")
        self.pictures_taken += 1
        filename = self.get_next_name()
        f = FileOutputStream(filename)
        f.write(data)
        f.close()
        # startPreview must be called *after* the
        # jpeg onPictureTaken callback returns
        Clock.schedule_once(self.startPreview, 0)

    def startPreview(self, *args):
        if self.cam:
            self.cam.startPreview()
            self.ready = True
            Logger.debug("timelapse.service: ready!")

    def run(self):
        Logger.debug("timelapse.service: run")
        self._running = True
        self.startPreview()
        while self._running:
            oscAPI.readQueue(self.oscId)
            # TODO: is this tick necessary???
            Clock.tick()
            sleep(.1)
        Logger.debug("timelapse.service: shutdown commencing")
        self.stop()
        self.cam.stopPreview()
        self.cam.release()
        oscAPI.dontListen(self.oscId)
        Logger.debug("timelapse.service: shutdown complete")
        self.service.stopSelf()


    def callback(self, message, *args):
        Logger.info("timelapse.service: callback %s", str(message[2]))
        channel, msg = eval(message[2])
        self.sendMsg(channel, msg)

    def echo(self, message, *args):
        Logger.info("timelapse.service: echo %s", str(message[2]))
        self.sendMsg("/echo", message[2])
        
    def ping(self, *args):
        Logger.info("timelapse.service: ping")
        self.sendMsg("/pong")

    def start(self, *args):
        Logger.info("timelapse.service: start taking pictures")
        if self.active:
            self.stop()
        #self.take_picture()
        Clock.schedule_interval(self.take_picture, self.interval)
        self.active = True
        
    def stop(self, *args):
        Logger.info("timelapse.service: stop taking pictures")
        Clock.unschedule(self.take_picture)
        self.active = False

    def shutdown(self, *args):
        Logger.info("timelapse.service: received shutdown message")
        self._running = False

    def shutdown_if_inactive(self, *args):
        Logger.info("timelapse.service: shutdown_if_inactive")
        if not self.active:
            self._running = False

    def set_interval(self, message, *args):
        type(message[2])
        was_active = self.active
        if was_active:
            self.stop()
        self.interval = int(message[2])
        Logger.info("timelapse.service: set interval to %d" % self.interval)
        if was_active:
            self.start()

    def get_info(self, *args):
        Logger.info("timelapse.service: get_info")
        self.sendMsg("/get/info", {"ready": self.ready,
                                   "active": self.active,
                                   "pictures_taken": self.pictures_taken,
                                   "next_filename": self.get_next_name(),
                                   "picture_sizes:": self._get_picture_sizes()})

    def get_info_ready(self, *args):
        Logger.info("timelapse.service: get_info_ready")
        self.sendMsg("/get/info/ready", self.ready)

    def _get_picture_sizes(self, *args):
        sizes = []
        if self.cam:
            params = self.cam.getParameters()
            l = params.getSupportedPictureSizes()
            for i in xrange(l.size()):
                size = l.get(i)
                sizes.append([size.width, size.height])
        return sizes

    def get_picture_sizes(self, *args):
        Logger.info("timelapse.service: get_picture_sizes")
        sizes = self._get_picture_sizes()
        self.sendMsg("/get/picture_sizes", sizes)
        

if __name__ == '__main__':
    timelapseService = TimelapseService()
    timelapseService.run()
