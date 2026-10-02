"""FreeType smoke test: save before/after font-loading comparison images."""

from pathlib import Path

import _maix_image as image

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/ms-core-fonts/msyh.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
)

# text samples: CJK, mixed, numbers, long sentence
TEXT_SAMPLES = (
    "中文 ABC",
    "你好，世界！",
    "FreeType 0123456789",
    "The quick brown fox 敏捷的棕毛狐狸",
)

BEFORE_IMG = "test_before_font.jpg"


def find_cjk_fonts():
    """Return all existing fonts from FONT_CANDIDATES."""
    return [c for c in FONT_CANDIDATES if Path(c).is_file()]


def test_load_missing_font():
    """load_freetype must reject a nonexistent font file (from original test)."""
    missing = "/definitely/missing/font.ttf"
    try:
        image.load_freetype(missing)
    except ValueError:
        print("  [missing] load_freetype rejected %s as expected" % missing)
    else:
        raise RuntimeError("load_freetype should reject missing font: %s" % missing)


def save_before_image():
    """Draw WITHOUT any font loaded -> save the result (expect failure/blank)."""
    canvas = image.new(size=(320, 80), color=(0, 0, 0), mode="RGB")
    try:
        canvas.draw_string(2, 2, "中文 ABC", color=(255, 255, 255))
        print("  [before] draw_string worked without font?!")
    except Exception as error:
        print("  [before] draw_string failed as expected: %s" % error)
    canvas.save(BEFORE_IMG)
    print("  [before] saved %s" % BEFORE_IMG)


def draw_samples(font_path, font_height=24, index=0):
    """Load font, draw all samples on one canvas, save to a UNIQUE file."""
    stem = Path(font_path).stem
    out = "test_after_font_%02d_%s_h%d.jpg" % (index, stem, font_height)

    image.load_freetype(font_path, fontHeight=font_height)
    try:
        # measure first
        for text in TEXT_SAMPLES:
            w, h = image.get_string_size(text)
            print("  [measure] %-32s -> %dx%d" % (text, w, h))
            if w <= 0 or h <= 0:
                raise RuntimeError("invalid string size for %r" % text)

        canvas = image.new(size=(480, 40 + 40 * len(TEXT_SAMPLES)),
                           color=(0, 0, 0), mode="RGB")
        y = 10
        for text in TEXT_SAMPLES:
            canvas.draw_string(10, y, text, color=(255, 255, 255))
            y += 40
        canvas.save(out)
        print("  [after] saved %s (font=%s h=%d)" % (out, font_path, font_height))
    finally:
        image.free_freetype()


def main():
    test_load_missing_font()
    save_before_image()

    fonts = find_cjk_fonts()
    if not fonts:
        raise RuntimeError("no test font installed")

    # draw one image per font, each with a unique filename
    for index, path in enumerate(fonts):
        try:
            draw_samples(path, font_height=24, index=index)
        except Exception as error:
            print("  [skip] %s: %s" % (path, error))


if __name__ == "__main__":
    main()