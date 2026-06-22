from pixelle_video.services.api_media import APIProviderMediaService


def test_agnes_video_model_is_listed_with_text_to_video_capability():
    service = APIProviderMediaService(config={})

    workflows = service.list_workflows()
    agnes = next(
        workflow
        for workflow in workflows
        if workflow["key"] == "api/agnes/agnes-video-v2.0"
    )

    assert agnes["provider"] == "agnes"
    assert agnes["model"] == "agnes-video-v2.0"
    assert agnes["media_type"] == "video"
    assert "text_to_video" in agnes["adapter_ability_types"]
    assert agnes["api_contract_verified"] is True
