# 内核移植记录（i.MX6ULL / 100ASK IMX6ULL Pro）

> 内核：Linux 4.9.88（NXP `imx_4.9.88_2.0.0_ga`）
> 工具链：Linaro GCC 4.9.4（与 U-Boot、rootfs 保持一致）
> 板级：`my_imx_emmc_defconfig` + `imx6ull-my14x14-emmc.dts`

先说结论：这次移植没写一行驱动，也没动 SoC 级代码。本板和 NXP EVK 的差别，全落在**设备树**和**defconfig**这两个地方。流程跟上游仓库 **一模一样**。

所以本文不复述上游那些讲原理的章节，只记五件事：环境怎么搭、配置怎么挑出来的、实际改了什么、怎么编译、中间撞了哪些墙。至于上板验收，上游写得很细，这里就不重复了。

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

上游文档已经锁了版本，链接放在第 8 节。下文凡是提到"原理"，都是指回那几篇，不再抄一遍。

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

拿源码。内核版本得跟 U-Boot 配套，分支别乱挑：

```bash
git clone -b imx_4.9.88_2.0.0_ga --single-branch https://github.com/nxp-imx/linux-imx.git
cd linux-imx
```

拉下来先别急着编，确认一下版本：

```bash
make kernelversion          # 4.9.88
git log --oneline -1        # 确认分支
```

> 工具链要和 U-Boot、rootfs 用同一套。注意，三者不一致的时候，编译阶段往往一声不吭，代价要等到 rootfs 的 init 起不来才付：`No working init found`。头一回见这行字，十有八九会怀疑内核编坏了。

---

## 3. 配置是怎么选出来的

### 3.1 defconfig：`imx_v7_defconfig` → `my_imx_emmc_defconfig`

配置不是拍脑袋选的，是拿现成的配置一步步筛出来的：

| 步骤 | 做法 | 依据 |
|------|------|------|
| 找候选 | `ls arch/arm/configs/ \| grep imx` | 缩小到 i.MX 系列 |
| 选基线 | `imx_v7_defconfig` | i.MX6ULL 是 ARMv7，这是 NXP 给 i.MX6/i.MX7 的 EVK 参考配置 |
| 交叉验证 | 与韦东山已有的 `100ask_imx6ull_defconfig` 做 diff | 差异主要是"展开的 .config"与"精简 defconfig"的格式差别，内容最接近的就是 `imx_v7_defconfig` |
| 复制改名 | `cp arch/arm/configs/imx_v7_defconfig arch/arm/configs/my_imx_emmc_defconfig` | 后续所有配置改动都落在自己的 defconfig 上 |

> 这里有个容易踩的坑：正点原子用的是 `imx_v7_mfg_defconfig`，名字看着像亲戚，可那是 4.1.15 年代的叫法，跟 4.9.88 不是一回事。照抄过去，编得出来，跑不跑得起来就另说了。

### 3.2 设备树：`imx6ull-14x14-evk-emmc.dts` → `imx6ull-my14x14-emmc.dts`

设备树的挑法更简单，一路排除就行：

1. **封装**：排除 `imx6ull-9x9-evk*`（本板是 14x14 封装）；
2. **板型**：选 `evk` 系列（第三方板厂普遍参考 EVK 设计），排除 `ddr3-arm2`；
3. **存储**：选 `imx6ull-14x14-evk-emmc.dts`（本板是 eMMC 方案）。

先看看这两份到底差在哪，免得选错：

```bash
diff arch/arm/boot/dts/imx6ull-14x14-evk.dts \
     arch/arm/boot/dts/imx6ull-14x14-evk-emmc.dts
```

看下来，`evk-emmc.dts` 没干别的，就是 include 了 `evk.dts`，再把 `usdhc2` 改成 8 线 eMMC。所以"基于 emmc 版"说白了就是"基于 evk，外加一份 8 线 eMMC 配置"。

复制一份，顺手把名字改掉：

```bash
cp arch/arm/boot/dts/imx6ull-14x14-evk-emmc.dts \
   arch/arm/boot/dts/imx6ull-my14x14-emmc.dts
```

然后在 `arch/arm/boot/dts/Makefile` 的 `CONFIG_SOC_IMX6ULL` 段追加：

```makefile
imx6ull-my14x14-emmc.dtb \
```

