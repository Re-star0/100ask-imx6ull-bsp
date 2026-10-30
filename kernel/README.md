# 内核移植（100ASK IMX6ULL Pro）

Linux 4.9.88（NXP `imx_4.9.88_2.0.0_ga`）移植到 100ASK IMX6ULL Pro：板级 defconfig 为 `my_imx_emmc_defconfig`，设备树为 `imx6ull-my14x14-emmc.dts`。

> 本项目的移植流程与上游仓库**完全一致**：没有自定义驱动、没有 SoC 级代码改动，板级差异只落在设备树和 defconfig 两处。

## 目录

```
kernel/
├── README.md                          # 本文件
├── configs/
│   └── imx6ull-my14x14-emmc.dts       # 本板设备树（完整文件）
└── docs/
    └── kernel_porting_record.md       # 移植记录：选择依据、改动、命令、踩坑
```

## 关键信息

| 项 | 值 |
|----|-----|
| 内核 | 4.9.88，分支 `imx_4.9.88_2.0.0_ga` |
| 工具链 | Linaro GCC 4.9.4（与 U-Boot、rootfs 一致） |
| defconfig | `my_imx_emmc_defconfig`（基于 `imx_v7_defconfig`） |
| 设备树 | `imx6ull-my14x14-emmc.dts` / `.dtb` |
| 产物 | `arch/arm/boot/zImage`、`arch/arm/boot/dts/imx6ull-my14x14-emmc.dtb` |

## 从哪看起

| 想知道什么 | 看这里 |
|-----------|--------|
| 配置怎么选的、板级改了什么、怎么编、遇到过什么问题 | [docs/kernel_porting_record.md](docs/kernel_porting_record.md) |
| 完整设备树 | [configs/imx6ull-my14x14-emmc.dts](configs/imx6ull-my14x14-emmc.dts) |
| 上游的完整原理与验证 | [上游文档（锁定 commit）](https://github.com/illusOwo-ff/i.MX6ULL-bsp-driver-project/blob/5bd89d010d99eea1c8da0437607cf45d7951d790/kernel/docs/kernel_porting_100ask_imx6ull.md) |
