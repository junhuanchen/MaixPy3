"""Red/blue channel diagnosis for MaixPy3 traditional vision APIs.

Both board-side input paths are exercised on the same logical picture:

- ``addr``: a BGR buffer owned by Python, attached with ``image.new(addr=...)``
- ``open``: a lossless PNG written by this script and decoded by ``image.open``

Colour-sensitive APIs (imlib LAB thresholds and the OpenCV colour helpers) are
checked against known red/blue targets.  Geometry and code readers do not
output colours, so for them the script only verifies that they run and that
both input paths give identical results.

Run from the MaixPy3 repository root on the board::

    python3 find_xxx_results/test_color_channels.py

To force a freshly built extension instead of the installed one::

    PYTHONPATH=build/lib.linux-armv7l-3.10:. python3 find_xxx_results/test_color_channels.py

Results and annotated images are written to ``../color_channel_results/``.
"""

import ctypes
import hashlib
import os
import struct
import sys
import time
import zlib

import _maix_image
from maix import image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import test_find_xxx as fixtures  # noqa: E402  (QR/AprilTag/EAN-13 helpers)

OUTPUT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "color_channel_results")

WIDTH, HEIGHT = 320, 240
GRAY = (128, 128, 128)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
RED_CIRCLE = (80, 120, 50)     # cx, cy, r -> left half
BLUE_CIRCLE = (240, 120, 50)   # cx, cy, r -> right half
RED_ROI = (60, 100, 40, 40)
BLUE_ROI = (220, 100, 40, 40)

# OpenMV LAB thresholds (Lmin, Lmax, Amin, Amax, Bmin, Bmax) used by imlib.
# Pure red  -> L 53, A  80, B   67
# Pure blue -> L 32, A  79, B -108
# Gray 128  -> L 54, A   0, B    0  (excluded by Amin)
RED_LAB = (20, 80, 20, 127, 0, 127)
BLUE_LAB = (10, 60, 20, 127, -128, -40)

# find_blobs_cv / find_ball_color / custom_find_ball_blob thresholds.
# co=0: (Rmin, Gmin, Bmin, Rmax, Gmax, Bmax)
RED_RGB = (200, 0, 0, 255, 60, 60)
BLUE_RGB = (0, 0, 200, 60, 60, 255)
# co=1 for find_ball_color / custom_find_ball_blob: documented
# (Lmin, Amin, Bmin, Lmax, Amax, Bmax) order.
RED_LAB_MINMAX = (20, 20, 0, 80, 127, 127)
BLUE_LAB_MINMAX = (10, 0, -128, 60, 127, -40)
# co=1 for find_blobs_cv: the current implementation rewrites the tuple in
# place and effectively consumes the OpenMV order with saturated upper bounds,
# so the OpenMV tuples are the ones that work there today.
RED_LAB_CV = RED_LAB
BLUE_LAB_CV = BLUE_LAB
# co=2: (Hmin, Smin, Vmin, Hmax, Smax, Vmax), H 0-360, S/V 0-100.
# The backend scales S/V with int(v * 2.55); 100 becomes 254, which excludes
# fully saturated pixels, so 101 is used as the upper bound here.
RED_HSV = (0, 50, 50, 20, 101, 101)
BLUE_HSV = (220, 50, 50, 260, 101, 101)
DIAGONAL_RED = (100, 100)  # inside the red disc and invariant to x/y transposition

GEOM_CENTER = (160, 120)
LIGHT = (238, 242, 248, 255)
GREEN = (40, 255, 80)
YELLOW = (255, 230, 40)

KEEP_ALIVE = []  # ctypes buffers that back zero-copy images


class Report(object):
    def __init__(self):
        self.lines = []
        self.failures = 0

    def add(self, name, path, status, detail=""):
        if status in ("FAIL", "ERROR"):
            self.failures += 1
        line = "%-30s %-5s %-6s %s" % (name, path, status, detail)
        self.lines.append(line)
        print(line)

    def check(self, name, path, ok, detail=""):
        self.add(name, path, "PASS" if ok else "FAIL", detail)

    def write(self, path):
        with open(path, "w") as output:
            output.write("\n".join(self.lines) + "\n")


