# i.MX6ULL BSP 驱动项目

基于 NXP i.MX6ULL（Cortex-A7）的嵌入式 Linux BSP 学习与移植项目，硬件平台为**百问网 100ASK IMX6ULL Pro**。

项目按 BSP 三层组织：**U-Boot 移植 → 内核移植 → 根文件系统构建**，每层独立成目录，文档与产物就近存放。

## 目录结构

```
100ask-imx6ull-bsp/
├── uboot/                  # U-Boot 移植（2017.03，板级 mx6ull_myboard_wds）
│   ├── README.md
│   ├── configs/            # 板级 defconfig
│   ├── docs/               # 移植流程文档
│   │   └── images/         # 移植过程截图（6 张）
│   └── sources/            # U-Boot 源码包（zip，23.2 MB）+ 说明
├── kernel/                 # 内核移植（4.9.88）
│   ├── README.md
│   ├── configs/            # 本板设备树
│   └── docs/               # 移植记录（kernel_porting_record.md）
├── rootfs/                 # 根文件系统构建（Buildroot 2020.02.12）
│   ├── README.md
│   ├── configs/            # Buildroot defconfig
│   ├── overlay/            # rootfs overlay（PS1 定制）
│   ├── docs/               # 构建流程 + 踩坑记录
│   └── sources/            # Buildroot 源码包 + dl 缓存（约 2.0 GB）
└── drivers/                # 字符设备驱动（预留）
```

## 三层职责

| 层 | 目录 | 产出 | 状态 |
|----|------|------|------|
| Bootloader | `uboot/` | `u-boot-dtb.imx` | 已移植（2017.03，SD 卡 + eMMC 启动） |
| Kernel | `kernel/` | `zImage` + `imx6ull-my14x14-emmc.dtb` | 已移植（4.9.88） |
| Rootfs | `rootfs/` | `rootfs.tar` / `rootfs.ext2` | 已构建（Buildroot 2020.02.12，NFS 验证 + eMMC 部署） |

## 文档导航

| 想了解 | 看这里 |
|--------|--------|
| rootfs 完整构建流程、每一步的原因、14 个踩坑 | [rootfs/docs/rootfs_build_guide.md](rootfs/docs/rootfs_build_guide.md) |
| U-Boot 移植流程、板级与网络适配、8 条踩坑 | [uboot/docs/uboot_porting_guide.md](uboot/docs/uboot_porting_guide.md) |
| 内核配置、设备树与移植要点 | [kernel/README.md](kernel/README.md) |
| Buildroot 源码包与 dl 缓存的位置/用法 | [rootfs/sources/README.md](rootfs/sources/README.md) |
| U-Boot 源码包的位置/解压 | [uboot/sources/README.md](uboot/sources/README.md) |
| 各模块目录与关键信息 | [uboot/README.md](uboot/README.md) · [rootfs/README.md](rootfs/README.md) |

## 参考

上游参考项目：<https://github.com/illusOwo-ff/i.MX6ULL-bsp-driver-project>

本项目在其基础上，补充了本机环境（GCC 4.9.4、NFS 启动、Dropbear 调试）下的完整流程与问题记录。

## 许可证

本项目以 **GNU General Public License v2.0** 发布，全文见 [LICENSE](LICENSE)。

上游项目同样采用 GPL 授权；本项目在其基础上补充了本机环境下的完整流程与问题记录，因此沿用 GPL-2.0。
