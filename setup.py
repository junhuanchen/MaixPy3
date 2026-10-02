#!/usr/bin/env python

"""
setup.py file for maixpy3
"""

import sys, platform
from setuptools import setup, find_packages

ext_modules, data_files, py_modules = [], [], []

sysstr = platform.system()

if (sysstr == "Windows"):
  from envs.windows import _maix_modules, _maix_data_files, _maix_py_modules
elif (sysstr == "Linux"):
  if 'linux_ubuntu' in sys.argv:
    sys.argv.remove('linux_ubuntu')
    from envs.linux_ubuntu import _maix_modules, _maix_data_files, _maix_py_modules
  elif 'maix_v83x' in sys.argv:
    sys.argv.remove('maix_v83x')
    from envs.maix_v83x import _maix_modules, _maix_data_files, _maix_py_modules
  elif 'maix_r329' in sys.argv:
    from envs.maix_r329 import _maix_modules, _maix_data_files, _maix_py_modules
    sys.argv.remove('maix_r329')
  else:
    # 自动选择 Linux 构建环境：
    #   x86 + glibc（如 Ubuntu 桌面）→ linux_ubuntu（-ubuntu-2204 现成静态库）
    #   其它（如 Alpine armhf 虚拟机）→ linux_desktop（通用 opencv-mobile-4.13.0）
    machine = platform.machine().lower()
    libc, _ = platform.libc_ver()
    if machine in ('x86_64', 'amd64', 'i386', 'i486', 'i586', 'i686') and libc == 'glibc':
      from envs.linux_ubuntu import _maix_modules, _maix_data_files, _maix_py_modules
    else:
      from envs.linux_desktop import _maix_modules, _maix_data_files, _maix_py_modules

ext_modules.extend(_maix_modules)
data_files.extend(_maix_data_files)
py_modules.extend(_maix_py_modules)

from maix import version

setup(
  name='maixpy3',
  version=version,
  license='MIT',
  author='Sipeed',
  author_email="support@sipeed.com",
  url='https://github.com/sipeed/maixpy3',
  description="MaixPy Python3 library",
  long_description=open('README.md', 'r', encoding='UTF-8').read(),
  long_description_content_type='text/markdown',
  install_requires=py_modules,
  ext_modules=ext_modules,
  packages = find_packages(
    exclude=['envs'] # remove from build
    ), # find __init__.py packages
  classifiers=[
      'Programming Language :: Python :: 3',
  ],
  extras_require={"test": "pytest"},
  entry_points={
    "console_scripts": ["maixpy3_rpycs=maix.mjpg:start"]
  },
  include_package_data=True,
  package_data = {
      '': ['*.so'],
      '': ['*.h'],
  },
  data_files=data_files,
)
