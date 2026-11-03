# i.MX6ULL Buildroot 根文件系统构建流程（rootfs 部分）

> 平台：100ASK IMX6ULL Pro（NXP i.MX6ULL，Cortex-A7）
> Buildroot：2020.02.12（LTS）
> 配置起点：`imx6ulevk_defconfig`
> 对应模块：`rootfs/`（本仓库），上游参考：<https://github.com/illusOwo-ff/i.MX6ULL-bsp-driver-project>
> 前置条件：U-Boot 与 Kernel 已自行移植完成（见本仓库 `uboot/`、`kernel/`）

这份记录，是从一个空目录一路干到"板子上跑起来"的完整过程。全文按"做什么、为什么、怎么做、怎么验证"展开，末尾照例是踩坑记录。文里的配置项全按 `make menuconfig` 里实际显示的菜单文字写，对着屏幕找就行。

---

## 0. 文档说明

### 0.1 这份文档解决什么问题

参考仓库里的 `rootfs_project_record.md` 更像一份"结果记录"，几个环节串成一条线。头一回照着做，多半会碰上两种难受：

1. **不知道每一步为什么这么做**，换个环境立马抓瞎；
2. **出了错不知道往哪查**，报错信息跟配置项根本对不上号。

所以本文按"阶段"拆开，每一步都写清楚目的和验证方法，实际踩到的坑单独拎出来，放在第 7 章。

### 0.2 适用边界

- 适用于 **Buildroot 2020.02.x**；其他版本的菜单名和 Kconfig 符号可能不同（例如 2020.02 里叫 `Pre-installed toolchain`，旧版可能叫 `Custom toolchain`）。
- 适用于 **BusyBox init + mdev** 的精简系统，不涉及 systemd / udev。
- 内核版本以 **4.9.88** 为基准（ext4 的 `metadata_csum` 兼容性问题与此强相关）。

### 0.3 环境与路径约定

表里是本项目的真实取值。你换了机器或者目录，就整表替换，别只改一半。

| 变量 | 本项目取值 | 说明 |
|------|-----------|------|
| `BUILDROOT_DIR` | `<仓库>/rootfs/sources/buildroot-2020.02.12`（由同目录的 `buildroot-2020.02.12.tar.gz` 解压得到） | Buildroot 源码根目录 |
| `DL_DIR` | `<仓库>/rootfs/sources/dl` | 软件包下载缓存；编译前 `export BR2_DL_DIR=$DL_DIR` |
| `TOOLCHAIN_DIR` | `/usr/local/arm/gcc-linaro-4.9.4-2017.01-x86_64_arm-linux-gnueabihf` | 交叉工具链安装目录（`bin/` 的上一级） |
| `TOOLCHAIN_PREFIX` | `arm-linux-gnueabihf` | 工具链前缀 |
| `NFS_ROOT` | `/home/edison/linux/nfs/my_rootfs` | NFS 导出的根文件系统目录 |
| `HOST_IP` | `192.168.1.7` | Ubuntu 虚拟机 IP（NFS/TFTP 服务器） |
| `BOARD_IP` | `192.168.1.6` | 开发板 IP |
| `KERNEL_DIR` | `~/my-linux-imx-imx_4.9.88.2.0` | 内核源码 |
| `UBOOT_DIR` | `~/my-uboot-v2017.03-4.9.88` | U-Boot 源码 |

> 参考仓库作者的环境是 `GCC 6.2.1`（`/home/book/100ask_imx6ull-sdk/...`），网段 `192.168.5.x`。**工具链版本不一样，编译阶段就会给你颜色看**；本项目用的是 4.9.4，怎么绕过去的见 7.3。
>
> 表中 `<仓库>` 指本工作区（`E:\100ask-imx6ull-bsp`）；`rootfs/sources/` 下存放 Buildroot 源码包与 `dl/` 缓存，详见 `rootfs/sources/README.md`。

---

## 1. 总体流程

```
┌────────────────────────────────────────────────────────────────────┐
│ 阶段一 前置条件                                                     │
│   U-Boot 已移植  →  Kernel 已移植  →  确认工具链  →  补内核配置      │
└───────────────────────────────┬────────────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────────────┐
│ 阶段二 Buildroot 配置与编译                                          │
│   defconfig 起点 → 改工具链 → 关内核/U-Boot → 系统配置 → 软件包      │
│   → overlay → 镜像格式 → savedefconfig → make                       │
└───────────────────────────────┬────────────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────────────┐
│ 阶段三 NFS 启动验证（先不烧 eMMC）                                   │
│   解压 rootfs.tar → 配 exports → U-Boot bootargs → 启动             │
└───────────────────────────────┬────────────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────────────┐
│ 阶段四 部署到 eMMC                                                 │
│   dd 写分区 2 → 内核/dtb 放入 /boot → 改 U-Boot 加载参数 → 重编 U-Boot│
└───────────────────────────────┬────────────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────────────┐
│ 阶段五 上板验证                                                     │
│   ps / /dev / 挂载 eMMC / 调试工具 / SSH                            │
└────────────────────────────────────────────────────────────────────┘
```

**为什么非得按这个顺序来？**

1. **先 NFS，后 eMMC**：NFS 的 rootfs 就放在主机上，改个文件、板子重启就生效；eMMC 每次都得 `dd` 重写，慢不说，还伤寿命。调试阶段来回改的次数，可比最终部署多得多。
2. **先编个"能跑的最小系统"，再往里加包**：Buildroot 配错的症状五花八门——缺库、没 init、网络不通，看着都像别处的毛病。最小系统先跑起来，才能把 Buildroot 的锅和驱动、内核的锅分开。
3. **U-Boot 的启动参数留到最后动**：这玩意儿改错，你会连日志都看不见。等系统验证好用了再改，真出问题退回去也容易。

---

## 2. 阶段一：前置条件

### 2.1 确认已完成的组件

| 组件 | 状态 | 关键信息 |
|------|------|----------|
| U-Boot | 已移植 | 2017.03，板级文件 `mx6ull_myboard`，产物 `u-boot-dtb.imx` |
| Kernel | 已移植 | 4.9.88，`my_imx_emmc_defconfig`，设备树 `imx6ull-my14x14-emmc.dts` |
| 启动方式 | 可用 | SD 卡 U-Boot + TFTP 内核 + eMMC 原厂 rootfs |

**为什么先确认这些**：Buildroot 只管用户态，U-Boot 和内核能不能用，是它的前提。内核本身就起不来的话，后面所有 rootfs 的问题都会被算错账。

### 2.2 确认工具链（决定后续一切）

