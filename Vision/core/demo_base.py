import os
import time
import cv2
from pathlib import Path
from utils.trackbars import noop
import depthai as dai
from utils.error_utils import component_check

@component_check("demo_base")
class Demo:
    DISP_CONF_MIN = int(os.getenv("DISP_CONF_MIN", 0))
    DISP_CONF_MAX = int(os.getenv("DISP_CONF_MAX", 255))
    SIGMA_MIN = int(os.getenv("SIGMA_MIN", 0))
    SIGMA_MAX = int(os.getenv("SIGMA_MAX", 250))
    LRCT_MIN = int(os.getenv("LRCT_MIN", 0))
    LRCT_MAX = int(os.getenv("LRCT_MAX", 10))
    error = None

    def run_all(self, conf):
        # If an external app is specified, delegate to it; otherwise just run the demo.
        if conf.args.app is not None:
            from depthai_helpers.app_manager import App
            app = App(appName=conf.args.app)
            self.onAppSetup(app)
            app.createVenv()
            self.onAppStart(app)
            app.runApp(shouldRun=self.shouldRun)
        else:
            self.setup(conf)
            self.run()

    def __init__(self, displayFrames=True, onNewFrame=noop, onShowFrame=noop, onNn=noop, onReport=noop,
                 onSetup=noop, onTeardown=noop, onIter=noop, onAppSetup=noop, onAppStart=noop,
                 shouldRun=lambda: True, showDownloadProgress=None):
        self._openvinoVersion = None
        self._displayFrames = displayFrames
        self.onNewFrame = onNewFrame
        self.onShowFrame = onShowFrame
        self.onNn = onNn
        self.onReport = onReport
        self.onSetup = onSetup
        self.onTeardown = onTeardown
        self.onIter = onIter
        self.shouldRun = shouldRun
        self.showDownloadProgress = showDownloadProgress
        self.onAppSetup = onAppSetup
        self.onAppStart = onAppStart

    def setCallbacks(self, **callbacks):
        for key, cb in callbacks.items():
            if cb is not None:
                setattr(self, key, cb)

    def setup(self, conf):
        print("Setting up demo...")
        self._conf = conf

        if self._conf.useNN:
            from depthai_helpers.config_manager import DEPTHAI_ZOO
            model_dir = Path(DEPTHAI_ZOO) / self._conf.getModelName()
            if not model_dir.exists():
                print(f"Downloading model files to {model_dir}...")
                try:
                    model_dir.mkdir(parents=True, exist_ok=True)
                    from depthai_sdk.managers import BlobManager
                    self._blobManager = BlobManager(zooDir=DEPTHAI_ZOO,
                                                    zooName=self._conf.getModelName(),
                                                    progressFunc=self.showDownloadProgress)
                except Exception as e:
                    raise RuntimeError(f"Failed to set up model directory: {e}")

        if self._conf.args.openvinoVersion:
            self._openvinoVersion = getattr(dai.OpenVINO.Version, 'VERSION_' + self._conf.args.openvinoVersion)
        self._deviceInfo = dai.Device.getAnyAvailableDevice()  # simplified device selection
        from depthai_sdk.managers import PipelineManager, EncodingManager
        self._pm = PipelineManager(openvinoVersion=self._openvinoVersion, lowCapabilities=self._conf.lowCapabilities)
        maxUsbSpeed = dai.UsbSpeed.SUPER
        self._device = dai.Device(self._pm.pipeline.getOpenVINOVersion(), self._deviceInfo, maxUsbSpeed)
        if not self._device:
            raise RuntimeError("Device initialization failed!")
        try:
            self._calibration = self._device.readCalibration()
            self._pm.pipeline.setCalibrationData(self._calibration)
        except Exception as e:
            print(f"Failed to read calibration: {e}")
            raise

        self._nnManager = None
        if self._conf.useNN:
            from core.nnet_manager import NNetManager
            self._blobManager = self._blobManager  # already set above
            self._nnManager = NNetManager(inputSize=self._conf.inputSize, sync=self._conf.args.sync)
            if self._conf.getModelDir() is not None:
                configPath = self._conf.getModelDir() / (self._conf.getModelName() + ".json")
                print(configPath)
                self._nnManager.readConfig(configPath)
            self._nnManager.countLabel(self._conf.getCountLabel(self._nnManager))
            self._pm.setNnManager(self._nnManager)

        self._conf.adjustParamsToDevice(self._device)
        self._conf.adjustPreviewToOptions()
        if self._conf.lowBandwidth:
            self._pm.enableLowBandwidth(poeQuality=self._conf.args.poeQuality)

        if self._conf.useCamera:
            self._cap = cv2.VideoCapture(self._conf.args.video) if not self._conf.useCamera else None
            from depthai_sdk.fps import FPSHandler
            self._fps = FPSHandler() if self._conf.useCamera else FPSHandler(self._cap)
            pvClass = ( __import__('depthai_sdk.previews').previews.SyncedPreviewManager
                       if self._conf.args.sync
                       else __import__('depthai_sdk.previews').previews.PreviewManager )
            self._pv = pvClass(display=self._conf.args.show,
                               nnSource=self._conf.getModelSource(),
                               colorMap=self._conf.getColorMap(),
                               dispMultiplier=self._conf.dispMultiplier,
                               mouseTracker=True,
                               decode=self._conf.lowBandwidth and not self._conf.lowCapabilities,
                               fpsHandler=self._fps,
                               createWindows=self._displayFrames,
                               depthConfig=self._pm._depthConfig)
            if self._conf.leftCameraEnabled:
                self._pm.createLeftCam(args=self._conf.args)
            if self._conf.rightCameraEnabled:
                self._pm.createRightCam(args=self._conf.args)
            if self._conf.rgbCameraEnabled:
                self._pm.createColorCam(args=self._conf.args)
            if self._conf.useDepth:
                self._pm.createDepth(args=self._conf.args)
            self._encManager = None
            if len(self._conf.args.encode) > 0:
                self._encManager = EncodingManager(self._conf.args.encode, self._conf.args.encodeOutput)
                self._encManager.createEncoders(self._pm)

        if len(self._conf.args.report) > 0:
            self._pm.createSystemLogger()

        if self._conf.useNN:
            from depthai_sdk.previews import Previews
            self._nn = self._nnManager.createNN(
                pipeline=self._pm.pipeline, nodes=self._pm.nodes,
                source=self._conf.getModelSource(),
                blobPath=self._blobManager.getBlob(shaves=self._conf.shaves,
                                                   openvinoVersion=self._nnManager.openvinoVersion),
                useDepth=self._conf.useDepth,
                minDepth=self._conf.args.minDepth,
                maxDepth=self._conf.args.maxDepth,
                sbbScaleFactor=self._conf.args.sbbScaleFactor,
                fullFov=not self._conf.args.disableFullFovNn,
            )
            self._pm.addNn(nn=self._nn,
                           xoutNnInput=("nnInput" in self._conf.args.show),
                           xoutSbb=self._conf.args.spatialBoundingBox and self._conf.useDepth)

    def run(self):
        self._seqNum = 0
        self._hostFrame = None
        self._nnData = []
        self.onSetup(self)
        self.timer = time.monotonic()
        try:
            while self.shouldRun() and self.canRun():
                self.onIter(self)
                self.loop()
        except StopIteration:
            pass
        except Exception as ex:
            raise ex
        finally:
            self.stop()

    def stop(self, *args, **kwargs):
        print("Stopping demo...")
        try:
            self._device.close()
        except:
            pass
        if hasattr(self, "onTeardown"):
            self.onTeardown(self)

    def canRun(self):
        return hasattr(self, "_device")

    def _logMonitorCallback(self, msg):
        import sys
        if msg.level == dai.LogLevel.CRITICAL:
            print(f"[CRITICAL] {msg.payload}", file=sys.stderr)

    def loop(self):
        diff = time.monotonic() - self.timer
        if diff < 0.02:
            time.sleep(0.02 - diff)
        self.timer = time.monotonic()
        if self.error is not None:
            self.stop()
            raise self.error
        if self._conf.useCamera:
            self._pv.prepareFrames(callback=self.onNewFrame)
            if self._encManager is not None:
                self._encManager.parseQueues()
            self._pv.showFrames(callback=self._showFramesCallback)
        else:
            readCorrectly, rawHostFrame = self._cap.read()
            if not readCorrectly:
                raise StopIteration()
            self._nnManager.sendInputFrame(rawHostFrame, self._seqNum)
            self._seqNum += 1
            self._hostFrame = rawHostFrame
            tempFrame = rawHostFrame.copy()
            if self._nnManager is not None:
                self._nnManager.draw(tempFrame, self._nnData)
            cv2.imshow("host", tempFrame)
            if cv2.waitKey(1) == ord('q'):
                raise StopIteration()

    def _createQueueCallback(self, queueName):
        from depthai_sdk.previews import Previews
        if self._displayFrames and queueName in [Previews.disparityColor.name,
                                                 Previews.disparity.name,
                                                 Previews.depth.name,
                                                 Previews.depthRaw.name]:
            from utils.trackbars import Trackbars
            Trackbars.createTrackbar('Disparity confidence', queueName,
                                       self.DISP_CONF_MIN, self.DISP_CONF_MAX,
                                       self._conf.args.disparityConfidenceThreshold,
                                       lambda value: self._pm.updateDepthConfig(dct=value))

    def _updateCameraConfigs(self, config):
        parsedConfig = {}
        for configOption, values in config.items():
            if values is not None:
                for cameraName, value in values:
                    newConfig = {**parsedConfig.get(cameraName, {}), configOption: value}
                    if cameraName == "all":
                        parsedConfig["left"] = newConfig.copy()
                        parsedConfig["right"] = newConfig.copy()
                        parsedConfig["color"] = newConfig.copy()
                    else:
                        parsedConfig[cameraName] = newConfig
        if self._conf.leftCameraEnabled and "left" in parsedConfig:
            self._pm.updateLeftCamConfig(**parsedConfig["left"])
        if self._conf.rightCameraEnabled and "right" in parsedConfig:
            self._pm.updateRightCamConfig(**parsedConfig["right"])
        if self._conf.rgbCameraEnabled and "color" in parsedConfig:
            self._pm.updateColorCamConfig(**parsedConfig["color"])

    def _showFramesCallback(self, frame, name):
        ret = self.onShowFrame(frame, name)
        return ret if ret is not None else frame

    def _printSysInfo(self, info):
        m = 1024 * 1024
        if not hasattr(self, "_reportFile"):
            if "memory" in self._conf.args.report:
                print(f"Memory Info: DDR/CMX etc.")
        else:
            data = {}
            if "memory" in self._conf.args.report:
                data["ddrUsed"] = info.ddrMemoryUsage.used
            if self.onReport:
                self.onReport(data) 