#!/usr/bin/env python3
"""Interactive coordinate inspector – True Color ▀ terminal display with mouse tracking."""

import os
import re
import sys
import tty
import json
import select
import termios

from renderer import load_sprite, render_frame, TARGET_SIZE

IMAGE_PATH = "images/perfect_image.png"
COORDS_FILE = "coords.json"

# ─── Terminal sequences ───────────────────────────────────────────────────────
ALT_ON   = "\033[?1049h"
ALT_OFF  = "\033[?1049l"
HIDE_CUR = "\033[?25l"
SHOW_CUR = "\033[?25h"
MOUSE_ON = "\033[?1003h\033[?1006h"   # all-motion + SGR encoding
MOUSE_OFF= "\033[?1003l\033[?1006l"
RESET    = "\033[0m"
BOLD     = "\033[1m"
DIM      = "\033[90m"
GREEN    = "\033[32m"

# Image occupies rows 1..IMG_ROWS, cols 1..TARGET_SIZE (1-indexed terminal coords)
IMG_START_ROW = 1
IMG_START_COL = 1
IMG_TERM_ROWS = TARGET_SIZE // 2   # 32 rows for 64 px height


def goto(row: int, col: int) -> str:
    return f"\033[{row};{col}H"


def clr() -> str:
    return "\033[2K"


def color_swatch(r: int, g: int, b: int) -> str:
    return f"\033[48;2;{r};{g};{b}m   \033[0m"


# ─── Status rendering ─────────────────────────────────────────────────────────

def render_status(
    hover_pos,
    hover_rgb,
    recorded: list[tuple],
    message: str = "",
) -> str:
    out: list[str] = []
    base = IMG_START_ROW + IMG_TERM_ROWS  # first row after image

    # ── separator ──
    out.append(goto(base + 1, 1) + DIM + "─" * 72 + RESET)

    # ── hover info ──
    out.append(goto(base + 2, 1) + clr())
    if hover_pos:
        x, y = hover_pos
        r, g, b = hover_rgb
        out.append(
            f"{BOLD}Hover:{RESET}  x={x:3d}, y={y:3d}  "
            f"RGB=({r:3d}, {g:3d}, {b:3d})  {color_swatch(r, g, b)}"
        )
    else:
        out.append(DIM + "Move mouse over image to inspect pixels…" + RESET)

    # ── recorded list ──
    out.append(goto(base + 3, 1) + DIM + "─" * 72 + RESET)
    out.append(goto(base + 4, 1) + clr())
    out.append(f"{BOLD}Recorded coords ({len(recorded)}):{RESET}  "
               + DIM + "[Click image to record  |  s=save  |  c=clear  |  q=quit]" + RESET)

    visible = recorded[-12:]  # last 12 entries
    for i, (x, y, r, g, b, label) in enumerate(visible):
        row_idx = base + 5 + i
        out.append(goto(row_idx, 1) + clr())
        lbl_str = f"  ← {label}" if label else ""
        out.append(
            f"  {DIM}[{len(recorded) - len(visible) + i + 1:2d}]{RESET} "
            f"x={x:3d}, y={y:3d}  RGB=({r:3d}, {g:3d}, {b:3d})  "
            f"{color_swatch(r, g, b)}{DIM}{lbl_str}{RESET}"
        )

    # Clear any leftover lines from a previous longer list
    for extra in range(len(visible), 12):
        out.append(goto(base + 5 + extra, 1) + clr())

    # ── message ──
    msg_row = base + 5 + 12 + 1
    out.append(goto(msg_row, 1) + clr())
    if message:
        out.append(GREEN + message + RESET)

    return "".join(out)


# ─── Mouse event parsing ──────────────────────────────────────────────────────

_SGR_RE = re.compile(rb"\x1b\[<(\d+);(\d+);(\d+)([Mm])")


def parse_mouse(data: bytes) -> list[tuple[str, int, int]]:
    """Return list of ('move'|'click', col, row) from SGR mouse byte stream."""
    events = []
    for m in _SGR_RE.finditer(data):
        btn     = int(m.group(1))
        col     = int(m.group(2))
        row     = int(m.group(3))
        pressed = m.group(4) == b"M"

        is_scroll = bool(btn & 64)
        is_motion = bool(btn & 32) and not is_scroll
        is_click  = pressed and not is_motion and not is_scroll and (btn & 3) == 0

        if is_motion:
            events.append(("move", col, row))
        elif is_click:
            events.append(("click", col, row))
    return events


