"""Animation frame builder – blink + tail wag + ball dribble composite."""

import sys
import time
from PIL import Image
from renderer import load_sprite, render_frame

FPS = 10

# ── Eye region (white + pupil combined) ──────────────────────────────────────
EYE_X1, EYE_Y1 = 35, 12
EYE_X2, EYE_Y2 = 36, 14

# ── Tail region ───────────────────────────────────────────────────────────────
TAIL_X1, TAIL_Y1 = 11, 42
TAIL_X2, TAIL_Y2 = 22, 50
TAIL_TIP_X2 = 17        # base x=18〜22 fixed; tip x=11〜17 moves
TAIL_WAG_AMP = 3        # ±3 px vertical swing

# ── Ball dribble ──────────────────────────────────────────────────────────────
BALL_DX_MAX = 4         # max rightward shift (pixels)

# Background fill color
BG = (18, 21, 26, 255)


# ── Sprite cleanup ────────────────────────────────────────────────────────────

def _clean_sprite(img: Image.Image) -> Image.Image:
    """Paint stray red jersey pixels in the tail wag zone to background."""
    frame = img.copy()
    pixels = frame.load()
    h = img.size[1]
    scan_y1 = max(0, TAIL_Y1 - TAIL_WAG_AMP - 4)
    scan_y2 = min(h - 1, TAIL_Y2 + TAIL_WAG_AMP + 2)
    for x in range(TAIL_X1, TAIL_TIP_X2 + 1):
        for y in range(scan_y1, scan_y2 + 1):
            r, g, b, a = pixels[x, y]
            if r > 60 and r > 2 * g:
                pixels[x, y] = BG
    return frame


# ── Helpers ───────────────────────────────────────────────────────────────────

