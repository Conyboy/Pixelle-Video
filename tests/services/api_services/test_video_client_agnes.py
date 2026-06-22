from pixelle_video.services.api_services import video_client as video_client_module
from pixelle_video.services.api_services.config import Config
from pixelle_video.services.api_services.video_client import VideoClient


def test_video_client_routes_agnes_model(monkeypatch, tmp_path):
    routed = {}

    class FakeAgnesVideoClient:
        def __init__(self, api_key=None, base_url=None, local_proxy=None):
            routed["init"] = {
                "api_key": api_key,
                "base_url": base_url,
                "local_proxy": local_proxy,
            }

        def generate_video(self, **kwargs):
            routed["generate"] = kwargs
            return "https://cdn.example/agnes.mp4"

    monkeypatch.setattr(video_client_module, "AgnesVideoClient", FakeAgnesVideoClient)

    client = VideoClient(
        agnes_api_key="agnes-key",
        agnes_base_url="https://apihub.agnes-ai.com",
        agnes_local_proxy="http://127.0.0.1:9090",
    )
    result = client.generate_video(
        prompt="A cinematic city sunrise",
        image_path=None,
        save_path=str(tmp_path / "out.mp4"),
        model="agnes-video-v2.0",
        duration=5,
        video_ratio="16:9",
        resolution="720p",
    )

    assert result == "https://cdn.example/agnes.mp4"
    assert routed["init"] == {
        "api_key": "agnes-key",
        "base_url": "https://apihub.agnes-ai.com",
        "local_proxy": "http://127.0.0.1:9090",
    }
    assert routed["generate"]["prompt"] == "A cinematic city sunrise"
    assert routed["generate"]["model"] == "agnes-video-v2.0"
    assert routed["generate"]["duration"] == 5
    assert routed["generate"]["resolution"] == "720p"


def test_config_facade_reads_agnes_environment(monkeypatch):
    monkeypatch.setenv("AGNES_API_KEY", "env-agnes-key")
    monkeypatch.setenv("AGNES_BASE_URL", "https://env.agnes.example")

    assert Config.AGNES_API_KEY == "env-agnes-key"
    assert Config.AGNES_BASE_URL == "https://env.agnes.example"
