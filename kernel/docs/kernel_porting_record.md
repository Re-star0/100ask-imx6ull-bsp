# 内核移植记录（i.MX6ULL / 100ASK IMX6ULL Pro）

> 内核：Linux 4.9.88（NXP `imx_4.9.88_2.0.0_ga`）
> 工具链：Linaro GCC 4.9.4（与 U-Boot、rootfs 保持一致）
> 板级：`my_imx_emmc_defconfig` + `imx6ull-my14x14-emmc.dts`

本项目的移植流程与上游仓库 **完全一致**：没有自定义驱动、没有修改 SoC 级代码，所有板级差异都收敛在**设备树**和**defconfig**两处。

因此本文不复述上游的原理性讲解，只记录：环境、配置是怎么选出来的、实际改了什么、构建命令、过程中遇到的问题与处理。验收/验证结果不在本文范围。

---

## 1. 记录范围

| 内容 | 是否记录 | 说明 |
|------|---------|------|
| 版本、源码、工具链 | ✅ | 本文第 2 节 |
| defconfig / 设备树的选择依据 | ✅ | 第 3 节 |
| 板级改动（dts、defconfig） | ✅ | 第 4 节 |
| 构建命令与产物 | ✅ | 第 5 节 |
| 与上游的差异 | ✅ | 第 6 节（结论：无流程差异） |
| 遇到的问题与处理 | ✅ | 第 7 节 |
| 上板验证/验收 | ❌ | 见上游文档第 8 节 |

上游文档已锁定版本，链接见第 8 节；本文提到"原理"时直接指过去，不重复。

---

## 2. 环境与源码

| 项 | 值 |
|----|-----|
| 内核版本 | Linux 4.9.88 |
| NXP 分支 | `imx_4.9.88_2.0.0_ga` |
| 仓库 | <https://github.com/nxp-imx/linux-imx> |
| 工具链 | Linaro GCC 4.9.4（`arm-linux-gnueabihf-`） |
| 源码目录（示例） | `~/linux/IMX6ULL/kernel/linux-imx-4.9.88` |
| defconfig | `my_imx_emmc_defconfig` |
| 设备树 | `imx6ull-my14x14-emmc.dts` / `.dtb` |
| 产物 | `arch/arm/boot/zImage`、`arch/arm/boot/dts/imx6ull-my14x14-emmc.dtb` |

获取源码（与 U-Boot 版本配套）：

```bash
git clone -b imx_4.9.88_2.0.0_ga --single-branch https://github.com/nxp-imx/linux-imx.git
cd linux-imx
```

版本自检：

```bash
make kernelversion          # 4.9.88
git log --oneline -1        # 确认分支
```

> 工具链必须与 U-Boot、rootfs 的一致。三者不一致时的典型症状是 rootfs 的 init 起不来（`No working init found`），而不是编译报错。

---

## 3. 配置是怎么选出来的

### 3.1 defconfig：`imx_v7_defconfig` → `my_imx_emmc_defconfig`

| 步骤 | 做法 | 依据 |
|------|------|------|
| 找候选 | `ls arch/arm/configs/ \| grep imx` | 缩小到 i.MX 系列 |
| 选基线 | `imx_v7_defconfig` | i.MX6ULL 是 ARMv7，这是 NXP 给 i.MX6/i.MX7 的 EVK 参考配置 |
| 交叉验证 | 与韦东山已有的 `100ask_imx6ull_defconfig` 做 diff | 差异主要是"展开的 .config"与"精简 defconfig"的格式差别，内容最接近的就是 `imx_v7_defconfig` |
| 复制改名 | `cp arch/arm/configs/imx_v7_defconfig arch/arm/configs/my_imx_emmc_defconfig` | 后续所有配置改动都落在自己的 defconfig 上 |

> 不能照搬别人的 defconfig：正点原子用的是 `imx_v7_mfg_defconfig`，那是 4.1.15 内核的命名，与 4.9.88 不是一回事。

