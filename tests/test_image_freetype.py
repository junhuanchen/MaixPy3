from pathlib import Path

import pytest

image = pytest.importorskip("_maix_image")


def _cjk_font():
    candidates = (
        "/usr/share/fonts/truetype/ms-core-fonts/msyh.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    pytest.skip("no CJK font installed")


def test_load_draw_measure_and_free_freetype():
    with pytest.raises(ValueError):
        image.load_freetype("/definitely/missing/font.ttf")

    image.load_freetype(_cjk_font(), fontHeight=24)
    try:
        width, height = image.get_string_size("中文 ABC")
        assert width > 0
        assert height > 0

        canvas = image.new(size=(240, 80), color=(0, 0, 0), mode="RGB")
        before = canvas.tobytes("rgb")
        canvas.draw_string(2, 2, "中文 ABC", color=(255, 255, 255))
        assert canvas.tobytes("rgb") != before
    finally:
        image.free_freetype()
