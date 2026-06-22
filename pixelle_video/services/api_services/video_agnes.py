"""Agnes Video V2.0 text-to-video API client."""

import logging
import os
import time
from typing import Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

AGNES_BASE_URL = "https://apihub.agnes-ai.com"


class AgnesVideoClient:
    """Client for Agnes asynchronous text-to-video generation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        local_proxy: Optional[str] = None,
        timeout: int = 120,
        poll_interval: int = 5,
        max_polls: int = 120,
    ) -> None:
        self.api_key = api_key or os.getenv("AGNES_API_KEY", "")
        self.base_url = (base_url or os.getenv("AGNES_BASE_URL") or AGNES_BASE_URL).rstrip("/")
        self.local_proxy = local_proxy
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_polls = max_polls

        if not self.api_key:
            logger.warning("AgnesVideoClient: AGNES_API_KEY is not set")

    def generate_video(
        self,
        prompt: str,
        image_path: Optional[str],
        save_path: str,
        model: str = "agnes-video-v2.0",
        duration: int = 5,
        width: Optional[int] = None,
        height: Optional[int] = None,
        frame_rate: int = 24,
        **kwargs,
    ) -> str:
        """Generate a text-to-video clip and download it to ``save_path``."""
        if not self.api_key:
            raise RuntimeError("AGNES_API_KEY not set.")
        if image_path:
            raise ValueError("Agnes provider is text-to-video only in this integration.")

        resolved_width = int(width or kwargs.get("media_width") or 1152)
        resolved_height = int(height or kwargs.get("media_height") or 768)
        resolved_frame_rate = int(frame_rate or kwargs.get("frame_rate") or 24)
        num_frames = max(1, int(round(float(duration) * resolved_frame_rate)))

        video_id = self._submit_task(
            prompt=prompt,
            model=model,
            width=resolved_width,
            height=resolved_height,
            num_frames=num_frames,
            frame_rate=resolved_frame_rate,
        )
        video_url = self._poll_until_done(video_id=video_id, model=model)
        self._download_video(video_url, save_path)
        return video_url

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _proxies(self) -> Optional[dict]:
        if not self.local_proxy:
            return None
        return {"http": self.local_proxy, "https": self.local_proxy}

    def _submit_task(
        self,
        prompt: str,
        model: str,
        width: int,
        height: int,
        num_frames: int,
        frame_rate: int,
    ) -> str:
        url = f"{self.base_url}/v1/videos"
        payload = {
            "model": model,
            "prompt": prompt,
            "height": height,
            "width": width,
            "num_frames": num_frames,
            "frame_rate": frame_rate,
        }

        logger.info(f"AgnesVideoClient: submitting text-to-video task model={model}")
        resp = requests.post(
            url,
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
            proxies=self._proxies(),
        )
        if not resp.ok:
            logger.error(f"Agnes task creation failed: {resp.text}")
            resp.raise_for_status()

        data = resp.json()
        video_id = data.get("video_id")
        if not video_id:
            raise RuntimeError(f"Agnes API did not return video_id: {data}")
        return video_id

    def _poll_until_done(self, video_id: str, model: str) -> str:
        query = urlencode({"video_id": video_id, "model_name": model})
        url = f"{self.base_url}/agnesapi?{query}"

        for attempt in range(self.max_polls):
            resp = requests.get(
                url,
                headers=self._headers(),
                timeout=30,
                proxies=self._proxies(),
            )
            resp.raise_for_status()
            data = resp.json()
            status = str(data.get("status", "")).lower()

            if status == "completed":
                video_url = data.get("video_url") or data.get("remixed_from_video_id")
                if not video_url:
                    raise RuntimeError(f"Agnes task completed but did not return video URL: {data}")
                return video_url

            if status in {"failed", "error", "cancelled", "canceled"}:
                error = data.get("error") or data.get("message") or data
                raise RuntimeError(f"Agnes video generation failed: {error}")

            logger.debug(
                "AgnesVideoClient: task in progress "
                f"video_id={video_id}, status={status}, poll={attempt + 1}"
            )
            time.sleep(self.poll_interval)

        raise TimeoutError(f"Agnes video generation timed out (video_id={video_id})")

    def _download_video(self, url: str, save_path: str) -> None:
        save_dir = os.path.dirname(save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)

        resp = requests.get(
            url,
            stream=True,
            timeout=120,
            proxies=self._proxies(),
        )
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        logger.info(f"AgnesVideoClient: video saved: {save_path}")
