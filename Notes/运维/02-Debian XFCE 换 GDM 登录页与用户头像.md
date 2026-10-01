---
title: "Debian XFCE 换 GDM 登录页与用户头像"
description: "机器：Debian 13（trixie）+ XFCE，原先用 LightDM + lightdm-gtk-greeter。"
permalink: /blog/运维/Debian XFCE 换 GDM 登录页与用户头像/
createTime: 2026-10-01
tags: ["运维"]
type: post
---
## 目标与边界

机器：**Debian 13（trixie）+ XFCE**，原先用 **LightDM + lightdm-gtk-greeter**。

要做的事：

1. 登录界面换成 **GDM3**（只要登录页，**不**换 GNOME 桌面）
2. 登录后仍进 **Xfce Session**
3. 能用图形工具调登录页外观（壁纸等）
4. 搞清楚 **登录头像** 改哪里、为什么 Mugshot / 只改 `~/.face` 不生效

明确不做（本文范围外）：

- 不装 WhiteSur / macOS 风 GDM 主题（可以后再加）
- 不卸载 LightDM 包（方便回退）

桌面侧其它整理可对照：[Debian 13 XFCE 开发机整理：熄屏、软件源、全局菜单与防火墙](./Debian%2013%20XFCE%20开发机整理：熄屏、软件源、全局菜单与防火墙.md)。

---

## 1. 先备份

```bash
sudo cp -a /etc/X11/default-display-manager \
  /etc/X11/default-display-manager.bak.$(date +%Y%m%d%H%M%S)
sudo cp -a /etc/lightdm/lightdm.conf \
  /etc/lightdm/lightdm.conf.bak.$(date +%Y%m%d%H%M%S)
```

确认当前 DM 与 XFCE 会话文件存在：

```bash
cat /etc/X11/default-display-manager
# 常见：/usr/sbin/lightdm

ls /usr/share/xsessions/
# 应有 xfce.desktop
```

---

## 2. 安装 GDM：注意混源 / 过新库

### 2.1 理想情况（纯 trixie）

图形桌面里执行即可，**不必**先切救援模式或纯命令行：

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends gdm3
```

若弹出「默认显示管理器」，选 **gdm3**。未弹出则：

```bash
echo /usr/sbin/gdm3 | sudo tee /etc/X11/default-display-manager
sudo DEBIAN_FRONTEND=noninteractive dpkg-reconfigure -f noninteractive gdm3
```

```bash
sudo systemctl enable gdm.service   # 或 gdm3.service，视包而定
sudo systemctl disable lightdm.service
```

确认：

```bash
cat /etc/X11/default-display-manager   # → /usr/sbin/gdm3
readlink -f /etc/systemd/system/display-manager.service
# → .../gdm.service
test -f /usr/share/xsessions/xfce.desktop && echo xfce OK
```

然后 **重启**（比只注销稳）：

```bash
sudo reboot
```

登录页若出现会话菜单，选 **Xfce Session**。

### 2.2 本机踩坑：glib / heif / xkb 比 trixie 新

若机器上曾混过 **sid** 包（例如 `libglib2.0` / `gir1.2-glib-2.0` 已是 2.89.x），直接装 trixie 的 `gdm3` 常会失败，典型报错类似：

- `gdm3` → 依赖 `gnome-shell`
- `libgjs0g` 与现有 `gir1.2-glib-2.0` **Breaks**
- `libheif1` 过新导致 `heif-thumbnailer` / `gnome-control-center` 装不上
- `libxkbcommon0` 版本与 `libxkbregistry0` 对不上

**不要**为装 GDM 盲目把整套 glib/gtk4 **降级**回 trixie——容易把已能用的桌面、Cursor 等拖垮。

可行做法之一（与本机一致时）：**临时**用 sid 装与当前新库匹配的 `gdm3`，装完再去掉 sid 源，避免以后 `apt upgrade` 整桌面滚飞：

```bash
# 临时 sid（优先级压低）
echo 'deb https://mirrors.bfsu.edu.cn/debian sid main contrib non-free non-free-firmware' \
  | sudo tee /etc/apt/sources.list.d/sid-temp.list

sudo tee /etc/apt/preferences.d/sid-temp >/dev/null <<'EOF'
Package: *
Pin: release a=unstable
Pin-Priority: 100
EOF

