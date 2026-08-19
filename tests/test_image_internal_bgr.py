"""Regression and micro-benchmark tests for public RGB(A), internal BGR(A).

Run from the repository root:
    PYTHONPATH=. python3 tests/test_image_internal_bgr.py
"""

import ctypes
import ctypes.util
import os
import tempfile
import time
import unittest

import cv2
import numpy as np
from PIL import Image as PILImage


libgomp = ctypes.util.find_library("gomp")
if libgomp:
    ctypes.CDLL(libgomp, mode=ctypes.RTLD_GLOBAL)

from maix import image


RGB_PIXELS = np.array(
    [[[255, 0, 0], [0, 255, 0]],
     [[0, 0, 255], [17, 83, 191]]], dtype=np.uint8)


def internal_array(img):
    channels = 4 if img.mode == "RGBA" else 3
    storage = (ctypes.c_uint8 * img.size).from_address(img.to_addr())
    return np.ctypeslib.as_array(storage).reshape(img.height, img.width,
                                                   channels)


class InternalBGRTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tempdir.cleanup()

    def path(self, name):
        return os.path.join(self.tempdir.name, name)

    def test_load_and_tobytes_boundary(self):
        rgb = image.load(RGB_PIXELS.tobytes(), size=(2, 2), mode="RGB")
        np.testing.assert_array_equal(internal_array(rgb),
                                      RGB_PIXELS[:, :, ::-1])
        self.assertEqual(rgb.tobytes(), RGB_PIXELS.tobytes())

        alpha = np.full((2, 2, 1), 137, dtype=np.uint8)
        rgba_pixels = np.concatenate((RGB_PIXELS, alpha), axis=2)
        rgba = image.load(rgba_pixels.tobytes(), size=(2, 2), mode="RGBA")
        expected_bgra = rgba_pixels[:, :, [2, 1, 0, 3]]
        np.testing.assert_array_equal(internal_array(rgba), expected_bgra)
        self.assertEqual(rgba.tobytes(), rgba_pixels.tobytes())

    def test_open_process_and_save_keep_public_colors(self):
        source = self.path("source.png")
        output = self.path("output.png")
        PILImage.fromarray(RGB_PIXELS, "RGB").save(source)

        img = image.open(source)
        self.assertEqual(img.mode, "RGB")
        np.testing.assert_array_equal(internal_array(img),
                                      RGB_PIXELS[:, :, ::-1])
        self.assertEqual(img.tobytes(), RGB_PIXELS.tobytes())

        # Pixel and drawing APIs still consume/return public RGB tuples.
        img.set_pixel(1, 1, (201, 31, 73))
        self.assertEqual(img.get_pixel(1, 1)[:3], [201, 31, 73])
        self.assertEqual(tuple(internal_array(img)[1, 1]), (73, 31, 201))
        self.assertEqual(img.save(output), 0)
        self.assertEqual(PILImage.open(output).convert("RGB").getpixel((1, 1)),
                         (201, 31, 73))

    def test_internal_buffer_is_direct_opencv_display_storage(self):
        """OpenCV can save/display the address buffer without color conversion."""
        img = image.load(RGB_PIXELS.tobytes(), size=(2, 2), mode="RGB")
        direct_output = self.path("direct-bgr.png")
        self.assertTrue(cv2.imwrite(direct_output, internal_array(img)))
        np.testing.assert_array_equal(
            np.asarray(PILImage.open(direct_output).convert("RGB")), RGB_PIXELS)

        rgba_pixels = np.dstack((RGB_PIXELS, np.full((2, 2), 255,
                                                     dtype=np.uint8)))
        rgba = image.load(rgba_pixels.tobytes(), size=(2, 2), mode="RGBA")
        direct_rgba_output = self.path("direct-bgra.png")
        self.assertTrue(cv2.imwrite(direct_rgba_output, internal_array(rgba)))
        np.testing.assert_array_equal(
            np.asarray(PILImage.open(direct_rgba_output).convert("RGBA")),
            rgba_pixels)

    def test_rgb_rgba_convert_and_geometry(self):
        img = image.load(RGB_PIXELS.tobytes(), size=(2, 2), mode="RGB")
        img.convert("RGBA")
        expected = np.dstack((RGB_PIXELS, np.full((2, 2), 255,
                                                  dtype=np.uint8)))
        self.assertEqual(img.tobytes(), expected.tobytes())
        img.resize(4, 4, padding=0)
        cropped = img.crop(0, 0, 2, 2)
        self.assertEqual(cropped.mode, "RGBA")
        self.assertEqual(len(cropped.tobytes()), 2 * 2 * 4)
        cropped.convert("RGB")
        self.assertEqual(cropped.mode, "RGB")


def benchmark(iterations=100, width=640, height=480):
    rng = np.random.default_rng(20260819)
    pixels = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
    payload = pixels.tobytes()

    start = time.perf_counter()
    for _ in range(iterations):
        img = image.load(payload, size=(width, height), mode="RGB")
    load_ms = (time.perf_counter() - start) * 1000 / iterations

    start = time.perf_counter()
    for _ in range(iterations):
        img.tobytes()
    tobytes_ms = (time.perf_counter() - start) * 1000 / iterations

    start = time.perf_counter()
    for _ in range(iterations):
        cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR)
    conversion_ms = (time.perf_counter() - start) * 1000 / iterations

    start = time.perf_counter()
    for _ in range(iterations):
        internal_array(img)
    zero_copy_view_us = (time.perf_counter() - start) * 1_000_000 / iterations

    print("\n640x480 RGB boundary benchmark (%d iterations):" % iterations)
    print("  image.load RGB->BGR: %.3f ms/call" % load_ms)
    print("  image.tobytes BGR->RGB: %.3f ms/call" % tobytes_ms)
    print("  cv2 channel swap only: %.3f ms/call" % conversion_ms)
    print("  to_addr BGR zero-copy view: %.3f us/call" % zero_copy_view_us)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(InternalBGRTest)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        benchmark()
    raise SystemExit(not result.wasSuccessful())
