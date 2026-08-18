"""Read pre-generated input images and run find_xxx tests on a MaixPy3 board."""

import os

from maix import image


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = SCRIPT_DIR
OUTPUT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR),
                          "find_xxx_embedded_results")
WIDTH, HEIGHT = 720, 480
POSITIONS = ((90, 80), (630, 80), (360, 240), (90, 400), (630, 400))
BARCODE_POSITIONS = ((140, 80), (580, 80), (360, 240),
                     (140, 400), (580, 400))
GREEN = (40, 255, 80, 255)
YELLOW = (255, 230, 40, 255)


def input_path(name):
    path = os.path.join(INPUT_DIR, name)
    if not os.path.exists(path):
        raise RuntimeError("missing input: %s" % path)
    return path


def open_rgba_for_detection(name):
    """Return an RGBA drawing image and an RGB find_xxx working copy."""
    rgba = image.open(input_path(name))
    rgba.convert("RGBA")
    if rgba.mode != "RGBA":
        raise RuntimeError("RGB to RGBA conversion is unavailable")
    rgb = rgba.copy()
    rgb.convert("RGB")
    if rgb.mode != "RGB":
        raise RuntimeError("RGBA to RGB conversion is unavailable")
    return rgba, rgb


def roi_around(cx, cy, half_w=65, half_h=55):
    x, y = max(0, cx - half_w), max(0, cy - half_h)
    return (x, y, min(WIDTH - x, half_w * 2), min(HEIGHT - y, half_h * 2))


def label(img, text, x, y):
    img.draw_string(max(0, x), max(0, y), str(text)[:58],
                    scale=0.9, color=YELLOW, thickness=1)