```bash
which arm-linux-gnueabihf-gcc
# /usr/local/arm/gcc-linaro-4.9.4-2017.01-x86_64_arm-linux-gnueabihf/bin/arm-linux-gnueabihf-gcc

$TOOLCHAIN_DIR/bin/arm-linux-gnueabihf-gcc -v
# gcc version 4.9.4 (Linaro GCC 4.9-2017.01)
```

顺手把内核头文件版本也读出来，Buildroot 里 `External toolchain kernel headers series` 那一项要填它：

```bash
grep -m1 LINUX_VERSION_CODE \
  $TOOLCHAIN_DIR/arm-linux-gnueabihf/libc/usr/include/linux/version.h
# #define LINUX_VERSION_CODE 263680   → 0x040600 → 4.6.0
```

换算公式：`(code >> 16).(code >> 8 & 0xFF).(code & 0xFF)`。

**为什么说这步最关键**：Buildroot 出来的 rootfs 里装的是 glibc 动态库，它得跟内核、跟编内核那套工具链**同源**。工具链一乱，典型的下场是启动到最后一步，屏幕上一行大字：

```
Kernel panic - not syncing: No working init found.
```

到这儿，内核和 rootfs 看着都"编译成功"了，根子却在动态库和 ABI 对不上。**记住一条铁律：U-Boot、Kernel、rootfs 用同一套工具链。**

### 2.3 补内核配置

rootfs 里那些调试工具，背后都有内核选项撑着，移植内核的时候未必开了。翻开 `my_imx_emmc_defconfig` 对一遍：

| 配置项 | 作用 | 本项目状态 |
|--------|------|-----------|
| `CONFIG_DEVTMPFS` / `CONFIG_DEVTMPFS_MOUNT` | 内核自动挂载 devtmpfs，`/dev` 才有设备节点 | 已开 |
| `CONFIG_EXT4_FS` | 挂载 ext4 根文件系统 | 已开（由 `CONFIG_EXT3_FS` 隐含） |
| `CONFIG_TMPFS` | BusyBox/系统运行需要 | 已开 |
| `CONFIG_I2C_CHARDEV` | `i2c-tools` 依赖 `/dev/i2c-*` | 已开 |
| `CONFIG_SPI_SPIDEV` | `spi-tools` / spidev 测试 | 已开 |
| `CONFIG_GPIO_SYSFS` | GPIO sysfs 验证（libgpiod 用不了时的退路） | 已开 |
| `CONFIG_DEVMEM` | `devmem` 直接读写寄存器 | 已开 |
| `CONFIG_NFS_FS` + `CONFIG_ROOT_NFS` | NFS 根文件系统启动 | 已开 |
| `CONFIG_FUNCTION_TRACER` 等 Ftrace 项 | `trace-cmd` 的用户态追踪 | **被显式关闭，需要打开** |

**原因很简单**：`# CONFIG_FTRACE is not set` 一挂，`trace-cmd` 就是个摆设；`DEVTMPFS` 不开，系统起来 `/dev` 空空荡荡，串口、块设备一个都找不着。这种毛病在 Buildroot 那边怎么查都查不出来，只能回头找内核配置。

开 Ftrace 的步骤：

```bash
cd $KERNEL_DIR
make my_imx_emmc_defconfig
make menuconfig
# Kernel hacking → Tracers
#   [*] CONFIG_FUNCTION_TRACER
#   [*] CONFIG_FUNCTION_GRAPH_TRACER
#   [*] CONFIG_IRQSOFF_TRACER
#   [*] CONFIG_SCHED_TRACER
# Kernel hacking → printk and dmesg options
#   [*] CONFIG_DYNAMIC_DEBUG
make savedefconfig
cp defconfig arch/arm/configs/my_imx_emmc_defconfig
```

验证（板子上）：

```bash
ls /sys/kernel/debug/tracing/
cat /sys/kernel/debug/tracing/available_tracers
# function_graph function irqsoff ... 都在即可
```

### 2.4 复用 dl 缓存

仓库里塞了一份现成的下载缓存：`rootfs/sources/dl/`，418 个包目录、906 个文件、差不多 2.0 GB，跟着源码一起入库。Buildroot 编译前先来这儿翻，有就不下载。

```bash
export BR2_DL_DIR=<仓库>/rootfs/sources/dl
# 或写进 .config：Build options → Download dir
```

**为什么值得折腾这一下**：一次完整编译要下载几十个包，国内网络三天两头超时。命中缓存，编译能从"一小时起步"压到 5~10 分钟，7.1、7.13 那种下载翻车也一并躲开。

**注意**：`dl/` 里偏偏没有 `dropbear` 和 `nano`（SDK 原本用的是 openssh），本项目挑了这两个包，头一次编译还得去下，见 7.13。

---

## 3. 阶段二：Buildroot 配置与编译

### 3.1 获取源码

Buildroot 走的是"源码发布包"路线，没有板级仓库，源码直接去官网下。它跟 BusyBox 那种"毛坯房，家具自己一件件搬"的路子不同，更像精装房——菜单上勾几样软件包，拎包入住。

官方下载页：<https://buildroot.org/downloads/>
本项目使用的版本：<https://buildroot.org/downloads/buildroot-2020.02.12.tar.gz>

获取源码：

```bash
wget https://buildroot.org/downloads/buildroot-2020.02.12.tar.gz
tar -xzf buildroot-2020.02.12.tar.gz
cd buildroot-2020.02.12
```

**另一种方式（防呆）**：仓库里另存了一份同版本的源码包 `rootfs/sources/buildroot-2020.02.12.tar.gz`（约 6.5 MB），离线或官网下载失败时可直接用，解压后的内容与上面一致：

```bash
cd <仓库>/rootfs/sources
tar -xzf buildroot-2020.02.12.tar.gz     # 得到 buildroot-2020.02.12/
export BR2_DL_DIR=$PWD/dl                # 让 Buildroot 使用仓库内的缓存
cd buildroot-2020.02.12
```

两种方式二选一；无论用哪种，编译前都要把 `BR2_DL_DIR` 指向仓库缓存 `rootfs/sources/dl/`（见 2.4）。

**为什么挑 2020.02.12**：一来它是 LTS 分支，二来跟韦东山 SDK 的 `Buildroot_2020.02.x` 同系列，仓库里那份 `dl/` 缓存（也是从那个 SDK 来的）正好能直接吃。

**想直接复现最终配置**：把仓库里的 `rootfs/configs/my_imx6ull_defconfig` 拷进解压后的 `configs/`，`make my_imx6ull_defconfig` 一敲，3.3 那堆逐项修改就全跳过了。不过本文还是按"从零改起"讲，不然你不知道每一项在忙什么。

### 3.2 选择配置起点

```bash
make imx6ulevk_defconfig
```

