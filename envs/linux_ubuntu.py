
from pybind11 import get_cmake_dir
from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import Extension
from .utils import get_incs, get_srcs

freetype_sources = [
    "autofit/autofit.c", "base/ftbase.c", "base/ftbbox.c",
    "base/ftbdf.c", "base/ftbitmap.c", "base/ftcid.c",
    "base/ftdebug.c", "base/ftfstype.c", "base/ftgasp.c",
    "base/ftglyph.c", "base/ftgxval.c", "base/ftinit.c", "base/ftmm.c",
    "base/ftotval.c", "base/ftpatent.c", "base/ftpfr.c",
    "base/ftstroke.c", "base/ftsynth.c", "base/fttype1.c",
    "base/ftwinfnt.c", "bdf/bdf.c", "bzip2/ftbzip2.c",
    "cache/ftcache.c", "cff/cff.c", "cid/type1cid.c", "gzip/ftgzip.c",
    "lzw/ftlzw.c", "pcf/pcf.c", "pfr/pfr.c", "psaux/psaux.c",
    "pshinter/pshinter.c", "psnames/psnames.c", "raster/raster.c",
    "sdf/sdf.c", "sfnt/sfnt.c", "smooth/smooth.c", "svg/svg.c",
    "truetype/truetype.c", "type1/type1.c", "type42/type42.c",
    "winfonts/winfnt.c", "../builds/unix/ftsystem.c",
]
freetype_sources = ["ext_modules/freetype-2.14.3/src/" + source
                    for source in freetype_sources]

libi2c_module = Extension('pylibi2c',
  include_dirs=[
    'ext_modules/libi2c/src'
  ],
  sources=get_srcs('ext_modules/libi2c/src')
)

_maix_module = Extension('_maix',
    include_dirs=[
    'ext_modules/_maix/include'],
    sources=get_srcs('ext_modules/_maix'),
    libraries=[
    "jpeg"
])

_maix_image_module = Pybind11Extension(
    name = "_maix_image",
    include_dirs=[ 
        # '/usr/include/opencv4/', '/usr/local/include/opencv4/',
        get_incs(
            'ext_modules/opencv-mobile-4.13.0-ubuntu-2204/include'),
        get_incs(
            'ext_modules/opencv-mobile-4.13.0-ubuntu-2204/include/opencv4'),
        get_incs(
            'ext_modules/freetype-2.14.3/include'),
        get_incs(
            'ext_modules/libmaix/components/libmaix/include'),
        get_incs(
            'ext_modules/libmaix/components/maix_cv_image/include'),
        get_incs(
            'ext_modules/libmaix/libmaix/lib/arch/desktop/libmaix_utils'),
        get_incs(
            'ext_modules/libmaix/libmaix/lib/arch/desktop/libmaix_image'),
        get_incs(
            'ext_modules/libmaix/components/maix_cv_image/include'),
        get_incs(
            'ext_modules/libmaix/components/third_party/include'),
        get_incs(
            'ext_modules/libmaix/components/third_party/imlib/include'),
        get_incs(
            'ext_modules/_maix_image/include')
    ],
    sources= get_srcs('ext_modules/libmaix/components/maix_cv_image/src') +
             get_srcs('ext_modules/libmaix/components/libmaix/lib/arch/desktop/libmaix_utils') +
             get_srcs('ext_modules/libmaix/components/libmaix/lib/arch/desktop/libmaix_image') +
             get_srcs('ext_modules/libmaix/components/third_party/imlib/src') +
             get_srcs('ext_modules/_maix_image') +
             freetype_sources,
    libraries=[
        # "opencv_core", "opencv_imgproc", "opencv_imgcodecs", "opencv_freetype"
        "opencv_core", "opencv_imgproc", "opencv_video", "opencv_features2d", "opencv_highgui", "opencv_photo", "gomp"
    ],
    extra_objects=[
        "./ext_modules/opencv-mobile-4.13.0-ubuntu-2204/lib/libopencv_core.a",
        "./ext_modules/opencv-mobile-4.13.0-ubuntu-2204/lib/libopencv_imgproc.a",
        "./ext_modules/opencv-mobile-4.13.0-ubuntu-2204/lib/libopencv_video.a",
        "./ext_modules/opencv-mobile-4.13.0-ubuntu-2204/lib/libopencv_features2d.a",
        "./ext_modules/opencv-mobile-4.13.0-ubuntu-2204/lib/libopencv_highgui.a",
        "./ext_modules/opencv-mobile-4.13.0-ubuntu-2204/lib/libopencv_photo.a",
    ],
    library_dirs=[
        # ext_so,
        "./ext_modules/opencv-mobile-4.13.0-ubuntu-2204/lib/",
    ],
    extra_compile_args=['-std=c++11', '-std=gnu++11', '-DFT2_BUILD_LIBRARY', '-DHAVE_UNISTD_H=1', '-DHAVE_FCNTL_H=1', '-DIMLIB_CONFIG_H_FILE="costom_imlib_config.h"' ],
)