### 3.2 设备树：`imx6ull-14x14-evk-emmc.dts` → `imx6ull-my14x14-emmc.dts`

筛选逻辑，按顺序排除：

1. **封装**：排除 `imx6ull-9x9-evk*`（本板是 14x14 封装）；
2. **板型**：选 `evk` 系列（第三方板厂普遍参考 EVK 设计），排除 `ddr3-arm2`；
3. **存储**：选 `imx6ull-14x14-evk-emmc.dts`（本板是 eMMC 方案）。

确认 `evk` 与 `evk-emmc` 的差异：

```bash
diff arch/arm/boot/dts/imx6ull-14x14-evk.dts \
     arch/arm/boot/dts/imx6ull-14x14-evk-emmc.dts
```

结论：`evk-emmc.dts` 只是 include `evk.dts`，再覆盖 `usdhc2` 为 8 线 eMMC 模式。所以"基于 emmc 版"本质就是"基于 evk + 8 线 eMMC 配置"。

复制并注册：

```bash
cp arch/arm/boot/dts/imx6ull-14x14-evk-emmc.dts \
   arch/arm/boot/dts/imx6ull-my14x14-emmc.dts
```

然后在 `arch/arm/boot/dts/Makefile` 的 `CONFIG_SOC_IMX6ULL` 段追加：

```makefile
imx6ull-my14x14-emmc.dtb \
```

> 本仓库最终保存的设备树 include 的是 `imx6ull-14x14-evk.dts`，并在文件里显式重写了 `usdhc2`（8 线、`no-1-8-v`、`non-removable`），效果与基于 emmc 版一致。完整文件见 [`kernel/configs/imx6ull-my14x14-emmc.dts`](../configs/imx6ull-my14x14-emmc.dts)。

---

## 4. 板级改了什么

### 4.1 设备树（5 类改动）

| # | 节点 | 改动 | 原因 |
|---|------|------|------|
| 1 | `&pinctrl_lcdif_reset` | 清空 `fsl,pins` | TAMPER9 在本板用作 ENET1 PHY 复位，LCD_RESET 走专用引脚，解除占用不影响 LCD |
| 2 | `&iomuxc_snvs` | 新增 `pinctrl_enet1_reset` / `pinctrl_enet2_reset`（GPIO5_IO09 / GPIO5_IO06） | EVK 用 74HC595 间接复位，本板是 GPIO 直连 |
| 3 | `&fec1` / `&fec2` | 加 `phy-reset-gpios`、`phy-reset-duration = <200>`，`pinctrl-0` 引用复位组 | 让 FEC 驱动上电时执行 PHY 硬件复位 |
| 4 | `&ethphy0` | `reg = <0>`（EVK 是 2） | 原理图：本板 ENET1 的 PHYAD0 下拉，地址为 0 |
| 5 | `&usdhc1` / `&usdhc2` | 加 `no-1-8-v`；`usdhc1` 去掉 `vmmc-supply` | eMMC/SD 的 IO 电源固定 3.3V，没有 1.8V 切换电路，也没有可控电源开关 |

两个 PHY 节点还加了 `smsc,disable-energy-detect`，避免 LAN8720A 的节能检测干扰链路。

PHY 地址的覆盖方式有个坑：**不能重新定义 `ethphy0: ethernet-phy@0`**，因为 EVK 里已有 `ethphy0: ethernet-phy@2`，同 label 会报 `Duplicate label 'ethphy0'`。正确做法是用 `&ethphy0` 覆盖节点、只改 `reg`，节点名仍叫 `ethernet-phy@2`，内核按 `reg` 取地址。

### 4.2 defconfig（1 处）

```diff
 CONFIG_MICREL_PHY=y
+CONFIG_SMSC_PHY=y
```

EVK 用 KSZ8081（Micrel），本板用 LAN8720A（SMSC），两个驱动同时保留不冲突。

### 4.3 为 rootfs 补齐的内核选项

rootfs 里的调试工具依赖这些选项，逐项确认打开：

