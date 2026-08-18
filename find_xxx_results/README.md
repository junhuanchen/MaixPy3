# MaixPy3 `find_xxx` 两阶段图像测试

测试分为“样本生成/管理”和“嵌入式二次检测”两个阶段。所有测试图尺寸均为
720×480，目标分别放置在左上、右上、中间、左下和右下。

## 文件职责

- `generate_find_xxx_samples.py`：只生成和管理样本输入图片，不调用 `find_xxx`。
- `test_find_xxx_embedded.py`：只读取已生成的输入图片，执行检测、绘制坐标并保存结果。
- `test_find_xxx.py`：保留的一键式生成与检测版本，便于开发机回归。

三个脚本都只使用 Python 标准库 `os` 和 MaixPy3 自带的 `maix.image`，不依赖
OpenCV、Pillow、ReportLab 或 ctypes。

## 测试脚本说明

### `generate_find_xxx_samples.py`

这是样本生成入口。它从 `test_find_xxx.py` 导入公共的绘图和样本生成函数，创建八组
720×480 输入图以及模板小图，但不会调用任何 `find_xxx` 检测函数。

适合以下流程：先在开发机或一块板子上生成固定输入，再把整个 `find_xxx_results/`
目录复制到待测板子，保证不同设备读取完全相同的测试图片。

运行后主要生成：

- `01_find_blobs_input.jpg` 至 `08_find_barcodes_input.jpg`；
- AprilTag 使用无损的 `07_find_apriltags_input.png`；
- 模板匹配额外生成 `06_find_template_patch.jpg`。

### `test_find_xxx_embedded.py`

这是推荐的板端二次测试入口。脚本不会重新生成输入图，而是读取当前目录已有的样本，
依次调用八个 `find_xxx` 接口。每个检测目标的坐标和返回信息会绘制回 RGBA 图像，随后
通过 `image.save()` 保存为 JPEG。

检测结果写入与本目录同级的 `find_xxx_embedded_results/`：

- `NN_<name>_result.jpg`：带检测框、坐标和识别信息的结果图；
- `00_summary.txt`：每项的 `PASS`、`FAIL`、`ERROR` 和检测数量。

脚本以每项检测到五个目标作为通过条件，即 `PASS count=5`。缺少输入图片、RGBA/RGB
转换失败或保存失败时会输出 `ERROR`。

### `test_find_xxx.py`

这是公共实现兼一键回归入口，包含样本矩阵、EAN-13 生成、绘图辅助函数和全部检测测试。
前两个脚本会复用其中的样本生成代码。直接运行它时会在当前
`find_xxx_results/` 目录重新生成输入，然后立即完成八项检测，适合开发过程中快速回归：

```bash
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libgomp.so.1 \
PYTHONPATH=. python3 find_xxx_results/test_find_xxx.py
```

一键入口会把输入图、标注结果和 `00_summary.txt` 都保存在 `find_xxx_results/`；正式的
两阶段板端测试建议使用前两个脚本，以免输入和检测结果混在同一目录。

## RGBA 默认路径

- 所有测试样本均先通过 `image.new(..., mode="RGBA")` 创建并使用 RGBA 绘图接口生成。
- `draw_line`、`draw_rectangle`、`draw_circle`、`draw_string`、`draw_image` 和
  `image.save()` 均直接支持 RGBA；RGBA 同模式贴图使用裁剪后的 ROI 直接复制，默认路径
  不引入逐像素混合开销。
- JPEG/PNG 保存时，底层会把内存中的 RGBA 转换成 OpenCV 编码器要求的 BGRA，避免
  红蓝通道互换。
- 当前 imlib 的 `find_xxx` 算法使用 RGB888 图像结构。板端脚本因此保留一张 RGBA
  原图用于标注和保存，并仅为检测创建一张 RGB 工作副本；检测结果再绘制回 RGBA 原图。
  这样无需侵入式改写每个算法的像素访问宏，也不会给算法内部循环增加 RGBA 分支。
- `test_find_xxx_embedded.py` 在保存前会检查结果图仍为 `RGBA`，模式不符合会立即报错。

## 电脑 Linux 开发端命令

电脑端 `_maix_image` 使用了 OpenMP。运行 Python 前需要通过 `LD_PRELOAD` 提前引入
`libgomp.so.1`，否则可能出现缺少 `GOMP_*` 或 `omp_*` 符号的加载错误。以下命令均在
MaixPy3 仓库根目录执行。