_maix_camera_module = Pybind11Extension(
    name = '_maix_camera',
    include_dirs=[ '/usr/include/opencv4/', '/usr/local/include/opencv4/',
        get_incs(
            'ext_modules/libmaix/components/libmaix/include'),
        get_incs(
            'ext_modules/libmaix/components/maix_cv_image/include'),
        get_incs(
            'ext_modules/libmaix/libmaix/lib/arch/desktop/libmaix_utils'),
        get_incs(
            'ext_modules/libmaix/libmaix/lib/arch/desktop/libmaix_image'),
        get_incs(
            'ext_modules/libmaix/libmaix/lib/arch/desktop/libmaix_cam'),
        get_incs(
            'ext_modules/libmaix/components/maix_cv_image/include'),
        get_incs(
            'ext_modules/_maix_camera/include')
    ],
    sources= get_srcs('ext_modules/libmaix/components/maix_cv_image/src') +
             get_srcs('ext_modules/libmaix/components/libmaix/lib/arch/desktop/libmaix_utils') +
             get_srcs('ext_modules/libmaix/components/libmaix/lib/arch/desktop/libmaix_image') +
             get_srcs('ext_modules/libmaix/components/libmaix/lib/arch/desktop/libmaix_cam') +
             get_srcs('ext_modules/_maix_camera'),
    libraries=[
        "opencv_videoio", "opencv_highgui", "opencv_core", "opencv_imgproc", "opencv_imgcodecs", "opencv_freetype"
    ],
    library_dirs=[
        "/usr/lib/",
        "/usr/lib/x86_64-linux-gnu/",
        "/usr/local/lib64/",
    ],
    extra_link_args=[
    ],
    extra_compile_args=['-std=c++11', '-std=gnu++11' ],
)

_maix_display_module = Pybind11Extension(
    name = "_maix_display",
    include_dirs=[ '/usr/include/opencv4/', '/usr/local/include/opencv4/',
        get_incs(
            'ext_modules/libmaix/components/libmaix/include'),
        get_incs(
            'ext_modules/libmaix/components/maix_cv_image/include'),
        get_incs(
            'ext_modules/libmaix/libmaix/lib/arch/desktop/libmaix_utils'),
        get_incs(
            'ext_modules/libmaix/libmaix/lib/arch/desktop/libmaix_image'),
        get_incs(
            'ext_modules/libmaix/libmaix/lib/arch/desktop/libmaix_disp'),
        get_incs(
            'ext_modules/libmaix/components/maix_cv_image/include'),
        get_incs(
            'ext_modules/_maix_display/include')
    ],
    sources= get_srcs('ext_modules/libmaix/components/maix_cv_image/src') +
             get_srcs('ext_modules/libmaix/components/libmaix/lib/arch/desktop/libmaix_utils') +
             get_srcs('ext_modules/libmaix/components/libmaix/lib/arch/desktop/libmaix_image') +
             get_srcs('ext_modules/libmaix/components/libmaix/lib/arch/desktop/libmaix_disp') +
             get_srcs('ext_modules/_maix_display'),
    libraries=[
        "opencv_core", "opencv_imgproc", "opencv_imgcodecs", "opencv_freetype"
    ],
    extra_objects=[
        "./ext_modules/opencv-mobile-4.13.0-ubuntu-2204/lib/libopencv_imgproc.a",
        "./ext_modules/opencv-mobile-4.13.0-ubuntu-2204/lib/libopencv_video.a",
        "./ext_modules/opencv-mobile-4.13.0-ubuntu-2204/lib/libopencv_imgcodecs.a",
        "./ext_modules/opencv-mobile-4.13.0-ubuntu-2204/lib/libopencv_features2d.a",
        "./ext_modules/opencv-mobile-4.13.0-ubuntu-2204/lib/libopencv_highgui.a",
        "./ext_modules/opencv-mobile-4.13.0-ubuntu-2204/lib/libopencv_photo.a",
    ],
    library_dirs=[
        "/usr/lib/",
        "/usr/lib/x86_64-linux-gnu/",
        "/usr/local/lib64/",
    ],
    extra_link_args=[
    ],
    extra_compile_args=['-std=c++11', '-std=gnu++11' ],
)

# python3.8 -m pip install pybind11
# _maix_speech_module = Pybind11Extension("_maix_speech",
#     include_dirs=[
#         get_incs(
#             './ext_modules/libmaix/components/maix_speech/Maix-Speech/components/asr_lib/include'),
#         get_incs(
#             './ext_modules/libmaix/components/maix_speech/Maix-Speech/components/utils/include')
#     ],
#     sources = get_srcs('ext_modules/_maix_speech', exclude=["utils", "projects"]),
#     libraries=[
#         "ms_asr_armv7musl"
#     ],
#     library_dirs=[
#         # ext_so,
#         "./ext_modules/libmaix/components/maix_speech/Maix-Speech/components/asr_lib/lib/v83x",
#     ],
#     extra_objects=[
#         "./ext_modules/libmaix/components/maix_speech/Maix-Speech/components/asr_lib/lib/v83x/libms_asr_armv7musl.a",
#     ],
#     extra_compile_args=['-D__ARM__', '-D__ARMV7__', '-DCONF_KERNEL_IOMMU', '-DCONF_KERNEL_VERSION_4_9', '-std=c++11', '-std=gnu++11'],
#     extra_link_args=[
#         # set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Wno-unused-variable -fPIC -c -s -ffunction-sections -fdata-sections -march=armv7-a  -mtune=cortex-a7" PARENT_SCOPE)
#         # set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wno-sign-compare -Wno-unused-variable -fPIC -fexceptions -s -ffunction-sections -fdata-sections -fpermissive -march=armv7-a  -mtune=cortex-a7" PARENT_SCOPE)
#     ],
# )

_maix_modules = [
    libi2c_module,
    _maix_module,
    _maix_image_module,
    # _maix_camera_module,
    # _maix_display_module,
    # _maix_speech_module
]

_maix_data_files = [

]

_maix_py_modules = [
    "numpy",
    # "rpyc",
    "gpiod",
    "evdev",
    "spidev",
    "pybind11",
    "pyserial"
]
