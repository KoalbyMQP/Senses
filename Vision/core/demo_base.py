import os
import time
import cv2
from pathlib import Path
from utils.trackbars import noop
import depthai as dai
import numpy as np

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
        self._blobManager = None

        if self._conf.useNN:
            from depthai_helpers.config_manager import DEPTHAI_ZOO
            model_dir = Path(DEPTHAI_ZOO) / self._conf.getModelName()
            if not model_dir.exists():
                print(f"Downloading model files to {model_dir}...")
                try:
                    # Remove the file if it exists
                    if model_dir.is_file():
                        model_dir.unlink()
                    # Create directory and parent directories
                    model_dir.parent.mkdir(parents=True, exist_ok=True)
                    model_dir.mkdir(exist_ok=True)
                    
                    from depthai_sdk.managers import BlobManager
                    self._blobManager = BlobManager(
                        zooDir=DEPTHAI_ZOO,
                        zooName=self._conf.getModelName(),
                        progressFunc=self.showDownloadProgress
                    )
                except Exception as e:
                    raise RuntimeError(f"Failed to set up model directory: {e}")

        if self._conf.args.openvinoVersion:
            self._openvinoVersion = getattr(dai.OpenVINO.Version, 'VERSION_' + self._conf.args.openvinoVersion)
        
        from depthai_sdk import getDeviceInfo
        self._deviceInfo = getDeviceInfo(self._conf.args.deviceId)
        from depthai_sdk.managers import PipelineManager
        self._pm = PipelineManager(openvinoVersion=self._openvinoVersion, lowCapabilities=self._conf.lowCapabilities)

        if self._conf.args.xlinkChunkSize is not None:
            self._pm.setXlinkChunkSize(self._conf.args.xlinkChunkSize)

        if self._conf.args.cameraTuning:
            self._pm.setCameraTuningBlob(self._conf.args.cameraTuning)

        maxUsbSpeed = dai.UsbSpeed.HIGH if self._conf.args.usbSpeed == "usb2" else dai.UsbSpeed.SUPER
        self._device = dai.Device(self._pm.pipeline.getOpenVINOVersion(), self._deviceInfo, maxUsbSpeed)
        self._device.addLogCallback(self._logMonitorCallback)
        if not self._device:
            raise RuntimeError("Device initialization failed!")
        
        # Read calibration
        try:
            self._calibration = self._device.readCalibration()
            self._pm.pipeline.setCalibrationData(self._calibration)
        except Exception as e:
            print(f"Failed to read calibration: {e}")
            raise
        
        self._nnManager = None
        if self._conf.useNN:
            from depthai_sdk.managers import NNetManager, BlobManager
            if not self._blobManager:
                self._blobManager = BlobManager(
                    zooDir=DEPTHAI_ZOO,
                    zooName=self._conf.getModelName(),
                    progressFunc=self.showDownloadProgress
                )
            
            self._nnManager = NNetManager(inputSize=self._conf.inputSize, sync=self._conf.args.sync)
            
            self._nnManager.device = self._device
            self._nnManager.calibData = None
            self._nnManager.cameraIntrinsics = None
            self._nnManager.distCoeffs = None
            self._nnManager.measurement_buffer = []
            self._nnManager.max_buffer_size = 500
            self._nnManager.min_confidence = 0.70
            self._nnManager.coordinates_sent = False
            self._nnManager._target_object = None
            
            def initializeCalibration(nnm):
                if nnm.calibData is not None:
                    return
                    
                if nnm.device is None:
                    raise RuntimeError("Device not initialized! Pass device instance during NNetManager initialization.")
                    
                nnm.calibData = nnm.device.readCalibration()
                
                eeprom = nnm.calibData.getEepromData()
                if "OAK-1" in eeprom.boardName or "BW1093OAK" in eeprom.boardName:
                    nnm.cameraIntrinsics = np.array(nnm.calibData.getCameraIntrinsics(dai.CameraBoardSocket.CAM_A, 1280, 720))
                    nnm.distCoeffs = np.array(nnm.calibData.getDistortionCoefficients(dai.CameraBoardSocket.CAM_A))
                    nnm.fov = nnm.calibData.getFov(dai.CameraBoardSocket.CAM_A)
                else:
                    M_rgb, width, height = nnm.calibData.getDefaultIntrinsics(dai.CameraBoardSocket.CAM_A)
                    nnm.cameraIntrinsics = np.array(M_rgb)
                    
                    nnm.cameraIntrinsics = np.array(nnm.calibData.getCameraIntrinsics(dai.CameraBoardSocket.CAM_A, 
                                                                                  1920, 1080))
                    
                    nnm.distCoeffs = np.array(nnm.calibData.getDistortionCoefficients(dai.CameraBoardSocket.CAM_A))
                    nnm.fov = nnm.calibData.getFov(dai.CameraBoardSocket.CAM_A)
                    
                return nnm.cameraIntrinsics, nnm.distCoeffs, nnm.fov
            
            def getCameraIntrinsics(nnm, frame_width=None, frame_height=None):
                if nnm.calibData is None:
                    nnm.initializeCalibration()
                
                if frame_width is not None and frame_height is not None:
                    return (np.array(nnm.calibData.getCameraIntrinsics(dai.CameraBoardSocket.RGB, 
                                                                  frame_width, frame_height)),
                            nnm.distCoeffs,
                            nnm.fov)
                
                return nnm.cameraIntrinsics, nnm.distCoeffs, nnm.fov
            
            def calculatePhysicalDimensions(nnm, detection, frame):
                if not hasattr(detection, 'spatialCoordinates'):
                    return None
                    
                coords = {
                    'position': {
                        'x': detection.spatialCoordinates.x / 1000,  # Convert to meters
                        'y': detection.spatialCoordinates.y / 1000,
                        'z': detection.spatialCoordinates.z / 1000,
                    },
                    'label': nnm.getLabelText(detection.label),
                    'confidence': float(detection.confidence),
                    'detection_id': id(detection)
                }
                
                if frame is not None and hasattr(detection, 'xmin'):
                    width = abs(detection.xmax - detection.xmin)
                    height = abs(detection.ymax - detection.ymin)
                    
                    coords['dimensions'] = {
                        'width': width,
                        'height': height
                    }
                
                if coords['confidence'] >= nnm.min_confidence:
                    nnm.measurement_buffer.append(coords)
                    if len(nnm.measurement_buffer) > nnm.max_buffer_size:
                        nnm.measurement_buffer.pop(0)
                
                return coords
            
            def get_measurement_buffer(nnm):
                return nnm.measurement_buffer
            
            def clear_measurement_buffer(nnm):
                nnm.measurement_buffer = []
            
            def set_target_object(nnm, target):
                if target is None:
                    nnm._target_object = None
                    return True
                    
                for label in nnm._labels:
                    if target.lower() == label.lower():
                        nnm._target_object = target.lower()
                        return True
                
                print(f"Warning: Target '{target}' not found in available labels: {nnm._labels}")
                return False
            
            def _should_draw_detection(nnm, detection):
                if not hasattr(nnm, '_target_object') or nnm._target_object is None:
                    return True
                    
                label_text = nnm.getLabelText(detection.label).lower()
                return label_text == nnm._target_object.lower()
            
            original_draw = self._nnManager.draw
            def extended_draw(source, decodedData):
                if hasattr(self._nnManager, '_target_object') and self._nnManager._target_object is not None:
                    filtered_data = [det for det in decodedData if self._nnManager._should_draw_detection(det)]
                    original_draw(source, filtered_data)
                    
                    if source is not None and len(filtered_data) > 0:
                        for detection in filtered_data:
                            self._nnManager.calculatePhysicalDimensions(detection, source)
                else:
                    original_draw(source, decodedData)
            
            self._nnManager.initializeCalibration = lambda: initializeCalibration(self._nnManager)
            self._nnManager.getCameraIntrinsics = lambda frame_width=None, frame_height=None: getCameraIntrinsics(self._nnManager, frame_width, frame_height)
            self._nnManager.calculatePhysicalDimensions = lambda detection, frame: calculatePhysicalDimensions(self._nnManager, detection, frame)
            self._nnManager.get_measurement_buffer = lambda: get_measurement_buffer(self._nnManager)
            self._nnManager.clear_measurement_buffer = lambda: clear_measurement_buffer(self._nnManager)
            self._nnManager.set_target_object = lambda target: set_target_object(self._nnManager, target)
            self._nnManager._should_draw_detection = lambda detection: _should_draw_detection(self._nnManager, detection)
            self._nnManager.draw = lambda source, decodedData: extended_draw(source, decodedData)
            
            if self._conf.getModelDir() is not None:
                configPath = self._conf.getModelDir() / Path(self._conf.getModelName()).with_suffix(f".json")
                print(configPath)
                self._nnManager.readConfig(configPath)

            self._nnManager.countLabel(self._conf.getCountLabel(self._nnManager))
            self._pm.setNnManager(self._nnManager)

        self._conf.adjustParamsToDevice(self._device)
        self._conf.adjustPreviewToOptions()
        if self._conf.lowBandwidth:
            self._pm.enableLowBandwidth(poeQuality=self._conf.args.poeQuality)
            
        self._cap = cv2.VideoCapture(self._conf.args.video) if not self._conf.useCamera else None
        
        if self._conf.useCamera:
            from depthai_sdk.fps import FPSHandler
            from depthai_sdk.previews import Previews
            self._fps = FPSHandler() if self._conf.useCamera else FPSHandler(self._cap)
            
            # Choose the right preview manager class
            if self._conf.args.sync:
                from depthai_sdk.managers import SyncedPreviewManager
                pvClass = SyncedPreviewManager
            else:
                from depthai_sdk.managers import PreviewManager
                pvClass = PreviewManager
                
            self._pv = pvClass(
                display=self._conf.args.show,
                nnSource=self._conf.getModelSource(),
                colorMap=self._conf.getColorMap(),
                dispMultiplier=self._conf.dispMultiplier,
                mouseTracker=True,
                decode=self._conf.lowBandwidth and not self._conf.lowCapabilities,
                fpsHandler=self._fps,
                createWindows=self._displayFrames,
                depthConfig=self._pm._depthConfig
            )

            if self._conf.leftCameraEnabled:
                self._pm.createLeftCam(args=self._conf.args)
            if self._conf.rightCameraEnabled:
                self._pm.createRightCam(args=self._conf.args)
            if self._conf.rgbCameraEnabled:
                self._pm.createColorCam(args=self._conf.args)

            if self._conf.useDepth:
                self._pm.createDepth(args=self._conf.args)

            # Handle IR drivers if available
            irDrivers = self._device.getIrDrivers()
            if irDrivers and self._conf.irEnabled(self._device):
                self._pm.updateIrConfig(self._device, self._conf.args.irDotBrightness, self._conf.args.irFloodBrightness)

            self._encManager = None
            if len(self._conf.args.encode) > 0:
                from depthai_sdk.managers import EncodingManager
                self._encManager = EncodingManager(self._conf.args.encode, self._conf.args.encodeOutput)
                self._encManager.createEncoders(self._pm)

        if len(self._conf.args.report) > 0:
            self._pm.createSystemLogger()

        if self._conf.useNN:
            from depthai_sdk.previews import Previews
            self._nn = self._nnManager.createNN(
                pipeline=self._pm.pipeline,
                nodes=self._pm.nodes,
                source=self._conf.getModelSource(),
                blobPath=self._blobManager.getBlob(shaves=self._conf.shaves, openvinoVersion=self._nnManager.openvinoVersion),
                useDepth=self._conf.useDepth,
                minDepth=self._conf.args.minDepth,
                maxDepth=self._conf.args.maxDepth,
                sbbScaleFactor=self._conf.args.sbbScaleFactor,
                fullFov=not self._conf.args.disableFullFovNn,
            )

            self._pm.addNn(nn=self._nn,
                          xoutNnInput=Previews.nnInput.name in self._conf.args.show,
                          xoutSbb=self._conf.args.spatialBoundingBox and self._conf.useDepth)

    def run(self):
        print("Starting pipeline...")
        self._device.startPipeline(self._pm.pipeline)
        self._pm.createDefaultQueues(self._device)
        
        self._sbbOut = self._device.getOutputQueue("sbb", maxSize=1, blocking=False) if self._conf.useNN and self._conf.args.spatialBoundingBox else None
        self._logOut = self._device.getOutputQueue("systemLogger", maxSize=30, blocking=False) if len(self._conf.args.report) > 0 else None

        if self._conf.useDepth:
            from itertools import cycle
            self._medianFilters = cycle([item for name, item in vars(dai.MedianFilter).items() 
                                      if name.startswith('KERNEL_') or name.startswith('MEDIAN_')])
            for medFilter in self._medianFilters:
                # move the cycle to the current median filter
                if medFilter == self._pm._depthConfig.postProcessing.median:
                    break
        else:
            self._medianFilters = []

        if self._conf.useCamera:
            cameras = self._device.getConnectedCameras()
            if dai.CameraBoardSocket.CAM_B in cameras and dai.CameraBoardSocket.CAM_C in cameras:
                self._pv.collectCalibData(self._device)

            self._pv.createQueues(self._device, self._createQueueCallback)
            if self._encManager is not None:
                self._encManager.createDefaultQueues(self._device)
                
        if self._conf.useNN:
            self._nnManager.createQueues(self._device)

        self._seqNum = 0
        self._hostFrame = None
        self._nnData = []
        self._sbbRois = []
        self.onSetup(self)

        self.timer = time.monotonic()
        try:
            while self.shouldRun() and self.canRun():
                self._fps.nextIter()
                self.onIter(self)
                self.loop()
        except StopIteration:
            pass
        except Exception as ex:
            raise
        finally:
            self.stop()

    def stop(self, *args, **kwargs):
        print("Stopping demo...")
        if hasattr(self, '_device'):
            self._device.close()
            del self._device
        if hasattr(self, '_pm'):
            try:
                self._pm.closeDefaultQueues()
            except:
                pass
        if hasattr(self, '_pv'):
            try:
                self._pv.closeQueues()
            except:
                pass
        if hasattr(self, '_nnManager'):
            try:
                self._nnManager.closeQueues()
            except:
                pass
        if hasattr(self, '_encManager') and self._encManager is not None:
            try:
                self._encManager.close()
            except:
                pass
        if hasattr(self, '_sbbOut') and self._sbbOut is not None:
            self._sbbOut.close()
        if hasattr(self, '_logOut') and self._logOut is not None:
            self._logOut.close()
        if hasattr(self, 'onTeardown'):
            self.onTeardown(self)

    def canRun(self):
        return hasattr(self, "_device") and not self._device.isClosed()

    def _logMonitorCallback(self, msg):
        import sys
        if msg.level == dai.LogLevel.CRITICAL:
            print(f"[CRITICAL] [{msg.time.get()}] {msg.payload}", file=sys.stderr)
            sys.stderr.flush()
            temperature = self._device.getChipTemperature()
            if any(map(lambda field: getattr(temperature, field) > 100, ["average", "css", "dss", "mss", "upa"])):
                self.error = RuntimeError(f"Device overheated: {msg.payload}")
            else:
                self.error = RuntimeError(msg.payload)

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

            if self._sbbOut is not None:
                sbb = self._sbbOut.tryGet()
                if sbb is not None:
                    self._sbbRois = sbb.getConfigData()
                    
            if self._conf.useNN:
                newData, inNn = self._nnManager.parse()
                if inNn is not None:
                    self.onNn(inNn, newData)
                    self._fps.tick('nn')
                if newData is not None:
                    self._nnData = newData

            if self._nnManager is not None:
                self._nnManager.draw(self._pv, self._nnData)
            self._pv.showFrames(callback=self._showFramesCallback)
        elif self._hostFrame is not None:
            debugHostFrame = self._hostFrame.copy()
            if self._nnManager is not None:
                self._nnManager.draw(debugHostFrame, self._nnData)
            self._fps.drawFps(debugHostFrame, "host")
            if self._displayFrames:
                cv2.imshow("host", debugHostFrame)

        if self._logOut:
            logs = self._logOut.tryGetAll()
            for log in logs:
                self._printSysInfo(log)

        if self._displayFrames:
            key = cv2.waitKey(1)
            if key == ord('q'):
                raise StopIteration()
            elif key == ord('m') and self._conf.useDepth:
                nextFilter = next(self._medianFilters)
                self._pm.updateDepthConfig(self._device, median=nextFilter)

    def _createQueueCallback(self, queueName):
        from depthai_sdk.previews import Previews
        if self._displayFrames and queueName in [Previews.disparityColor.name, Previews.disparity.name, Previews.depth.name, Previews.depthRaw.name]:
            from utils.trackbars import Trackbars
            Trackbars.createTrackbar('Disparity confidence', queueName, self.DISP_CONF_MIN, self.DISP_CONF_MAX, self._conf.args.disparityConfidenceThreshold,
                     lambda value: self._pm.updateDepthConfig(dct=value))
            if queueName in [Previews.depthRaw.name, Previews.depth.name]:
                Trackbars.createTrackbar('Bilateral sigma', queueName, self.SIGMA_MIN, self.SIGMA_MAX, self._conf.args.sigma,
                         lambda value: self._pm.updateDepthConfig(sigma=value))
            if self._conf.args.stereoLrCheck:
                Trackbars.createTrackbar('LR-check threshold', queueName, self.LRCT_MIN, self.LRCT_MAX, self._conf.args.lrcThreshold,
                         lambda value: self._pm.updateDepthConfig(lrcThreshold=value))

    def _updateCameraConfigs(self, config):
        parsedConfig = {}
        for configOption, values in config.items():
            if values is not None:
                for cameraName, value in values:
                    newConfig = {
                        **parsedConfig.get(cameraName, {}),
                        configOption: value
                    }
                    if cameraName == "all":
                        from depthai_sdk.previews import Previews
                        parsedConfig[Previews.left.name] = newConfig
                        parsedConfig[Previews.right.name] = newConfig
                        parsedConfig[Previews.color.name] = newConfig
                    else:
                        parsedConfig[cameraName] = newConfig

        if self._conf.leftCameraEnabled and Previews.left.name in parsedConfig:
            self._pm.updateLeftCamConfig(**parsedConfig[Previews.left.name])
        if self._conf.rightCameraEnabled and Previews.right.name in parsedConfig:
            self._pm.updateRightCamConfig(**parsedConfig[Previews.right.name])
        if self._conf.rgbCameraEnabled and Previews.color.name in parsedConfig:
            self._pm.updateColorCamConfig(**parsedConfig[Previews.color.name])

    def _showFramesCallback(self, frame, name):
        returnFrame = self.onShowFrame(frame, name)
        return returnFrame if returnFrame is not None else frame

    def _printSysInfo(self, info):
        m = 1024 * 1024 # MiB
        if not hasattr(self, "_reportFile"):
            if "memory" in self._conf.args.report:
                print(f"Drr used / total - {info.ddrMemoryUsage.used / m:.2f} / {info.ddrMemoryUsage.total / m:.2f} MiB")
                print(f"Cmx used / total - {info.cmxMemoryUsage.used / m:.2f} / {info.cmxMemoryUsage.total / m:.2f} MiB")
        else:
            data = {}
            if "memory" in self._conf.args.report:
                data = {
                    **data,
                    "ddrUsed": info.ddrMemoryUsage.used,
                    "ddrTotal": info.ddrMemoryUsage.total,
                }
            self.onReport(data) 