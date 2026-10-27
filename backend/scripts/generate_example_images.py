"""Generate the ten illustrations used by the Breaking News example content.

The images are drawn, not photographed, so the repository carries no third
party pictures. Each one is a flat editorial illustration on an election-day
theme, drawn with Pillow from a fixed seed: running the script again produces
the same files.

Usage::

    uv run python scripts/generate_example_images.py
"""

from collections.abc import Callable
from pathlib import Path
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFilter

import math
import random


WIDTH, HEIGHT = 1200, 675
TARGET = (
    Path(__file__).parent.parent
    / "src"
    / "asgidemo"
    / "setuphandlers"
    / "breaking_news"
    / "images"
)

GREEN = (0, 132, 61)
YELLOW = (255, 204, 41)
BLUE = (0, 39, 118)
WHITE = (250, 250, 245)
INK = (24, 28, 38)
RED = (200, 30, 45)
SKY = (120, 170, 220)

Painter = Callable[[ImageDraw.ImageDraw, random.Random], None]


def gradient(top: tuple, bottom: tuple) -> Image.Image:
    """A vertical gradient filling the canvas.

    :param top: RGB colour at the top.
    :param bottom: RGB colour at the bottom.
    :returns: A new RGB image.
    """
    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        colour = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom, strict=True))
        draw.line([(0, y), (WIDTH, y)], fill=colour)
    return image