| 配置 | 用途 |
|------|------|
| `CONFIG_DEVTMPFS` / `CONFIG_DEVTMPFS_MOUNT` | `/dev` 设备节点 |
| `CONFIG_EXT4_FS` | ext4 根文件系统 |
| `CONFIG_TMPFS` | 运行时文件系统 |
| `CONFIG_NFS_FS` + `CONFIG_ROOT_NFS` | NFS 根文件系统启动 |
| `CONFIG_I2C_CHARDEV` | `i2c-tools` |
| `CONFIG_SPI_SPIDEV` | `spi-tools` / spidev |
| `CONFIG_GPIO_SYSFS` | GPIO sysfs 验证（libgpiod 因头文件 4.6 不可用，见 rootfs 踩坑 7.7） |
| `CONFIG_DEVMEM` | `devmem` 读写寄存器 |
| `CONFIG_FUNCTION_TRACER` / `FUNCTION_GRAPH_TRACER` / `IRQSOFF_TRACER` / `SCHED_TRACER` | `trace-cmd` / Ftrace |
| `CONFIG_DYNAMIC_DEBUG` | 运行时开关 `pr_debug` |

其中 Ftrace 相关项在原始配置里是 `# CONFIG_FTRACE is not set`，属于必须手动打开的一项。

### 4.4 明确不需要改的

| 项 | 原因 |
|----|------|
| `smsc.c` PHY 驱动 | 4.9.88 的 `smsc_phy_reset` 已无条件调用 `genphy_soft_reset()`，不需要像 U-Boot 那样加软复位补丁 |
| `fec_main.c`（SION 位） | 设备树 `pinctrl_enet1/2` 里 TX_CLK 的电气属性 `0x4001b031` 已含 SION 位 |
| `pinctrl_enet1/2` 的 RMII 引脚 | 标准 RMII 专用引脚，所有 RMII 板子一致 |
| `CONFIG_ARCH_MULTI_V6` | 4.9.88 的 defconfig 默认已关闭（本板是纯 ARMv7） |
| 引脚电气属性值 | 先用 EVK 默认值，异常时再调 |

---

## 5. 构建

```bash
# 1. 配置
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- my_imx_emmc_defconfig

# 2. 快速验证设备树语法
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- dtbs

# 3. 编译内核
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j$(nproc)
```

产物：

```
arch/arm/boot/zImage
arch/arm/boot/dts/imx6ull-my14x14-emmc.dtb
```

改过 `menuconfig` 后要把配置固化回 defconfig，否则 `make distclean` 会丢：

```bash
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- savedefconfig
cp defconfig arch/arm/configs/my_imx_emmc_defconfig
```

---

## 6. 与上游的差异

| 项 | 上游 | 本项目 | 差异 |
|----|------|--------|------|
| 流程 | 见上游文档 | 同左 | 无 |
| 内核版本/分支 | 4.9.88 / `imx_4.9.88_2.0.0_ga` | 同左 | 无 |
| defconfig | `my_imx_emmc_defconfig` | 同左 | 无 |
| 设备树 | `imx6ull-my14x14-emmc.dts` | 同左 | 无 |
| 自定义代码 | 无 | 无 | 无 |
| 工具链 | Linaro GCC 6.2（上游记录） | Linaro GCC 4.9.4 | 版本不同，但内核/U-Boot/rootfs 三者自洽 |

结论：**可以直接按上游文档执行**；本文只补充了本机的路径、defconfig 固化的习惯和实际踩过的点。

---

## 7. 过程中遇到的问题与处理

按出现顺序记录，均已解决。

### 7.1 eMMC 初始化超时（`error -110`）

**现象**：启动日志反复出现

```
mmc1: Tuning failed, falling back to fixed sampling clock
mmc1: error -110 whilst initialising MMC card
```

**定位**：`mmc1` 对应 `usdhc2`。查看 EVK 的 `usdhc2` 节点，发现没有 `no-1-8-v`，内核会尝试 UHS 的 1.8V 切换；对照核心板原理图，eMMC 的 VCC/VDDI 都接 VDD_3V3，没有电压切换电路。