def write_png(path, width, height, rgb_rows):
    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(
            ">I", zlib.crc32(body) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + row for row in rgb_rows)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    with open(path, "wb") as output:
        output.write(b"\x89PNG\r\n\x1a\n")
        output.write(chunk(b"IHDR", header))
        output.write(chunk(b"IDAT", zlib.compress(raw, 9)))
        output.write(chunk(b"IEND", b""))


def color_rows(order):
    """Gray canvas with a red disc on the left and a blue disc on the right."""
    def pixel(color):
        return bytes(color if order == "rgb" else color[::-1])

    rows = []
    for y in range(HEIGHT):
        row = bytearray(pixel(GRAY) * WIDTH)
        for (cx, cy, radius), color in ((RED_CIRCLE, RED), (BLUE_CIRCLE, BLUE)):
            dy = y - cy
            if abs(dy) <= radius:
                half = int((radius * radius - dy * dy) ** 0.5)
                x0, x1 = cx - half, cx + half
                row[x0 * 3:(x1 + 1) * 3] = pixel(color) * (x1 - x0 + 1)
        rows.append(bytes(row))
    return rows


def attach_bgr(raw, width, height):
    buffer = (ctypes.c_uint8 * len(raw)).from_buffer_copy(raw)
    KEEP_ALIVE.append(buffer)
    img = image.new(size=(width, height), mode="RGB",
                    addr=ctypes.addressof(buffer))
    if img.width != width or img.height != height or img.mode != "RGB":
        raise RuntimeError("image.new(addr=) did not attach the buffer")
    return img


def raw_bytes(img):
    return ctypes.string_at(img.to_addr(), img.size)


def open_png(path):
    img = image.open(path)
    if img.width == 0 or img.mode != "RGB":
        raise RuntimeError("image.open failed: %s" % path)
    return img


def color_images():
    png_path = os.path.join(OUTPUT_DIR, "color_input.png")
    write_png(png_path, WIDTH, HEIGHT, color_rows("rgb"))
    bgr = b"".join(color_rows("bgr"))
    return {"addr": attach_bgr(bgr, WIDTH, HEIGHT), "open": open_png(png_path)}, bgr


def side(x):
    return "left" if x < WIDTH // 2 else "right"


def pixel_rgb(img, x, y):
    return tuple(img.get_pixel(x, y)[:3])


def raw_pixel_rgb(img, x, y):
    """Public RGB of pixel (x, y) read straight from the internal BGR memory."""
    offset = (y * img.width + x) * 3
    b, g, r = ctypes.string_at(img.to_addr() + offset, 3)
    return (r, g, b)


def blob_summary(items, key_x="centroid_x", key_y="centroid_y"):
    return ["(%s,%s)" % (int(item[key_x]), int(item[key_y])) for item in items]


def check_pixels(report, path, img, expected_bgr):
    rx, ry = RED_CIRCLE[0], RED_CIRCLE[1]
    bx, by = BLUE_CIRCLE[0], BLUE_CIRCLE[1]
    diag = pixel_rgb(img, *DIAGONAL_RED)
    gray = pixel_rgb(img, 10, 10)
    report.check("get_pixel channel order", path, (diag, gray) == (RED, GRAY),
                 "red(100,100)=%s gray(10,10)=%s" % (diag, gray))
    red, blue = pixel_rgb(img, rx, ry), pixel_rgb(img, bx, by)
    detail = "red(%d,%d)=%s blue(%d,%d)=%s" % (rx, ry, red, bx, by, blue)
    if red != RED and red == raw_pixel_rgb(img, ry, rx):
        detail += " XY_TRANSPOSED (get_pixel(x,y) returns pixel (y,x))"
    report.check("get_pixel coordinates", path, (red, blue) == (RED, BLUE), detail)
    raw = raw_bytes(img)
    offset = (ry * WIDTH + rx) * 3
    red_mem = tuple(raw[offset:offset + 3])
    report.check("internal_memory_is_bgr", path, red_mem == (0, 0, 255),
                 "red pixel bytes=%s (expect B,G,R = 0,0,255)" % (red_mem,))
    report.check("memory_matches_bgr_buffer", path, raw == expected_bgr,
                 "%d bytes" % len(raw))


