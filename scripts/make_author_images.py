"""Build author photo assets for the blog from one source portrait.

Usage: python3 make_author_images.py SOURCE.jpg SITE_ROOT [DISPLAY_FONT.ttf]
Writes assets/images/author/{portrait.jpg, portrait-duotone.jpg, avatar.jpg}
and, when a font is given, assets/images/og-default.png into SITE_ROOT.
"""
import sys
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageEnhance

SHADOW = (18, 22, 84)        # deep ink indigo
MID = (92, 110, 255)         # signal blue, lifted
HIGHLIGHT = (255, 249, 226)  # pale highlighter


def duotone(img):
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g, cutoff=1)
    g = ImageEnhance.Contrast(g).enhance(1.12)
    return ImageOps.colorize(g, black=SHADOW, white=HIGHLIGHT, mid=MID,
                             blackpoint=0, whitepoint=255, midpoint=118)


def main(src, root):
    out = Path(root) / "assets" / "images" / "author"
    out.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    w, h = im.size
    box = (int(w * 0.098), int(h * 0.026), int(w * 0.902), int(h * 0.026 + w * 0.804 * 1.25))
    crop = im.crop(box).resize((720, 900), Image.LANCZOS)
    crop.save(out / "portrait.jpg", quality=84, optimize=True, progressive=True)
    duo = duotone(crop)
    duo.save(out / "portrait-duotone.jpg", quality=84, optimize=True, progressive=True)
    face = im.crop((int(w * 0.13), int(h * 0.035), int(w * 0.87), int(h * 0.035 + w * 0.74)))
    duotone(face.resize((240, 240), Image.LANCZOS)).save(out / "avatar.jpg", quality=86, optimize=True)
    print("wrote", sorted(p.name for p in out.iterdir()))
    return duo


def font(path, size, weight, width=100):
    f = ImageFont.truetype(path, size)
    try:
        f.set_variation_by_axes([14 if size < 40 else 96, weight, width])  # opsz, wght, wdth
    except Exception:
        pass
    return f


def og_image(duo, root, font_path):
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    for x in range(0, W, 28):
        d.line([(x, 0), (x, H)], fill=(233, 237, 248))
    for y in range(0, H, 28):
        d.line([(0, y), (W, y)], fill=(233, 237, 248))
    pw, ph = 380, 475
    px, py = W - pw - 80, (H - ph) // 2 - 6
    d.rounded_rectangle([px + 14, py + 14, px + pw + 14, py + ph + 14], 26, fill=(255, 224, 102))
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw, ph], 26, fill=255)
    img.paste(duo.resize((pw, ph), Image.LANCZOS), (px, py), mask)
    ink = (18, 21, 43)
    title = font(font_path, 74, 800, 82)
    small = font(font_path, 26, 500)
    label = font(font_path, 34, 700)
    d.line([(84, 118), (100, 98), (116, 118)], fill=ink, width=4)
    d.ellipse([76, 110, 92, 126], fill=(43, 60, 255))
    d.ellipse([92, 90, 108, 106], fill=ink)
    d.ellipse([108, 110, 124, 126], fill=(255, 224, 102), outline=ink, width=2)
    d.text((140, 92), "Agentic Field Notes", font=label, fill=ink)
    y = 190
    for line in ["Building agentic", "systems that survive", "production"]:
        d.text((76, y), line, font=title, fill=ink)
        y += 78
    d.text((80, y + 30), "Orchestration · MongoDB · RAG · Evals · Tracing", font=small, fill=(90, 96, 121))
    img.save(Path(root) / "assets" / "images" / "og-default.png", optimize=True)
    print("wrote og-default.png")


if __name__ == "__main__":
    duo_img = main(sys.argv[1], sys.argv[2])
    if len(sys.argv) > 3:
        og_image(duo_img, sys.argv[2], sys.argv[3])
