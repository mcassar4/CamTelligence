"""
Capture frames from the hardcoded DOOR camera for offline motion tuning.

Usage:
  python scripts/motion_capture.py --count 60 --interval 1.0
Frames are written to scripts/motion_lab/frames/frame_0000.jpg, etc.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2


DOOR_SOURCE = ## HIDDEN STREAM ADDRESS
# Keep capture outputs under scripts/motion_lab to stay consistent with the experiment runner.
FRAME_ROOT = Path("scripts/motion_lab/frames")


def capture_frames(source: str, frames_dir: Path, count: int, interval: float) -> None:
    frames_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise SystemExit(f"Failed to open source: {source}")
    captured = 0
    try:
        while captured < count:
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(interval)
                continue
            out_path = frames_dir / f"frame_{captured:04d}.jpg"
            cv2.imwrite(str(out_path), frame)
            captured += 1
            time.sleep(interval)
    finally:
        cap.release()


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture frames from DOOR camera for motion tuning.")
    parser.add_argument("--count", type=int, default=60, help="Number of frames to capture (default: 60)")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between frames (default: 1.0)")
    parser.add_argument("--out", default=str(FRAME_ROOT), help="Output directory for frames")
    args = parser.parse_args()

    frames_dir = Path(args.out)
    print(f"Capturing {args.count} frames from {DOOR_SOURCE} into {frames_dir} ...")
    capture_frames(DOOR_SOURCE, frames_dir, args.count, args.interval)
    print("Capture complete.")


if __name__ == "__main__":
    main()