**为什么不自建**：ARM 的架构选项细得吓人——CPU 型号、浮点 ABI、NEON，一项填错就是"能编译，但跑不起来"。`imx6ulevk_defconfig` 是 NXP 官方 i.MX6UL EVK 的配置，i.MX6ULL 跟它同架构（Cortex-A7），拿它开刀最省事。

### 3.3 逐项修改

`make menuconfig` 进去以后，照着下面几张表逐项收拾。每张表都分"动作"和"原因"两列：前者告诉你点哪儿，后者告诉你为什么点。

#### A. 架构（保留不动）

| 配置项 | 动作 | 原因 |
|--------|------|------|
| `BR2_arm` / `BR2_cortex_a7` / `BR2_ARM_FPU_NEON_VFPV4` | 保留 | 与 i.MX6ULL 一致，改了就跑不起来 |

#### B. 内核（全部删除）

| 配置项 | 动作 | 原因 |
|--------|------|------|
| `BR2_LINUX_KERNEL` 及其所有子项 | 取消 | 内核已手动编译（4.9.88），Buildroot 再编一份既浪费时间又可能与板级补丁冲突 |
| `BR2_PACKAGE_HOST_LINUX_HEADERS_CUSTOM_5_4` | 删除 | 属于"Buildroot 自己编内核"时的头文件配置，改用外部工具链后无意义 |

#### C. U-Boot（全部删除）

| 配置项 | 动作 | 原因 |
|--------|------|------|
| `BR2_TARGET_UBOOT` 及其所有子项 | 取消 | U-Boot 已移植（2017.03 板级补丁）。**且 Buildroot 2020.02 自带的 U-Boot 是 2018.07，要求 GCC ≥ 6.0**，4.9.4 工具链会直接报 `checkgcc6` 失败（详见 7.3） |

#### D. 工具链（Internal → External）

这一节最容易翻车，慢点看。

| 配置项 | 值 | 原因 |
|--------|-----|------|
| `Toolchain type` | `External toolchain` | 复用已有 Linaro 工具链，不重新编译工具链 |
| `Toolchain` | `Custom external toolchain` | 用自己下载的 Linaro 包，不在官方列表里 |
| `Toolchain origin` | **`Pre-installed toolchain`** | 用本地已安装的，不下载（选错会去 ARM 官网下载并失败，见 7.1/7.2） |
| `Toolchain path` | `$TOOLCHAIN_DIR` | 填到 `bin/` 的**上一级** |
| `Toolchain prefix` | `arm-linux-gnueabihf` | 实际前缀，注意菜单里默认是 `$(ARCH)-linux` |
| `External toolchain gcc version` | `4.9.x` | 与实际工具链一致 |
| `External toolchain kernel headers series` | 按 2.2 读出的值填 | 填错会导致部分包被错误地显示/隐藏 |
| `External toolchain C library` | `glibc` | Linaro 工具链用的是 glibc |
| `Toolchain has C++ support?` | 勾选 | 部分包（如 gdb）需要 |

**为什么非得选"外部工具链"**：
1. 别让 Buildroot 自己去下工具链，下不下来的故事见 7.1；
2. 保证跟内核同源，就是 2.2 那条铁律。

#### E. System configuration

| 配置项 | 值 | 原因 |
|--------|-----|------|
| `System hostname` | `my-imx6ull` | 决定提示符里的主机名 |
| `System banner` | `Welcome to my imx6ull` | 登录前的欢迎语，用于一眼确认跑的是自己的系统 |
| `Init system` | `BusyBox` | 精简，够用 |
| `/dev management` | `Dynamic using devtmpfs + mdev` | BusyBox 自带的轻量设备管理，替代 udev（见 7.6） |
| `Enable root login with password` | 勾选 | 不勾选则 root 为空密码，SSH 会拒绝登录（见 7.12） |
| `Root password` | `123456` | 串口/SSH 登录用 |
| `Root filesystem overlay directories` | `board/my_imx6ull/rootfs-overlay` | 见 3.4 |

#### F. 软件包

| 软件包 | 配置符号 | 用途 |
|--------|---------|------|
| BusyBox 显示重叠包 | `BR2_PACKAGE_BUSYBOX_SHOW_OTHERS` | 不开这一项，`i2c-tools` 等会被 BusyBox 的同名 applet 隐藏 |
| gdb / gdbserver | `BR2_PACKAGE_GDB` | 远程调试用户态程序 |
| strace | `BR2_PACKAGE_STRACE` | 追踪系统调用（i2c/spi 驱动验证用） |
| trace-cmd | `BR2_PACKAGE_TRACE_CMD` | Ftrace 用户态前端 |
| nfs-utils | `BR2_PACKAGE_NFS_UTILS` | 板子挂载 NFS |
| evtest | `BR2_PACKAGE_EVTEST` | input 子系统测试 |
| i2c-tools | `BR2_PACKAGE_I2C_TOOLS` | `i2cdetect/i2cget/i2cset` |
| spi-tools | `BR2_PACKAGE_SPI_TOOLS` | SPI 控制器验证 |
| dropbear | `BR2_PACKAGE_DROPBEAR` | 轻量 SSH 服务端（见 7.12） |
| nano | `BR2_PACKAGE_NANO` | 板端编辑文件 |

dropbear 子选项建议：

```
[*] client programs
[*] disable reverse DNS lookups     # 防止 SSH 登录卡顿
[*] optimize for size
```

**为什么用 dropbear、不用 openssh**：体积差一个数量级，BusyBox 环境下完全够用。`disable reverse DNS lookups` 是为了别让登录卡在反查上——板子压根没有 DNS。

**libgpiod 的坑**：`BR2_PACKAGE_LIBGPIOD` 要 `BR2_TOOLCHAIN_HEADERS_AT_LEAST_4_8`，本工具链头文件才 4.6，灰的，选不上。退路是用内核自带的 GPIO sysfs 接口（`/sys/class/gpio/`）验证驱动，见 7.7。

#### G. 文件系统镜像

| 配置项 | 值 | 原因 |
|--------|-----|------|
| `ext2/3/4 root filesystem` | 勾选 | eMMC 分区是 ext4 |
| `ext4` | 勾选 | `rootfs.ext2` 实际是 ext4，另有 `rootfs.ext4` 软链接 |
| `additional mke2fs options` | `-O ^64bit,^metadata_csum` | 4.9.88 内核与新版 e2fsprogs 的 `metadata_csum` 不兼容（见 7.11） |
| tar | 保持默认（自动生成） | NFS 部署用 `rootfs.tar` |

**为什么非去掉 `metadata_csum` 不可**：虚拟机上的 `mke2fs` 默认就把这个特性打开了，可 4.9.88 的 ext4 驱动一看校验和不对，直接拒绝挂载，U-Boot 的 `ext4write` 也不认。于是表面上"镜像做出来了"，搬到板子上根本挂不上。

