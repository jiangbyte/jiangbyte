---
date: 2026-10-07
description: "主机 dev（Debian 13 + GNOME X11）安装 ugeetablet 4.3 后画笔失效：内核争用、uinput 权限，以及随后 HVUG STYLUS 变成 floating 导致有压感无位移。结论与配置均来自本机命令与日志。"
categories: ["运维"]
tags: ["运维", "Debian", "数位板", "ugee", "XP-Pen"]
---

## 环境

采集时间：2026-10-07。主机名 `dev`。

| 项 | 值 | 依据 |
| --- | --- | --- |
| 系统 | Debian GNU/Linux 13 (trixie)，`DEBIAN_VERSION_FULL=13.7` | `/etc/os-release` |
| 内核 | `6.12.111+deb13-amd64` | `uname -r` |
| 机型 | HP ProBook 450 15.6 inch G9 Notebook PC | `/sys/class/dmi/id/product_name` |
| 会话 | `XDG_SESSION_TYPE=x11`，`DISPLAY=:0`，`XDG_CURRENT_DESKTOP=GNOME`，`GDMSESSION=gnome-xorg` | 环境变量 |
| 数位板 USB | `Bus 003 Device 022: ID 28bd:0905 XP-Pen 10 inch PenTablet` | `lsusb` |
| sysfs | `/sys/bus/usb/devices/3-4`，`manufacturer=UGTABLET`，`product=10 inch PenTablet` | sysfs |
| 驱动包 | `ugeetablet 4.3`（`Maintainer: tech@xp-pen.com`） | `dpkg -l` / `apt-cache show` |
| 安装包文件 | `/home/charlie/Downloads/ugeeTablet4.3.5-241031.deb`（约 22MB，mtime 2026-10-07 19:36） | `ls` |
| 驱动路径 | `/usr/lib/ugeeTablet/{ugeeTabletDriver,ugeeTablet,ugeeTabletDriver.sh}` | 文件系统 |
| 驱动配置目录 | `~/.config/Hanvon Ugee/ugee.conf`（仅 LocalSocket 时间戳） | 文件系统 |
| 相关已装包 | `xserver-xorg-input-wacom 1.2.3-1`，`libwacom9`，`libwacom-common` | `dpkg -l` |
| 其它输入设备（配置未改） | 内置键盘 `AT Translated Set 2 keyboard`；`Newmen ... 2.4G Keyboard Mouse`；`SEMICO USB Gaming Keyboard`；触控板 `SYNA30E5:00 06CB:CEAC` | `/sys/class/input/*/name` |

驱动 journal（2026-10-07 19:39:11）中的设备标识：

```text
QString sTitleName: "绘影 EX08"
QString sTitleName: BPU1002
find the xml Config: "BPU1002"
MyDeviceCallBack VID_28BD&PID_0905&MI_02_LINUX_0 1
```

现象与目标：

1. 安装 `ugeetablet`（安装包名 ugeeTablet / PenTable）后画笔不可用。  
2. 仅走内核输入栈时压感不可用。  
3. 采用官方驱动独占该板；内核对该 VID:PID 的接管需去掉，且不影响其它键鼠与触控板。  
4. 修复需开机持久化。  
5. 第一阶段修复后出现第二现象：有压感，但笔位置（光标）不动；根因为 `HVUG STYLUS stylus` 处于 floating，已 reattach 并固化。

---

## 故障现象（本机观测）

### 1. 官方驱动与内核争用同一设备

驱动启动后 journal：

```text
Oct 07 19:37:32 ... Segmentation fault      ... ugeeTabletDriver
Oct 07 19:37:36 ... Segmentation fault      ... ugeeTabletDriver
Oct 07 19:37:36 ... QLocalServer::listen: Address in use
```

同一时段 `~/.local/share/xorg/Xorg.0.log` 先出现笔设备，随后被移除：

```text
(--) wacom: UGTABLET 10 inch PenTablet Pen stylus: maxX=50800 maxY=31750 maxZ=8191 ...
(II) XINPUT: Adding extended input device "UGTABLET 10 inch PenTablet Pen stylus" (type: STYLUS, ...)
(II) XINPUT: Adding extended input device "UGTABLET 10 inch PenTablet Pad pad" (type: PAD, ...)
...
(EE) UGTABLET 10 inch PenTablet Pen stylus: Error reading wacom device : No such device
(II) config/udev: removing device UGTABLET 10 inch PenTablet Pen stylus
(EE) UGTABLET 10 inch PenTablet Pad pad: Error reading wacom device : No such device
```

