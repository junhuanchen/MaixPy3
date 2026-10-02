"""Board-side find_xxx tests using MaixPy3 image APIs only."""

import os

from maix import image


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = SCRIPT_DIR
WIDTH, HEIGHT = 720, 480
POSITIONS = ((90, 80), (630, 80), (360, 240), (90, 400), (630, 400))
GREEN = (40, 255, 80, 255)
YELLOW = (255, 230, 40, 255)


def reset_output():
    if not os.path.isdir(OUT):
        os.mkdir(OUT)
    for name in os.listdir(OUT):
        path = os.path.join(OUT, name)
        generated = (name == "00_summary.txt" or
                     name.startswith(tuple("%02d_" % i for i in range(1, 9))))
        if os.path.isfile(path) and generated and not name.endswith(".py"):
            os.remove(path)


def canvas():
    return image.new(size=(WIDTH, HEIGHT), color=(238, 242, 248, 255), mode="RGBA")


def save_input(number, name, img, extension="jpg"):
    path = os.path.join(OUT, "%02d_%s_input.%s" % (number, name, extension))
    if img.save(path) != 0:
        raise RuntimeError("save failed: %s" % path)
    return path


def label(img, text, x, y, color=YELLOW):
    img.draw_string(max(0, x), max(0, y), str(text)[:58],
                    scale=0.9, color=color, thickness=1)


