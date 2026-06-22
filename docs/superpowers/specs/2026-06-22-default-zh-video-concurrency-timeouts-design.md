# Default Chinese, Video Segment Concurrency, and Timeout Buckets Design

## Goal

Make the Web UI start in Chinese by default, allow users to configure concurrent frame/segment generation inside a single video, and normalize request/browser timeout values into larger timeout buckets.

## Scope

This change covers three behaviors:

- The default Web UI language is `zh_CN` on startup.
- A single generated video can process multiple storyboard frames concurrently when the user configures a concurrency value greater than `1`.
- Explicit timeout values used for network requests and bounded waits are rounded up into these buckets:
  - Less than 30 seconds becomes 30 seconds.
  - 30 to 60 seconds becomes 60 seconds.
  - 60 to 300 seconds becomes 300 seconds.
  - 300 to 600 seconds becomes 600 seconds.

This change does not add batch-video concurrency. Batch mode continues to generate videos in its existing order.

## Default Language

The current `web/i18n/__init__.py` startup behavior detects the server or OS locale and falls back to English. In WSL or server deployments that often starts the page in English even when the target user expects Chinese.

The new behavior is:

- `zh_CN` is the default language after locale files are loaded.
- Existing session language selection still wins inside Streamlit session state.
- Users can still switch languages using the existing header language selector.
- System language detection can remain as a helper, but startup initialization no longer uses it as the default.

## Video Segment Concurrency

The existing `StandardPipeline.produce_assets` already has a parallel path, but it only activates for RunningHub workflows via `comfyui.runninghub_concurrent_limit`. The new behavior introduces a general video frame concurrency setting.

Configuration:

- Add `comfyui.video.concurrent_limit` to the schema.
- Default: `1`.
- Validation range: `1` to `10`.
- Add the same key to `config.example.yaml`.
- Expose the setting in the Web UI when configuring video media generation.

Runtime behavior:

- The Standard pipeline reads `video_concurrent_limit` from generation params, falling back to `config_manager.config.comfyui.video.concurrent_limit`, then `1`.
- If `video_concurrent_limit > 1` and the storyboard has more than one frame, `produce_assets` processes frames with an `asyncio.Semaphore(video_concurrent_limit)`.
- If `video_concurrent_limit == 1`, behavior remains serial.
- The existing RunningHub concurrency setting remains available for RunningHub-specific capacity configuration, but the new video setting controls single-video storyboard frame concurrency.

UI behavior:

- In the video media generation section, show a numeric input labeled as single-video segment concurrency.
- The control is shown for video templates, independent of whether the source is RunningHub, selfhost, or direct API.
- The selected value is passed into `pixelle_video.generate_video(...)` as `video_concurrent_limit`.
- Batch mode passes the same shared setting into each single-video task, but does not run multiple videos concurrently.

## Timeout Normalization

Only explicit timeout values are changed. Retry delays, poll intervals, retry counts, JWT token TTL, and maximum poll counts are not timeout values and are not modified.

Timeout targets include:

- `requests.get/post(..., timeout=...)`
- `httpx.Client/AsyncClient(timeout=...)`
- `httpx.Timeout(...)`
- `asyncio.wait_for(..., timeout=...)`
- function defaults whose parameter is named `timeout`

Mapping examples:

- `timeout=2`, `timeout=5`, `timeout=10`, `connect=10.0` become `30` or `30.0`.
- `timeout=30`, `read=60`, `write=60`, `pool=60` become `60`.
- `timeout=120` becomes `300`.
- `timeout=300` becomes `600`.
- Existing `timeout=600` stays `600`.

Tuple timeouts are normalized per element. For example `timeout=(10, 30)` becomes `timeout=(30, 60)`.

## Testing

Add focused tests for pure behavior where practical:

- Default language initializes to `zh_CN` after importing `web.i18n`.
- `StandardPipeline.produce_assets` uses concurrent frame processing when `video_concurrent_limit > 1`, while preserving frame order and total duration.
- Timeout constants in touched provider clients remain at the expected bucket values through direct unit assertions where the values are constructor defaults.

Run targeted tests plus lint:

- `python -m pytest ...`
- `python -m ruff check ...`

## Risks

Concurrency can increase load on providers and local resources. The default remains `1`, and the UI caps the setting at `10`.

Some providers may rate limit concurrent requests. Users can reduce the setting to `1` to restore serial behavior.

Longer timeout values may make failed network operations take longer to return, but they reduce premature failure for video and media generation calls.