#### H. 后处理脚本（重要）

| 配置项 | 动作 | 原因 |
|--------|------|------|
| `Custom scripts to run after creating filesystem images`（`BR2_ROOTFS_POST_IMAGE_SCRIPT`） | **清空** | 默认值 `board/freescale/common/imx/post-image.sh` 会把 zImage/dtb 打包成整卡镜像；内核编译已关闭，找不到 zImage 就报错（见 7.4） |
| `genimage` / `dosfstools` / `mtools` | 取消 | 只服务于上面的整卡打包，本项目分步部署，不需要 |

### 3.4 配置 Overlay（提示符定制）

Overlay 说白了就是个"编译完再盖上去"的目录，最后会被覆盖到 `output/target`，专门放那些不属于任何软件包的定制文件。

```bash
cd $BUILDROOT_DIR
mkdir -p board/my_imx6ull/rootfs-overlay/etc/profile.d/
cat > board/my_imx6ull/rootfs-overlay/etc/profile.d/ps1.sh << 'EOF'
export PS1='[\u@\h:\w]# '
EOF
```

再回到 `System configuration`，光标移到 `Root filesystem overlay directories`：

- 这一项**不是复选框**，按 `Enter` 直接输入路径；
- 填相对路径 `board/my_imx6ull/rootfs-overlay`（相对 Buildroot 根目录）；
- 多个目录用空格分隔，按顺序覆盖。

验证配置：

```bash
grep ROOTFS_OVERLAY .config
# BR2_ROOTFS_OVERLAY="board/my_imx6ull/rootfs-overlay"
```

**为什么用 `profile.d/ps1.sh`，不直接改 `/etc/profile`**：Buildroot 的 `/etc/profile` 里有一堆默认环境变量，直接盖掉就把它们弄丢了；`profile.d/*.sh` 是"追加执行"，安全得多。参考仓库也是这么干的（见 7.5）。

**为什么用 Overlay，不编完再手改**：手改的东西，`make clean` 一下、或者重新解压一次，全没了；Overlay 是配置的一部分，每回编译自动生效。

### 3.5 保存自定义配置

配置调完，赶紧存一份，别让它白调：

```bash
make savedefconfig BR2_DEFCONFIG=configs/my_imx6ull_defconfig
make show-targets
```

`show-targets` 的输出里应该能看到 `busybox dropbear i2c-tools ... rootfs-ext2`，唯独**没有 `linux` 和 `uboot`**。这就是"内核和 U-Boot 确实被关掉了"的铁证。

**为什么非要存成 defconfig**：`.config` 一遇 `make clean` 就没；`savedefconfig` 只记跟默认值不同的项，文件小、能入库、可复现。以后一句 `make my_imx6ull_defconfig`，就回到今天这个状态。

### 3.6 编译

该点的都点完了，开编。头一回会慢一些，泡杯茶的工夫：

```bash
cd $BUILDROOT_DIR
export BR2_DL_DIR=$DL_DIR    # 前面未 export 时补上
make -j$(nproc)
```

产物在 `output/images/`：

```
rootfs.ext2     # ext4 格式的根文件系统镜像（约 10~20MB）
rootfs.ext4     # 指向 rootfs.ext2 的软链接
rootfs.tar      # tar 包，NFS 部署用
```

验证 overlay 生效：

```bash
cat output/target/etc/profile.d/ps1.sh
# export PS1='[\u@\h:\w]# '
```

**为什么加 `-j$(nproc)`**：Buildroot 按包依赖并行编译，`nproc` 拿到的是 CPU 核数；不加 `-j` 就是单核慢慢熬，耗时差好几倍。当然也别把 `-j` 开到内存扛不住的地步，编大包的时候会 OOM 给你看。

---

## 4. 阶段三：NFS 启动验证

### 4.1 为什么先做 NFS

- rootfs 搁在主机目录里，**改完文件，板子重启就生效**，一个 `tar xf` 就算"重新部署"；
- 不用反复 `dd` 写 eMMC，又快又不磨芯片；
- 出了错，直接在主机上改配置再启动，到底是 rootfs 的毛病还是驱动的毛病，一测就分得清。

### 4.2 部署 rootfs

```bash
mkdir -p $NFS_ROOT
sudo rm -rf $NFS_ROOT/*          # 先清空，避免旧文件残留导致"改了没生效"的假象
sudo tar xf $BUILDROOT_DIR/output/images/rootfs.tar -C $NFS_ROOT
```

> 每回重新编译，这一步都得重来。NFS 是"共享目录"，不解压新的，板子跑的还是旧系统。

配置 NFS 导出（**导出到 `my_rootfs` 本身**，而不是它的父目录）：

```bash
echo '/home/edison/linux/nfs/my_rootfs *(rw,sync,no_root_squash,no_subtree_check)' | sudo tee -a /etc/exports
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server
```

验证：

```bash
showmount -e localhost
# /home/edison/linux/nfs/my_rootfs *
```

**为什么反复强调"导出到 my_rootfs 本身"**：要是导出的是父目录，`nfsroot` 又只写到 `nfs`，板子就会挂到一个空目录上。表现是"内核启动成功，然后 `No working init found`"，或者干脆给你一个 panic。少一层路径，就少一个错点（见 7.9）。

### 4.3 U-Boot 启动命令

先手动跑一遍，确认能进系统再说：

```bash
setenv ipaddr 192.168.1.6
setenv serverip 192.168.1.7
setenv bootargs 'console=ttymxc0,115200 root=/dev/nfs rw nfsroot=192.168.1.7:/home/edison/linux/nfs/my_rootfs,v3 ip=192.168.1.6:192.168.1.7:192.168.1.1:255.255.255.0::eth0:off'
tftp 80800000 zImage
tftp 83000000 imx6ull-my14x14-emmc.dtb
bootz 80800000 - 83000000
```

参数含义：

| 参数 | 含义 |
|------|------|
| `root=/dev/nfs` | 根文件系统走网络 |
| `nfsroot=IP:路径,v3` | NFS 服务器地址 + 导出路径；`v3` 用 NFSv3，兼容性最好 |
| `ip=板卡:主机:网关:掩码::eth0:off` | 内核启动阶段的静态 IP 配置；`off` 表示不自动配置 |
| `console=ttymxc0,115200` | 与硬件串口一致，必须和 U-Boot 的 `console` 一致 |

**为什么不用 `ifconfig`**：U-Boot 里没这命令，那是 Linux 的。U-Boot 的网络全靠环境变量 `ipaddr/serverip/netmask/gatewayip`，敲 `tftp`、`ping` 的时候自动套用（见 7.10）。