def mark_box(img, x, y, w, h, text):
    img.draw_rectangle(x, y, x + w, y + h, color=GREEN, thickness=3)
    img.draw_cross(x + w // 2, y + h // 2, 0x07E0, size=8, thickness=2)
    label(img, text, x, y - 18)


def mark_corners(img, corners):
    for index in range(4):
        x1, y1 = corners[index]
        x2, y2 = corners[(index + 1) % 4]
        img.draw_line(x1, y1, x2, y2, color=GREEN, thickness=3)


def save_result(number, name, img, found):
    if img.mode != "RGBA":
        raise RuntimeError("result drawing image is not RGBA: %s" % img.mode)
    label(img, "%02d %s count=%d" % (number, name, len(found)), 8, 8)
    path = os.path.join(OUTPUT_DIR, "%02d_%s_result.jpg" % (number, name))
    if img.save(path) != 0:
        raise RuntimeError("save failed: %s" % path)
    return path


def test_blobs():
    img, detect = open_rgba_for_detection("01_find_blobs_input.jpg")
    found = list(detect.find_blobs([(20, 80, 20, 127, 0, 127)],
                                   area_threshold=300, pixels_threshold=300))
    for i, item in enumerate(found, 1):
        mark_box(img, item["x"], item["y"], item["w"], item["h"],
                 "#%d px=%s code=%s" % (i, item["pixels"], item["code"]))
    return save_result(1, "find_blobs", img, found), found


def test_rects():
    img, detect = open_rgba_for_detection("02_find_rects_input.jpg")
    found = []
    for cx, cy in POSITIONS:
        rx, ry, rw, rh = roi_around(cx, cy)
        for item in detect.crop(rx, ry, rw, rh).find_rects(threshold=12000,
                                                           is_xywh=1):
            item[0], item[1] = item[0] + rx, item[1] + ry
            found.append(item)
    for i, (x, y, w, h, magnitude) in enumerate(found, 1):
        mark_box(img, x, y, w, h, "#%d mag=%s" % (i, magnitude))
    return save_result(2, "find_rects", img, found), found


def test_circles():
    img, detect = open_rgba_for_detection("03_find_circles_input.jpg")
    found = []
    for cx, cy in POSITIONS:
        rx, ry, rw, rh = roi_around(cx, cy)
        candidates = list(detect.crop(rx, ry, rw, rh).find_circles(
            threshold=2500, r_min=20, r_max=40, r_step=2,
            x_margin=20, y_margin=20, r_margin=10))
        if candidates:
            item = min(candidates, key=lambda v: abs(v[0] - rw // 2) +
                       abs(v[1] - rh // 2) + abs(v[2] - 30))
            item[0], item[1] = item[0] + rx, item[1] + ry
            found.append(item)
    for i, (x, y, radius, magnitude) in enumerate(found, 1):
        img.draw_circle(x, y, radius, color=GREEN, thickness=3)
        label(img, "#%d (%d,%d) r=%d m=%s" %
              (i, x, y, radius, magnitude), x - radius, y - radius - 18)
    return save_result(3, "find_circles", img, found), found


def test_lines():
    img, detect = open_rgba_for_detection("04_find_lines_input.jpg")
    found = []
    for cx, cy in POSITIONS:
        rx, ry, rw, rh = roi_around(cx, cy)
        candidates = list(detect.crop(rx, ry, rw, rh).find_lines(threshold=1200))
        if candidates:
            item = max(candidates,
                       key=lambda v: (v[2] - v[0]) ** 2 + (v[3] - v[1]) ** 2)
            item[0], item[1] = item[0] + rx, item[1] + ry
            item[2], item[3] = item[2] + rx, item[3] + ry
            found.append(item)
    for i, (x1, y1, x2, y2) in enumerate(found, 1):
        img.draw_line(x1, y1, x2, y2, color=GREEN, thickness=3)
        label(img, "#%d (%d,%d)-(%d,%d)" % (i, x1, y1, x2, y2),
              min(x1, x2), min(y1, y2) - 18)
    return save_result(4, "find_lines", img, found), found


def test_qrcodes():
    img, detect = open_rgba_for_detection("05_find_qrcodes_input.jpg")
    found = []
    for cx, cy in POSITIONS:
        found.extend(detect.find_qrcodes(roi=roi_around(cx, cy, 60, 60)))
    for i, item in enumerate(found, 1):
        mark_box(img, item["x"], item["y"], item["w"], item["h"],
                 "#%d %s v=%s" % (i, item["payload"], item["version"]))
    return save_result(5, "find_qrcodes", img, found), found


def test_template():
    img, detect = open_rgba_for_detection("06_find_template_input.jpg")
    unused_rgba_template, template = open_rgba_for_detection(
        "06_find_template_patch.jpg")
    found_all = []
    for cx, cy in POSITIONS:
        rx, ry, rw, rh = roi_around(cx, cy)
        found = dict(detect.crop(rx, ry, rw, rh).find_template(
            template, thresh=0.55, step=2, search=1))
        if found:
            found["x"], found["y"] = found["x"] + rx, found["y"] + ry
            found_all.append(found)
            mark_box(img, found["x"], found["y"], found["w"], found["h"],
                     "match=%.3f" % found["thresh"])
    return save_result(6, "find_template", img, found_all), found_all


def test_apriltags():
    img, detect = open_rgba_for_detection("07_find_apriltags_input.png")
    found = [item for item in detect.find_apriltags(families=16)
             if abs(item["centroid"][0] - WIDTH // 2) < 80 and
             abs(item["centroid"][1] - HEIGHT // 2) < 80]
    for cx, cy in (POSITIONS[0], POSITIONS[1], POSITIONS[3], POSITIONS[4]):
        rx, ry, rw, rh = roi_around(cx, cy, 58, 58)
        for item in detect.crop(rx, ry, rw, rh).find_apriltags(families=16):
            item["x"], item["y"] = item["x"] + rx, item["y"] + ry
            item["centroid"] = [item["centroid"][0] + rx,
                                item["centroid"][1] + ry]
            item["corners"] = [[x + rx, y + ry] for x, y in item["corners"]]
            found.append(item)
    for i, item in enumerate(found, 1):
        mark_corners(img, item["corners"])
        label(img, "#%d id=%s family=%s h=%s" %
              (i, item["id"], item["family"], item["hamming"]),
              item["x"], item["y"] - 18)
    return save_result(7, "find_apriltags", img, found), found


def test_barcodes():
    img, detect = open_rgba_for_detection("08_find_barcodes_input.jpg")
    found = []
    for cx, cy in BARCODE_POSITIONS:
        rx, ry, rw, rh = roi_around(cx, cy, 125, 48)
        for item in detect.crop(rx, ry, rw, rh).find_barcodes():
            item["x"], item["y"] = item["x"] + rx, item["y"] + ry
            item["corners"] = [[x + rx, y + ry] for x, y in item["corners"]]
            found.append(item)
    for i, item in enumerate(found, 1):
        mark_corners(img, item["corners"])
        label(img, "#%d %s type=%s q=%s" %
              (i, item["payload"], item["type"], item["quality"]),
              item["x"], item["y"] - 18)
    return save_result(8, "find_barcodes", img, found), found


def main():
    if not os.path.isdir(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)
    tests = (test_blobs, test_rects, test_circles, test_lines,
             test_qrcodes, test_template, test_apriltags, test_barcodes)
    report = []
    for number, test in enumerate(tests, 1):
        try:
            result, found = test()
            status = "PASS" if len(found) == 5 else "FAIL"
            line = ("%02d %-18s %-4s count=%d" %
                    (number, test.__name__[5:], status, len(found)))
            print(line, "->", result)
        except Exception as error:
            line = ("%02d %-18s ERROR %s" %
                    (number, test.__name__[5:], error))
            print(line)
        report.append(line)
    summary = os.path.join(OUTPUT_DIR, "00_summary.txt")
    with open(summary, "w") as output:
        output.write("\n".join(report) + "\n")
    print("summary:", summary)


if __name__ == "__main__":
    main()