def _head_green(img: Image.Image) -> tuple:
    """Sample the green head skin color just below the eye."""
    pixels = img.load()
    h = img.size[1]
    candidates = []
    for x in range(EYE_X1, EYE_X2 + 1):
        r, g, b, a = pixels[x, min(h - 1, EYE_Y2 + 2)]
        if g > r and g > b and r < 200:
            candidates.append((r, g, b, 255))
    if candidates:
        return candidates[len(candidates) // 2]
    return (34, 120, 40, 255)


# ── Blink ─────────────────────────────────────────────────────────────────────

def _blink(img: Image.Image, ratio: float) -> Image.Image:
    """Return a copy of img with eyelid descended by ratio (0.0=open, 1.0=closed)."""
    if ratio == 0.0:
        return img
    eye_h = EYE_Y2 - EYE_Y1 + 1
    close_rows = round(eye_h * ratio)
    lid_color = _head_green(img)
    frame = img.copy()
    pixels = frame.load()
    for y in range(EYE_Y1, EYE_Y1 + close_rows):
        for x in range(EYE_X1, EYE_X2 + 1):
            pixels[x, y] = lid_color
    return frame


# ── Tail wag ──────────────────────────────────────────────────────────────────

def _wag_tail(img: Image.Image, dy: int) -> Image.Image:
    """Return a copy of img with the tail tip shifted vertically by dy pixels."""
    if dy == 0:
        return img

    frame = img.copy()
    pixels = frame.load()
    h = img.size[1]
    pivot_x = TAIL_TIP_X2
    tip_x   = TAIL_X1

    tip_pixels: dict[tuple[int, int], tuple] = {}
    for y in range(TAIL_Y1 - TAIL_WAG_AMP, TAIL_Y2 + TAIL_WAG_AMP + 1):
        for x in range(TAIL_X1, TAIL_TIP_X2 + 1):
            if 0 <= y < h:
                tip_pixels[(x, y)] = img.getpixel((x, y))

    for x in range(TAIL_X1, TAIL_TIP_X2 + 1):
        for y in range(TAIL_Y1 - TAIL_WAG_AMP, TAIL_Y2 + TAIL_WAG_AMP + 1):
            if 0 <= y < h:
                pixels[x, y] = BG

    span = pivot_x - tip_x
    for (x, y), color in tip_pixels.items():
        blend = (pivot_x - x) / span
        shifted_dy = round(dy * blend)
        ny = y + shifted_dy
        if 0 <= ny < h:
            pixels[x, ny] = color

    return frame


# ── Ball dribble ──────────────────────────────────────────────────────────────

def _detect_ball(img: Image.Image) -> tuple[int, int, int, int]:
    """Auto-detect soccer ball bounding box (white cluster in right-lower area)."""
    pixels = img.load()
    w, h = img.size
    # Ball is right of character body (x>40), in lower portion
    xs, ys = [], []
    for x in range(40, w):
        for y in range(h * 3 // 5, h):
            r, g, b, a = pixels[x, y]
            if a < 128:
                continue
            brightness = (r + g + b) / 3
            if brightness > 120:
                xs.append(x)
                ys.append(y)
    if len(xs) >= 10:
        return min(xs), min(ys), max(xs), max(ys)
    print("[animation] WARNING: ball not auto-detected, using fallback coords")
    return 42, 49, 55, 59


def _extract_ball_pixels(img: Image.Image, bounds: tuple) -> dict:
    """Extract all non-background pixels within the ball bounding box."""
    x1, y1, x2, y2 = bounds
    pixels = img.load()
    w, h = img.size
    ball_px = {}
    for x in range(max(0, x1), min(w, x2 + 1)):
        for y in range(max(0, y1), min(h, y2 + 1)):
            r, g, b, a = pixels[x, y]
            # Lower threshold (10) to capture dark pentagon patches on the ball
            if a >= 128 and (
                abs(r - BG[0]) > 10 or abs(g - BG[1]) > 10 or abs(b - BG[2]) > 10
            ):
                ball_px[(x, y)] = (r, g, b, a)
    return ball_px


def _make_no_ball_base(img: Image.Image, ball_px: dict) -> Image.Image:
    """Return a copy of img with exactly the ball pixels erased to background.

    Only erases the detected ball_px positions — no padding — so adjacent
    character pixels (pants, feet) are never touched.
    """
    frame = img.copy()
    pixels = frame.load()
    for (x, y) in ball_px:
        pixels[x, y] = BG
    return frame


def _paint_ball(img: Image.Image, ball_px: dict, dx: int, dy: int = 0) -> Image.Image:
    """Return a copy of img with ball_px painted at offset (dx, dy)."""
    frame = img.copy()
    pixels = frame.load()
    w, h = img.size
    for (x, y), color in ball_px.items():
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h:
            pixels[nx, ny] = color
    return frame


# ── Frame builder ─────────────────────────────────────────────────────────────

def build_frames(sprite_path: str, save_cleaned: bool = True) -> list[str]:
    """Load sprite and build the full animation sequence as rendered strings."""
    img = load_sprite(sprite_path)
    img = _clean_sprite(img)

    if save_cleaned:
        import pathlib
        p = pathlib.Path(sprite_path)
        out = p.with_stem(p.stem + "_cleaned")
        img.save(str(out))
        print(f"[animation] cleaned sprite saved → {out.name}")

    # ── Ball setup ────────────────────────────────────────────────────────────
    ball_bounds = _detect_ball(img)
    x1, y1, x2, y2 = ball_bounds
    print(f"[animation] ball detected at x={x1}-{x2}, y={y1}-{y2}")
    ball_px = _extract_ball_pixels(img, ball_bounds)
    no_ball = _make_no_ball_base(img, ball_px)

    # ── Render helper ─────────────────────────────────────────────────────────
    def render(blink_ratio: float = 0.0, tail_dy: int = 0,
               ball_dx: int = 0, ball_dy: int = 0) -> str:
        # Always start from no_ball base, repaint ball at requested position
        f = _paint_ball(no_ball, ball_px, ball_dx, ball_dy)
        if blink_ratio > 0.0:
            f = _blink(f, blink_ratio)
        if tail_dy != 0:
            f = _wag_tail(f, tail_dy)
        return render_frame(f)

    # ── Pre-render variants ───────────────────────────────────────────────────
    idle = render()
    b35  = render(blink_ratio=0.35)
    b75  = render(blink_ratio=0.75)
    b100 = render(blink_ratio=1.0)

    amp = TAIL_WAG_AMP
    wag = {dy: render(tail_dy=dy) for dy in range(-amp, amp + 1) if dy != 0}

    # Dribble: ball rolls right then returns, with slight vertical bounce
    # dx profile: 0→1→2→3→4→4→3→2→1→0→0→0  (12 frames per cycle)
    # dy bounce: slight upward (-1) while moving, flat at extremes
    dribble_dxs = [1, 2, 3, 4, 4, 3, 2, 1, 0, 0, 0, 0]
    dribble_dys = [0, -1, -1, 0, 0, -1, -1, 0, 0, 0, 0, 0]
    drib = {
        (dx, dy): render(ball_dx=dx, ball_dy=dy)
        for dx, dy in set(zip(dribble_dxs, dribble_dys))
    }
    dribble_cycle = [drib[(dx, dy)] for dx, dy in zip(dribble_dxs, dribble_dys)]

    # ── Blink sequence (6 frames: open→close→open) ───────────────────────────
    blink_seq = [b35, b75, b100, b100, b75, b35]

    # ── Tail wag cycle (12 frames) ────────────────────────────────────────────
    wag_cycle = (
        [wag[-1], wag[-2], wag[-amp], wag[-2], wag[-1]]
        + [idle]
        + [wag[1],  wag[2],  wag[amp],  wag[2],  wag[1]]
        + [idle]
    )

    # ── Full animation loop ───────────────────────────────────────────────────
    # idle → blink → idle → wag×2 → dribble×2 → idle → blink → wag+dribble
    sequence = (
        [idle] * 10
        + blink_seq
        + [idle] * 6
        + wag_cycle * 2
        + [idle] * 4
        + dribble_cycle * 2
        + [idle] * 6
        + blink_seq
        + [idle] * 4
        + wag_cycle
        + dribble_cycle
        + [idle] * 4
    )

    return sequence


# ── Animation loop ────────────────────────────────────────────────────────────

def run(frames: list[str]) -> None:
    """Cycle through frames in a loop until Ctrl+C."""
    if not frames:
        return

    n_lines = frames[0].count("\n") + 1
    interval = 1.0 / FPS

    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    try:
        sys.stdout.write(frames[0] + "\n")
        sys.stdout.flush()
        idx = 1
        while True:
            time.sleep(interval)
            sys.stdout.write(f"\033[{n_lines}A\r")
            sys.stdout.write(frames[idx % len(frames)] + "\n")
            sys.stdout.flush()
            idx += 1
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[0m\033[?25h\n")
        sys.stdout.flush()