因此：系统曾出现过带 `maxZ=8191` 的 `UGTABLET ... Pen stylus` 节点；该节点在官方驱动介入过程中被 remove。未在绘图软件内对内核该节点做压感功能实测。

### 2. 冲突高峰：仅剩 Mouse

冲突期间输入节点曾只剩：

```text
UGTABLET 10 inch PenTablet Mouse
```

capabilities：`abs=0`（无绝对坐标/压感位），仅为相对鼠标。HID 绑定为 `uclogic`（`lsmod` 有 `hid_uclogic`，`udevadm` 为 `DRIVER=uclogic`）。

`ugeeTabletDriver` 仍打开 `/dev/bus/usb/003/022`。journal 有 `PenKey 1 down/up`，同时有：

```text
Uinput Init , Presser : 8191
ParseData failed.
```

### 3. `/dev/uinput` 权限阻止虚拟笔创建

解绑内核 HID 后，驱动日志仍有 `Uinput Init`，但 `/sys/class/input` 无 `HVUG*`。当时：

```text
crw------- 1 root root 10, 223 ... /dev/uinput
```

账户 `charlie` 无法写入。将 uinput 改为可写并重启驱动后，虚拟设备出现（见「修复后状态」）。`charlie` 随后加入 `input` 组。

### 4. 包装未提供登录自启桌面文件

```text
dpkg -L ugeetablet | grep autostart
# /etc/xdg/autostart          ← 仅有目录
# 无 ugeetablet.desktop
```

桌面入口仅存在于 `/usr/share/applications/ugeetablet.desktop`。不另加 autostart 时，登录后驱动不会自动启动。

### 5. 排查过程中的其它本机事实

- `/sys/module/usbhid/parameters/quirks` 权限为 `-r--r--r--`，运行中写入得到 `Permission denied`；需 modprobe 配置（并打进 initramfs）或对接口 `unbind`。  
- `pkill -f '/usr/lib/ugeeTablet/'` 会匹配到含该路径的当前 shell 命令行，曾误杀排查进程。  
- 辅助脚本曾误执行会覆盖 `/dev/uinput` 的操作，节点一度变成普通空文件；已用 `modprobe uinput` / `mknod c 10 223` 恢复为字符设备。

---

## 修复过程

策略：官方驱动独占 `28bd:0905`；其它键鼠与触控板配置不动。

### 步骤

1. `blacklist hid_uclogic`，并对 **仅** `0x28bd:0x0905` 设置 `usbhid quirks=...:0x4`（`HID_QUIRK_IGNORE`）。  
2. 将该板 USB 接口从 `usbhid` unbind（本机为 `3-4:1.0` / `3-4:1.1` / `3-4:1.2`）。  
3. 保证 `/dev/uinput` 为字符设备，且 mode 允许驱动进程写入。  
4. Xorg 对 `MatchUSBID "28bd:0905"` 的内核节点设置 `Ignore`（虚拟 `HVUG*` 无 USBID，不受影响）。  
5. 重启 `/usr/lib/ugeeTablet/ugeeTabletDriver.sh`。  
6. 写入 udev、systemd、autostart，并执行 `update-initramfs -u`。

### 修复后状态（2026-10-07 20:03 复查）

```text
# USB 仍在
lsusb → 28bd:0905 XP-Pen 10 inch PenTablet

# 内核不再绑定该板 HID
ls /sys/bus/hid/devices/*28BD* → none
lsmod → 无 hid_uclogic；usbhid 仍加载（其它 USB 键鼠在用）

# 官方驱动在跑
/usr/lib/ugeeTablet/ugeeTabletDriver
/usr/lib/ugeeTablet/ugeeTablet

# 虚拟输入（官方 uinput）
HVUG STYLUS  abs=d000103  phys=（空）
HVUG MOUSE   abs=0        phys=（空）
HVUG ERASER  abs=d000003  phys=（空）

# Xorg
(--) wacom: HVUG STYLUS stylus: maxX=52324 maxY=29600 maxZ=8192 ...
(II) XINPUT: Adding extended input device "HVUG STYLUS stylus" (type: STYLUS, ...)

# uinput
crw-rw-rw- 1 root input 10, 223 ... /dev/uinput
character special file

# 其它输入仍在（抽样）
AT Translated Set 2 keyboard
Newmen Tech.,LTD 2.4G Keyboard Mouse
SEMICO   USB Gaming Keyboard
SYNA30E5:00 06CB:CEAC Touchpad
```