第一阶段，只生成样本：

```bash
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libgomp.so.1 \
PYTHONPATH=. python3 find_xxx_results/generate_find_xxx_samples.py
```

第二阶段，读取生成的样本并执行检测：

```bash
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libgomp.so.1 \
PYTHONPATH=. python3 find_xxx_results/test_find_xxx_embedded.py
```

一键生成并检测：

```bash
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libgomp.so.1 \
PYTHONPATH=. python3 find_xxx_results/test_find_xxx.py
```

这里设置 `PYTHONPATH=.` 是为了优先加载当前仓库中刚编译的 MaixPy3 模块。上述
`libgomp.so.1` 路径适用于当前 x86_64 Debian/Ubuntu 环境；如果系统路径不同，可以用
`ldconfig -p | grep libgomp.so.1` 查询实际位置。

## 嵌入式板端命令

输入图片可以在电脑端生成后随整个 `find_xxx_results/` 目录复制到板子，也可以直接在
板子上生成。以下假设当前目录是 `find_xxx_results/` 的上一级，并且板端已经安装当前
版本的 MaixPy3。板端不需要设置电脑 x86_64 的 `LD_PRELOAD`。

第一阶段，在板端生成样本：

```bash
python3 find_xxx_results/generate_find_xxx_samples.py
```

第二阶段，读取样本并执行检测：

```bash
python3 find_xxx_results/test_find_xxx_embedded.py
```

一键生成并检测：

```bash
python3 find_xxx_results/test_find_xxx.py
```

### 板端二次检测目录

确保板子上的目录结构为：

```text
工作目录/
└── find_xxx_results/
    ├── README.md
    ├── generate_find_xxx_samples.py
    ├── test_find_xxx.py
    ├── test_find_xxx_embedded.py
    ├── 01_find_blobs_input.jpg
    ├── 02_find_rects_input.jpg
    ├── 03_find_circles_input.jpg
    ├── 04_find_lines_input.jpg
    ├── 05_find_qrcodes_input.jpg
    ├── 06_find_template_input.jpg
    ├── 06_find_template_patch.jpg
    ├── 07_find_apriltags_input.png
    └── 08_find_barcodes_input.jpg
```

嵌入式检测结果保存到独立目录 `find_xxx_embedded_results/`，不会覆盖输入样本。

如需在加载 `_maix_image` 前调整图像算法内存池：

```bash
MAIX_IMAGE_FB_ALLOC_SIZE=8M python3 \
find_xxx_results/test_find_xxx_embedded.py
```

默认内存池为 6 MiB。

## 测试顺序

1. `find_blobs`：检测五个红色色块，绘制边框、中心和像素信息。
2. `find_rects`：检测五个矩形，绘制边框和 magnitude。
3. `find_circles`：检测五个圆，绘制圆心、半径和 magnitude。
4. `find_lines`：检测五条直线，绘制端点坐标。
5. `find_qrcodes`：检测五个二维码，绘制 payload 和版本。
6. `find_template`：分别匹配四角和中心的模板，绘制匹配范围和相似度。
7. `find_apriltags`：检测五个 AprilTag，绘制 ID、family 和 hamming。
8. `find_barcodes`：检测五个 EAN-13 条码，绘制 payload、类型和质量。

## 输入与输出命名

- `NN_<name>_input.jpg`：生成的测试输入图。
- `07_find_apriltags_input.png`：无损 AprilTag 输入图，避免 JPEG 压缩破坏小模块。
- `find_xxx_embedded_results/NN_<name>_result.jpg`：板端绘制坐标和信息后的结果图。
- `06_find_template_patch.jpg`：模板匹配使用的小图。
- `find_xxx_embedded_results/00_summary.txt`：板端每项测试的状态和检测数量。

成功运行后，每项应显示 `PASS count=5`。

## Python 内存接口

模块加载后也可以查询或调整内存池：

```python
from maix import image

print(image.get_fb_alloc_size())
image.set_fb_alloc_size(8 * 1024 * 1024)
```

动态调整应在没有 `find_xxx` 算法正在执行时进行。

## 依赖

二维码和 AprilTag 位图已内置，EAN-13 条码由纯 Python 计算后通过
`image.draw_rectangle()` 绘制。样本生成脚本和嵌入式检测脚本都可以直接放到板子上运行。