**为什么非得设 `ip=`**：NFS 挂载发生在内核启动阶段，那会儿用户态的 DHCP 客户端还没生出来，网卡只能让内核自己配。

### 4.4 验证清单

板子跑起来以后，挨个对一遍：

| 检查点 | 预期 |
|--------|------|
| 串口输出 | 出现 `Welcome to my imx6ull` |
| 登录 | `my-imx6ull login:` 输入 `root` + 密码成功 |
| 提示符 | `[root@my-imx6ull:~]#` |
| 根文件系统 | `mount \| grep nfs` 显示 NFS 挂载 |
| 网络 | `ifconfig eth0` 有 `192.168.1.6` |
| 设备节点 | `ls /dev/ttymxc0 /dev/mmcblk1` 存在 |

### 4.5 固化启动命令（可选）

每次上电都手敲一长串，敲错是迟早的事。U-Boot 开机自动执行 `bootcmd`，把整串塞进去就一劳永逸：

```bash
setenv bootcmd 'setenv ipaddr 192.168.1.6; setenv serverip 192.168.1.7; setenv bootargs console=ttymxc0,115200 root=/dev/nfs rw nfsroot=192.168.1.7:/home/edison/linux/nfs/my_rootfs,v3 ip=192.168.1.6:192.168.1.7:192.168.1.1:255.255.255.0::eth0:off; tftp 80800000 zImage; tftp 83000000 imx6ull-my14x14-emmc.dtb; bootz 80800000 - 83000000'
saveenv
```

**为什么调试期可以先不 `saveenv`**：环境变量存在 U-Boot 的 env 分区里。后面按 5.2 改板级头文件、重新烧 U-Boot 时，`saveenv` 存的内容有可能被盖掉，白忙一场。等参数稳定、U-Boot 不再动了，再固化。

---

## 5. 阶段四：部署到 eMMC

### 5.1 确认分区与文件位置

板子上（NFS 启动状态）：

```bash
fdisk -l /dev/mmcblk1
# mmcblk1p1  1000MB  Linux
# mmcblk1p2  1500MB  Linux   ← rootfs
# mmcblk1p3   500MB  FAT32

mount /dev/mmcblk1p2 /mnt/emmc
ls /mnt/emmc/boot/
```

**为什么先看这个**：U-Boot 的加载参数（分区号、文件放 `/boot/` 下、用 `ext2load` 还是 `fatload`）全看这套布局。布局确认了，下面那 4 处改动才有依据。

### 5.2 修改 U-Boot 启动参数

`include/configs/mx6ull_myboard.h` 里有 4 处跟实际情况对不上：

| 变量 | 原值 | 改为 | 原因 |
|------|------|------|------|
| `CONFIG_SYS_MMC_IMG_LOAD_PART` | `1` | `2` | 内核在分区 2 |
| `fdt_file` | 未定义（默认 `imx6ull-myboard.dtb`） | `imx6ull-my14x14-emmc.dtb` | 要用内核编译出的设备树，不是 U-Boot 自己的 |
| `loadimage` | `fatload mmc ${mmcdev}:${mmcpart} ${loadaddr} ${image}` | `ext2load mmc ${mmcdev}:${mmcpart} ${loadaddr} /boot/${image}` | 分区是 ext4 不是 FAT，且文件在 `/boot/` 下 |
| `loadfdt` | `fatload ... ${fdt_file}` | `ext2load ... /boot/${fdt_file}` | 同上 |

```c
#define CONFIG_SYS_MMC_IMG_LOAD_PART	2

"fdt_file=imx6ull-my14x14-emmc.dtb\0" \
"loadimage=ext2load mmc ${mmcdev}:${mmcpart} ${loadaddr} /boot/${image}\0" \
"loadfdt=ext2load mmc ${mmcdev}:${mmcpart} ${fdt_addr} /boot/${fdt_file}\0" \
```

改完重编 U-Boot：

```bash
cd $UBOOT_DIR
make distclean
make mx6ull_myboard_defconfig
make -j$(nproc)
# 产物 u-boot-dtb.imx
```

**为什么光改 `bootargs` 没用**：`bootcmd → mmcboot → loadimage/loadfdt` 是一条写死的调用链，`fatload` 碰上 ext4 分区，直接一句 `** Unable to read file **`。不换成 `ext2load`，内核根本加载不上。

### 5.3 写入 eMMC

主机侧准备文件到 NFS 目录：

```bash
cp $BUILDROOT_DIR/output/images/rootfs.ext2 $NFS_ROOT/root/
cp $KERNEL_DIR/arch/arm/boot/zImage $NFS_ROOT/root/
cp $KERNEL_DIR/arch/arm/boot/dts/imx6ull-my14x14-emmc.dtb $NFS_ROOT/root/
```

板子上（NFS 启动状态）：

```bash
dd if=/root/rootfs.ext2 of=/dev/mmcblk1p2 bs=1M
sync

mount /dev/mmcblk1p2 /mnt/emmc
mkdir -p /mnt/emmc/boot
cp /root/zImage /mnt/emmc/boot/
cp /root/imx6ull-my14x14-emmc.dtb /mnt/emmc/boot/
sync
umount /mnt/emmc
```

**为什么用板子上敲 `dd`，不用烧录工具的"更新内核/设备树"**：那工具底层走的是 U-Boot 的 `ext4write`，可 2017.03 的 `ext4write` 不认 `metadata_csum`，必然失败（见 7.11）。`dd` 加 `cp`，绕开它。

U-Boot 本身用烧录工具的"更新 Uboot"把 `u-boot-dtb.imx` 写到 eMMC。

### 5.4 验证

断电，拔 SD 卡，拨码开关切 eMMC 启动：

```
U-Boot 2017.03 ...
Board: MX6ULL MYBOARD
...
8938120 bytes read in 509 ms          ← zImage 从 eMMC 加载
36760 bytes read in 121 ms            ← dtb 从 eMMC 加载
Kernel command line: console=ttymxc0,115200 root=/dev/mmcblk1p2 rootwait rw
EXT4-fs (mmcblk1p2): mounted filesystem with ordered data mode
Welcome to my imx6ull
my-imx6ull login: root
[root@my-imx6ull:~]#
```

看见 `EXT4-fs ... mounted`，说明分区和文件系统都对；再看见提示符，init 也就起来了。

---

## 6. 阶段五：上板验证

换到 eMMC 启动之后，下面这些挨个过一遍，心里就有底了：