此时 `HVUG*` 虚拟设备与压感轴已具备；随后又出现「有压感、光标位置不动」，见下一节。

---

## 第二阶段：有压感但笔位置不动（2026-10-07 21:43）

### 观测

环境仍为官方独占方案：`28bd:0905` 无内核 HID 绑定；`ugeeTabletDriver` 在跑；存在 `HVUG STYLUS` / `HVUG MOUSE` / `HVUG ERASER`。

对 `/dev/input/event6`（`HVUG STYLUS`）采样约 6 秒：

```text
ABS_X: min=0 max=52324
ABS_Y: min=0 max=29600
ABS_P: min=0 max=8192
counts  x=164 y=157
changed x=163 y=156
minmax  x=[21965,49517] y=[6111,25214]
```

说明 **evdev 层 X/Y 坐标在变化**，问题不在板子停报位置。

`xinput list`（本机随后安装 `xinput 1.6.4-1`）显示：

```text
∼ HVUG STYLUS stylus                       id=28  [floating slave]
```

同时 `HVUG MOUSE`、`HVUG ERASER eraser` 等挂在 `Virtual core pointer` 下。  
`HVUG STYLUS stylus` 为 **floating slave**：未挂到核心指针，故桌面光标不跟笔走；部分软件仍可读到压感。

同设备属性（挂接前）摘要：

```text
Device Enabled: 1
Coordinate Transformation Matrix: 单位矩阵
Wacom Tablet Area: 0, 0, 52324, 29600
Device Node: /dev/input/event6
屏幕: eDP-1 1920x1080 primary
```

### 处理

```bash
DISPLAY=:0 xinput reattach 'HVUG STYLUS stylus' 'Virtual core pointer'
```

挂接后：

```text
⎜   ↳ HVUG STYLUS stylus                       [slave  pointer  (2)]
```

并对干扰项执行（会话内）：

```bash
xinput disable 'HVUG ERASER touch'
```

（该节点常被识别为多余 touch slave。）

### 固化

新增登录自启脚本，在设备出现后若仍为 floating 则重新挂接。

---

## 固化配置（照抄自本机磁盘）

### `/etc/modprobe.d/ugee-official-only.conf`

```conf
# Prefer ugee official userspace driver for tablet 28bd:0905 only.
# Does not affect other USB keyboards/mice/touchpads.
blacklist hid_uclogic
options usbhid quirks=0x28bd:0x0905:0x4
```

已执行 `update-initramfs -u`。复查：

```text
lsinitramfs /boot/initrd.img-6.12.111+deb13-amd64 | grep ugee-official-only
# etc/modprobe.d/ugee-official-only.conf
```

### `/usr/local/sbin/ugee-exclusive-tablet.sh`

```bash
#!/bin/bash
# Ensure XP-Pen/Ugee 28bd:0905 is not claimed by usbhid; keep /dev/uinput usable.
# Safe for other input devices.

if [ -e /dev/uinput ]; then
  chmod 0666 /dev/uinput 2>/dev/null || true
fi

unbind_iface() {
  local name="$1"
  if [ -e "/sys/bus/usb/drivers/usbhid/$name" ]; then
    echo -n "$name" > /sys/bus/usb/drivers/usbhid/unbind 2>/dev/null || true
  fi
}

# If called with a kernel interface name from udev (%k)
if [ -n "${1:-}" ]; then
  unbind_iface "$1"
  exit 0
fi

# Boot sweep: find 28bd:0905 interfaces and unbind
for vendor in /sys/bus/usb/devices/*/idVendor; do
  [ -f "$vendor" ] || continue
  dev=$(dirname "$vendor")
  v=$(cat "$vendor" 2>/dev/null || true)
  p=$(cat "$dev/idProduct" 2>/dev/null || true)
  if [ "$v" = "28bd" ] && [ "$p" = "0905" ]; then
    for iface in "$dev":*; do
      [ -d "$iface" ] || continue
      unbind_iface "$(basename "$iface")"
    done
  fi
done
```

