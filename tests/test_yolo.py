from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.yolo_service import YOLOService


class FakeBox:
    cls = [4]
    conf = [0.81]
    xyxy = [SimpleNamespace(tolist=lambda: [1.2, 2.3, 40.4, 50.5])]


class FakeResult:
    names = {
        0: "garbage",
        1: "broken_glass_or_cracked_window",
        2: "graffiti",
        3: "fire_sign",
        4: "water_leak",
    }
    boxes = [FakeBox()]

    def plot(self):
        return object()


def test_inference_normalizes_embedded_model_names(monkeypatch, tmp_path):
    service = YOLOService()
    monkeypatch.setitem(__import__("sys").modules, "cv2", SimpleNamespace(imwrite=lambda *args: True))
    monkeypatch.setattr(service, "model", lambda: FakeModel())

    detections, _ = service.infer(tmp_path / "image.jpg")

    assert detections[0].label == "water_leak"
    assert detections[0].confidence == 0.81
    assert detections[0].bbox == [1.2, 2.3, 40.4, 50.5]


def test_empty_detection_result_is_valid(monkeypatch, tmp_path):
    service = YOLOService()
    monkeypatch.setattr(service, "model", lambda: EmptyModel())
    monkeypatch.setitem(__import__("sys").modules, "cv2", SimpleNamespace(imwrite=lambda *args: True))

    detections, _ = service.infer(tmp_path / "image.jpg")

    assert detections == []


@pytest.mark.skipif(not Path("models/weights/best.pt").is_file(), reason="trained model is not available")
def test_model_loads_when_ultralytics_is_installed():
    pytest.importorskip("ultralytics")
    model = YOLOService().model()
    assert set(model.names.values()) == {
        "garbage",
        "broken_glass_or_cracked_window",
        "graffiti",
        "fire_sign",
        "water_leak",
    }


class FakeModel:
    names = FakeResult.names

    def __call__(self, *_args, **_kwargs):
        return [FakeResult()]


class EmptyModel:
    names = FakeResult.names

    def __call__(self, *_args, **_kwargs):
        return [SimpleNamespace(names=self.names, boxes=[], plot=lambda: object())]
