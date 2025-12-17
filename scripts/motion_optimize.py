import argparse
from pathlib import Path
from dataclasses import dataclass


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

def main() -> None:
    parser = argparse.ArgumentParser(description="Evolutionary motion parameter optimizer (uses captured frames).")
    parser.add_argument("--optimize", action="store_true", help="Run evolutionary search.")
    parser.add_argument("--generations", type=int, default=20, help="Number of generations (default: 20)")
    parser.add_argument("--pop-size", type=int, default=24, help="Population size (default: 24)")
    parser.add_argument("--warmup", type=int, default=15, help="Warmup frames to skip from scoring (default: 15)")
    parser.add_argument("--export-best", action="store_true", help="Export masks/annotated frames for the best params.")
    args = parser.parse_args()