**处理**：`&usdhc2` 加 `no-1-8-v`。

### 7.2 SD 卡初始化超时（`error -110`）

**现象**：

```
mmc0: error -110 whilst initialising SD card
```

**定位**：`mmc0` 对应 `usdhc1`。两处不符：EVK 有 `vmmc-supply`（板上有电源开关 GPIO），本板 SD 卡 VDD 直连 3.3V；同时同样缺少 `no-1-8-v`。CD 引脚不用改——`cd-gpios = <&gpio1 19 GPIO_ACTIVE_LOW>` 与本板 `SD1_CD` 一致。

**处理**：`&usdhc1` 去掉 `vmmc-supply`，加 `no-1-8-v`。

### 7.3 网络 PHY 不识别

**现象**：`fec` 注册成功，但没有任何 PHY attach / link up 的日志。

**定位与处理**，四个子问题：

| 子问题 | 结论 | 处理 |
|--------|------|------|
| PHY 地址 | ENET1 的 PHYAD0 下拉 → 地址 0，EVK 写的是 2 | `&ethphy0 { reg = <0>; }` |
| PHY 复位 | EVK 靠 74HC595，本板 GPIO5_IO09 / GPIO5_IO06 直连 | `phy-reset-gpios` + `pinctrl_enet*_reset` |
| PHY 驱动 | `CONFIG_SMSC_PHY` 默认未开（EVK 是 KSZ8081） | defconfig 加 `CONFIG_SMSC_PHY=y` |
| 引脚冲突 | TAMPER9 被 `pinctrl_lcdif_reset` 占用 | 清空该 pinctrl 的 pins |

### 7.4 设备树报 `Duplicate label 'ethphy0'`

**现象**：在 `&fec2` 里重新定义 `ethphy0: ethernet-phy@0` 后编译失败。

**原因**：EVK 已有 `ethphy0: ethernet-phy@2`，label 重复。

**处理**：不新建节点，改用 `&ethphy0` 覆盖，只改 `reg`。

### 7.5 网卡名从 `eth0` 变成 `eth2`

**现象**：启动日志

```
fec 20b4000.ethernet eth124: renamed from eth0
fec 20b4000.ethernet eth2: renamed from eth124
Starting network: Cannot find device "eth0"
```

**原因**：出厂 rootfs 里的 udev 规则按 MAC/PCI 排序重命名网卡，和新内核的命名顺序对不上；硬件本身正常。

**处理**：不属于内核移植问题。自建 rootfs（BusyBox + mdev，无 udev 规则）后网卡按内核默认顺序命名，问题自然消失。

### 7.6 工具链一致性

**注意**：内核、U-Boot、rootfs 必须同一套 `arm-linux-gnueabihf-`。上游记录用 GCC 6.2，本项目用 4.9.4，只要三者一致即可；混用会在 rootfs 启动阶段表现为 `No working init found`。

---

## 8. 上游参考

锁定 commit `5bd89d0` 的文档（内容不会随 `main` 变动）：

- 内核移植全文：<https://github.com/illusOwo-ff/i.MX6ULL-bsp-driver-project/blob/5bd89d010d99eea1c8da0437607cf45d7951d790/kernel/docs/kernel_porting_100ask_imx6ull.md>
- 内核模块说明：<https://github.com/illusOwo-ff/i.MX6ULL-bsp-driver-project/blob/5bd89d010d99eea1c8da0437607cf45d7951d790/kernel/README.MD>

章节对照：

| 本文 | 上游对应 |
|------|---------|
| 第 2 节 环境与源码 | 上游 §1.2、§2.1 |
| 第 3 节 配置选择 | 上游 §2.2、§2.3 |
| 第 4 节 板级改动 | 上游 §4、§5、§6 |
| 第 5 节 构建 | 上游 §3.1、§7 |
| 第 7 节 问题与处理 | 上游 §5、§8（现象部分） |
| 验收/验证结果 | 上游 §8（本文不重复） |
