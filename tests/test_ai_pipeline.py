import pytest
import asyncio

from app.services.ai_pipeline import (
    Detection,
    DEPARTMENT_ROUTING,
    sample_video_frames,
    safety_and_departments,
)


def test_safety_rules_override_for_critical_fire_evidence():
    detections = [
        Detection(class_id=3, label="fire_sign", confidence=0.9, bbox=[0, 0, 10, 10])
    ]

    final_severity, departments, audit = safety_and_departments(detections, 3)

    assert final_severity == 5
    assert departments == ["Fire & Safety"]
    assert audit["override_applied"] is True
    assert audit["model_severity"] == 3


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("garbage", ["Housekeeping / Sanitation"]),
        ("broken_glass_or_cracked_window", ["Maintenance / Carriage & Wagon"]),
        ("graffiti", ["Security / Railway Protection Force"]),
        ("fire_sign", ["Fire & Safety"]),
        ("water_leak", ["Engineering / Carriage & Wagon"]),
    ],
)
def test_department_routing_matches_expected_sections(label, expected):
    assert DEPARTMENT_ROUTING[label] == expected


def test_video_frame_sampling_respects_limits():
    frames = sample_video_frames(20, max_frames=8, interval_seconds=2)

    assert len(frames) <= 8
    assert frames == [0, 2, 4, 6, 8, 10, 12, 14]


def test_multimodal_evidence_reaches_qwen(monkeypatch, tmp_path):
    from app.services import ai_pipeline

    image = tmp_path / "complaint.jpg"
    image.write_bytes(b"image")

    monkeypatch.setattr(
        ai_pipeline.yolo_service,
        "infer",
        lambda _image: ([Detection(class_id=4, label="water_leak", confidence=0.81, bbox=[1, 2, 3, 4])], None),
    )
    monkeypatch.setattr(ai_pipeline.ocr_service, "read", lambda _image: [])

    async def fake_analyze(_image, detections, _ocr, _transcript, user_text=None):
        assert detections[0].label == "water_leak"
        assert user_text == "There is water on the floor"
        return ai_pipeline.AIResult(
            category="water_leak",
            subcategory="coach leakage",
            severity=3,
            summary="Water is present on the coach floor.",
            suggested_action="Inspect and isolate the leak.",
            confidence=0.9,
        )

    monkeypatch.setattr(ai_pipeline.qwen_client, "analyze", fake_analyze)
    result, state = asyncio.run(ai_pipeline.analyze_complaint("image", image, "There is water on the floor"))

    assert result.category == "water_leak"
    assert result.evidence[0]["label"] == "water_leak"
    assert state.status == "classified"
