# rootfs/sources —— Buildroot 源码与下载缓存

本目录存放构建根文件系统所需的**全部离线资料**：Buildroot 源码包与软件包下载缓存。

原先位于 `E:\韦东山IMX6ULL PRO开发板资料\Buildroot源码\`，现已完整迁移到此处，目录结构与内部相对路径保持不变。

---

## 一、目录现状

```
rootfs/sources/                          # 约 2.0 GB
├── README.md                            # 本文件
├── buildroot-2020.02.12.tar.gz          # Buildroot 2020.02.12 源码包（6,826,528 字节，约 6.5 MB，未解压）
└── dl/                                  # Buildroot 软件包下载缓存（418 个包目录，906 个文件，约 2.0 GB）
    ├── .git/                            # SDK 自带的 git 元数据（韦东山用于更新缓存），Buildroot 不读取
    ├── busybox/busybox-1.31.1.tar.bz2
    ├── openssh/openssh-8.1p1.tar.gz
    ├── acl/acl-2.2.53.tar.gz
    └── ...                              # 其余 400+ 个包
```

## 二、分别是什么、干什么用

### 1. `buildroot-2020.02.12.tar.gz` —— Buildroot 源码

| 项 | 内容 |
|----|------|
| 是什么 | Buildroot 官方 2020.02.12 LTS 发布包的原始压缩包 |
| 包内结构 | 顶层目录 `buildroot-2020.02.12/`，共 14,963 个条目 |
| 作用 | **唯一的源码来源**：`make menuconfig` / `make` 都在解压后的这棵树上执行，`configs/`、`package/`、`toolchain/`、`fs/` 全部来自这里 |
| 为什么保留压缩包 | 6.5 MB 单文件，便于传输和校验；解压后的工作树（上万个文件）可由它随时重建 |

### 2. `dl/` —— 软件包下载缓存

| 项 | 内容 |
|----|------|
| 是什么 | Buildroot 的 `BR2_DL_DIR` 目录；每个子目录对应一个软件包，里面是该包对应版本的源码压缩包（`.tar.gz` / `.tar.bz2` / `.tar.xz`） |
| 规模 | 418 个包目录、906 个文件、416 个源码包、约 2.0 GB |
| 作用 | Buildroot 编译前先在这里查找，**命中就不联网下载**；决定一次编译是 5 分钟还是 1 小时，也避免国内网络导致的下载失败 |
| 已知缺口 | **没有 `dropbear`、`nano`**（韦东山 SDK 的 Buildroot 用 openssh，不编这两个包）。本项目配置选了它们，首次编译会去下载；离线环境请按第 5 节补入 |

## 三、怎么用（在 Ubuntu 构建机上）

### 方案 A：`BR2_DL_DIR` 指向现有缓存（推荐，不改目录结构）

```bash
cd <仓库>/rootfs/sources
tar -xzf buildroot-2020.02.12.tar.gz          # 得到 buildroot-2020.02.12/
export BR2_DL_DIR=$PWD/dl                      # 让 Buildroot 使用这里的缓存
cd buildroot-2020.02.12

# 放入本项目配置与 overlay
cp ../../configs/my_imx6ull_defconfig configs/
mkdir -p board/my_imx6ull/rootfs-overlay
cp -r ../../overlay/* board/my_imx6ull/rootfs-overlay/

make my_imx6ull_defconfig
make -j$(nproc)
```

`BR2_DL_DIR` 的三种等价写法：

```bash
export BR2_DL_DIR=/path/to/rootfs/sources/dl   # 环境变量（本次会话有效）
make BR2_DL_DIR=/path/to/rootfs/sources/dl     # 命令行参数（单次有效）
# 或写进 .config：Build options → Download dir
```

### 方案 B：软链接成 Buildroot 默认的 `dl`

Buildroot 默认 `DL_DIR = $(TOPDIR)/dl`，把 `dl` 链过去即可，后续 `make` 不用再带参数：

```bash
cd <仓库>/rootfs/sources
tar -xzf buildroot-2020.02.12.tar.gz
ln -s ../dl buildroot-2020.02.12/dl
```

### 注意事项

- **必须在 Linux 内解压**：Buildroot 依赖大小写敏感、符号链接和文件权限；在 Windows 解压再拷进 Linux 会丢失权限、软链接退化成普通文件。
- 通过 VMware 共享目录访问时，建议先 `cp` 到 Linux 本地磁盘再解压，避免共享文件系统的权限和性能问题。
- `dl/.git` 只是 SDK 的更新元数据，保留原样即可，不影响 Buildroot 使用。

## 四、校验记录（迁移后实测）

| 项目 | 结果 |
|------|------|
| `tar -tzf buildroot-2020.02.12.tar.gz` | 14,963 个条目，顶层 `buildroot-2020.02.12/`，可正常读取 |
| tar.gz 大小 | 6,826,528 字节 |
| `dl/` 包目录数 / 文件数 | 418 / 906 |
| `dl/` 体积 | 约 2,046.8 MB |
| `dl/` 源码包数量 | 416 个 `.tar.gz` / `.tar.bz2` / `.tar.xz` |
| 样本包可读性 | `busybox-1.31.1.tar.bz2`、`openssh-8.1p1.tar.gz`、`acl-2.2.53.tar.gz` 均可 `tar -tf` 正常列出 |
| 已知缺口 | `dropbear`、`nano` |

## 五、补充缺失的包

以 `dropbear` 为例，先查出该 Buildroot 版本需要的文件名，再放进对应目录：

```bash
cd <仓库>/rootfs/sources/buildroot-2020.02.12
grep -E 'DROPBEAR_VERSION|DROPBEAR_SITE' package/dropbear/dropbear.mk
# 例如 DROPBEAR_VERSION = 2019.78、DROPBEAR_SITE = https://matt.ucc.asn.au/dropbear/releases

# 下载后放入：
#   <仓库>/rootfs/sources/dl/dropbear/dropbear-2019.78.tar.bz2
```

`nano` 同理：

```bash
grep -E 'NANO_VERSION|NANO_SITE' package/nano/nano.mk
#   下载后放入 <仓库>/rootfs/sources/dl/nano/nano-<版本>.tar.xz
```

文件名必须与 `_VERSION` 完全一致（含版本号与后缀），Buildroot 才能命中缓存。

## 六、迁移记录

| 时间 | 内容 |
|------|------|
| 2026-10-30 | 从 `E:\韦东山IMX6ULL PRO开发板资料\Buildroot源码\` 整体迁移：`dl/` → `rootfs/sources/dl/`；`buildroot-2020.02.12.tar.gz` → `rootfs/sources/`。文件数量、体积、内部结构均保持原样 |