def strip_escapes(data: bytes) -> bytes:
    """Remove all ESC sequences so we can safely check plain keys."""
    return re.sub(rb"\x1b\[.*?[A-Za-z~]", b"", data)


def term_to_pixel(col: int, row: int) -> tuple[int, int]:
    """Map 1-indexed terminal cell → image pixel (x, y). Each row = 2 px rows."""
    px = col - IMG_START_COL
    py = (row - IMG_START_ROW) * 2
    return px, py


def in_image(px: int, py: int) -> bool:
    return 0 <= px < TARGET_SIZE and 0 <= py < TARGET_SIZE


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    img     = load_sprite(IMAGE_PATH)
    pixels  = img.load()
    frame   = render_frame(img)

    # Load existing coords.json if present
    recorded: list[tuple] = []
    if os.path.exists(COORDS_FILE):
        with open(COORDS_FILE) as f:
            for entry in json.load(f):
                r, g, b = entry["rgb"]
                recorded.append((entry["x"], entry["y"], r, g, b, entry.get("label", "")))

    hover_pos = None
    hover_rgb = (0, 0, 0)
    message   = f"Loaded {len(recorded)} coords from {COORDS_FILE}" if recorded else ""

    old_settings = termios.tcgetattr(sys.stdin)

    try:
        sys.stdout.write(ALT_ON + HIDE_CUR + MOUSE_ON + "\033[2J")

        # Draw image once
        sys.stdout.write(goto(IMG_START_ROW, IMG_START_COL) + frame)
        sys.stdout.write(render_status(None, (0, 0, 0), recorded))
        sys.stdout.flush()

        tty.setraw(sys.stdin.fileno())

        while True:
            r_ready, _, _ = select.select([sys.stdin], [], [], 0.05)
            if not r_ready:
                continue

            data = os.read(sys.stdin.fileno(), 4096)
            plain = strip_escapes(data)

            # ── key handling ──
            if b"q" in plain or b"\x03" in plain:
                break

            if b"s" in plain:
                payload = [
                    {"x": x, "y": y, "rgb": [r, g, b], "label": label}
                    for x, y, r, g, b, label in recorded
                ]
                with open(COORDS_FILE, "w") as f:
                    json.dump(payload, f, indent=2)
                message = f"✓ Saved {len(recorded)} coords → {COORDS_FILE}"
                sys.stdout.write(render_status(hover_pos, hover_rgb, recorded, message))
                sys.stdout.flush()
                continue

            if b"c" in plain:
                recorded.clear()
                message = "Cleared all recorded coords."
                sys.stdout.write(render_status(hover_pos, hover_rgb, recorded, message))
                sys.stdout.flush()
                continue

            # ── mouse events ──
            needs_redraw = False
            for event_type, col, row in parse_mouse(data):
                px, py = term_to_pixel(col, row)

                if not in_image(px, py):
                    if hover_pos is not None:
                        hover_pos = None
                        needs_redraw = True
                    continue

                r_val, g_val, b_val, _ = pixels[px, py]

                if event_type == "move":
                    hover_pos = (px, py)
                    hover_rgb = (r_val, g_val, b_val)
                    needs_redraw = True
                    message = ""

                elif event_type == "click":
                    recorded.append((px, py, r_val, g_val, b_val, ""))
                    hover_pos = (px, py)
                    hover_rgb = (r_val, g_val, b_val)
                    message = f"Recorded → x={px}, y={py}  RGB=({r_val}, {g_val}, {b_val})"
                    needs_redraw = True

            if needs_redraw:
                sys.stdout.write(render_status(hover_pos, hover_rgb, recorded, message))
                sys.stdout.flush()

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        sys.stdout.write(MOUSE_OFF + SHOW_CUR + ALT_OFF)
        sys.stdout.flush()

    # ── post-exit summary ──
    if recorded:
        print(f"\nRecorded {len(recorded)} coordinate(s):")
        for i, (x, y, r, g, b, label) in enumerate(recorded, 1):
            print(f"  [{i:2d}] x={x:3d}, y={y:3d}  RGB=({r:3d}, {g:3d}, {b:3d})"
                  + (f"  ← {label}" if label else ""))
    else:
        print("\nNo coordinates recorded.")


if __name__ == "__main__":
    main()
