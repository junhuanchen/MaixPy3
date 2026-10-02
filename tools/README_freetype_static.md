# FreeType build

MaixPy uses the vendored `ext_modules/freetype-2.14.3` source directly.  The
selected FreeType modules are compiled by setuptools and linked into
`_maix_image`, without a separately prepared `libfreetype.a`.

`setup.py` chooses the environment automatically: on x86 + glibc (e.g. the
Ubuntu desktop) it builds against `opencv-mobile-4.13.0-ubuntu-2204`; on any
other Linux (e.g. the Alpine armhf VM) it builds against the generic
`opencv-mobile-4.13.0`.  The same command works on both:

```sh
python3 setup.py build_ext --inplace
```

To force the Ubuntu package environment explicitly (for example a non-x86
glibc host that still ships the `-ubuntu-2204` package):

```sh
python3 setup.py linux_ubuntu build_ext --inplace
```

The vendored archive is FreeType 2.14.3.  Its original license files are kept
in the source directory.  The source archive used for the import had SHA-256:

```
36bc4f1cc413335368ee656c42afca65c5a3987e8768cc28cf11ba775e785a5f
```
