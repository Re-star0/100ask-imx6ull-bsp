# Buildroot 根文件系统（100ASK IMX6ULL Pro）

用 Buildroot 2020.02.12 为 100ASK IMX6ULL Pro 构建根文件系统：基于 `imx6ulevk_defconfig`，改用外部工具链，集成驱动调试与 SSH 工具，产出 `rootfs.tar` / `rootfs.ext2`，经 NFS 验证后部署到 eMMC。

状态：已构建并验证（NFS 启动成功、SSH 可登录、可 dd 到 eMMC 独立启动）。

## 目录

```
rootfs/
├── README.md                        # 本文件
├── configs/
│   └── my_imx6ull_defconfig         # Buildroot 配置（复制到 configs/ 后 make my_imx6ull_defconfig）
├── overlay/
│   └── etc/profile.d/ps1.sh         # PS1 提示符定制（复制到 board/my_imx6ull/rootfs-overlay/）
├── docs/
│   └── rootfs_build_guide.md        # 完整构建流程 + 踩坑记录
└── sources/                         # 离线构建资料（约 2.0 GB）
    ├── buildroot-2020.02.12.tar.gz  # Buildroot 源码包（解压后使用）
    ├── dl/                          # 软件包下载缓存（418 个包目录）
    └── README.md                    # 源码/缓存的位置、作用与用法
```

## 关键信息

| 项 | 值 |
|----|-----|
| Buildroot | 2020.02.12（LTS），起点 `imx6ulevk_defconfig` |
| 工具链 | Linaro GCC 4.9.4（内核头文件 4.6.x），路径写在 defconfig 的 `BR2_TOOLCHAIN_EXTERNAL_PATH` |
| 源码包 | `sources/buildroot-2020.02.12.tar.gz`（约 6.5 MB） |
| 下载缓存 | `sources/dl/`（418 个包目录、约 2.0 GB） |
| 产物 | `rootfs.tar` / `rootfs.ext2` / `rootfs.ext4` |

## 从哪看起

| 要做的事 | 看这里 |
|---------|--------|
| 配置：工具链、系统、软件包、overlay、镜像格式 | [guide 3.3–3.4](docs/rootfs_build_guide.md) |
| 编译、保存 defconfig、产物 | [guide 3.5–3.6](docs/rootfs_build_guide.md) |
| NFS 启动验证 | [guide 第 4 章](docs/rootfs_build_guide.md) |
| 部署到 eMMC（dd + U-Boot 参数 4 处） | [guide 第 5 章](docs/rootfs_build_guide.md) |
| 上板验证清单 | [guide 第 6 章](docs/rootfs_build_guide.md) |
| 14 条踩坑记录 | [guide 第 7 章](docs/rootfs_build_guide.md) |
| 源码包、dl 缓存、缺包补充 | [sources/README.md](sources/README.md) |