sudo apt-get update
echo 'gdm3 shared/default-x-display-manager select gdm3' | sudo debconf-set-selections
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends -t sid gdm3

echo /usr/sbin/gdm3 | sudo tee /etc/X11/default-display-manager
sudo systemctl disable lightdm.service || true
# display-manager.service 应指向 gdm

# 用完立刻删临时源，降低误升级风险
sudo rm -f /etc/apt/sources.list.d/sid-temp.list /etc/apt/preferences.d/sid-temp
sudo apt-get update
```

> 这会拉上 `gnome-shell` 等一批依赖，体积不小；桌面日常仍用 XFCE，只是登录器用 GDM。混源系统请自己评估风险。

---

## 3. 重启后：不选 Session 进不去

### 现象

GDM 登录页必须手动选会话，否则登不上或进奇怪会话。

### 原因

默认会话还停在 LightDM 时代的 **`lightdm-xsession`**：

- `~/.dmrc` 里可能是 `Session=lightdm-xsession`
- AccountsService 里 `Session` / `XSession` 也可能是它
- `/usr/share/xsessions/lightdm-xsession.desktop` 的 `Exec=default`，对 GDM 基本不可用

当前会话环境也可能显示：

```bash
echo "$DESKTOP_SESSION"   # 曾出现 lightdm-xsession
```

### 修复：默认改为 xfce

```bash
# 1) 用户 dmrc
printf '%s\n' '[Desktop]' 'Session=xfce' > ~/.dmrc

# 2) AccountsService（把 charlie 换成你的用户名）
sudo tee /var/lib/AccountsService/users/charlie >/dev/null <<'EOF'
[User]
Session=xfce
XSession=xfce
Icon=/var/lib/AccountsService/icons/charlie
SystemAccount=false
EOF
sudo chmod 600 /var/lib/AccountsService/users/charlie
sudo systemctl restart accounts-daemon

# 3) 也可用 D-Bus（uid 按 id -u）
busctl call org.freedesktop.Accounts \
  /org/freedesktop/Accounts/User$(id -u) \
  org.freedesktop.Accounts.User SetXSession s xfce
```

### 隐藏失效的 Default Xsession

避免下次再点错：

```bash
echo 'Hidden=true' | sudo tee -a /usr/share/xsessions/lightdm-xsession.desktop
echo 'NoDisplay=true' | sudo tee -a /usr/share/xsessions/lightdm-xsession.desktop
```

之后登录页可直接输密码；若仍出现会话菜单，**选一次 Xfce Session**，一般会记住。

---

## 4. GDM 图形配置：GDM Settings

GDM **没有**像「控制中心里完整登录页编辑器」的官方小面板；实用方案是 Flatpak **GDM Settings**：

```bash
flatpak install -y flathub io.github.realmazharhussain.GdmSettings
```

启动：

```bash
flatpak run io.github.realmazharhussain.GdmSettings
```

或在应用菜单搜 **GDM Settings**。

可改：外观 / 字体 / 顶栏 / 登录页壁纸与 logo / 电源相关等。改登录页配置通常要提权；点 **Apply** 后注销到登录页看效果。

**注意：GDM Settings 不能改用户头像**（Appearance 只管主题/壁纸一类）。

---

## 5. 登录页用户头像

### 5.1 头像实际读哪里

| 路径 | 作用 |
|------|------|
| `~/.face` / `~/.face.icon` | 用户目录头像，很多工具会写这里 |
| `/var/lib/AccountsService/icons/<用户名>` | **GDM 可靠读取的位置** |
| `/var/lib/AccountsService/users/<用户名>` 里的 `Icon=` | 告诉 AccountsService / GDM 用哪张图 |

查看：

```bash
ls -la ~/.face
grep ^Icon= /var/lib/AccountsService/users/$(whoami)   # 可能需 sudo
ls -la /var/lib/AccountsService/icons/
busctl get-property org.freedesktop.Accounts \
  /org/freedesktop/Accounts/User$(id -u) \
  org.freedesktop.Accounts.User IconFile