def swap_detail(red_items, blue_items):
    red_x = [int(item["centroid_x"]) if "centroid_x" in item else int(item["cx"])
             for item in red_items]
    blue_x = [int(item["centroid_x"]) if "centroid_x" in item else int(item["cx"])
              for item in blue_items]
    if red_x and blue_x and side(red_x[0]) == "right" and side(blue_x[0]) == "left":
        return "RB_SWAPPED"
    return ""


def check_find_blobs(report, path, img):
    kwargs = dict(area_threshold=1000, pixels_threshold=1000)
    red = list(img.find_blobs([RED_LAB], **kwargs))
    blue = list(img.find_blobs([BLUE_LAB], **kwargs))
    red_ok = len(red) == 1 and side(red[0]["centroid_x"]) == "left"
    blue_ok = len(blue) == 1 and side(blue[0]["centroid_x"]) == "right"
    detail = "red->%s blue->%s %s" % (blob_summary(red), blob_summary(blue),
                                      swap_detail(red, blue))
    report.check("find_blobs(imlib LAB)", path, red_ok and blue_ok, detail.strip())

    overlay = img.copy()
    for item in red:
        overlay.draw_rectangle(item["x"], item["y"], item["x"] + item["w"],
                               item["y"] + item["h"], color=GREEN, thickness=3)
    for item in blue:
        overlay.draw_rectangle(item["x"], item["y"], item["x"] + item["w"],
                               item["y"] + item["h"], color=YELLOW, thickness=3)
    overlay.draw_string(6, 6, "%s: green=RED_LAB yellow=BLUE_LAB" % path,
                        scale=0.8, color=YELLOW, thickness=1)
    overlay.save(os.path.join(OUTPUT_DIR, "01_find_blobs_%s_result.jpg" % path))


def check_binary(report, path, img):
    work = img.copy()
    work.binary([RED_LAB])
    red = raw_pixel_rgb(work, RED_CIRCLE[0], RED_CIRCLE[1])
    blue = raw_pixel_rgb(work, BLUE_CIRCLE[0], BLUE_CIRCLE[1])
    gray = raw_pixel_rgb(work, 10, 10)
    ok = red == (255, 255, 255) and blue == (0, 0, 0) and gray == (0, 0, 0)
    detail = "red=%s blue=%s gray=%s" % (red, blue, gray)
    if red == (0, 0, 0) and blue == (255, 255, 255):
        detail += " RB_SWAPPED"
    report.check("binary(imlib LAB)", path, ok, detail)


def bins_mode(bins, minimum, maximum):
    index = max(range(len(bins)), key=lambda i: bins[i])
    return minimum + index * (maximum - minimum) / float(len(bins) - 1)


def check_histogram(report, path, img):
    red = img.get_histogram(roi=RED_ROI)
    blue = img.get_histogram(roi=BLUE_ROI)
    red_l = bins_mode(red.l_bins(), 0, 100)
    red_b = bins_mode(red.b_bins(), -128, 127)
    blue_l = bins_mode(blue.l_bins(), 0, 100)
    blue_b = bins_mode(blue.b_bins(), -128, 127)
    ok = red_b > 30 and blue_b < -40 and red_l > blue_l
    detail = "red(L=%.0f,B=%.0f) blue(L=%.0f,B=%.0f)" % (red_l, red_b, blue_l, blue_b)
    if red_b < -40 and blue_b > 30:
        detail += " RB_SWAPPED"
    report.check("get_histogram(imlib LAB)", path, ok, detail)


def check_statistics(report, path, img):
    red = img.get_statistics(roi=RED_ROI)
    blue = img.get_statistics(roi=BLUE_ROI)
    red_l, red_a, red_b = red[0], red[8], red[16]
    blue_l, blue_a, blue_b = blue[0], blue[8], blue[16]
    ok = red_b > 30 and blue_b < -40 and red_a > 40 and blue_a > 40 and red_l > blue_l
    detail = "red(L=%d,A=%d,B=%d) blue(L=%d,A=%d,B=%d)" % (
        red_l, red_a, red_b, blue_l, blue_a, blue_b)
    if red_b < -40 and blue_b > 30:
        detail += " RB_SWAPPED"
    report.check("get_statistics(imlib LAB)", path, ok, detail)


