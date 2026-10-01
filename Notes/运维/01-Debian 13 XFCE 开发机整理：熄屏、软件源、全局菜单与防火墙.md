---
title: "Debian 13 XFCE 开发机整理：熄屏、软件源、全局菜单与防火墙"
date: 2026-10-01
draft: false
description: "机器是一台日常开发本：Debian GNU/Linux 13 (trixie) + XFCE，硬件是 HP ProBook，双 NVMe，本机还跑着 Docker（MySQL / Redis / Portainer 等）。"
categories: ["运维"]
tags: ["运维"]
---
## 先说场景

机器是一台日常开发本：**Debian GNU/Linux 13 (trixie) + XFCE**，硬件是 HP ProBook，双 NVMe，本机还跑着 Docker（MySQL / Redis / Portainer 等）。

一次顺手整理，把几件容易踩坑的事一起做完：

1. 关掉自动熄屏 / 挂起（插电、电池都关）
2. 看清「要不要更新」，以及为什么 `apt` 会甩出一千多个可升级包
3. 注释掉 `sid` / `bullseye` 混源，只做安全范围内的升级
4. 弄清 XApp / AppMenu，装上全局菜单并让它对齐、能导出菜单
5. 看资源占用，给开发机开防火墙（默认不让别的设备访问）

下面按实际操作顺序写，命令可直接复用。

## 1. XFCE：关掉自动熄屏和挂起

### 电源管理 GUI

打开：

```bash
xfce4-power-manager-settings
```

重点看两个标签，且 **On battery / Plugged in 都要改**：

- **System**：`When inactive for` → **Never**
- **Display**：`Put to sleep after` / `Switch off after` → **Never**  
  更干净的做法：直接关掉 **Display power management** 总开关

`Devices` 标签只显示电池信息，没有熄屏相关选项。

### 屏保

本机没有 `xfce4-screensaver`（`command not found` 很正常），可以忽略。真正黑屏多半来自电源管理或 DPMS。

### DPMS（硬件级熄屏）

终端立刻关掉：

```bash
xset s off
xset -dpms
xset s noblank
```

想开机也生效：在 **设置 → 会话和启动 → 应用程序自动启动** 加一条：

```bash
xset s off -dpms s noblank
```

也可用 xfconf 关掉电源管理侧的 DPMS：

```bash
xfconf-query -c xfce4-power-manager -p /xfce4-power-manager/dpms-enabled -s false
xfconf-query -c xfce4-power-manager -p /xfce4-power-manager/blank-on-ac -s 0
xfconf-query -c xfce4-power-manager -p /xfce4-power-manager/blank-on-battery -s 0
```

## 2. 系统要不要更新：先看源，再看数量

### 表面现象

```bash
apt list --upgradable
```

一度出现 **一千多个** 可升级包，内核候选版本甚至从 `6.12` 跳到 `7.x`。这不是「trixie 落后很多」，而是软件源混了。

### 实际系统状态（整理前）

| 项             | 状态                                              |
| ------------- | ----------------------------------------------- |
| 发行版           | Debian 13.6 (trixie)                            |
| 内核            | `6.12.107+deb13-amd64`                          |
| 重启需求          | 无                                               |
| 真正该升的（排除 sid） | 主要是 Chrome / Firefox / Thunderbird / VS Code 一类 |

### 问题根源：`sources.list` 混进了 sid 和 bullseye

典型危险行：

```text
deb http://ftp.de.debian.org/debian sid main
deb http://deb.debian.org/debian bullseye main non-free contrib
deb http://deb.debian.org/debian bullseye-updates main non-free contrib
```

`sid` 与 `trixie` 同为优先级 500 时，`apt upgrade` 会大量拉 unstable，等于把稳定桌面往滚动版拖。

### 处理：注释掉混源

先备份，再注释：

```bash
sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak.$(date +%Y%m%d%H%M%S)
sudo sed -i '/ftp\.de\.debian\.org\/debian sid/s/^/# /' /etc/apt/sources.list
sudo sed -i -E '/deb\.debian\.org\/debian bullseye/s/^([^#])/# \1/' /etc/apt/sources.list
sudo apt update
```

干净后应只剩：

- `trixie` / `trixie-updates` / `trixie-backports`（镜像）
- `trixie-security`
- 以及 Chrome / Docker / VS Code 等第三方源

此时可升级包会从一千多个掉到几个。

### 安全升级（不要 full-upgrade 乱扫）

```bash
sudo apt upgrade -y
```

当时升的是：

- `firefox-esr` / 语言包 → 安全更新
- `thunderbird` → 安全更新
- `google-chrome-stable`
- `code`（VS Code）

**不要**对着带 `/unstable` 的那一千个包直接 `full-upgrade`。

## 3. XFCE 全局菜单：AppMenu，不是 XApp Menu

### 容易混淆的名字

| 名字                 | 实际是什么                                   |
| ------------------ | --------------------------------------- |
| XApp               | Linux Mint 的跨桌面组件库（托盘 StatusNotifier 等） |
| `xapp-sn-watcher`  | 托盘相关服务，**不是**开始菜单                       |
| **AppMenu Plugin** | 全局菜单：当前窗口的 File / Edit 显示在面板上           |

Debian 上对应的包：

```bash
sudo apt install xfce4-appmenu-plugin appmenu-gtk3-module
```

会顺带装上 `appmenu-registrar`。装完后：

1. 面板右键 → **添加新项目** → **AppMenu Plugin**
2. **注销再登录**（环境变量要进图形会话）

