"""Blink frame generation and animation loop."""

import sys
import time
from PIL import Image
from renderer import load_sprite, render_frame

# Frames per second for the animation loop
FPS = 8
# How many open-eye frames before each blink
OPEN_HOLD = 10


def find_eye_box(img: Image.Image, brightness: int = 180) -> tuple[int, int, int, int] | None:
    """Return (x1, y1, x2, y2) bounding box of the eye region.

    Strategy: collect bright pixels in the upper half, then keep only the
    topmost contiguous cluster (the eye), discarding lower white areas
    such as the jersey collar / shoulder.
    """
    pixels = img.load()
    w, h = img.size

    # Gather all bright pixels in upper third (head/face area only)
    bright: list[tuple[int, int]] = []
    for y in range(h // 3):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r > brightness and g > brightness and b > brightness:
                bright.append((x, y))

    if not bright:
        return None

    # Find the y-row with the most bright pixels (peak density = eye center)
    from collections import Counter
    y_counts = Counter(p[1] for p in bright)
    peak_y = y_counts.most_common(1)[0][0]

    # Grow a contiguous y-range upward and downward from peak_y,
    # stopping as soon as we hit a row with NO bright pixels.
    # This avoids pulling in lower white areas (jersey shoulder, etc.)
    bright_ys = set(y_counts.keys())
    y_top = peak_y
    while y_top - 1 in bright_ys:
        y_top -= 1
    y_bot = peak_y
    while y_bot + 1 in bright_ys:
        y_bot += 1

    eye_pixels = [(x, y) for x, y in bright if y_top <= y <= y_bot]

    if not eye_pixels:
        return None

    xs = [p[0] for p in eye_pixels]
    ys = [p[1] for p in eye_pixels]
    return (min(xs), min(ys), max(xs), max(ys))


def _sample_eyelid_color(img: Image.Image, x1: int, y1: int, x2: int, y2: int) -> tuple:
    """Sample the green head color just below the eye bounding box."""
    pixels = img.load()
    candidates = []
    h = img.size[1]
    for x in range(x1, x2 + 1):
        r, g, b, a = pixels[x, min(h - 1, y2 + 1)]
        # Accept green-ish pixels (not white/bright)
        if g > r and g > b and r < 200:
            candidates.append((r, g, b))
    if candidates:
        r = sum(c[0] for c in candidates) // len(candidates)
        g = sum(c[1] for c in candidates) // len(candidates)
        b = sum(c[2] for c in candidates) // len(candidates)
        return (r, g, b, 255)
    # Fallback: dark green
    return (34, 120, 40, 255)


def _close_eye(img: Image.Image, box: tuple, ratio: float) -> Image.Image:
    """Return a copy of img with the eye partially closed.

    ratio: 0.0 = fully open, 1.0 = fully closed.
    The eyelid descends from the top of the eye bounding box.
    """
    x1, y1, x2, y2 = box
    eye_h = y2 - y1 + 1
    close_rows = round(eye_h * ratio)
    if close_rows == 0:
        return img

    lid_color = _sample_eyelid_color(img, x1, y1, x2, y2)
    frame = img.copy()
    pixels = frame.load()

    for y in range(y1, y1 + close_rows):
        for x in range(x1, x2 + 1):
            r, g, b, a = pixels[x, y]
            if r > 150 and g > 150 and b > 150:  # was a bright eye pixel
                pixels[x, y] = lid_color

    return frame


def build_frames(sprite_path: str) -> list[str]:
    """Load sprite and build rendered string frames for the blink cycle."""
    img = load_sprite(sprite_path)
    box = find_eye_box(img)

    open_rendered = render_frame(img)

    if box is None:
        # No eye found — static display
        return [open_rendered] * (OPEN_HOLD + 4)

    blink_sequence = [
        (0.0,  OPEN_HOLD),   # fully open  × OPEN_HOLD frames
        (0.35, 1),           # 35 % closed × 1
        (0.75, 1),           # 75 % closed × 1
        (1.0,  2),           # fully closed× 2
        (0.75, 1),           # 75 % open   × 1
        (0.35, 1),           # 35 % open   × 1
    ]

    frames = []
    for ratio, count in blink_sequence:
        if ratio == 0.0:
            rendered = open_rendered
        else:
            rendered = render_frame(_close_eye(img, box, ratio))
        frames.extend([rendered] * count)

    return frames


def run(frames: list[str]) -> None:
    """Animate frames in a loop. Ctrl+C exits cleanly."""
    if not frames:
        return

    n_lines = frames[0].count("\n") + 1
    interval = 1.0 / FPS

    # Hide cursor
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    try:
        # Print the first frame to establish position
        sys.stdout.write(frames[0] + "\n")
        sys.stdout.flush()
        idx = 1
        while True:
            time.sleep(interval)
            # Move cursor up to top of frame, then overwrite
            sys.stdout.write(f"\033[{n_lines}A\r")
            sys.stdout.write(frames[idx % len(frames)] + "\n")
            sys.stdout.flush()
            idx += 1
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[0m\033[?25h\n")
        sys.stdout.flush()