```

### 5.2 为什么只改 ~/.face / 用 Mugshot「没用」

常见两层原因（本机都遇到过）：

1. **家目录权限是 `700`（`drwx------`）**  
   GDM 进程用户是 `Debian-gdm`，**进不了** `/home/你的用户`，自然读不到 `~/.face`。  
   即使用 Mugshot 成功写入了 `.face`，登录页仍是旧图或默认图。

2. **图太大**  
   AccountsService 的 `SetIconFile` 会拒过大文件（例如 1080×1080、1.7MB 级 PNG），报错类似：  
   `file '...' is too large to be used as an icon`  
   建议缩到约 **256×256**、体积几十 KB 量级（JPEG 即可）。

因此：**不要依赖「只改家目录 .face」**；要同步到 AccountsService 图标目录，并保证 `Debian-gdm` 对该路径可读（系统目录 `644` 即可）。

Mugshot 会拉 cheese/clutter 等依赖；若不想污染环境，用下面手动步骤即可，不必装 Mugshot。

### 5.3 以后更换头像（推荐步骤）

把 `你的图.jpg`、用户名换成自己的：

```bash
# 1) 缩放（有 ImageMagick / ffmpeg / 带 PIL 的 python 任一即可）
# 示例：python3 + Pillow
python3 - <<'PY'
from PIL import Image
im = Image.open("你的图.jpg").convert("RGB")
im = im.resize((256, 256), Image.Resampling.LANCZOS)
im.save("/tmp/face.jpg", "JPEG", quality=85, optimize=True)
print("ok")
PY

# 2) 用户目录备份一份（可选）
cp /tmp/face.jpg ~/.face

# 3) 写入 GDM 可读路径并登记
sudo install -d -m 755 /var/lib/AccountsService/icons
sudo install -m 644 /tmp/face.jpg /var/lib/AccountsService/icons/charlie
sudo sed -i 's|^Icon=.*|Icon=/var/lib/AccountsService/icons/charlie|' \
  /var/lib/AccountsService/users/charlie
# 若没有 Icon= 行，用编辑器在 [User] 下加一行 Icon=...

sudo busctl call org.freedesktop.Accounts \
  /org/freedesktop/Accounts/User$(id -u) \
  org.freedesktop.Accounts.User SetIconFile s \
  /var/lib/AccountsService/icons/charlie

# 4) 注销到登录页查看（一般不用重启）
```

也可用「GNOME 设置 → 用户」点头像；若只更新了 `~/.face`、登录页没变，仍按上面把图拷到 `/var/lib/AccountsService/icons/`。

### 5.4 不建议的「永久自动化」

用 systemd path 监听 `~/.face` 再 sudo 同步、或为缩放再装一堆图像库，容易引入多余依赖、搞乱环境。开发机更稳妥是：**换头像时跑一遍上面的小段命令**。

---

## 6. 回退到 LightDM（GDM 起不来时）

`Ctrl+Alt+F3` 登录后：

```bash
echo /usr/sbin/lightdm | sudo tee /etc/X11/default-display-manager
sudo apt-get install -y --reinstall lightdm
sudo systemctl enable lightdm
sudo systemctl disable gdm.service 2>/dev/null || sudo systemctl disable gdm3.service 2>/dev/null || true
sudo reboot
```

LightDM 包平时可保留，不必为换 GDM 卸载。

---

## 7. 检查清单

换 GDM 后建议确认：

```bash
cat /etc/X11/default-display-manager          # gdm3
test -f /usr/share/xsessions/xfce.desktop && echo xfce
grep -E '^(Session|XSession|Icon)=' /var/lib/AccountsService/users/$(whoami)  # 可能需 sudo
cat ~/.dmrc                                   # Session=xfce
flatpak info io.github.realmazharhussain.GdmSettings 2>/dev/null | head -5
```

登录页：

- [ ] 出现 GDM（非 LightDM gtk-greeter）
- [ ] 可不选手动 Session 直接进 XFCE（或选一次后记住）
- [ ] 头像为预期图片
- [ ] 桌面仍是 XFCE（面板 / WhiteSur 等未丢）

---

## End

| 项目 | 结论 |
|------|------|
| 登录器 | LightDM → GDM3；桌面仍用 XFCE |
| 默认会话 | 必须改成 `xfce`，去掉/隐藏 `lightdm-xsession` |
| 登录页 GUI | Flatpak **GDM Settings**；不改头像 |
| 头像 | 写入 `/var/lib/AccountsService/icons/<用户>` + `Icon=`；注意家目录 700 与图片体积 |

纯 trixie 环境优先用仓库里的 `gdm3`；若已混 sid 新库，再考虑临时 sid 安装并立刻撤源，避免为降级把现有桌面拆坏。