def check_blob_color(report, path, img):
    red_rgb = tuple(img.get_blob_color(roi=RED_ROI, critical=0, co=0))
    blue_rgb = tuple(img.get_blob_color(roi=BLUE_ROI, critical=0, co=0))
    detail = "red=%s blue=%s" % (red_rgb, blue_rgb)
    if red_rgb == BLUE and blue_rgb == RED:
        detail += " RB_SWAPPED"
    report.check("get_blob_color(co=0 rgb)", path,
                 red_rgb == RED and blue_rgb == BLUE, detail)

    red_lab = img.get_blob_lab(roi=RED_ROI, critical=0, co=1)
    blue_lab = img.get_blob_lab(roi=BLUE_ROI, critical=0, co=1)
    ok = red_lab[2] > 30 and blue_lab[2] < -40
    detail = "red=%s blue=%s" % (list(red_lab), list(blue_lab))
    if red_lab[2] < -40 and blue_lab[2] > 30:
        detail += " RB_SWAPPED"
    report.check("get_blob_lab(co=1 lab)", path, ok, detail)

    red_hsv = img.get_blob_color(roi=RED_ROI, critical=0, co=2)
    blue_hsv = img.get_blob_color(roi=BLUE_ROI, critical=0, co=2)
    red_h, blue_h = red_hsv[0], blue_hsv[0]
    ok = (red_h < 10 or red_h > 170) and 110 <= blue_h <= 130
    detail = "red_h=%s blue_h=%s (OpenCV scale, red 0 / blue 120)" % (red_h, blue_h)
    report.check("get_blob_color(co=2 hsv)", path, ok, detail)


def check_find_blobs_cv(report, path, img):
    kwargs = dict(area_threshold=1000, pixels_threshold=1000)
    for label, red_t, blue_t, co in (("co=0 rgb", RED_RGB, BLUE_RGB, 0),
                                     ("co=1 lab", RED_LAB_CV, BLUE_LAB_CV, 1),
                                     ("co=2 hsv", RED_HSV, BLUE_HSV, 2)):
        red = list(img.find_blobs_cv([list(red_t)], co=co, **kwargs))
        blue = list(img.find_blobs_cv([list(blue_t)], co=co, **kwargs))
        red_ok = len(red) == 1 and side(red[0]["cx"]) == "left"
        blue_ok = len(blue) == 1 and side(blue[0]["cx"]) == "right"
        detail = "red->%s blue->%s %s" % (blob_summary(red, "cx", "cy"),
                                          blob_summary(blue, "cx", "cy"),
                                          swap_detail(red, blue))
        report.check("find_blobs_cv(%s)" % label, path, red_ok and blue_ok,
                     detail.strip())


def check_ball_color(report, path, img):
    for label, red_t, blue_t, co in (("co=0 rgb", RED_RGB, BLUE_RGB, 0),
                                     ("co=1 lab", RED_LAB_MINMAX, BLUE_LAB_MINMAX, 1),
                                     ("co=2 hsv", RED_HSV, BLUE_HSV, 2)):
        red = list(img.find_ball_color(list(red_t), co=co))
        blue = list(img.find_ball_color(list(blue_t), co=co))
        red_ok = len(red) == 1 and side(red[0][0]) == "left"
        blue_ok = len(blue) == 1 and side(blue[0][0]) == "right"
        detail = "red->%s blue->%s" % ([tuple(item[:2]) for item in red],
                                       [tuple(item[:2]) for item in blue])
        if red and blue and side(red[0][0]) == "right" and side(blue[0][0]) == "left":
            detail += " RB_SWAPPED"
        report.check("find_ball_color(%s)" % label, path, red_ok and blue_ok, detail)


def check_custom_ball(report, path, img):
    kwargs = dict(area_threshold=1000, pixels_threshold=1000)
    for label, red_t, blue_t, co in (("co=0 rgb", RED_RGB, BLUE_RGB, 0),
                                     ("co=1 lab", RED_LAB_MINMAX, BLUE_LAB_MINMAX, 1),
                                     ("co=2 hsv", RED_HSV, BLUE_HSV, 2)):
        red = list(img.custom_find_ball_blob([list(red_t)], co=co, **kwargs))
        blue = list(img.custom_find_ball_blob([list(blue_t)], co=co, **kwargs))
        red_ok = len(red) == 1 and side(red[0]["cx"]) == "left" and red[0]["ball"]
        blue_ok = len(blue) == 1 and side(blue[0]["cx"]) == "right" and blue[0]["ball"]
        detail = "red->%s blue->%s %s" % (blob_summary(red, "cx", "cy"),
                                          blob_summary(blue, "cx", "cy"),
                                          swap_detail(red, blue))
        report.check("custom_find_ball_blob(%s)" % label, path, red_ok and blue_ok,
                     detail.strip())


