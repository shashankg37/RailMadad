from pathlib import Path

from pydantic import BaseModel, Field

from app.core.config import get_settings


class Detection(BaseModel):
    class_id: int
    label: str
    confidence: float = Field(ge=0, le=1)
    bbox: list[float]


class YOLOService:
    """Extract visual evidence without deciding complaint category or severity."""

    def __init__(self):
        self._model = None

    def model(self):
        if self._model is None:
            settings = get_settings()
            path = settings.resolved_yolo_model_path
            if not path.is_file():
                raise RuntimeError(f"YOLO model not found at {path}; place trained best.pt there")
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise RuntimeError("Install ultralytics to enable YOLO inference") from exc
            self._model = YOLO(str(path))
        return self._model

    def infer(self, image: Path) -> tuple[list[Detection], Path | None]:
        image = Path(image)
        model = self.model()
        settings = get_settings()
        result = model(str(image), conf=settings.yolo_confidence_threshold, verbose=False)[0]
        names = result.names or getattr(model, "names", {})
        detections: list[Detection] = []
        for box in result.boxes or []:
            class_id = int(box.cls[0])
            label = names.get(class_id, str(class_id)) if hasattr(names, "get") else names[class_id]
            detections.append(
                Detection(
                    class_id=class_id,
                    label=str(label),
                    confidence=float(box.conf[0]),
                    bbox=[round(float(value), 2) for value in box.xyxy[0].tolist()],
                )
            )

        annotated = image.with_name(f"{image.stem}.annotated.jpg")
        try:
            import cv2

            cv2.imwrite(str(annotated), result.plot())
        except ImportError:
            annotated = None
        return detections, annotated