| 项目 | 命令 | 预期 |
|------|------|------|
| 进程 | `ps` | PID 1 是 `init`（BusyBox），有 `syslogd`、`dropbear` |
| 存储 | `ls /dev/mmcblk*` | `mmcblk1p1/p2/p3`、`mmcblk1boot0/rpmb` |
| 串口 | `ls /dev/ttymxc*` | `ttymxc0`、`ttymxc1` |
| 挂载 eMMC | `mount /dev/mmcblk1p2 /mnt/emmc` | 成功；`couldn't mount as ext3` 是正常回退日志 |
| I2C | `i2cdetect -l` / `i2cdetect -y 0` | 列出适配器与地址 |
| SPI | `spi-config -d /dev/spidev0.0 -q` | 能读到模式/速率 |
| 追踪 | `trace-cmd record -p function ...` | 有输出 |
| SSH | 主机 `ssh root@192.168.1.6` | 能登录 |

SSH 登录失败先看服务在不在：

```bash
ps | grep dropbear
# 184 root /usr/sbin/dropbear -R
```

---

## 7. 踩坑记录

先给张速查表，详细经过在 7.1~7.14。

| # | 问题 | 关键现象 | 处理 |
|---|------|---------|------|
| 7.1 | 工具链自动下载失败 | `无法验证 developer.arm.com 的证书` + `sources.buildroot.net 404` | 改用本地工具链 |
| 7.2 | 找不到 `Download toolchain automatically` | 菜单里只有两个选项 | 选 `Pre-installed toolchain` |
| 7.3 | U-Boot 编译报 GCC < 6.0 | `Your GCC is older than 6.0`、`checkgcc6` | 关闭 Buildroot 的 U-Boot |
| 7.4 | 编译尾部找不到 zImage | `post-image.sh` 报错，rootfs 已生成 | 清空 post-image 脚本 |
| 7.5 | overlay 路径与官方规范不一致 | 两套路径 | 概念澄清：路径自定，profile.d 更优 |
| 7.6 | `/dev` 管理方式选错 | `/dev` 为空或缺节点 | `devtmpfs + mdev` |
| 7.7 | libgpiod 选不上 | 依赖 headers ≥ 4.8 | 用 sysfs 验证 GPIO |
| 7.8 | 内核与 rootfs 工具链不一致 | `No working init found` | 统一工具链 |
| 7.9 | NFS 挂载失败 | 挂到空目录 / panic | exports 指到 `my_rootfs` |
| 7.10 | U-Boot 没有 `ifconfig` | `Unknown command 'ifconfig'` | 用 `setenv ipaddr/serverip` |
| 7.11 | eMMC 挂载失败 | `invalid superblock checksum`、`ext4write` 失败 | `-O ^64bit,^metadata_csum` |
| 7.12 | SSH 密码错误 | root / 123456 都不对 | 板端 `passwd root`；勾选 root 登录 |
| 7.13 | dl 缺包、下载慢 | 卡在下载 | 手动放入 `dl/` |
| 7.14 | 网卡名从 eth2 变 eth0 | 启动参数里 `eth2` 失效 | 改用 `eth0` |

### 7.1 工具链自动下载失败（证书 + 404）

**现象**：编译才起步，就卡在下载工具链上，最后甩出一堆：

```
>>> toolchain-external-arm-arm 2019.12 Downloading
错误: 无法验证 developer.arm.com 的由 "CN=GlobalSign ..." 颁发的证书
--2026-10-28 17:06:22--  http://sources.buildroot.net/toolchain-external-arm-arm/...tar.xz
错误 404：Not Found。
package/pkg-generic.mk:167: recipe for target '.../.stamp_downloaded' failed
```

**原因**：`Toolchain` 那一项选成了官方预置的 ARM 工具链（`toolchain-external-arm-arm`），Buildroot 二话不说就去下载，结果：

1. `developer.arm.com` 的证书链在旧发行版上校验不过（根证书过期或者干脆没有）；
2. Buildroot 的备用镜像 `sources.buildroot.net` 上，这个文件也早没了。

**处理**（三选一，推荐第一种）：

1. **改用本地已安装工具链**（本项目做法）：见 3.3 D 节，`Toolchain` → `Custom external toolchain`，`Toolchain origin` → `Pre-installed toolchain`，填路径/前缀/版本。完全不联网。
2. 手动下载 `gcc-arm-9.2-2019.12-x86_64-arm-none-linux-gnueabihf.tar.xz`，放到 `dl/toolchain-external-arm-arm/` 下，重跑 `make`。
3. 临时给 wget 加 `--no-check-certificate`（改 `Config.in` 里的 `BR2_WGET` 默认值）—— 不推荐，属于降低安全校验的临时手段。

**结论**：本机已经有工具链了，就别让 Buildroot 去下载，一次都别。

### 7.2 找不到 `Download toolchain automatically`

**现象**：`Toolchain` 菜单里只有 `Toolchain to be downloaded and installed` 和 `Pre-installed toolchain` 两项，找不到教程里说的 `Download toolchain automatically`。

**原因**：这选项藏在 `toolchain-external-custom` 分支的 `Toolchain origin` 里，而且不同版本、不同教程叫法还不统一：

- Buildroot 2020.02 的写法是 **`Pre-installed toolchain`** 和 `Toolchain to be downloaded and installed`；
- 某些旧教程写的是 `Custom toolchain` 加 `Download toolchain automatically`。

**处理**：`Toolchain` 选 `Custom external toolchain` → `Toolchain origin` 选 **`Pre-installed toolchain`**，此时会出现 `Toolchain path` / `Toolchain prefix` 输入框。

**结论**：菜单名对不上，先翻当前版本 Buildroot 的 `Config.in`，别硬套教程——写教程的人，用的不是你这个版本。

### 7.3 U-Boot 编译报 `Your GCC is older than 6.0`

**现象**：别的包都好好的，编到 U-Boot 这一步突然翻脸：

```
*** Your GCC is older than 6.0 and is not supported
arch/arm/config.mk:66: recipe for target 'checkgcc6' failed
package/pkg-generic.mk:266: recipe for target '.../uboot-2018.07/.stamp_built' failed
```

**原因**：Buildroot 2020.02 里的 U-Boot 包是 **2018.07**，其 `arch/arm/config.mk` 里有 `checkgcc6` 目标，强制要求 GCC ≥ 6.0；本项目工具链是 **4.9.4**。

**处理**（三选一）：

1. **关闭 Buildroot 的 U-Boot**（本项目做法，推荐）：2017.03 的 U-Boot 咱自己已经移植好了，`Bootloaders` 里把 `U-Boot` 一取消就行，还省得再重编一遍。
2. 换 GCC 6.x/7.x 工具链，并**同时重编内核**（否则 7.8 的坑）。
3. 改 U-Boot 的 `checkgcc6` 规则去掉版本检查 —— 不推荐，编译出来的 U-Boot 未经验证。

