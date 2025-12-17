import argparse
from pathlib import Path
from dataclasses import dataclass
import random
import cv2
import numpy as np
from typing import Iterable, List, Tuple

FRAME_ROOT = Path("scripts/motion_lab/frames")
EXP_ROOT = Path("scripts/motion_lab/experiments")

# Evaluation windows: frames 29-34 contain motion; all others are no-motion.
MOTION_FRAMES = set(range(29, 35))
def expected_label(idx: int) -> int:
    # Frames 29-34 are motion; everything else is no-motion.
    return 1 if idx in MOTION_FRAMES else 0


@dataclass(frozen=True)
class MotionParams:
    history: int
    kernel: int
    min_area: int
    threshold: int
    area_threshold: int
    max_fg_ratio: float

    def label(self) -> str:
        return (
            f"h{self.history}_k{self.kernel}_a{self.min_area}_t{self.threshold}"
            f"_ar{self.area_threshold}_fg{int(self.max_fg_ratio*1000)}"
        )

def random_params() -> MotionParams:
    return MotionParams(
        history=random.randint(2, 24),
        kernel=random.choice([4, 8, 12]),
        min_area=random.randint(8, 2048),
        threshold=random.randint(8, 2048),
        area_threshold=random.randint(8, 8912),
        max_fg_ratio=random.uniform(0.02, 0.6),
    )

def evaluate_params(frames: List[str], params: MotionParams, warmup: int = 15) -> Tuple[int, int]:
    subtractor = cv2.createBackgroundSubtractorKNN(history=params.history, detectShadows=False)
    kernel = np.ones((params.kernel, params.kernel), np.uint8)
    invalid = 0
    considered = 0

    for idx, frame_path in enumerate(frames):
        image = cv2.imread(frame_path)
        if image is None:
            continue
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        fg = subtractor.apply(gray)
        _, fg = cv2.threshold(fg, params.threshold, 255, cv2.THRESH_BINARY)
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel)

        fg_ratio = float(cv2.countNonZero(fg)) / float(fg.size)
        if idx < warmup or fg_ratio > params.max_fg_ratio:
            continue

        contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        total_area = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < params.min_area:
                continue
            total_area += int(area)

        predicted = 1 if total_area >= params.area_threshold else 0
        expected = expected_label(idx)
        if expected is None:
            continue
        considered += 1
        if predicted != expected:
            invalid += 1

    return invalid, considered

def _evaluate_worker(frames: List[str], params: MotionParams, warmup: int) -> Tuple[str, int, int]:
    invalid, considered = evaluate_params(frames, params, warmup=warmup)
    return params.label(), invalid, considered


# EVOLUTIONARY ALGORITHMS

def mutate(params: MotionParams, rate: float = 0.3) -> MotionParams:
    def pick(val, low, high, step=1):
        return max(low, min(high, val + random.randint(-step, step)))

    history = pick(params.history, 4, 24, step=1) if random.random() < rate else params.history
    kernel = random.choice([4, 8, 12]) if random.random() < rate else params.kernel
    min_area = pick(params.min_area, 8, 2048, step=16) if random.random() < rate else params.min_area
    threshold = pick(params.threshold, 8, 2048, step=16) if random.random() < rate else params.threshold
    area_threshold = pick(params.area_threshold, 8, 8912, step=16) if random.random() < rate else params.area_threshold
    max_fg_ratio = (
        max(0.02, min(0.6, params.max_fg_ratio + random.uniform(-0.04, 0.04)))
        if random.random() < rate
        else params.max_fg_ratio
    )
    return MotionParams(history, kernel, min_area, threshold, area_threshold, max_fg_ratio)

def crossover(a: MotionParams, b: MotionParams) -> MotionParams:
    return MotionParams(
        history=random.choice([a.history, b.history]),
        kernel=random.choice([a.kernel, b.kernel]),
        min_area=random.choice([a.min_area, b.min_area]),
        threshold=random.choice([a.threshold, b.threshold]),
        area_threshold=random.choice([a.area_threshold, b.area_threshold]),
        max_fg_ratio=random.choice([a.max_fg_ratio, b.max_fg_ratio]),
    )




def main() -> None:
    parser = argparse.ArgumentParser(description="Evolutionary motion parameter optimizer (uses captured frames).")
    parser.add_argument("--optimize", action="store_true", help="Run evolutionary search.")
    parser.add_argument("--generations", type=int, default=20, help="Number of generations (default: 20)")
    parser.add_argument("--pop-size", type=int, default=24, help="Population size (default: 24)")
    parser.add_argument("--warmup", type=int, default=15, help="Warmup frames to skip from scoring (default: 15)")
    parser.add_argument("--export-best", action="store_true", help="Export masks/annotated frames for the best params.")
    args = parser.parse_args()