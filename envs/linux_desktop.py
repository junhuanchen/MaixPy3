"""Generic Linux/Alpine build using the architecture-local opencv-mobile."""

from .linux_ubuntu import _maix_data_files, _maix_modules, _maix_py_modules


_ubuntu_opencv = "opencv-mobile-4.13.0-ubuntu-2204"
_generic_opencv = "opencv-mobile-4.13.0"

for extension in _maix_modules:
    extension.include_dirs = [
        path.replace(_ubuntu_opencv, _generic_opencv)
        for path in extension.include_dirs
    ]
    extension.library_dirs = [
        path.replace(_ubuntu_opencv, _generic_opencv)
        for path in extension.library_dirs
    ]
    extension.extra_objects = [
        path.replace(_ubuntu_opencv, _generic_opencv)
        for path in (extension.extra_objects or [])
    ]
