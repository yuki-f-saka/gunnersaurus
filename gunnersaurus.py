"""Gunnersaurus TUI — entry point."""

import pathlib
from animation import build_frames, run

SPRITE = pathlib.Path(__file__).parent / "images" / "perfect_image.png"


def main() -> None:
    frames = build_frames(str(SPRITE))
    run(frames)


if __name__ == "__main__":
    main()
