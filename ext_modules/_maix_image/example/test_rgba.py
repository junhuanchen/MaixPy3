"""Create, draw, and save an RGBA image with MaixPy3."""

import ctypes
import ctypes.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent


def import_local_image_module():
    """Load the extension built in this source tree."""
    # This desktop build uses OpenMP but does not record libgomp as a direct
    # dependency, so make its symbols globally visible before importing it.
    libgomp = ctypes.util.find_library("gomp")
    if libgomp:
        ctypes.CDLL(libgomp, mode=ctypes.RTLD_GLOBAL)

    build_dirs = sorted(ROOT.glob("build/lib.*"), reverse=True)
    for build_dir in build_dirs:
        if any(build_dir.glob("_maix_image*.so")):
            sys.path.insert(0, str(build_dir))
            break

    from maix import image

    if not hasattr(image, "new"):
        raise RuntimeError(
            "_maix_image was not loaded; build it for Python %d.%d first"
            % sys.version_info[:2]
        )
    return image


image = import_local_image_module()


WIDTH = 320
HEIGHT = 240
OUTPUT = ROOT / "rgba_drawing.jpg"


def main():
    # Create a 32-bit RGBA canvas and draw directly on it. MaixPy3 exposes this
    # pixel format as "RGBA" (four bytes per pixel).
    img = image.new(size=(WIDTH, HEIGHT),
                    color=(24, 32, 48, 255), mode="RGBA")

    # Color panels (filled rectangles).
    img.draw_rectangle(16, 16, 96, 78, color=(255, 64, 64, 255), thickness=-1)
    img.draw_rectangle(112, 16, 208, 78, color=(64, 255, 96, 255), thickness=-1)
    img.draw_rectangle(224, 16, 304, 78, color=(64, 128, 255, 255), thickness=-1)

    # Primitive shapes and text.
    img.draw_rectangle(16, 96, 304, 224, color=(240, 240, 240, 255), thickness=3)
    img.draw_line(28, 208, 292, 104, color=(255, 220, 32, 255), thickness=4)
    img.draw_circle(90, 158, 42, color=(255, 96, 220, 255), thickness=-1)
    img.draw_circle(90, 158, 42, color=(255, 255, 255, 255), thickness=3)
    img.draw_ellipse(225, 158, 56, 34, 20, 0, 360,
                     color=(80, 224, 255, 255), thickness=5)
    img.draw_string(115, 145, "RGBA", scale=1.0,
                    color=(255, 255, 255, 255), thickness=2)

    # Save the drawing as a directly viewable JPEG with image.save().
    result = img.save(str(OUTPUT))
    if result != 0 or not OUTPUT.exists():
        raise RuntimeError("failed to save image: %s" % OUTPUT)

    expected_size = WIDTH * HEIGHT * 4
    assert img.mode == "RGBA"
    assert img.size == expected_size, (img.size, expected_size)

    print("saved:", OUTPUT)
    print("mode:", img.mode)
    print("size: %d bytes (%d x %d x 4)" % (img.size, WIDTH, HEIGHT))


if __name__ == "__main__":
    main()