> 顺带说一句：本仓库最终保存的设备树，include 的是 `imx6ull-14x14-evk.dts`，然后在文件里把 `usdhc2` 显式重写了一遍（8 线、`no-1-8-v`、`non-removable`），效果跟基于 emmc 版一样。完整文件见 [`kernel/configs/imx6ull-my14x14-emmc.dts`](../configs/imx6ull-my14x14-emmc.dts)。

---

## 4. 板级改了什么

### 4.1 设备树（5 类改动）

设备树上动了五处，一处一处记：

| # | 节点 | 改动 | 原因 |
|---|------|------|------|
| 1 | `&pinctrl_lcdif_reset` | 清空 `fsl,pins` | TAMPER9 在本板用作 ENET1 PHY 复位，LCD_RESET 走专用引脚，解除占用不影响 LCD |
| 2 | `&iomuxc_snvs` | 新增 `pinctrl_enet1_reset` / `pinctrl_enet2_reset`（GPIO5_IO09 / GPIO5_IO06） | EVK 用 74HC595 间接复位，本板是 GPIO 直连 |
| 3 | `&fec1` / `&fec2` | 加 `phy-reset-gpios`、`phy-reset-duration = <200>`，`pinctrl-0` 引用复位组 | 让 FEC 驱动上电时执行 PHY 硬件复位 |
| 4 | `&ethphy0` | `reg = <0>`（EVK 是 2） | 原理图：本板 ENET1 的 PHYAD0 下拉，地址为 0 |
| 5 | `&usdhc1` / `&usdhc2` | 加 `no-1-8-v`；`usdhc1` 去掉 `vmmc-supply` | eMMC/SD 的 IO 电源固定 3.3V，没有 1.8V 切换电路，也没有可控电源开关 |

另外两个 PHY 节点都加了 `smsc,disable-energy-detect`，省得 LAN8720A 的节能检测隔三差五来捣乱，把链路弄断。

改 PHY 地址这里有个坑，值得单独拎出来说：**千万别在 `&fec2` 里重新定义 `ethphy0: ethernet-phy@0`**。EVK 里早就有 `ethphy0: ethernet-phy@2` 了，同一个 label 定义两次，设备树编译器一句话就把你顶回来：`Duplicate label 'ethphy0'`。正确姿势是用 `&ethphy0` 覆盖原节点、只改 `reg`，节点名还叫 `ethernet-phy@2` 无所谓——内核认的是 `reg`，不是节点名。

### 4.2 defconfig（1 处）

只补一个 PHY 驱动：

```diff
 CONFIG_MICREL_PHY=y
+CONFIG_SMSC_PHY=y
```

EVK 板上焊的是 KSZ8081（Micrel），本板是 LAN8720A（SMSC）。两个驱动都留着，各认各的芯片，互不打架。

### 4.3 为 rootfs 补齐的内核选项

rootfs 里那堆调试工具，背后都得靠内核选项撑着。逐项对一遍，缺哪个补哪个：

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

Ftrace 这几项，在原始配置里是 `# CONFIG_FTRACE is not set`，属于"必须手动打开"的那一类，别指望它自己开。

### 4.4 这些地方看着该改，其实不用

下面这几处，乍看都像得动两下，其实原样就能用：

| 项 | 原因 |
|----|------|
| `smsc.c` PHY 驱动 | 4.9.88 的 `smsc_phy_reset` 已无条件调用 `genphy_soft_reset()`，不需要像 U-Boot 那样加软复位补丁 |
| `fec_main.c`（SION 位） | 设备树 `pinctrl_enet1/2` 里 TX_CLK 的电气属性 `0x4001b031` 已含 SION 位 |
| `pinctrl_enet1/2` 的 RMII 引脚 | 标准 RMII 专用引脚，所有 RMII 板子一致 |
| `CONFIG_ARCH_MULTI_V6` | 4.9.88 的 defconfig 默认已关闭（本板是纯 ARMv7） |
| 引脚电气属性值 | 先用 EVK 默认值，异常时再调 |

---

## 5. 构建

命令就三条，按顺序来：

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

顺手提醒一句：改过 `menuconfig`，一定记得把配置固化回 defconfig。不然下次一句 `make distclean`，辛苦点出来的选项全没：

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
| 工具链 | Linaro GCC 6.2（上游记录） | Linaro GCC 4.9.4 | 版本不同，但内核/U-Boot/rootfs 三者对得上 |