COLOR_CHECKS = (check_pixels, check_find_blobs, check_binary, check_histogram,
                check_statistics, check_blob_color, check_find_blobs_cv,
                check_ball_color, check_custom_ball)


def run_color_checks(report):
    images, bgr = color_images()
    for path in ("addr", "open"):
        img = images[path]
        for check in COLOR_CHECKS:
            try:
                if check is check_pixels:
                    check(report, path, img, bgr)
                else:
                    check(report, path, img)
            except Exception as exc:  # keep going, report the failure
                report.add(check.__name__, path, "ERROR", repr(exc))


def rgba_canvas():
    return image.new(size=(WIDTH, HEIGHT), color=LIGHT, mode="RGBA")


def open_pair(name, rgba):
    """Save a drawing losslessly, decode it (open path) and mirror the decoded
    BGR memory into a zero-copy image (addr path)."""
    path = os.path.join(OUTPUT_DIR, name)
    if rgba.save(path) != 0:
        raise RuntimeError("save failed: %s" % path)
    opened = open_png(path)
    return {"open": opened,
            "addr": attach_bgr(raw_bytes(opened), opened.width, opened.height)}


def roi_around(cx, cy, half_w=65, half_h=55):
    x, y = max(0, cx - half_w), max(0, cy - half_h)
    return (x, y, min(WIDTH - x, half_w * 2), min(HEIGHT - y, half_h * 2))


def compare_paths(report, name, pair, run):
    results = {}
    for path in ("addr", "open"):
        try:
            results[path] = repr(run(pair[path]))
        except Exception as exc:
            results[path] = None
            report.add(name, path, "ERROR", repr(exc))
    if None in results.values():
        return
    consistent = results["addr"] == results["open"]
    produced = results["open"] not in ("[]", "{}", "None", "b''")
    if not consistent:
        report.add(name, "both", "FAIL", "addr=%s open=%s" % (
            results["addr"][:60], results["open"][:60]))
    elif not produced:
        report.add(name, "both", "WARN", "consistent but no result")
    else:
        report.add(name, "both", "PASS", "consistent: %s" % results["open"][:70])


