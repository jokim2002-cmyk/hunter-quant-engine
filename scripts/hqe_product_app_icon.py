from __future__ import annotations

import argparse
import struct
import shutil
from pathlib import Path


def draw_icon(size: int = 64) -> list[list[tuple[int, int, int, int]]]:
    pixels: list[list[tuple[int, int, int, int]]] = []
    for y in range(size):
        row = []
        for x in range(size):
            # Blue-purple gradient with gold diagonal glow
            r = int(18 + 30 * x / size)
            g = int(35 + 25 * y / size)
            b = int(90 + 80 * (x + y) / (2 * size))
            if abs(x - y) < 6:
                r, g, b = 210, 154, 42
            row.append((r, g, b, 255))
        pixels.append(row)

    gold = (255, 205, 80, 255)
    dark = (8, 14, 30, 255)

    def rect(x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int, int]) -> None:
        for yy in range(max(0, y1), min(size, y2)):
            for xx in range(max(0, x1), min(size, x2)):
                pixels[yy][xx] = color

    # Border
    rect(0, 0, size, 3, gold)
    rect(0, size - 3, size, size, gold)
    rect(0, 0, 3, size, gold)
    rect(size - 3, 0, size, size, gold)

    # Block letters HQE
    # H
    rect(9, 18, 13, 46, gold)
    rect(23, 18, 27, 46, gold)
    rect(9, 30, 27, 35, gold)
    # Q / stylized circle
    rect(32, 18, 51, 22, gold)
    rect(32, 42, 51, 46, gold)
    rect(32, 18, 36, 46, gold)
    rect(47, 18, 51, 46, gold)
    rect(45, 42, 54, 50, gold)
    # small E underline mark
    rect(10, 51, 54, 55, dark)
    rect(10, 56, 54, 59, gold)
    return pixels


def write_ico(path: Path, size: int = 64) -> None:
    pixels = draw_icon(size)
    # ICO with 32-bit BGRA DIB. Bitmap height is doubled for XOR+AND mask.
    bitmap_header = struct.pack(
        "<IIIHHIIIIII",
        40,
        size,
        size * 2,
        1,
        32,
        0,
        size * size * 4,
        0,
        0,
        0,
        0,
    )
    xor = bytearray()
    for y in range(size - 1, -1, -1):
        for x in range(size):
            r, g, b, a = pixels[y][x]
            xor.extend([b, g, r, a])
    # AND mask rows padded to 32-bit boundaries
    mask_row_bytes = ((size + 31) // 32) * 4
    and_mask = bytes(mask_row_bytes * size)
    image_data = bitmap_header + bytes(xor) + and_mask

    header = struct.pack("<HHH", 0, 1, 1)
    directory = struct.pack(
        "<BBBBHHII",
        size if size < 256 else 0,
        size if size < 256 else 0,
        0,
        0,
        1,
        32,
        len(image_data),
        6 + 16,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + directory + image_data)


def main() -> int:
    p = argparse.ArgumentParser(description="Generate HQE product app ICO")
    p.add_argument("--output", default=str(Path("assets") / "HQE_PRODUCT_APP.ico"))
    args = p.parse_args()
    out = Path(args.output)
    branded = Path("assets") / "branding" / "hqe_app_icon" / "HQE.ico"
    out.parent.mkdir(parents=True, exist_ok=True)
    if branded.exists() and branded.resolve() != out.resolve():
        shutil.copy2(branded, out)
        print(f"ICON_WRITTEN {out} SOURCE_BRANDING {branded}")
    else:
        write_ico(out)
        print(f"ICON_WRITTEN {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
