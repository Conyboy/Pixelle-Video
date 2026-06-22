import pytest

from pixelle_video.services.api_services.video_agnes import AgnesVideoClient


class FakeResponse:
    def __init__(self, payload=None, ok=True, content_chunks=None):
        self._payload = payload or {}
        self.ok = ok
        self.text = str(self._payload)
        self._content_chunks = content_chunks or []

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(self.text)

    def iter_content(self, chunk_size=8192):
        yield from self._content_chunks


def test_missing_api_key_raises_before_network(monkeypatch, tmp_path):
    def fail_post(*args, **kwargs):
        raise AssertionError("network should not be called without an API key")

    monkeypatch.setattr("requests.post", fail_post)

    client = AgnesVideoClient(api_key="")

    with pytest.raises(RuntimeError, match="AGNES_API_KEY"):
        client.generate_video(
            prompt="A calm cinematic beach scene",
            image_path=None,
            save_path=str(tmp_path / "out.mp4"),
        )


def test_image_path_is_rejected_for_text_to_video_only(tmp_path):
    client = AgnesVideoClient(api_key="test-key")

    with pytest.raises(ValueError, match="text-to-video only"):
        client.generate_video(
            prompt="Animate this image",
            image_path="input.png",
            save_path=str(tmp_path / "out.mp4"),
        )


def test_generate_video_creates_task_polls_by_video_id_and_downloads(monkeypatch, tmp_path):
    calls = {"post": None, "get": []}
    save_path = tmp_path / "agnes.mp4"

    def fake_post(url, headers, json, timeout, proxies):
        calls["post"] = {
            "url": url,
            "headers": headers,
            "json": json,
            "timeout": timeout,
            "proxies": proxies,
        }
        return FakeResponse(
            {
                "task_id": "task_123",
                "video_id": "video_456",
                "status": "queued",
            }
        )

    def fake_get(url, headers=None, timeout=None, proxies=None, stream=False):
        calls["get"].append(
            {
                "url": url,
                "headers": headers,
                "timeout": timeout,
                "proxies": proxies,
                "stream": stream,
            }
        )
        if "agnesapi" in url:
            return FakeResponse(
                {
                    "video_id": "video_456",
                    "status": "completed",
                    "remixed_from_video_id": "https://cdn.example/video.mp4",
                }
            )
        return FakeResponse(content_chunks=[b"mp4", b"-bytes"])

    monkeypatch.setattr("requests.post", fake_post)
    monkeypatch.setattr("requests.get", fake_get)

    client = AgnesVideoClient(api_key="test-key", base_url="https://apihub.agnes-ai.com")
    result_url = client.generate_video(
        prompt="A cinematic shot of a cat walking on the beach",
        image_path=None,
        save_path=str(save_path),
        model="agnes-video-v2.0",
        duration=5,
        width=1152,
        height=768,
        frame_rate=24,
    )

    assert result_url == "https://cdn.example/video.mp4"
    assert save_path.read_bytes() == b"mp4-bytes"

    assert calls["post"]["url"] == "https://apihub.agnes-ai.com/v1/videos"
    assert calls["post"]["headers"]["Authorization"] == "Bearer test-key"
    assert calls["post"]["json"] == {
        "model": "agnes-video-v2.0",
        "prompt": "A cinematic shot of a cat walking on the beach",
        "height": 768,
        "width": 1152,
        "num_frames": 120,
        "frame_rate": 24,
    }

    poll_call = calls["get"][0]
    assert poll_call["url"] == (
        "https://apihub.agnes-ai.com/agnesapi"
        "?video_id=video_456&model_name=agnes-video-v2.0"
    )
    assert poll_call["headers"]["Authorization"] == "Bearer test-key"


def test_completed_response_without_video_url_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "requests.post",
        lambda *args, **kwargs: FakeResponse({"video_id": "video_456"}),
    )
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: FakeResponse({"status": "completed"}),
    )

    client = AgnesVideoClient(api_key="test-key")

    with pytest.raises(RuntimeError, match="video URL"):
        client.generate_video(
            prompt="A calm cinematic beach scene",
            image_path=None,
            save_path=str(tmp_path / "out.mp4"),
        )
