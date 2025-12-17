import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Evolutionary motion parameter optimizer (uses captured frames).")
    parser.add_argument("--optimize", action="store_true", help="Run evolutionary search.")
    parser.add_argument("--generations", type=int, default=20, help="Number of generations (default: 20)")
    parser.add_argument("--pop-size", type=int, default=24, help="Population size (default: 24)")
    parser.add_argument("--warmup", type=int, default=15, help="Warmup frames to skip from scoring (default: 15)")
    parser.add_argument("--export-best", action="store_true", help="Export masks/annotated frames for the best params.")
    args = parser.parse_args()