def ballot_box(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    draw.rectangle([380, 300, 820, 620], fill=WHITE, outline=INK, width=6)
    draw.rectangle([380, 300, 820, 360], fill=BLUE)
    draw.rectangle([520, 318, 680, 338], fill=INK)
    for i, colour in enumerate((YELLOW, WHITE, GREEN)):
        x = 545 + i * 35
        draw.polygon(
            [(x, 120 + i * 30), (x + 90, 110 + i * 30), (x + 100, 320), (x + 10, 330)],
            fill=colour,
            outline=INK,
        )
    draw.ellipse([555, 450, 645, 540], outline=GREEN, width=10)
    draw.line([(575, 495), (595, 515), (630, 470)], fill=GREEN, width=10)


def polling_queue(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    draw.rectangle([0, 520, WIDTH, HEIGHT], fill=(205, 190, 160))
    draw.rectangle([820, 160, 1150, 520], fill=WHITE, outline=INK, width=5)
    draw.rectangle([930, 330, 1040, 520], fill=BLUE)
    draw.rectangle([840, 180, 1130, 240], fill=GREEN)
    for i in range(9):
        x = 760 - i * 82
        height = rng.randint(150, 200)
        colour = rng.choice([RED, BLUE, GREEN, YELLOW, (120, 80, 160), (230, 120, 40)])
        draw.rounded_rectangle([x - 26, 520 - height, x + 26, 520], 18, fill=colour)
        draw.ellipse(
            [x - 22, 520 - height - 48, x + 22, 520 - height - 4], fill=(230, 185, 140)
        )


def voting_machine(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    draw.rounded_rectangle([300, 140, 900, 560], 30, fill=(60, 64, 72))
    draw.rectangle([340, 180, 610, 380], fill=(215, 235, 210))
    for row in range(4):
        for col in range(3):
            x, y = 660 + col * 70, 190 + row * 80
            draw.rounded_rectangle([x, y, x + 55, y + 60], 8, fill=WHITE)
    draw.rounded_rectangle([660, 510, 720, 545], 6, fill=WHITE)
    draw.rounded_rectangle([730, 510, 790, 545], 6, fill=(230, 120, 40))
    draw.rounded_rectangle([800, 510, 860, 545], 6, fill=GREEN)
    for i in range(5):
        draw.line(
            [(360, 210 + i * 32), (590 - rng.randint(0, 90), 210 + i * 32)],
            fill=INK,
            width=8,
        )


def congress(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    draw.rectangle([0, 500, WIDTH, HEIGHT], fill=(90, 150, 90))
    draw.rectangle([150, 440, 1050, 500], fill=WHITE)
    draw.rectangle([555, 130, 590, 440], fill=WHITE)
    draw.rectangle([610, 130, 645, 440], fill=WHITE)
    draw.rectangle([555, 270, 645, 290], fill=WHITE)
    draw.pieslice([230, 330, 470, 560], 180, 360, fill=WHITE)
    draw.chord([730, 300, 970, 460], 180, 360, fill=WHITE)
    draw.rectangle([0, 560, WIDTH, 600], fill=(90, 140, 190))


def results_map(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    size = 46
    for row in range(12):
        for col in range(20):
            x, y = 140 + col * size, 60 + row * size
            dx, dy = (col - 10) / 9, (row - 6) / 6
            if dx * dx + dy * dy * 1.3 > 1 + rng.uniform(-0.15, 0.15):
                continue
            share = 0.5 + 0.45 * math.sin(col / 3.0 + row / 4.0) * rng.uniform(0.6, 1)
            colour = tuple(
                round(a + (b - a) * share)
                for a, b in zip(BLUE, (230, 90, 60), strict=True)
            )
            draw.rectangle([x, y, x + size - 4, y + size - 4], fill=colour)


def turnout_chart(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    draw.line([(140, 560), (1080, 560)], fill=INK, width=4)
    values = [18, 31, 44, 57, 66, 74, 79]
    for i, value in enumerate(values):
        x = 180 + i * 130
        top = 560 - value * 5.5
        draw.rectangle([x, top, x + 80, 560], fill=GREEN if i < 6 else YELLOW)
    points = [(220 + i * 130, 560 - v * 5.5 - 30) for i, v in enumerate(values)]
    draw.line(points, fill=BLUE, width=6, joint="curve")
    for x, y in points:
        draw.ellipse([x - 10, y - 10, x + 10, y + 10], fill=BLUE)


def celebration(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    for _ in range(420):
        x, y = rng.randint(0, WIDTH), rng.randint(0, HEIGHT)
        colour = rng.choice([GREEN, YELLOW, BLUE, WHITE, RED])
        angle = rng.uniform(0, math.pi)
        dx, dy = 14 * math.cos(angle), 14 * math.sin(angle)
        draw.line([(x - dx, y - dy), (x + dx, y + dy)], fill=colour, width=6)
    for i in range(14):
        x = 40 + i * 85
        draw.ellipse([x, 520, x + 70, 590], fill=(60, 45, 40))
        draw.rectangle(
            [x + 5, 580, x + 65, HEIGHT], fill=rng.choice([GREEN, YELLOW, BLUE])
        )
    draw.polygon([(300, 300), (900, 300), (850, 460), (350, 460)], fill=GREEN)
    draw.polygon([(600, 320), (800, 380), (600, 440), (400, 380)], fill=YELLOW)
    draw.ellipse([550, 330, 650, 430], fill=BLUE)


def newsroom(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    draw.rectangle([0, 470, WIDTH, HEIGHT], fill=(40, 44, 58))
    for i in range(3):
        x = 120 + i * 340
        draw.rectangle([x, 120, x + 300, 300], fill=INK, outline=(90, 96, 110), width=8)
        draw.rectangle(
            [x + 20, 140, x + 280, 280], fill=rng.choice([BLUE, GREEN, (90, 40, 60)])
        )
        draw.rectangle([x + 20, 250, x + 280, 280], fill=RED)
    draw.rounded_rectangle([250, 400, 950, 500], 20, fill=(200, 205, 215))
    for x in (380, 600, 820):
        draw.ellipse([x - 40, 300, x + 40, 380], fill=(200, 160, 120))
        draw.rounded_rectangle(
            [x - 60, 370, x + 60, 420], 20, fill=rng.choice([BLUE, INK, GREEN])
        )


def debate(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    for x in range(0, WIDTH, 60):
        draw.line([(x, 0), (WIDTH / 2, HEIGHT)], fill=(40, 60, 110), width=2)
    for x, colour in ((330, RED), (870, BLUE)):
        draw.polygon(
            [(x - 110, 620), (x + 110, 620), (x + 80, 380), (x - 80, 380)], fill=WHITE
        )
        draw.rectangle([x - 80, 380, x + 80, 410], fill=colour)
        draw.line([(x, 380), (x - 30, 330)], fill=INK, width=6)
        draw.ellipse([x - 45, 320, x - 15, 345], fill=INK)
    draw.ellipse([520, 80, 680, 240], outline=YELLOW, width=10)


def sunset(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    draw.ellipse([480, 330, 720, 570], fill=(255, 170, 60))
    draw.rectangle([0, 470, WIDTH, HEIGHT], fill=(40, 30, 50))
    for i in range(16):
        x = 40 + i * 72
        height = rng.randint(60, 190)
        draw.rectangle([x, 470 - height, x + 52, 470], fill=(50, 40, 64))
        for wy in range(470 - height + 15, 460, 28):
            if rng.random() < 0.5:
                draw.rectangle([x + 10, wy, x + 22, wy + 12], fill=(255, 210, 120))
    for i in range(5):
        y = 520 + i * 28
        draw.line([(420 + i * 20, y), (780 - i * 20, y)], fill=(255, 170, 60), width=4)


IMAGES: dict[str, tuple[tuple, tuple, Painter]] = {
    "ballot-box": ((210, 230, 245), (160, 200, 230), ballot_box),
    "polling-station": ((250, 225, 170), (245, 200, 130), polling_queue),
    "voting-machine": ((225, 230, 238), (180, 188, 200), voting_machine),
    "national-congress": (SKY, (200, 225, 245), congress),
    "results-map": ((245, 245, 240), (225, 228, 232), results_map),
    "turnout-chart": ((250, 250, 245), (230, 236, 240), turnout_chart),
    "celebration": ((20, 60, 40), (10, 30, 25), celebration),
    "newsroom": ((70, 76, 92), (30, 34, 46), newsroom),
    "debate-stage": ((10, 20, 60), (30, 40, 90), debate),
    "sunset-over-brasilia": ((250, 120, 80), (120, 60, 120), sunset),
}


def render(name: str) -> Image.Image:
    """Draw one illustration.

    :param name: Key in :data:`IMAGES`.
    :returns: The image.
    """
    top, bottom, painter = IMAGES[name]
    image = gradient(top, bottom)
    painter(ImageDraw.Draw(image), random.Random(name))  # noqa: S311
    return image.filter(ImageFilter.SMOOTH)


def main() -> None:
    """Write every illustration to :data:`TARGET` as JPEG."""
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in IMAGES:
        path = TARGET / f"{name}.jpg"
        render(name).save(path, "JPEG", quality=85, optimize=True)
        shown = (
            path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path
        )
        print(f"wrote {shown}")


if __name__ == "__main__":
    main()
