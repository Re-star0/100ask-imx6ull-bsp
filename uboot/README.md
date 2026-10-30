# U-Boot 2017.03（100ASK IMX6ULL Pro / mx6ull_myboard_wds）

把 NXP U-Boot 2017.03（`imx_v2017.03_4.9.88_2.0.0_ga`）移植到 100ASK IMX6ULL Pro：在 EVK 基础上创建板级 `mx6ull_myboard_wds`，适配双路 LAN8720A PHY（地址、复位、驱动），实现 SD 卡启动、网络可用、从 eMMC 加载内核。

状态：已移植并验证（`ping` 通，`mdio list` 识别 LAN8720，`bootz` 能从 eMMC 启动 Linux）。

> 板级命名：上游参考仓库用 `mx6ull_myboard`，本项目统一为 `mx6ull_myboard_wds`，流程完全一致。

## 目录

```
uboot/
├── README.md                        # 本文件
├── configs/
│   └── mx6ull_myboard_wds_defconfig # 板级 defconfig（复制到源码树 configs/）
├── docs/
│   ├── uboot_porting_guide.md       # 完整移植流程 + 踩坑记录
│   └── images/                      # 移植过程截图（6 张）
└── sources/
    ├── README.md                                   # 源码包说明、解压与校验
    └── uboot-imx-imx_v2017.03_4.9.88_2.0.0_ga.zip  # U-Boot 2017.03 源码包（23.2 MB）
```

## 关键信息

| 项 | 值 |
|----|-----|
| U-Boot | 2017.03，分支 `imx_v2017.03_4.9.88_2.0.0_ga` |
| 源码包 | `sources/uboot-imx-imx_v2017.03_4.9.88_2.0.0_ga.zip`（23.2 MB，未解压） |
| 工具链 | Linaro GCC 4.9.4（与内核、rootfs 保持一致） |
| 产物 | `u-boot-dtb.imx`，烧到 SD 卡 1KB 偏移处 |

## 从哪看起

| 要做的事 | 看这里 |
|---------|--------|
| 从零移植：背景 → 源码 → EVK 验证 → 加板级 → 网络适配 | [guide 第 1–5 章](docs/uboot_porting_guide.md) |
| 编译、烧写 SD 卡、验证网络与启动内核 | [guide 第 3.3、4.6、6 章](docs/uboot_porting_guide.md) |
| 改动了哪些文件 | [guide 第 8 章（修改文件汇总）](docs/uboot_porting_guide.md) |
| 源码包位置、解压、校验 | [sources/README.md](sources/README.md) |
| eMMC 启动参数的 4 处修改 | [rootfs 构建文档 5.2](../rootfs/docs/rootfs_build_guide.md) |