def mark_box(img, x, y, w, h, text):
    img.draw_rectangle(x, y, x + w, y + h, color=GREEN, thickness=3)
    img.draw_cross(x + w // 2, y + h // 2, 0x07E0, size=8, thickness=2)
    label(img, text, x, y - 18)


def mark_corners(img, corners):
    for index in range(4):
        x1, y1 = corners[index]
        x2, y2 = corners[(index + 1) % 4]
        img.draw_line(x1, y1, x2, y2, color=GREEN, thickness=3)


def roi_around(cx, cy, half_w=65, half_h=55):
    x = max(0, cx - half_w)
    y = max(0, cy - half_h)
    return (x, y, min(WIDTH - x, half_w * 2), min(HEIGHT - y, half_h * 2))


def finish(number, name, img, found):
    label(img, "%02d %s count=%d" % (number, name, len(found)), 8, 8)
    output = os.path.join(OUT, "%02d_%s_result.jpg" % (number, name))
    rc = img.save(output)
    if rc != 0 or not os.path.exists(output):
        raise RuntimeError("save failed: %s" % output)
    return output


def test_01_find_blobs():
    pil = canvas()
    for i, (cx, cy) in enumerate(POSITIONS, 1):
        pil.draw_rectangle(cx - 38, cy - 28, cx + 38, cy + 28,
                           color=(255, 0, 0, 255), thickness=-1)
    src = save_input(1, "find_blobs", pil)
    img = image.open(str(src))
    # OpenMV LAB threshold for saturated red.
    found = list(img.find_blobs([(20, 80, 20, 127, 0, 127)],
                                area_threshold=300, pixels_threshold=300))
    for i, item in enumerate(found, 1):
        mark_box(img, item["x"], item["y"], item["w"], item["h"],
                 "#%d px=%s code=%s" % (i, item["pixels"], item["code"]))
    return src, finish(1, "find_blobs", img, found), found


def test_02_find_rects():
    pil = canvas()
    for cx, cy in POSITIONS:
        pil.draw_rectangle(cx - 42, cy - 32, cx + 42, cy + 32,
                           color=(15, 15, 15, 255), thickness=6)
    src = save_input(2, "find_rects", pil)
    img = image.open(str(src))
    found = []
    for cx, cy in POSITIONS:
        rx, ry, rw, rh = roi_around(cx, cy)
        crop = img.crop(rx, ry, rw, rh)
        for item in crop.find_rects(threshold=12000, is_xywh=1):
            item[0] += rx
            item[1] += ry
            found.append(item)
    for i, item in enumerate(found, 1):
        x, y, w, h, magnitude = item
        mark_box(img, x, y, w, h, "#%d mag=%s" % (i, magnitude))
    return src, finish(2, "find_rects", img, found), found


def test_03_find_circles():
    pil = canvas()
    for cx, cy in POSITIONS:
        pil.draw_circle(cx, cy, 30, color=(10, 10, 10, 255), thickness=6)
    src = save_input(3, "find_circles", pil)
    img = image.open(str(src))
    found = []
    for cx, cy in POSITIONS:
        rx, ry, rw, rh = roi_around(cx, cy)
        crop = img.crop(rx, ry, rw, rh)
        candidates = list(crop.find_circles(
            threshold=2500, r_min=20, r_max=40,
            r_step=2, x_margin=20, y_margin=20, r_margin=10))
        if candidates:
            item = min(candidates,
                       key=lambda v: abs(v[0] - rw // 2) +
                       abs(v[1] - rh // 2) + abs(v[2] - 30))
            item[0] += rx
            item[1] += ry
            found.append(item)
    for i, item in enumerate(found, 1):
        x, y, radius, magnitude = item
        img.draw_circle(x, y, radius, color=GREEN, thickness=3)
        img.draw_cross(x, y, 0x07E0, size=8, thickness=2)
        label(img, "#%d (%d,%d) r=%d m=%s" %
              (i, x, y, radius, magnitude), x - radius, y - radius - 18)
    return src, finish(3, "find_circles", img, found), found


def test_04_find_lines():
    pil = canvas()
    for cx, cy in POSITIONS:
        pil.draw_line(cx - 45, cy + 25, cx + 45, cy - 25,
                      color=(5, 5, 5, 255), thickness=6)
    src = save_input(4, "find_lines", pil)
    img = image.open(str(src))
    found = []
    for cx, cy in POSITIONS:
        rx, ry, rw, rh = roi_around(cx, cy)
        crop = img.crop(rx, ry, rw, rh)
        candidates = list(crop.find_lines(threshold=1200))
        if candidates:
            item = max(candidates,
                       key=lambda v: (v[2] - v[0]) ** 2 + (v[3] - v[1]) ** 2)
            item[0] += rx
            item[1] += ry
            item[2] += rx
            item[3] += ry
            found.append(item)
    for i, item in enumerate(found, 1):
        x1, y1, x2, y2 = item
        img.draw_line(x1, y1, x2, y2, color=GREEN, thickness=3)
        label(img, "#%d (%d,%d)-(%d,%d)" %
              (i, x1, y1, x2, y2), min(x1, x2), min(y1, y2) - 18)
    return src, finish(4, "find_lines", img, found), found


QR_MATRIX = (
    "111111100101101111111", "100000100111001000001",
    "101110101101101011101", "101110100101001011101",
    "101110100010101011101", "100000100000101000001",
    "111111101010101111111", "000000001101100000000",
    "111011111111011000100", "100111011000001100010",
    "100000101110100010000", "011100001010001001111",
    "010100101010101011110", "000000001001010100001",
    "111111101111011011001", "100000101101110101000",
    "101110101101011010011", "101110100000001101010",
    "101110101110100001101", "100000101110001000111",
    "111111101000101110101",
)


def draw_matrix(img, matrix, cx, cy, module, quiet=1, black_bit="1"):
    width = (len(matrix[0]) + quiet * 2) * module
    height = (len(matrix) + quiet * 2) * module
    x0, y0 = cx - width // 2, cy - height // 2
    img.draw_rectangle(x0, y0, x0 + width - 1, y0 + height - 1,
                       color=(255, 255, 255, 255), thickness=-1)
    for row, bits in enumerate(matrix):
        for column, bit in enumerate(bits):
            if bit == black_bit:
                x = x0 + (column + quiet) * module
                y = y0 + (row + quiet) * module
                img.draw_rectangle(x, y, x + module - 1, y + module - 1,
                                   color=(0, 0, 0, 255), thickness=-1)


def test_05_find_qrcodes():
    pil = canvas()
    for cx, cy in POSITIONS:
        # Embedded version-1 QR payload: MAIXPY3-01.
        draw_matrix(pil, QR_MATRIX, cx, cy, module=4, quiet=4)
    src = save_input(5, "find_qrcodes", pil)
    img = image.open(str(src))
    found = []
    for cx, cy in POSITIONS:
        found.extend(img.find_qrcodes(roi=roi_around(cx, cy, 60, 60)))
    for i, item in enumerate(found, 1):
        mark_box(img, item["x"], item["y"], item["w"], item["h"],
                 "#%d %s v=%s" % (i, item["payload"], item["version"]))
    return src, finish(5, "find_qrcodes", img, found), found


def test_06_find_template():
    pil = canvas()
    for cx, cy in POSITIONS:
        pil.draw_rectangle(cx - 24, cy - 24, cx + 24, cy + 24,
                           color=(20, 20, 20, 255), thickness=-1)
        pil.draw_line(cx - 18, cy, cx + 18, cy,
                      color=(255, 255, 255, 255), thickness=5)
        pil.draw_line(cx, cy - 18, cx, cy + 18,
                      color=(255, 255, 255, 255), thickness=5)
    template_path = os.path.join(OUT, "06_find_template_patch.jpg")
    # RGBA crop is not implemented by the current backend. Build the small
    # template directly in RGBA instead of silently receiving an empty image.
    template_pil = image.new(size=(50, 50),
                             color=(20, 20, 20, 255), mode="RGBA")
    template_pil.draw_line(6, 25, 42, 25,
                           color=(255, 255, 255, 255), thickness=5)
    template_pil.draw_line(25, 6, 25, 42,
                           color=(255, 255, 255, 255), thickness=5)
    if template_pil.save(template_path) != 0 or not os.path.exists(template_path):
        raise RuntimeError("save failed: %s" % template_path)
    src = save_input(6, "find_template", pil)
    img = image.open(str(src))
    template = image.open(str(template_path))
    items = []
    for cx, cy in POSITIONS:
        rx, ry, rw, rh = roi_around(cx, cy)
        crop = img.crop(rx, ry, rw, rh)
        found = dict(crop.find_template(template, thresh=0.55,
                                        step=2, search=1))
        if found:
            found["x"] += rx
            found["y"] += ry
            items.append(found)
            mark_box(img, found["x"], found["y"], found["w"], found["h"],
                     "match=%.3f" % found["thresh"])
    return src, finish(6, "find_template", img, items), items


APRILTAG_36H11 = (
    ("00000000", "00010000", "00110100", "00001010",
     "00001100", "01011100", "01010110", "00000000"),
    ("00000000", "01001000", "01011010", "00001100",
     "00011110", "01110100", "00110110", "00000000"),
    ("00000000", "00100010", "00000010", "00101000",
     "01111010", "00011110", "00101110", "00000000"),
    ("00000000", "00011010", "00111000", "01101010",
     "00110110", "01000110", "00011110", "00000000"),
    ("00000000", "01010000", "00100000", "01011100",
     "01001010", "00110100", "01000000", "00000000"),
)


def test_07_find_apriltags():
    pil = canvas()
    for matrix, (cx, cy) in zip(APRILTAG_36H11, POSITIONS):
        # OpenCV's exported marker table uses 0 for black and 1 for white.
        draw_matrix(pil, matrix, cx, cy, module=12, quiet=0, black_bit="0")
    # Lossless input is important for small tag cells; JPEG artifacts make
    # some valid tag IDs undecodable on the bundled imlib implementation.
    src = save_input(7, "find_apriltags", pil, extension="png")
    img = image.open(str(src))
    # Full-image detection reliably finds the center tag. Detect the four
    # corners on crops to keep memory use bounded, then merge the results.
    found = [item for item in img.find_apriltags(families=16)
             if abs(item["centroid"][0] - WIDTH // 2) < 80 and
             abs(item["centroid"][1] - HEIGHT // 2) < 80]
    for cx, cy in (POSITIONS[0], POSITIONS[1], POSITIONS[3], POSITIONS[4]):
        rx, ry, rw, rh = roi_around(cx, cy, 58, 58)
        crop = img.crop(rx, ry, rw, rh)
        for item in crop.find_apriltags(families=16):
            item["x"] += rx
            item["y"] += ry
            item["centroid"] = [item["centroid"][0] + rx,
                                item["centroid"][1] + ry]
            item["corners"] = [[x + rx, y + ry] for x, y in item["corners"]]
            found.append(item)
    for i, item in enumerate(found, 1):
        mark_corners(img, item["corners"])
        x, y = item["centroid"]
        img.draw_cross(x, y, 0x07E0, size=8, thickness=2)
        label(img, "#%d id=%s family=%s h=%s" %
              (i, item["id"], item["family"], item["hamming"]),
              item["x"], item["y"] - 18)
    return src, finish(7, "find_apriltags", img, found), found


def barcode_image(first_twelve, module=2, height=80):
    """Render a standards-compliant EAN-13 barcode with integer-width bars."""
    l_code = ("0001101", "0011001", "0010011", "0111101", "0100011",
              "0110001", "0101111", "0111011", "0110111", "0001011")
    g_code = ("0100111", "0110011", "0011011", "0100001", "0011101",
              "0111001", "0000101", "0010001", "0001001", "0010111")
    r_code = tuple("".join("1" if bit == "0" else "0" for bit in code)
                   for code in l_code)
    parity = ("LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG",
              "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL")

    if len(first_twelve) != 12 or not first_twelve.isdigit():
        raise ValueError("EAN-13 input must contain its first 12 digits")
    checksum = (10 - sum((3 if i % 2 else 1) * int(ch)
                         for i, ch in enumerate(first_twelve)) % 10) % 10
    digits = first_twelve + str(checksum)
    left = "".join((l_code if kind == "L" else g_code)[int(digit)]
                   for kind, digit in zip(parity[int(digits[0])], digits[1:7]))
    right = "".join(r_code[int(digit)] for digit in digits[7:])
    bits = "0" * 12 + "101" + left + "01010" + right + "101" + "0" * 12

    result = image.new(size=(len(bits) * module, height),
                       color=(255, 255, 255, 255), mode="RGBA")
    for index, bit in enumerate(bits):
        if bit == "1":
            result.draw_rectangle(index * module, 5,
                                  (index + 1) * module - 1, height - 6,
                                  color=(0, 0, 0, 255), thickness=-1)
    return result, digits


def test_08_find_barcodes():
    pil = canvas()
    barcode_positions = ((140, 80), (580, 80), (360, 240),
                         (140, 400), (580, 400))
    payloads = []
    for i, (cx, cy) in enumerate(barcode_positions, 1):
        code, payload = barcode_image("69012345678%d" % i)
        payloads.append(payload)
        pil.draw_image(code, cx - code.width // 2, cy - code.height // 2)
    src = save_input(8, "find_barcodes", pil)
    img = image.open(str(src))
    found = []
    for cx, cy in barcode_positions:
        rx, ry, rw, rh = roi_around(cx, cy, 125, 48)
        crop = img.crop(rx, ry, rw, rh)
        for item in crop.find_barcodes():
            item["x"] += rx
            item["y"] += ry
            item["corners"] = [[x + rx, y + ry] for x, y in item["corners"]]
            found.append(item)
    for i, item in enumerate(found, 1):
        mark_corners(img, item["corners"])
        label(img, "#%d %s type=%s q=%s" %
              (i, item["payload"], item["type"], item["quality"]),
              item["x"], item["y"] - 18)
    return src, finish(8, "find_barcodes", img, found), found


def generate_samples():
    """Generate input fixtures only; do not run any find_xxx function."""
    reset_output()

    img = canvas()
    for cx, cy in POSITIONS:
        img.draw_rectangle(cx - 38, cy - 28, cx + 38, cy + 28,
                           color=(255, 0, 0, 255), thickness=-1)
    save_input(1, "find_blobs", img)

    img = canvas()
    for cx, cy in POSITIONS:
        img.draw_rectangle(cx - 42, cy - 32, cx + 42, cy + 32,
                           color=(15, 15, 15, 255), thickness=6)
    save_input(2, "find_rects", img)

    img = canvas()
    for cx, cy in POSITIONS:
        img.draw_circle(cx, cy, 30, color=(10, 10, 10, 255), thickness=6)
    save_input(3, "find_circles", img)

    img = canvas()
    for cx, cy in POSITIONS:
        img.draw_line(cx - 45, cy + 25, cx + 45, cy - 25,
                      color=(5, 5, 5, 255), thickness=6)
    save_input(4, "find_lines", img)

    img = canvas()
    for cx, cy in POSITIONS:
        draw_matrix(img, QR_MATRIX, cx, cy, module=4, quiet=4)
    save_input(5, "find_qrcodes", img)

    img = canvas()
    for cx, cy in POSITIONS:
        img.draw_rectangle(cx - 24, cy - 24, cx + 24, cy + 24,
                           color=(20, 20, 20, 255), thickness=-1)
        img.draw_line(cx - 18, cy, cx + 18, cy,
                      color=(255, 255, 255, 255), thickness=5)
        img.draw_line(cx, cy - 18, cx, cy + 18,
                      color=(255, 255, 255, 255), thickness=5)
    patch = image.new(size=(50, 50), color=(20, 20, 20, 255), mode="RGBA")
    patch.draw_line(6, 25, 42, 25, color=(255, 255, 255, 255), thickness=5)
    patch.draw_line(25, 6, 25, 42, color=(255, 255, 255, 255), thickness=5)
    patch.save(os.path.join(OUT, "06_find_template_patch.jpg"))
    save_input(6, "find_template", img)

    img = canvas()
    for matrix, (cx, cy) in zip(APRILTAG_36H11, POSITIONS):
        draw_matrix(img, matrix, cx, cy, module=12, quiet=0, black_bit="0")
    save_input(7, "find_apriltags", img, extension="png")

    img = canvas()
    barcode_positions = ((140, 80), (580, 80), (360, 240),
                         (140, 400), (580, 400))
    for i, (cx, cy) in enumerate(barcode_positions, 1):
        code, unused_payload = barcode_image("69012345678%d" % i)
        img.draw_image(code, cx - code.width // 2, cy - code.height // 2)
    save_input(8, "find_barcodes", img)

    print("samples:", OUT)


def main():
    reset_output()
    tests = [test_01_find_blobs, test_02_find_rects, test_03_find_circles,
             test_04_find_lines, test_05_find_qrcodes, test_06_find_template,
             test_07_find_apriltags, test_08_find_barcodes]
    report = []
    for number, test in enumerate(tests, 1):
        name = test.__name__.split("_", 2)[2]
        try:
            src, result, found = test()
            status = "PASS" if found else "NO_RESULT"
            line = "%02d %-18s %-9s count=%d" % (number, name, status, len(found))
            report.append(line)
            print(line, "->", os.path.basename(result))
        except Exception as exc:
            line = "%02d %-18s ERROR     %s" % (number, name, exc)
            report.append(line)
            print(line)
    report_path = os.path.join(OUT, "00_summary.txt")
    with open(report_path, "w") as output:
        output.write("\n".join(report) + "\n")
    print("summary:", report_path)


if __name__ == "__main__":
    main()
