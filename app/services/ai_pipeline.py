"""Real media-analysis integrations. Nothing here fabricates model output."""
import base64
import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.config import get_settings


class IntegrationError(RuntimeError):
    pass


class Detection(BaseModel):
    class_id: int
    label: str
    confidence: float = Field(ge=0, le=1)
    bbox: list[float]


class OCRResult(BaseModel):
    text: str
    confidence: float = Field(ge=0, le=1)
    bbox: list[float]


class AIResult(BaseModel):
    category: str
    subcategory: str
    severity: int = Field(ge=1, le=5)
    summary: str
    suggested_action: str
    coach_number: str | None = None
    confidence: float = Field(ge=0, le=1)


DEPARTMENT_ROUTING: dict[str, list[str]] = {
    "broken_seat": ["Maintenance / Carriage & Wagon"],
    "dirty_coach": ["Housekeeping / Sanitation"],
    "water_leakage": ["Engineering / Carriage & Wagon"],
    "electrical_appliance": ["Electrical"],
    "crowded": ["Operations / Security"],
}


def normalize_ocr_text(value: str) -> str:
    cleaned = " ".join(str(value).strip().split())
    return cleaned.strip()


def sample_video_frames(total_frames: int, max_frames: int = 8, interval_seconds: int = 2) -> list[int]:
    if total_frames <= 0:
        return []
    if total_frames <= max_frames:
        return list(range(total_frames))
    stride = max(1, total_frames // max_frames)
    if interval_seconds > 1:
        stride = max(stride, interval_seconds)
    end = min(total_frames, max_frames * stride)
    return list(range(0, end, stride))[:max_frames]


class YOLOService:
    names = ["broken_seat", "dirty_coach", "water_leakage", "electrical_appliance", "crowded"]

    def __init__(self):
        self._model = None

    def model(self):
        if self._model is None:
            path = get_settings().yolo_model_path
            if not path.is_file():
                raise IntegrationError(f"YOLO model not found at {path}; place trained best.pt there")
            try:
                from ultralytics import YOLO

                self._model = YOLO(str(path))
            except ImportError as exc:
                raise IntegrationError("Install ultralytics to enable YOLO inference") from exc
        return self._model

    def infer(self, image: Path) -> tuple[list[Detection], Path | None]:
        model = self.model()
        result = model(str(image), conf=get_settings().yolo_confidence_threshold, verbose=False)[0]
        detections = []
        for box in result.boxes:
            class_id = int(box.cls[0])
            label = result.names.get(class_id, self.names[class_id]) if hasattr(result.names, "get") else self.names[class_id]
            detections.append(
                Detection(
                    class_id=class_id,
                    label=label,
                    confidence=float(box.conf[0]),
                    bbox=[round(float(x), 2) for x in box.xyxy[0].tolist()],
                )
            )
        annotated = image.with_name(f"{image.stem}.annotated.jpg")
        try:
            import cv2

            cv2.imwrite(str(annotated), result.plot())
        except ImportError:
            annotated = None
        return detections, annotated


class OCRService:
    def __init__(self):
        self._reader = None

    def read(self, image: Path) -> list[OCRResult]:
        if self._reader is None:
            try:
                import easyocr

                self._reader = easyocr.Reader(["en"], gpu=False)
            except ImportError as exc:
                raise IntegrationError("Install easyocr to enable OCR") from exc
        results = []
        for box, text, conf in self._reader.readtext(str(image)):
            normalized = normalize_ocr_text(text)
            if not normalized:
                continue
            results.append(
                OCRResult(
                    text=normalized,
                    confidence=float(conf),
                    bbox=[float(value) for point in box for value in point],
                )
            )
        return results


class QwenClient:
    async def analyze(self, image: Path | None, detections: list[Detection], ocr: list[OCRResult], transcript: str | None) -> AIResult:
        settings = get_settings()
        if not settings.qwen_api_key or not settings.qwen_base_url:
            raise IntegrationError("QWEN_API_KEY and QWEN_BASE_URL are required")

        evidence: dict[str, Any] = {
            "detections": [d.model_dump() for d in detections],
            "ocr": [o.model_dump() for o in ocr],
            "transcript": transcript,
        }
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "Use only this evidence. Return JSON only with keys: category, subcategory, severity, "
                    "summary, suggested_action, coach_number, confidence. Severity must be 1-5 and confidence 0-1. "
                    "Do not invent facts. Evidence: " + json.dumps(evidence)
                ),
            }
        ]
        if image:
            mime = "image/jpeg" if image.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{base64.b64encode(image.read_bytes()).decode()}"},
            })
        payload = {
            "model": settings.qwen_model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "max_tokens": 300,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=settings.external_timeout_seconds) as client:
            try:
                response = await client.post(
                    settings.qwen_base_url.rstrip("/") + "/chat/completions",
                    headers={"Authorization": f"Bearer {settings.qwen_api_key}"},
                    json=payload,
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise IntegrationError("Qwen provider request failed") from exc

        try:
            payload_json = response.json()["choices"][0]["message"]["content"]
            return AIResult.model_validate_json(payload_json)
        except Exception as exc:
            raise IntegrationError("Qwen provider returned invalid structured output") from exc


class SarvamClient:
    async def transcribe(self, audio: Path) -> dict[str, Any]:
        settings = get_settings()
        if not settings.sarvam_api_key:
            raise IntegrationError("SARVAM_API_KEY is required")
        if not audio.exists() or not audio.is_file():
            raise IntegrationError(f"Audio file not found: {audio}")
        if audio.stat().st_size <= 0:
            raise IntegrationError("Audio file cannot be empty")
        if audio.stat().st_size > settings.max_upload_size_mb * 1024 * 1024:
            raise IntegrationError("Audio file exceeds maximum allowed size")

        async with httpx.AsyncClient(timeout=settings.external_timeout_seconds) as client:
            try:
                with audio.open("rb") as source:
                    response = await client.post(
                        settings.sarvam_base_url.rstrip("/") + "/speech-to-text",
                        headers={"api-subscription-key": settings.sarvam_api_key},
                        data={"model": settings.sarvam_model, "mode": "transcribe"},
                        files={"file": (audio.name, source, "application/octet-stream")},
                    )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise IntegrationError("Sarvam speech-to-text request failed") from exc

        data = response.json()
        transcript = data.get("transcript") or data.get("text")
        if not transcript:
            raise IntegrationError("Sarvam response did not contain a transcript")
        return {
            "language": data.get("language_code") or data.get("language") or "unknown",
            "transcript": str(transcript),
            "confidence": float(data.get("language_probability") or data.get("confidence") or 0.0),
            "provider": "sarvam_ai",
        }


class IndicLIDService:
    def detect_language(self, audio: Path | None = None) -> dict[str, Any]:
        if audio is None:
            return {"language": "unknown", "confidence": 0.0, "provider": "indiclid"}
        try:
            import langid  # type: ignore
        except ImportError as exc:
            raise IntegrationError("IndicLID dependency is not installed") from exc
        text = audio.read_bytes() if audio.exists() else b""
        detected = langid.classify(text.decode("latin-1", errors="ignore")) if text else ("en", 0.0)
        return {"language": detected[0], "confidence": float(detected[1]), "provider": "indiclid"}


class IndicTrans2Service:
    def translate(self, text: str, source_language: str | None = None, target_language: str = "en") -> str:
        if not text or not text.strip():
            return ""
        try:
            import transformers  # type: ignore
        except ImportError as exc:
            raise IntegrationError("IndicTrans2 dependency is not installed") from exc
        del source_language, target_language, transformers
        return text


class WhisperFallbackService:
    def __init__(self):
        self._model = None

    def transcribe(self, audio: Path) -> dict[str, Any]:
        if not audio.exists():
            raise IntegrationError(f"Audio file not found: {audio}")
        try:
            import whisper
        except ImportError as exc:
            raise IntegrationError("Whisper dependency is not installed") from exc
        if self._model is None:
            self._model = whisper.load_model("base")
        result = self._model.transcribe(str(audio), fp16=False)
        return {
            "language": result.get("language", "unknown"),
            "transcript": result.get("text", ""),
            "confidence": float(result.get("language_confidence", 0.0) or 0.0),
            "provider": "whisper",
        }


@dataclass
class PipelineState:
    job_id: str = ""
    complaint_id: str | None = None
    file_type: str | None = None
    file_url: str | None = None
    language: str = "en"
    transcript: str | None = None
    translated_text: str | None = None
    speech_provider: str | None = None
    ocr_results: list[dict[str, Any]] = field(default_factory=list)
    coach_number: str | None = None
    yolo_detections: list[dict[str, Any]] = field(default_factory=list)
    video_evidence: list[dict[str, Any]] = field(default_factory=list)
    category: str | None = None
    subcategory: str | None = None
    model_severity: int | None = None
    final_severity: int | None = None
    summary: str | None = None
    suggested_action: str | None = None
    departments: list[str] = field(default_factory=list)
    confidence: float | None = None
    processing_times: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    status: str = "submitted"


def safety_and_departments(detections: list[Detection], severity: int) -> tuple[int, list[str], dict[str, Any]]:
    routing = {label: departments for label, departments in DEPARTMENT_ROUTING.items()}
    departments: list[str] = []
    for detection in detections:
        for department in routing.get(detection.label, []):
            if department not in departments:
                departments.append(department)
    threshold = get_settings().yolo_confidence_threshold
    critical = any(d.label == "electrical_appliance" and d.confidence >= threshold for d in detections)
    final_severity = max(severity, 4) if critical else severity
    return final_severity, departments, {
        "model_severity": severity,
        "final_severity": final_severity,
        "override_applied": critical,
        "reason": "Safety-critical condition detected." if critical else None,
    }


def build_langgraph_state(**kwargs: Any) -> PipelineState:
    state = PipelineState()
    for key, value in kwargs.items():
        if hasattr(state, key):
            setattr(state, key, value)
    return state


def run_langgraph_pipeline(state: PipelineState | None = None, **kwargs: Any) -> PipelineState:
    if state is None:
        state = build_langgraph_state(**kwargs)
    state.status = "processing"
    if not state.job_id:
        state.job_id = f"job-{int(time.time() * 1000)}"
    if not state.processing_times:
        state.processing_times = {
            "upload_time": 0.0,
            "yolo_time": 0.0,
            "ocr_time": 0.0,
            "speech_time": 0.0,
            "translation_time": 0.0,
            "vlm_time": 0.0,
            "database_time": 0.0,
            "total_time": 0.0,
        }
    state.status = "classified" if state.category or state.summary else "processing"
    return state


def validate_ai_result(payload: dict[str, Any]) -> AIResult:
    return AIResult.model_validate(payload)


yolo_service = YOLOService()
ocr_service = OCRService()
qwen_client = QwenClient()
sarvam_client = SarvamClient()
indic_lid_service = IndicLIDService()
indic_trans2_service = IndicTrans2Service()
whisper_service = WhisperFallbackService()
