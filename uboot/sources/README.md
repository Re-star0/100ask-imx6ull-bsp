# uboot/sources —— U-Boot 源码

## 一、目录现状

```
uboot/sources/
├── README.md
└── uboot-imx-imx_v2017.03_4.9.88_2.0.0_ga.zip    # 23.2 MB（24,326,624 字节），未解压
```

源码为 NXP GitHub 仓库 `imx_v2017.03_4.9.88_2.0.0_ga` 分支的 **ZIP 下载包**（Code → Download ZIP），不是 `git clone` 得到的仓库，**包内没有 `.git`**。

## 二、源码信息

| 项 | 值 |
|----|-----|
| 仓库 | <https://github.com/nxp-imx/uboot-imx> |
| 分支 | `imx_v2017.03_4.9.88_2.0.0_ga` |
| U-Boot 版本 | 2017.03（NXP BSP，适配 4.9.88 内核） |
| 压缩包 | `uboot-imx-imx_v2017.03_4.9.88_2.0.0_ga.zip` |
| 包大小 | 24,326,624 字节（约 23.2 MB） |
| 顶层目录 | `uboot-imx-imx_v2017.03_4.9.88_2.0.0_ga/` |
| 条目数 | 15,311 |

已确认包内包含后续要用到的文件：

```
uboot-imx-imx_v2017.03_4.9.88_2.0.0_ga/Makefile
uboot-imx-imx_v2017.03_4.9.88_2.0.0_ga/configs/mx6ull_14x14_evk_defconfig
uboot-imx-imx_v2017.03_4.9.88_2.0.0_ga/include/configs/mx6ullevk.h
```

## 三、解压与使用

```bash
cd <仓库>/uboot/sources
unzip -q uboot-imx-imx_v2017.03_4.9.88_2.0.0_ga.zip
cd uboot-imx-imx_v2017.03_4.9.88_2.0.0_ga
```

之后按 `uboot/README.md` 的"编译与烧写"或 `uboot/docs/uboot_porting_guide.md` 第 4 章操作。

注意：

- **在 Linux 内解压**。Windows 解压再拷入会丢文件权限、把符号链接变成普通文件，`make` 可能直接失败。
- 解压后的工作树约 15,000 个文件，已在 `.gitignore` 中忽略（`uboot/sources/uboot-imx-imx_v2017.03_4.9.88_2.0.0_ga/`），随时可由 zip 重建。
- 通过 VMware 共享目录访问时，建议先拷到 Linux 本地磁盘再解压。

## 四、与补丁流程的关系

ZIP 包没有 `.git`，而用 `git diff` 生成补丁需要 git 仓库。首次使用时初始化一次即可：

```bash
cd uboot-imx-imx_v2017.03_4.9.88_2.0.0_ga
git init
git add -A
git commit -m "import uboot 2017.03 (nxp imx_v2017.03_4.9.88_2.0.0_ga)"
```

之后按清单修改，用 `git diff` 导出补丁；或直接用 `patch -p1 < xxx.patch` 应用已有补丁（不需要 git）。

## 五、校验记录

| 项目 | 结果 |
|------|------|
| 压缩包大小 | 24,326,624 字节 |
| `tar -tf` 可正常列出 | 15,311 个条目 |
| 顶层目录 | `uboot-imx-imx_v2017.03_4.9.88_2.0.0_ga/` |
| 关键文件 | `Makefile`、`configs/mx6ull_14x14_evk_defconfig`、`include/configs/mx6ullevk.h` 均在 |
| `.git` | 无（ZIP 下载） |

## 六、位置变更记录

| 时间 | 内容 |
|------|------|
| 2026-10-30 | 新增源码压缩包 `uboot-imx-imx_v2017.03_4.9.88_2.0.0_ga.zip` 至本目录；此前文档中的源码位置示例为虚拟机 `~/linux/IMX6ULL/uboot/uboot-imx-2017.03_4.9.88_2.0.0_ga`，现统一以 `uboot/sources/` 为准 |
