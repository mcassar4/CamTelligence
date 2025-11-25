import logging

import cv2
import numpy as np

logger = logging.getLogger("processor.movement")


class MovementDetector:
    """
    Per-camera motion detector mirroring the experimental background subtraction
    pipeline (KNN + threshold + morphology) with warmup and area gating.
    """

    def __init__(
        self,
        history: int = 200,
        kernel_size: int = 5,
        min_area: int = 1500,
        threshold: int = 200,
        area_threshold: int = 5000,
        warmup: int = 5,
        camera: str | None = None,
        max_foreground_ratio: float = 0.1,
        debug_dir: str | None = None,
    ) -> None:
        self.subtractor = cv2.createBackgroundSubtractorKNN(history=history, detectShadows=False)
        self.kernel = np.ones((kernel_size, kernel_size), np.uint8)
        self.min_area = min_area
        self.threshold = threshold
        self.area_threshold = area_threshold
        self.warmup = warmup
        self.camera = camera
        self.max_foreground_ratio = max_foreground_ratio
        self._frame_idx = 0
        self.debug_dir = debug_dir

    def detect(self, image: np.ndarray) -> list[tuple[int, int, int, int]]:
        frame_idx = self._frame_idx
        self._frame_idx += 1

        # Convert to grayscale to keep the background model simple/intensity-only.
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        fg_mask = self.subtractor.apply(gray)

        # Binarize and clean up noise from the raw foreground map.
        _, fg_mask = cv2.threshold(fg_mask, self.threshold, 255, cv2.THRESH_BINARY)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self.kernel)

        # Guard: warmup frames are used only to build the background model.
        fg_ratio = float(cv2.countNonZero(fg_mask)) / float(fg_mask.size)
        if frame_idx < self.warmup:
            logger.debug(
                "Skipping warmup frame for motion detector",
                extra={"extra_payload": {"camera": self.camera, "frame_idx": frame_idx}},
            )
            return []

        # Guard: drop frames where most pixels are foreground (e.g., sudden lighting).
        if fg_ratio > self.max_foreground_ratio:
            logger.debug(
                "Skipping frame due to high foreground ratio",
                extra={"extra_payload": {"ratio": fg_ratio, "camera": self.camera, "frame_idx": frame_idx}},
            )
            return []

        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boxes: list[tuple[int, int, int, int]] = []
        total_area = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Ignore tiny blobs; they are usually noise.
            if area < self.min_area:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            boxes.append((int(x), int(y), int(w), int(h)))
            total_area += int(area)

        # Declare motion only if the sum of kept contour areas crosses the threshold.
        motion = total_area >= self.area_threshold

        if motion and boxes:
            logger.debug(
                "Motion detected",
                extra={"extra_payload": {"count": len(boxes), "boxes": boxes[:5], "total_area": total_area}},
            )
            return boxes

        logger.debug(
            "No motion after area threshold",
            extra={"extra_payload": {"camera": self.camera, "total_area": total_area, "frame_idx": frame_idx}},
        )
        return []
