import os
from pathlib import Path
from typing import Optional

import numpy as np
import logging

from ..dto import Detection
from ..image_ops import crop, encode_jpeg
from ultralytics import YOLO

logger = logging.getLogger("processor.yolo")

COCO_CLASS_NAMES = (
    "person",
    "bicycle",
    "car",
    "motorbike",
    "_",
    "bus",
    "train",
    "truck",
)

PERSON_CLASS_ID = 0
VEHICLE_CLASS_IDS = {1, 2, 3, 5, 6, 7}  # bicycle, car, motorbike, bus, train, truck


class CocoYoloDetector:
    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
        min_vehicle_confidence: Optional[float] = None,
    ) -> None:
        default_model = Path(__file__).resolve().parent / "yolov8s.pt"
        self.model_path = model_path or os.getenv("YOLO_MODEL_PATH", str(default_model))
        self.conf_threshold = conf_threshold if conf_threshold is not None else float(os.getenv("YOLO_CONF_THRESHOLD", "0.4"))
        self.iou_threshold = iou_threshold if iou_threshold is not None else float(os.getenv("YOLO_IOU_THRESHOLD", "0.45"))
        self.min_vehicle_confidence = (
            min_vehicle_confidence if min_vehicle_confidence is not None else float(os.getenv("YOLO_VEHICLE_CONF", "0.3"))
        )
        self.model = YOLO(self.model_path)
        logger.debug(
            "YOLO detector initialized",
            extra={
                "extra_payload": {
                    "model_path": self.model_path,
                    "conf_threshold": self.conf_threshold,
                    "iou_threshold": self.iou_threshold,
                    "min_vehicle_confidence": self.min_vehicle_confidence,
                }
            },
        )

    def predict(self, image: np.ndarray) -> dict[str, list[Detection]]:
        results = self.model.predict(source=image, verbose=False, conf=self.conf_threshold, iou=self.iou_threshold)
        if not results:
            return {"persons": [], "vehicles": []}
        res = results[0]
        if not hasattr(res, "boxes") or res.boxes is None:
            return {"persons": [], "vehicles": []}

        detections: dict[str, list[Detection]] = {"persons": [], "vehicles": []}

        for box in res.boxes:
            cls_id = int(box.cls.item())
            conf = float(box.conf.item())
            if cls_id == PERSON_CLASS_ID:
                target = "persons"
            elif cls_id in VEHICLE_CLASS_IDS:
                if conf < self.min_vehicle_confidence:
                    continue
                target = "vehicles"
            else:
                continue

            x1, y1, x2, y2 = box.xyxy[0].tolist()
            w = x2 - x1
            h = y2 - y1
            cropped = crop(image, (x1, y1, w, h))
            detections[target].append(
                Detection(
                    bbox=(int(x1), int(y1), int(w), int(h)),
                    score=conf,
                    crop_bytes=encode_jpeg(cropped),
                )
            )
        logger.debug(
            "YOLO detections",
            extra={
                "extra_payload": {
                    "persons": len(detections["persons"]),
                    "vehicles": len(detections["vehicles"]),
                    "conf_threshold": self.conf_threshold,
                }
            },
        )
        return detections