一句话：照上游文档直接做就行。本文多出来的，无非是本机的路径、固化 defconfig 的习惯，还有下面这些亲手踩过的点。

---

## 7. 过程中遇到的问题与处理

按出问题的先后顺序记，现在都已经解决。

### 7.1 eMMC 初始化超时（`error -110`）

**现象**：板子起不来，日志一遍遍刷：

```
mmc1: Tuning failed, falling back to fixed sampling clock
mmc1: error -110 whilst initialising MMC card
```

**定位**：`mmc1` 对应的就是 `usdhc2`。翻 EVK 的 `usdhc2` 节点，没写 `no-1-8-v`，内核自然按 UHS 那套去切 1.8V。再对一眼核心板原理图：eMMC 的 VCC/VDDI 全接在 VDD_3V3 上，压根没有电压切换电路。

**处理**：给 `&usdhc2` 补上 `no-1-8-v`，世界安静了。

### 7.2 SD 卡初始化超时（`error -110`）

**现象**：

```
mmc0: error -110 whilst initialising SD card
```

**定位**：`mmc0` 对应 `usdhc1`。两处对不上：一来 EVK 有 `vmmc-supply`（板上带电源开关 GPIO），本板 SD 卡的 VDD 直连 3.3V；二来同样缺 `no-1-8-v`。CD 引脚倒是省心，`cd-gpios = <&gpio1 19 GPIO_ACTIVE_LOW>` 跟本板的 `SD1_CD` 正好一致，不用动。

**处理**：`&usdhc1` 去掉 `vmmc-supply`，再加 `no-1-8-v`。

### 7.3 网络 PHY 不识别

**现象**：`fec` 倒是注册成功了，可日志里翻不到半句 PHY attach，更别提 link up。

**定位与处理**：顺着往下摸，一共四个子问题，凑一块才把网络搞瘫：

| 子问题 | 结论 | 处理 |
|--------|------|------|
| PHY 地址 | ENET1 的 PHYAD0 下拉 → 地址 0，EVK 写的是 2 | `&ethphy0 { reg = <0>; }` |
| PHY 复位 | EVK 靠 74HC595，本板 GPIO5_IO09 / GPIO5_IO06 直连 | `phy-reset-gpios` + `pinctrl_enet*_reset` |
| PHY 驱动 | `CONFIG_SMSC_PHY` 默认未开（EVK 是 KSZ8081） | defconfig 加 `CONFIG_SMSC_PHY=y` |
| 引脚冲突 | TAMPER9 被 `pinctrl_lcdif_reset` 占用 | 清空该 pinctrl 的 pins |

### 7.4 设备树报 `Duplicate label 'ethphy0'`

**现象**：在 `&fec2` 里重新定义 `ethphy0: ethernet-phy@0`，编译当场失败。

**原因**：EVK 里早就有 `ethphy0: ethernet-phy@2` 了，同一个 label 定义两次，dtc 不干。

**处理**：别新建节点，改用 `&ethphy0` 覆盖，只改 `reg`。

### 7.5 网卡名从 `eth0` 变成 `eth2`

**现象**：开机日志里冒出这么几行：

```
fec 20b4000.ethernet eth124: renamed from eth0
fec 20b4000.ethernet eth2: renamed from eth124
Starting network: Cannot find device "eth0"
```

**原因**：出厂 rootfs 里的 udev 规则爱管闲事，按 MAC/PCI 排序把网卡重命名了一遍，跟新内核的命名顺序对不上。硬件本身好好的，纯粹是名字被换了。

**处理**：这不算内核移植的账。自建 rootfs（BusyBox + mdev，没有 udev 那套规则）之后，网卡按内核默认顺序命名，问题自己就没了。

### 7.6 工具链一致性

**注意**：内核、U-Boot、rootfs 必须同一套 `arm-linux-gnueabihf-`。上游记录用的是 GCC 6.2，本项目用 4.9.4，新旧无所谓，三者对得上就行；混着用，rootfs 启动阶段会甩你一句 `No working init found`。

---

## 8. 上游参考

下面这些链接都锁在 commit `5bd89d0` 上，内容不会跟着 `main` 乱变：

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

内核移植听着唬人，拆开看无非两件事：对着原理图改设备树，对着日志调配置。真正耗时间的从来不是技术，而是肯一行行读日志的耐心。
