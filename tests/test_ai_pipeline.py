import pytest

from app.services.ai_pipeline import (
    Detection,
    DEPARTMENT_ROUTING,
    sample_video_frames,
    safety_and_departments,
)


def test_safety_rules_override_for_critical_electrical_hazard():
    detections = [
        Detection(class_id=3, label="electrical_appliance", confidence=0.9, bbox=[0, 0, 10, 10])
    ]

    final_severity, departments, audit = safety_and_departments(detections, 3)

    assert final_severity == 4
    assert departments == ["Electrical"]
    assert audit["override_applied"] is True
    assert audit["model_severity"] == 3


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("broken_seat", ["Maintenance / Carriage & Wagon"]),
        ("dirty_coach", ["Housekeeping / Sanitation"]),
        ("water_leakage", ["Engineering / Carriage & Wagon"]),
        ("electrical_appliance", ["Electrical"]),
        ("crowded", ["Operations / Security"]),
    ],
)
def test_department_routing_matches_expected_sections(label, expected):
    assert DEPARTMENT_ROUTING[label] == expected


def test_video_frame_sampling_respects_limits():
    frames = sample_video_frames(20, max_frames=8, interval_seconds=2)

    assert len(frames) <= 8
    assert frames == [0, 2, 4, 6, 8, 10, 12, 14]