**结论**：自己维护的组件，就别让 Buildroot 再管一遍，能关就关。

### 7.4 编译尾部报找不到 zImage

**现象**：日志里 `Finalizing target directory`、`Copying overlay board/my_imx6ull/rootfs-overlay`、`rootfs.tar` 都成功了，最后却：

```
(board/freescale/common/imx/post-image.sh) Custom scripts to run after creating filesystem images
```

脚本里 `cp .../zImage` 失败，`make` 以 Error 退出。

**原因**：`BR2_ROOTFS_POST_IMAGE_SCRIPT` 默认指向 NXP 的 `post-image.sh`，它的职责是把 zImage、dtb、rootfs 打包成一张完整的 SD 卡镜像。但内核编译已经关闭，`output/images/` 里没有 zImage。

**处理**：`System configuration` → 清空 `Custom scripts to run after creating filesystem images`（或直接删掉 `BR2_ROOTFS_POST_IMAGE_SCRIPT` 那一行），同时取消 `genimage`、`dosfstools`、`mtools`。重新 `make`。

**结论**：**"rootfs 编出来了"和"整包打好了"是两码事**。本项目只要 `rootfs.tar` 和 `rootfs.ext2`，整包那一步失败，天塌不下来。

### 7.5 overlay 路径该按哪套来

**现象**：教程给的 `board/freescale/imx6ull_myboard/overlay/etc/profile` 与参考仓库的 `board/my_imx6ull/rootfs-overlay/etc/profile.d/ps1.sh` 不一致。

**原因**：两家都没错，纯粹是起名习惯不同：

- `board/freescale/<board>/overlay/` 是 Buildroot 官方示例的规范写法；
- `board/my_imx6ull/rootfs-overlay/` 是仓库作者自己定的路径。**Buildroot 不限制 overlay 目录叫什么、放哪儿**，只要 menuconfig 里填的跟实际对得上。

**处理**：跟随参考仓库（`board/my_imx6ull/rootfs-overlay`），并采用 `profile.d/ps1.sh` 的追加方式，避免覆盖默认 `/etc/profile`。

**结论**：路径随你定，但"menuconfig 里填的"和"硬盘上真有的"必须一个字不差。复制粘贴的时候，这里最容易翻车。

### 7.6 `/dev` management 选错

**现象**：系统起来后 `/dev` 下设备节点很少或没有，串口/块设备找不到。

**原因**：`/dev management` 选成了 `Dynamic using devtmpfs only`，没带 mdev。纯 devtmpfs 只能提供内核自动建的那部分节点，热插拔和权限管理一概没有。

**处理**：改为 `Dynamic using devtmpfs + mdev`（对应 `BR2_ROOTFS_DEVICE_CREATION_DYNAMIC_MDEV=y`）。

**结论**：BusyBox init 的标准搭配就是 devtmpfs + mdev。

### 7.7 libgpiod 无法启用

**现象**：搜索 `libgpiod` 有结果，但选不上（灰的）。

**原因**：`BR2_PACKAGE_LIBGPIOD` 依赖 `BR2_TOOLCHAIN_HEADERS_AT_LEAST_4_8`，本工具链头文件是 4.6。

**处理**：改用内核 GPIO sysfs 接口验证驱动：

```bash
echo 25 > /sys/class/gpio/export
ls /sys/class/gpio/gpio25/
cat /sys/class/gpio/gpio25/value
```

**结论**：工具链头文件的版本，直接决定了一部分包能不能用。这不算"配错了"，是环境就这条件。

### 7.8 内核与 rootfs 工具链不一致

**现象**：内核能启动，跑到初始化阶段，屏幕一黑，只剩下一行：

```
Kernel panic - not syncing: No working init found.
```

**原因**：rootfs 里的 `/sbin/init`（BusyBox）或者 glibc，是另一套工具链编出来的。ABI 和动态库版本跟内核的预期对不上，`execve` 一调就失败。

**处理**：确认内核、U-Boot、rootfs 三者使用同一套 `gcc-linaro-*`；如果之前用 6.2.1 编过内核，就用同一路径的 6.2.1 重编内核，或把 rootfs 改回 4.9.4。

**结论**：工具链一致，比"版本越新越好"重要得多。

### 7.9 NFS 挂载到空目录

**现象**：内核日志显示 NFS 挂载成功，但接着找不到 init 或进入 panic。

**原因**：`/etc/exports` 导出的是 `/home/edison/linux/nfs`（父目录），可 rootfs 解压在 `.../nfs/my_rootfs`；`nfsroot` 又只写到 `nfs`，于是板子挂上的其实是个空目录。

**处理**：`/etc/exports` 直接写 `my_rootfs` 的完整路径（本项目做法），或把 `nfsroot` 补全到 `my_rootfs`。改完执行：

```bash
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server
```

**结论**：`exports` 的路径、`nfsroot` 的路径、实际解压的目录，三者必须是同一个。

### 7.10 U-Boot 没有 `ifconfig`

**现象**：

```
=> ifconfig eth2 192.168.1.6 netmask 255.255.255.0 up
Unknown command 'ifconfig' - try 'help'
```

**原因**：`ifconfig` 是 Linux 用户态的命令，U-Boot 里没有（除非特意启用了老式 `CONFIG_CMD_NET` 的 `ifconfig` 别名，标准配置里没这项）。

**处理**：用环境变量：

```bash
setenv ipaddr 192.168.1.6
setenv serverip 192.168.1.7
setenv netmask 255.255.255.0
setenv gatewayip 192.168.1.1
ping 192.168.1.7
```

**结论**：U-Boot 的网络是"变量 + 命令"的路子，敲 `tftp`、`ping` 的时候自己套用。

### 7.11 eMMC 挂载失败：`invalid superblock checksum`

**现象**：

```
EXT4-fs (mmcblk1p2): VFS: Found ext4 filesystem with invalid superblock checksum.
EXT2-fs (mmcblk1p2): error: couldn't mount because of unsupported optional features (244)
```

要是用烧录工具点"更新内核/设备树"，download 会显示成功，`ext4write` 却悄悄失败。

**原因**：主机上的 `e2fsprogs` 较新，`mke2fs` 默认开启 `metadata_csum` 特性；4.9.88 内核的 ext4 驱动和 U-Boot 2017.03 的 `ext4write` 都不支持该特性。

**处理**：`Filesystem images` → e2fsprogs/`additional mke2fs options` 改为：

```
-O ^64bit,^metadata_csum
```

重新 `make`，用新的 `rootfs.ext2` 重新 `dd`。

**结论**："镜像生成成功"不等于"板子挂得上"。老内核配新 e2fsprogs，是一对经典冤家。

### 7.12 SSH 密码错误