### 只显示应用名、没有 File/Edit？

常见两个原因：

**① 会话没加载 `appmenu-gtk-module`**

检查：

```bash
echo "GTK_MODULES=$GTK_MODULES"
# 空的话菜单导不出来
```

写入 `~/.xsessionrc`（XFCE 会读）：

```bash
if [ -z "$GTK_MODULES" ]; then
  GTK_MODULES="appmenu-gtk-module"
else
  GTK_MODULES="$GTK_MODULES:appmenu-gtk-module"
fi
export GTK_MODULES
export UBUNTU_MENUPROXY=1
```

也可：

```bash
mkdir -p ~/.config/environment.d
cat > ~/.config/environment.d/appmenu.conf <<'EOF'
GTK_MODULES=appmenu-gtk-module
UBUNTU_MENUPROXY=1
EOF
```

官方脚本还会写 xsettings：

```bash
/usr/bin/xfce4-appmenu-plugin-enable
```

然后**注销重登**，用 **Thunar / Mousepad** 这类 GTK 应用验证。  
点桌面时显示 `Xfdesktop`、只有名字没有菜单，是正常的——桌面本身没有传统菜单栏。  
**Cursor / Chrome / VS Code** 等 Electron 应用通常也不支持全局菜单。

**② 菜单「居中」而不是靠左**

AppMenu 若开启 **Expand plugin on panel**，会占满面板中间空白；短标题（如 `Cursor`）会看起来像漂在中间。

关掉扩展（假设 AppMenu 是 `plugin-2`，用 `xfconf-query -c xfce4-panel -l -v | grep appmenu` 确认 ID）：

```bash
xfconf-query -c xfce4-panel -p /plugins/plugin-2/plugins/plugin-2/expand -n -t bool -s false
xfconf-query -c xfce4-panel -p /plugins/plugin-2/expand -n -t bool -s false
xfce4-panel -r
```

面板上保留一个 **Expand 的分隔符** 在 AppMenu 后面，托盘和时钟仍会靠右。

也可右键 AppMenu → 属性，取消勾选 **Expand plugin on panel**。  
注意：插件启动往往会把 expand 写回 `true`，只改 GUI 不够。完整原因与登录后强制关掉的脚本见：[XFCE AppMenu 居中与 Expand 被写回](./XFCE%20AppMenu%20居中与%20Expand%20被写回.md)。

## 4. 资源占用一眼看懂

整理防火墙前顺手摸了一下（开机约 1 小时时）：

| 资源 | 概况 |
|---|---|
| CPU | i5-1240P，16 逻辑核；负载 ~2.1，空闲约 80% |
| 内存 | 15 GiB，已用 ~9.6 GiB，可用 ~5.7 GiB；Swap 未用 |
| 磁盘 | `/` ~8%，`/home` ~20% |
| 温度 | CPU 包温约 62°C |
| 主要占用 | Firefox、Cursor、本机/容器相关服务、clash-verge |

常用命令：

```bash
uptime
free -h
df -hT
ps aux --sort=-%mem | head
ps aux --sort=-%cpu | head
sensors   # 需 lm-sensors
```

## 5. 防火墙：开发机默认不对外开放

### 整理前的真实状态

| 组件 | 状态 |
|---|---|
| UFW | **未安装**（仅有 `/etc/ufw` 残留目录） |
| firewalld | 无 |
| nftables 服务 | 装了但 disabled |
| **INPUT 策略** | **ACCEPT（入站全放行）** |

更麻烦的是 Docker 把端口绑在 `0.0.0.0` 上，例如：

- `3306` MySQL  
- `6379` Redis  
- `9000/9001`、`9874` Portainer 等  

局域网里别的设备理论上能直接连进来。开发本一般不需要这个。

### 安装并启用 UFW

```bash
sudo apt install -y ufw

sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw default deny routed

# 本机不跑对外 SSH，就不放行 22
sudo ufw --force enable
sudo ufw status verbose
```

期望结果：

```text
Status: active
Default: deny (incoming), allow (outgoing), deny (routed)
```

### 关键：UFW 管不住 Docker 发布端口

外部访问 Docker 映射端口走的是 **FORWARD + DNAT**，不是简单的 INPUT，所以还要在 `DOCKER-USER` 里拦一层。

追加到 `/etc/ufw/after.rules`（文件末尾）：

```text
# -*- Begin Docker protection (dev laptop) -*-
*filter
:DOCKER-USER - [0:0]
-A DOCKER-USER -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN
-A DOCKER-USER -i docker0 -j RETURN
-A DOCKER-USER -i lo -j RETURN
-A DOCKER-USER -s 172.16.0.0/12 -j RETURN
-A DOCKER-USER -j DROP
COMMIT
# -*- End Docker protection -*-
```

然后：

```bash
sudo ufw reload
sudo iptables -L DOCKER-USER -n -v
```

效果：

- 本机 `127.0.0.1:3306` / `:6379` → 照常  
- 其他设备访问你的局域网 IP + 这些端口 → 被丢弃  

### 常用维护

```bash
sudo ufw status verbose
sudo ufw allow 8080/tcp          # 临时给某个服务开洞
sudo ufw delete allow 8080/tcp
sudo ufw disable                 # 临时关掉
sudo ufw enable
```

更稳妥的长期做法，是把 compose / `docker run` 的端口改成只绑本机，例如 `-p 127.0.0.1:3306:3306`，防火墙只是第二道闸。
