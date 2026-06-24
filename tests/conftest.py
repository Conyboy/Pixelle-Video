import sys
import types
from pathlib import Path

if "pixelle_video" not in sys.modules:
    package_stub = types.ModuleType("pixelle_video")
    package_stub.__path__ = [str(Path(__file__).resolve().parents[1] / "pixelle_video")]
    package_stub.__version__ = "0.2.0"
    sys.modules["pixelle_video"] = package_stub

if "pixelle_video.services" not in sys.modules:
    services_stub = types.ModuleType("pixelle_video.services")
    services_stub.__path__ = [
        str(Path(__file__).resolve().parents[1] / "pixelle_video" / "services")
    ]
    sys.modules["pixelle_video.services"] = services_stub


if "comfykit" not in sys.modules:
    comfykit_stub = types.ModuleType("comfykit")

    class ComfyKit:
        pass

    comfykit_stub.ComfyKit = ComfyKit
    sys.modules["comfykit"] = comfykit_stub

if "ffmpeg" not in sys.modules:
    ffmpeg_stub = types.ModuleType("ffmpeg")

    class Error(Exception):
        def __init__(self, *args, stderr=None):
            super().__init__(*args)
            self.stderr = stderr

    ffmpeg_stub.Error = Error
    sys.modules["ffmpeg"] = ffmpeg_stub

if "edge_tts" not in sys.modules:
    edge_tts_stub = types.ModuleType("edge_tts")

    class Communicate:
        def __init__(self, *args, **kwargs):
            pass

    edge_tts_stub.Communicate = Communicate
    edge_tts_stub.list_voices = lambda: []
    sys.modules["edge_tts"] = edge_tts_stub

if "edge_tts.exceptions" not in sys.modules:
    edge_tts_exceptions_stub = types.ModuleType("edge_tts.exceptions")

    class NoAudioReceived(Exception):
        pass

    edge_tts_exceptions_stub.NoAudioReceived = NoAudioReceived
    sys.modules["edge_tts.exceptions"] = edge_tts_exceptions_stub
