"""PNG → ▀ True Color terminal renderer."""

from PIL import Image

# Dot size in the source PNG (each logical pixel = 16×16 source pixels)
DOT_SIZE = 16
# Target logical resolution after downscale
TARGET_SIZE = 64
# Alpha threshold below which a pixel is treated as black background
ALPHA_THRESHOLD = 128

RESET = "\033[0m"


def _ansi_fg(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


def _ansi_bg(r: int, g: int, b: int) -> str:
    return f"\033[48;2;{r};{g};{b}m"


def _remove_watermark(img: Image.Image) -> Image.Image:
    """Erase Gemini watermark (gray cross in bottom-right) after downscaling."""
    img = img.copy()
    pixels = img.load()
    w, h = img.size
    bg = (18, 21, 28, 255)
    # Watermark is a gray cross (~R=G=B≈136) in the bottom-right quadrant
    for y in range(h // 2, h):
        for x in range(w // 2, w):
            r, g, b, a = pixels[x, y]
            if abs(int(r) - int(g)) < 8 and abs(int(g) - int(b)) < 8 and 100 < r < 170:
                pixels[x, y] = bg
    return img


def load_sprite(path: str) -> Image.Image:
    """Load PNG and downscale to logical pixel grid using NEAREST resampling."""
    img = Image.open(path).convert("RGBA")
    img = img.resize((TARGET_SIZE, TARGET_SIZE), Image.NEAREST)
    img = _remove_watermark(img)
    return img


def render_frame(img: Image.Image) -> str:
    """
    Convert an RGBA image to a ▀-based True Color terminal string.

    Each terminal row represents 2 pixel rows:
      top pixel  → foreground color (▀ upper half)
      bottom pixel → background color (▀ lower half)
    """
    width, height = img.size
    pixels = img.load()
    lines = []

    for y in range(0, height - 1, 2):
        row = []
        for x in range(width):
            tr, tg, tb, ta = pixels[x, y]
            br, bg, bb, ba = pixels[x, y + 1]

            # Transparent pixels → black
            if ta < ALPHA_THRESHOLD:
                tr, tg, tb = 0, 0, 0
            if ba < ALPHA_THRESHOLD:
                br, bg, bb = 0, 0, 0

            row.append(_ansi_fg(tr, tg, tb) + _ansi_bg(br, bg, bb) + "▀")

        lines.append("".join(row) + RESET)

    # Handle odd height: last row uses black background
    if height % 2 == 1:
        y = height - 1
        row = []
        for x in range(width):
            tr, tg, tb, ta = pixels[x, y]
            if ta < ALPHA_THRESHOLD:
                tr, tg, tb = 0, 0, 0
            row.append(_ansi_fg(tr, tg, tb) + _ansi_bg(0, 0, 0) + "▀")
        lines.append("".join(row) + RESET)

    return "\n".join(lines)