权限：`755`，属主 root。

### `/etc/udev/rules.d/99-ugee-official-only.rules`

```conf
# Hand tablet 28bd:0905 to official ugee userspace driver only.
ACTION=="add", SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_interface", ATTRS{idVendor}=="28bd", ATTRS{idProduct}=="0905", RUN+="/usr/local/sbin/ugee-exclusive-tablet.sh %k"
```

### `/etc/udev/rules.d/60-uinput-ugee.rules`

```conf
KERNEL=="uinput", MODE="0666", OPTIONS+="static_node=uinput", GROUP="input"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="28bd", MODE="0666"
```

包装自带 `/lib/udev/rules.d/ugee4-1.rules` 内容相近，但本机曾出现 uinput 仍为 `600`，故在 `/etc` 另置一份。

### `/etc/X11/xorg.conf.d/80-ugee-ignore-kernel.conf`

```conf
Section "InputClass"
    Identifier "Ignore kernel UGTABLET USB nodes"
    MatchUSBID "28bd:0905"
    Option "Ignore" "true"
EndSection
```

### `/etc/systemd/system/ugee-exclusive-tablet.service`

```ini
[Unit]
Description=Reserve UGee/XP-Pen tablet 28bd:0905 for official driver
After=systemd-udevd.service
Before=graphical.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/ugee-exclusive-tablet.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

状态：`enabled`，`active (exited)`。

### 登录自启

`/etc/xdg/autostart/ugeetablet.desktop` 与 `/home/charlie/.config/autostart/ugeetablet.desktop`：

```ini
[Desktop Entry]
Type=Application
Name=ugeetablet
Name[zh_CN]=ugee 数位板驱动
Comment=UGEE/XP-Pen official tablet driver
Exec=/usr/lib/ugeeTablet/ugeeTabletDriver.sh
Icon=/usr/share/icons/hicolor/256x256/apps/ugeetablet.png
Terminal=false
Categories=Utility;
StartupNotify=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=2
```

### 账户组

```text
id charlie → ... groups=...,996(input),...
```

### `/usr/local/bin/ugee-reattach-stylus.sh`

依赖包：`xinput 1.6.4-1`（本机 `apt` 安装）。

```bash
#!/bin/bash
# Reattach official ugee virtual stylus to X core pointer if it becomes floating.
export DISPLAY="${DISPLAY:-:0}"
# pick a usable XAUTHORITY
if [ -z "${XAUTHORITY:-}" ]; then
  for a in "$HOME/.Xauthority" /run/user/$(id -u)/gdm/Xauthority; do
    [ -f "$a" ] && export XAUTHORITY="$a" && break
  done
fi

command -v xinput >/dev/null || exit 0

reattach_one() {
  local name="$1"
  # floating devices appear under "∼ name" in xinput list
  if xinput list --name-only 2>/dev/null | grep -qx "$name"; then
    # if floating, reattach; reattach on already-attached is harmless enough to try when floating marker present
    if xinput list 2>/dev/null | grep -F "$name" | grep -q '\[floating slave\]'; then
      xinput reattach "$name" "Virtual core pointer" 2>/dev/null || true
      echo "reattached $name"
    fi
  fi
}

# retry a while: driver may create devices after login
for i in $(seq 1 30); do
  reattach_one "HVUG STYLUS stylus"
  reattach_one "HVUG STYLUS eraser"
  # optional: disable bogus touch slave from eraser device (reduces interference)
  if xinput list --name-only 2>/dev/null | grep -qx "HVUG ERASER touch"; then
    xinput disable "HVUG ERASER touch" 2>/dev/null || true
  fi
  # stop early once stylus is a slave pointer
  if xinput list 2>/dev/null | grep -F "HVUG STYLUS stylus" | grep -q 'slave  pointer'; then
    if ! xinput list 2>/dev/null | grep -F "HVUG STYLUS stylus" | grep -q 'floating'; then
      exit 0
    fi
  fi
  sleep 2
