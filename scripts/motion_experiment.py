"""
Run a single motion experiment with parameters on captured frames. Algorithm is based on https://drlee.io/build-an-ai-motion-detector-with-opencv-28fbbc762449
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

# Keep read/write paths aligned with the capture script.
FRAME_ROOT = Path("scripts/motion_lab/frames")
EXP_ROOT = Path("scripts/motion_lab/experiments")


def run_experiment(
    frames: List[str],
    history: int,
    kernel_size: int,
    min_area: int,
    threshold: int,
    area_threshold: int,
    max_fg_ratio: float,
    warmup: int,
    label: str,
) -> None:
    out_dir = EXP_ROOT / label
    masks_dir = out_dir / "masks"
    anno_dir = out_dir / "annotated"
    masks_dir.mkdir(parents=True, exist_ok=True)
    anno_dir.mkdir(parents=True, exist_ok=True)
    # Ensure output folders exist before processing frames so results can be stored safely.
    subtractor = cv2.createBackgroundSubtractorKNN(history=history, detectShadows=False)
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    # Set up the subtractor and the morphology kernel used for cleaning the foreground mask.
    for idx, frame_path in enumerate(frames):
        image = cv2.imread(frame_path)
        if image is None:
            continue
        # Work in grayscale where background subtraction only sees intensity changes.
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        fg = subtractor.apply(gray)
        # Binarize and open to filter out noise from the raw foreground map.
        _, fg = cv2.threshold(fg, threshold, 255, cv2.THRESH_BINARY)
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel)
        fg_ratio = float(cv2.countNonZero(fg)) / float(fg.size)
        if idx < warmup or fg_ratio > max_fg_ratio:
            # Skip initial warmup frames or frames where too much of the image is marked foreground.
            continue

        contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes: List[Tuple[int, int, int, int]] = []
        total_area = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            boxes.append((x, y, w, h))
            total_area += int(area)
        # Collect bounding boxes and accumulate contour area for motion assessment.

        mask_name = masks_dir / f"mask_{idx:04d}.png"
        cv2.imwrite(str(mask_name), fg)
        # Persist the cleaned foreground mask for later inspection.

        annotated = image.copy()
        for (x, y, w, h) in boxes:
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 0, 255), thickness=4)
        status = "motion" if total_area >= area_threshold else "nomotion"
        frame_name = anno_dir / f"frame_{idx:04d}_{status}.jpg"
        cv2.imwrite(str(frame_name), annotated)
        # Save the annotated frame with motion boxes and a status label.


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a single motion experiment with given params.")
    parser.add_argument("--history", type=int, required=True, help="Background subtractor history.")
    parser.add_argument("--kernel", type=int, required=True, help="Morph kernel size (odd integer).")
    parser.add_argument("--min-area", type=int, required=True, help="Minimum contour area.")
    parser.add_argument("--threshold", type=int, required=True, help="Mask binarization threshold.")
    parser.add_argument("--area-threshold", type=int, required=True, help="Total area threshold to declare motion.")
    parser.add_argument(
        "--max-fg-ratio",
        type=float,
        required=True,
        help="Skip frames if foreground ratio exceeds this (must match optimizer output).",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=15,
        help="Frames to skip for warmup (use the same value you optimized with; default aligns with optimizer).",
    )
    parser.add_argument("--out-label", required=True, help="Label for output directory under experiments.")
    args = parser.parse_args()

    frames = sorted(str(p) for p in FRAME_ROOT.glob("frame_*.jpg"))
    if not frames:
        raise SystemExit(f"No frames found in {FRAME_ROOT}. Capture frames first (scripts/motion_capture.py).")

    run_experiment(
        frames=frames,
        history=args.history,
        kernel_size=args.kernel,
        min_area=args.min_area,
        threshold=args.threshold,
        area_threshold=args.area_threshold,
        max_fg_ratio=args.max_fg_ratio,
        warmup=args.warmup,
        label=args.out_label,
    )
    print(f"Done. Results written to {EXP_ROOT}/{args.out_label}/")


if __name__ == "__main__":
    main()
