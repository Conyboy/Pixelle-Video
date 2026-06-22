# Agnes Video Provider Design

## Goal

Add Agnes as a direct API video generation provider for Pixelle-Video. The first version only supports text-to-video generation through the Agnes Video V2.0 model.

## Scope

This integration adds one API video model:

- `api/agnes/agnes-video-v2.0`

The first version supports:

- Text-to-video requests from Pixelle API media workflows.
- Bearer-token authentication with an Agnes API key.
- Task creation through `POST /v1/videos`.
- Result polling through the recommended `video_id` lookup endpoint: `GET /agnesapi?video_id=<VIDEO_ID>`.
- Downloading the completed mp4 result to Pixelle's local output path.

The first version does not support:

- Image-to-video.
- Multi-image video generation.
- Keyframe animation.
- Uploading local images to public storage.
- Native audio controls beyond Pixelle's existing narration overlay workflow.

## Agnes API Contract

The official Agnes Video V2.0 documentation describes an asynchronous task API.

Create task:

```http
POST https://apihub.agnes-ai.com/v1/videos
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

Minimum request body for this integration:

```json
{
  "model": "agnes-video-v2.0",
  "prompt": "A cinematic shot...",
  "height": 768,
  "width": 1152,
  "num_frames": 121,
  "frame_rate": 24
}
```

The create response includes both `task_id` and `video_id`. This integration will prefer `video_id`.

Poll result:

```http
GET https://apihub.agnes-ai.com/agnesapi?video_id=<VIDEO_ID>&model_name=agnes-video-v2.0
Authorization: Bearer <API_KEY>
```

Completion is detected when `status` is `completed`. The mp4 URL is expected in `remixed_from_video_id` based on the official response example. The client should also tolerate a future explicit `video_url` field if Agnes adds one.

## Architecture

Add a new `AgnesVideoClient` beside the existing provider clients in `pixelle_video/services/api_services`. It will expose the same `generate_video(prompt, image_path, save_path, model, duration, ...) -> str` shape used by `VideoClient`.

`VideoClient` will lazily construct the Agnes client and route models containing `agnes` to it. Because version one is text-to-video only, the Agnes adapter should reject non-empty `image_path` with a clear error.

`APIProviderMediaService` will register `agnes-video-v2.0` as an API video workflow with text-to-video capability metadata. Duration from Pixelle will be converted to Agnes `num_frames` using a default `frame_rate` of 24.

Configuration will follow the existing API provider pattern:

```yaml
api_providers:
  agnes:
    api_key: ""
    base_url: "https://apihub.agnes-ai.com"
    use_proxy: false
```

The config facade should expose `AGNES_API_KEY` and `AGNES_BASE_URL` for old-style client access.

## Data Flow

1. User selects `api/agnes/agnes-video-v2.0` in the API video model list.
2. Pixelle generates a scene prompt and passes it to `APIProviderMediaService`.
3. `APIProviderMediaService` resolves the provider/model and calls `VideoClient.generate_video`.
4. `VideoClient` routes to `AgnesVideoClient`.
5. `AgnesVideoClient` creates an Agnes video task with prompt, width, height, `num_frames`, and `frame_rate`.
6. `AgnesVideoClient` polls the recommended `video_id` endpoint until status is `completed` or a failure/timeout occurs.
7. `AgnesVideoClient` downloads the mp4 URL into `save_path`.
8. Pixelle continues its existing composition path and overlays narration audio as usual.

## Error Handling

The client should raise clear exceptions for:

- Missing Agnes API key.
- Non-empty `image_path`, because image-to-video is out of scope.
- Create-task response without `video_id`.
- Failed task status or API error payload.
- Completed response without a usable mp4 URL.
- Polling timeout.
- Download failure.

## Testing

Add unit tests for:

- Agnes task creation payload uses `model`, `prompt`, `height`, `width`, `num_frames`, and `frame_rate`.
- Agnes polling uses `video_id` and includes `model_name`.
- Completed result downloads the URL from `remixed_from_video_id`.
- Missing API key raises before network calls.
- Non-empty `image_path` raises a text-to-video-only error.
- `VideoClient` routes `agnes-video-v2.0` to Agnes.
- `APIProviderMediaService` lists `api/agnes/agnes-video-v2.0` as a text-to-video model.

Network calls should be mocked. No test should call the real Agnes API.