**现象**：`ssh root@192.168.1.6`，`root`、`123456` 挨个试了一遍，全是密码错误；可串口那边，同样的账号密码一登就进。

**原因（常见）**：`System configuration` 里填了 `Root password`，却没勾 `Enable root login with password`；或者配置压根没重新生效。这样一来，系统里 root 实际是**空密码**，而 SSH 默认拒绝空密码登录。

**处理**：

1. 板端串口最快修：

```bash
passwd root
# New password: 123456
# Retype password: 123456
```

2. 根治：回 `menuconfig`，勾选 `Enable root login with password` 并填密码，`make` 后覆盖 NFS 目录。

3. 排查是不是空密码：

```bash
cat /etc/shadow | grep root
# root::...   ← 冒号之间为空，就是空密码
```

**结论**：串口能进、SSH 不能进，先怀疑"密码根本没设上"。

### 7.13 dl 缺包导致卡住

**现象**：编译停在 `Downloading` 很久，或某包下载失败。

**原因**：仓库自带的 `rootfs/sources/dl/` 里，确实没有 `dropbear` 和 `nano`——韦东山 SDK 的 Buildroot 用的是 openssh，压根不编这两个包。

**处理**：按 `package/*/*.mk` 里的 `_SITE` 手动下载，放入 `$DL_DIR/<pkg>/`（即 `rootfs/sources/dl/<pkg>/`）：

```bash
cd $BUILDROOT_DIR
grep -E 'DROPBEAR_VERSION|DROPBEAR_SITE' package/dropbear/dropbear.mk
grep -E 'NANO_VERSION|NANO_SITE' package/nano/nano.mk
```

**结论**：`dl/` 就是个纯缓存，随时能手工往里塞文件。文件名（含版本号）对得上，它照样认。

### 7.14 网卡名从 eth2 变成 eth0

**现象**：U-Boot 里写 `eth2` 的启动参数，在新 rootfs 下不通；`ifconfig -a` 只有 `eth0`。

**原因**：原厂 rootfs 带着 udev 的持久化命名规则，按 MAC/PCI 排序把网卡改名叫 `eth2`；本项目用 BusyBox + mdev，没这套规矩，网卡就按内核默认顺序叫 `eth0`、`eth1`。

**处理**：`bootargs` 里的 `ip=...:eth0:off` 和 `nfsroot` 相关的网卡名统一改成 `eth0`。

**结论**：换了 rootfs，网卡名真有可能变。这跟驱动没半毛钱关系，别往那儿查。

---

## 8. 复现清单

照着顺序往下打勾，就能把整套系统复现一遍。

- [ ] 确认工具链路径、版本、内核头文件版本（2.2）
- [ ] 内核 defconfig 补齐 DEVTMPFS / EXT4 / FTRACE（2.3）
- [ ] 准备 `dl/` 缓存（2.4）
- [ ] 解压 Buildroot 2020.02.12，`make imx6ulevk_defconfig`（3.1~3.2）
- [ ] 改工具链为 External + Pre-installed（3.3 D）
- [ ] 关闭 Kernel / U-Boot / post-image / genimage（3.3 B、C、H）
- [ ] System configuration：hostname、密码、mdev、overlay 路径（3.3 E）
- [ ] 勾选软件包（3.3 F）
- [ ] 镜像 ext4 + `-O ^64bit,^metadata_csum`（3.3 G）
- [ ] 建 overlay 目录与 `ps1.sh`（3.4）
- [ ] `make savedefconfig` + `make show-targets` 核对（3.5）
- [ ] `make -j$(nproc)`，确认 `rootfs.tar` / `rootfs.ext2`（3.6）
- [ ] 解压到 NFS 目录、配 exports、`exportfs -ra`（4.2）
- [ ] U-Boot 设 bootargs、tftp、bootz，确认进入 shell（4.3~4.4）
- [ ] eMMC 分区确认、U-Boot 头文件 4 处修改并重编（5.1~5.2）
- [ ] `dd` 写 p2、`/boot` 放 zImage + dtb（5.3）
- [ ] 拔 SD 卡、eMMC 启动验证（5.4）
- [ ] 上板测 ps / dev / eMMC 挂载 / 工具 / SSH（第 6 章）

---

## 9. 附录

### A. 常用命令速查

```bash
# Buildroot
make menuconfig                  # 配置（/ 搜索配置项）
make imx6ulevk_defconfig         # 官方起点
make my_imx6ull_defconfig        # 自己的配置
make savedefconfig BR2_DEFCONFIG=configs/my_imx6ull_defconfig
make show-targets                # 看会编哪些包
make -j$(nproc)                  # 编译
make linux-rebuild               # 只重编某个包（示例）
make clean                       # 清 output/（保留 dl/）
export BR2_DL_DIR=<仓库>/rootfs/sources/dl   # 使用仓库内缓存

# 查看配置项
grep -n "ROOTFS_OVERLAY" $BUILDROOT_DIR/.config
grep -rn "config BR2_PACKAGE_DROPBEAR" $BUILDROOT_DIR/package/

# NFS
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server
showmount -e localhost

# 板端
mount | grep nfs
ps | grep dropbear
passwd root
cat /etc/shadow | grep root
```

### B. 与本仓库文件的对应关系

| 文件 | 内容 |
|------|------|
| `rootfs/configs/my_imx6ull_defconfig` | 本流程最终配置（工具链路径需按你的机器修改） |
| `rootfs/overlay/etc/profile.d/ps1.sh` | PS1 定制脚本，复制到 `board/my_imx6ull/rootfs-overlay/` |
| `rootfs/docs/rootfs_build_guide.md` | 本文 |
| `rootfs/sources/` | Buildroot 源码包（`buildroot-2020.02.12.tar.gz`）与 `dl/` 缓存，说明见其 `README.md` |

### C. 关键结论

1. **工具链三件套得同源**（U-Boot、Kernel、rootfs），不然 init 起不来。
2. **Buildroot 只管用户态**：内核、U-Boot 自己维护，能关就关。
3. **rootfs 编出来了 ≠ 整包成功了**：post-image 那步失败，不影响产物。
4. **老内核配新 e2fsprogs**：`metadata_csum` 必须关。
5. **先 NFS 后 eMMC**：调试效率差得不是一点半点。
6. **配置错误会以"启动失败"的形式出现**，排查就按这个顺序来：内核配置、工具链一致性、rootfs 内容、U-Boot 参数。

> 题外话：这套流程头一回走，多半要在第 7 章里挨个儿撞一遍。撞完回头看，每一步其实都合情合理——rootfs 这活儿没什么高深理论，拼的是耐心，是对报错的那点儿敏感，还有一遍遍重来的劲头。别怕返工，这套流程就是靠一遍遍重来喂熟的。