def run_geometry_checks(report):
    cx, cy = GEOM_CENTER
    roi = roi_around(cx, cy)

    rgba = rgba_canvas()
    rgba.draw_rectangle(cx - 42, cy - 32, cx + 42, cy + 32, color=(15, 15, 15, 255),
                        thickness=6)
    pair = open_pair("geom_rects.png", rgba)
    compare_paths(report, "find_rects", pair,
                  lambda im: im.crop(*roi).find_rects(threshold=12000, is_xywh=1))
    compare_paths(report, "Canny", pair,
                  lambda im: hashlib.sha1(im.copy().Canny(10, 100).tobytes()).hexdigest())
    compare_paths(report, "find_line(func=0)", pair, lambda im: im.find_line(func=0))
    compare_paths(report, "find_line(func=1)", pair, lambda im: im.find_line(func=1))

    rgba = rgba_canvas()
    rgba.draw_circle(cx, cy, 30, color=(10, 10, 10, 255), thickness=6)
    pair = open_pair("geom_circles.png", rgba)
    compare_paths(report, "find_circles", pair,
                  lambda im: im.crop(*roi).find_circles(
                      threshold=2500, r_min=20, r_max=40, r_step=2,
                      x_margin=20, y_margin=20, r_margin=10))

    rgba = rgba_canvas()
    rgba.draw_line(cx - 45, cy + 25, cx + 45, cy - 25, color=(5, 5, 5, 255), thickness=6)
    pair = open_pair("geom_lines.png", rgba)
    compare_paths(report, "find_lines", pair,
                  lambda im: im.crop(*roi).find_lines(threshold=1200))
    compare_paths(report, "find_line_segments", pair,
                  lambda im: im.crop(*roi).find_line_segments())

    rgba = rgba_canvas()
    fixtures.draw_matrix(rgba, fixtures.QR_MATRIX, cx, cy, module=4, quiet=4)
    pair = open_pair("geom_qrcodes.png", rgba)
    compare_paths(report, "find_qrcodes", pair,
                  lambda im: im.find_qrcodes(roi=roi_around(cx, cy, 60, 60)))

    rgba = rgba_canvas()
    fixtures.draw_matrix(rgba, fixtures.APRILTAG_36H11[0], cx, cy, module=12,
                         quiet=0, black_bit="0")
    pair = open_pair("geom_apriltags.png", rgba)
    compare_paths(report, "find_apriltags", pair,
                  lambda im: [(item["id"], item["centroid"], item["hamming"])
                              for item in im.find_apriltags(families=16)])

    rgba = rgba_canvas()
    code, payload = fixtures.barcode_image("690123456781")
    rgba.draw_image(code, cx - code.width // 2, cy - code.height // 2)
    pair = open_pair("geom_barcodes.png", rgba)
    compare_paths(report, "find_barcodes(%s)" % payload, pair,
                  lambda im: [(item["payload"], item["type"])
                              for item in im.crop(*roi_around(cx, cy, 125, 48)).find_barcodes()])

    rgba = rgba_canvas()
    rgba.draw_rectangle(cx - 24, cy - 24, cx + 24, cy + 24, color=(20, 20, 20, 255),
                        thickness=-1)
    rgba.draw_line(cx - 18, cy, cx + 18, cy, color=(255, 255, 255, 255), thickness=5)
    rgba.draw_line(cx, cy - 18, cx, cy + 18, color=(255, 255, 255, 255), thickness=5)
    patch = image.new(size=(50, 50), color=(20, 20, 20, 255), mode="RGBA")
    patch.draw_line(6, 25, 42, 25, color=(255, 255, 255, 255), thickness=5)
    patch.draw_line(25, 6, 25, 42, color=(255, 255, 255, 255), thickness=5)
    template = open_pair("geom_template_patch.png", patch)["open"]
    pair = open_pair("geom_template.png", rgba)
    compare_paths(report, "find_template", pair,
                  lambda im: dict(im.crop(*roi).find_template(template, thresh=0.55,
                                                              step=2, search=1)))


def run_benchmark(report):
    sizes = ((320, 240), (640, 480), (1280, 960))
    attach_us, load_us = [], []
    for width, height in sizes:
        buffer = (ctypes.c_uint8 * (width * height * 3))()
        addr = ctypes.addressof(buffer)
        image.new(size=(width, height), mode="RGB", addr=addr)
        start = time.perf_counter()
        for _ in range(200):
            image.new(size=(width, height), mode="RGB", addr=addr)
        attach_us.append((time.perf_counter() - start) / 200 * 1e6)

        payload = bytes(buffer)
        start = time.perf_counter()
        for _ in range(10):
            image.load(payload, size=(width, height), mode="RGB")
        load_us.append((time.perf_counter() - start) / 10 * 1e6)

    ratio = attach_us[-1] / attach_us[0]
    detail = " ".join("%dx%d=%.0fus" % (w, h, us) for (w, h), us in zip(sizes, attach_us))
    report.check("image.new(addr) is O(1)", "addr", ratio < 4.0,
                 "%s ratio=%.2f (16x pixels)" % (detail, ratio))
    detail = " ".join("%dx%d=%.0fus" % (w, h, us) for (w, h), us in zip(sizes, load_us))
    report.add("image.load(bytes) copy path", "info", "INFO", detail)


def main():
    if not os.path.isdir(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)
    report = Report()
    so_path = os.path.abspath(_maix_image.__file__)
    with open(so_path, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    report.add("_maix_image", "so", "INFO", so_path)
    report.add("_maix_image", "sha", "INFO", digest)
    try:
        report.add("fb_alloc_size", "info", "INFO", str(image.get_fb_alloc_size()))
    except Exception:
        pass

    run_color_checks(report)
    run_geometry_checks(report)
    run_benchmark(report)

    verdict = "ALL PASS" if report.failures == 0 else "%d FAILURE(S)" % report.failures
    report.add("summary", "", "INFO", verdict)
    report.write(os.path.join(OUTPUT_DIR, "00_summary.txt"))
    print("results:", OUTPUT_DIR)
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