done
```

权限：`755`。

配套 autostart：`/etc/xdg/autostart/ugee-reattach-stylus.desktop` 与 `~/.config/autostart/ugee-reattach-stylus.desktop`：

```ini
[Desktop Entry]
Type=Application
Name=ugee reattach stylus
Comment=Keep HVUG STYLUS attached to X core pointer
Exec=/usr/local/bin/ugee-reattach-stylus.sh
Terminal=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
```

2026-10-07 21:52 复查 `xinput list` 中 `HVUG STYLUS stylus` 为 `slave pointer`（非 floating）；`HVUG ERASER touch` 可为 floating（已 disable）。

---

## 重启后核对

```bash
lsusb | grep 28bd
ls /sys/bus/hid/devices/*28BD* 2>/dev/null || echo 'no hid 28BD'
ps -eo pid,cmd | grep '/usr/lib/ugeeTablet' | grep -v grep
for d in /sys/class/input/input*/name; do grep -q HVUG "$d" && echo "OK $(cat $d)"; done
ls -l /dev/uinput; stat -c '%F' /dev/uinput
systemctl is-enabled ugee-exclusive-tablet.service
systemctl is-active ugee-exclusive-tablet.service
DISPLAY=:0 xinput list | grep -E 'HVUG|floating'
for d in /sys/class/input/input*/name; do
  n=$(cat "$d")
  echo "$n" | grep -Eq 'Newmen|SEMICO|SYNA|AT Translated' && echo "OK $n"
done
```

期望：

- 无 `28BD` HID 绑定；存在 `ugeeTabletDriver`；存在 `HVUG STYLUS/MOUSE/ERASER`  
- `/dev/uinput` 为 character special file  
- `HVUG STYLUS stylus` 为 **slave pointer**，**不是** `[floating slave]`  
- Newmen / SEMICO / SYNA / AT Translated 仍在  

若再次出现 floating：

```bash
DISPLAY=:0 xinput reattach 'HVUG STYLUS stylus' 'Virtual core pointer'
```

---

## 回滚

```bash
sudo systemctl disable --now ugee-exclusive-tablet.service
sudo rm -f \
  /etc/modprobe.d/ugee-official-only.conf \
  /etc/udev/rules.d/99-ugee-official-only.rules \
  /etc/udev/rules.d/60-uinput-ugee.rules \
  /etc/X11/xorg.conf.d/80-ugee-ignore-kernel.conf \
  /etc/xdg/autostart/ugeetablet.desktop \
  /etc/xdg/autostart/ugee-reattach-stylus.desktop \
  /etc/systemd/system/ugee-exclusive-tablet.service \
  /usr/local/sbin/ugee-exclusive-tablet.sh \
  /usr/local/bin/ugee-reattach-stylus.sh
rm -f \
  /home/charlie/.config/autostart/ugeetablet.desktop \
  /home/charlie/.config/autostart/ugee-reattach-stylus.desktop
sudo systemctl daemon-reload
sudo udevadm control --reload-rules
sudo update-initramfs -u
# 可选：sudo apt remove ugeetablet xinput
sudo reboot
```

---

## 结论

在主机 `dev`（Debian 13，GNOME X11）上，设备 `28bd:0905`（lsusb：`XP-Pen 10 inch PenTablet`；驱动标识：「绘影 EX08」/ `BPU1002`）安装 `ugeetablet 4.3` 后画笔问题分两阶段：

1. **驱动与内核争用 + uinput 权限**：`hid_uclogic` / `usbhid` 与 `ugeeTabletDriver` 争用设备，Xorg 中 `UGTABLET ... Pen stylus` 被移除；`/dev/uinput` 不可写时建不出 `HVUG*`。处理为仅对 `28bd:0905` 做内核忽略、usbhid unbind、uinput 权限与官方驱动自启（modprobe / udev / systemd / autostart / initramfs）。  
2. **X 输入挂接**：`HVUG STYLUS` 已有 X/Y/压感事件，但 `HVUG STYLUS stylus` 处于 `[floating slave]`，光标不跟随。处理为 `xinput reattach` 到 `Virtual core pointer`，并增加登录自启 `/usr/local/bin/ugee-reattach-stylus.sh`。

其它输入设备配置未改，复查仍在。
