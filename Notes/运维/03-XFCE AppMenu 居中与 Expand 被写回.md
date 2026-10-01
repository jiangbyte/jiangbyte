---
title: "XFCE AppMenu 居中与 Expand 被写回"
date: 2026-10-01
draft: false
description: "顶栏装了 AppMenu Plugin 之后："
categories: ["运维"]
tags: ["运维"]
---
## 现象

顶栏装了 **AppMenu Plugin** 之后：

- 菜单标题（如 `Cursor`、`Thunar`）不靠左，像漂在面板中间
- 右键属性里把 **Expand plugin on panel** 关掉，看起来正常了
- **注销 / 重启** 后，Expand 又被勾上，标题又居中

装全局菜单、环境变量、GTK module 等前置步骤见：[Debian 13 XFCE 开发机整理：熄屏、软件源、全局菜单与防火墙](./Debian%2013%20XFCE%20开发机整理：熄屏、软件源、全局菜单与防火墙.md)。本文只挖 **居中 / Expand 反复写回** 这一块。

---

## 1. AppMenu 是什么（不是另一套更好的菜单）

面板里叫 **AppMenu Plugin** 的东西，包名是：

```bash
apt-cache show xfce4-appmenu-plugin | grep -E '^(Package|Source|Description)'
```

实际就是 **vala-panel-appmenu** 的 XFCE 后端：把当前窗口的 File / Edit 等导出到面板。  
没有「再装一个更强的 AppMenu」这种替代品——同一种插件，名字略容易混。

相关包通常还有：`appmenu-gtk3-module`、`appmenu-registrar`。

---

## 2. 为什么会「居中」

面板插件有个开关：**Expand plugin on panel**（扩展以填满可用空间）。

AppMenu 打开 Expand 后，会占满中间整段空白。标题文字往往在插件内容区里左对齐或居中显示——空白被它吃掉时，短标题就会看起来像漂在屏幕中间。

正确布局一般是：

| 角色 | Expand |
|---|---|
| AppMenu | **关**（只占菜单实际宽度，靠左） |
| AppMenu 后面的 **分隔符** | **开**（把托盘、时钟等顶到右边） |

不要指望靠 AppMenu 自己 Expand 来「把右边顶开」——那正是居中感的来源。

---

## 3. 为什么关掉又会回来

只改 GUI 不够。`xfce4-appmenu-plugin` 启动时会把 Expand **默认写成 `true`**，并写回 xfconf。所以：

1. 你关掉 Expand → 面板正常  
2. 下次登录 / 面板重载插件 → 插件再写 `true` → 又居中  

配置里通常有 **两处** expand（以插件 ID 为 `2` 为例，你的 ID 可能不同）：

```text
/plugins/plugin-2/expand
/plugins/plugin-2/plugins/plugin-2/expand
```

嵌套那条是插件内部属性；外面那条是面板层。**两边都要关**，只关一边经常看起来「设了但没用」或重启后又开。

查自己的插件 ID：

```bash
xfconf-query -c xfce4-panel -l -v | grep -E 'appmenu|expand'
```

一次性关掉（把 `2` 换成你的 ID）：

```bash
xfconf-query -c xfce4-panel -p /plugins/plugin-2/plugins/plugin-2/expand -n -t bool -s false
xfconf-query -c xfce4-panel -p /plugins/plugin-2/expand -n -t bool -s false
```

也可：右键 AppMenu → 属性 → 取消 **Expand plugin on panel**。  
若只做这一步、不做下面的 autostart，**重启后多半还会回来**。

---

## 4. 永久压住：登录后强制 Expand=false

思路：不跟插件抢「启动瞬间」的默认值，等面板和 AppMenu 起来后，**再写两次 false**（插件有时会晚一点再写回一次）。

### 4.1 脚本

```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/appmenu-no-expand.sh <<'EOF'
#!/bin/bash
# AppMenu(xfce4-appmenu-plugin) 启动时会把 Expand 默认写回 true，登录后强制关掉。
set -e

export DISPLAY="${DISPLAY:-:0}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}"

# 等面板与 appmenu 就绪
for _ in $(seq 1 40); do
  if pgrep -x xfce4-panel >/dev/null \
    && xfconf-query -c xfce4-panel -l 2>/dev/null | grep -q '/plugins/plugin-.*/plugins/plugin-'; then
    break
  fi
  sleep 0.5
done
sleep 1

fix_appmenu_expand() {
  local id name
  for id in $(xfconf-query -c xfce4-panel -l 2>/dev/null \
    | sed -n 's|^/plugins/plugin-\([0-9]\+\)$|\1|p'); do
    name=$(xfconf-query -c xfce4-panel -p "/plugins/plugin-$id" 2>/dev/null || true)
    if [ "$name" = "appmenu" ]; then
      xfconf-query -c xfce4-panel -p "/plugins/plugin-$id/plugins/plugin-$id/expand" -n -t bool -s false
      xfconf-query -c xfce4-panel -p "/plugins/plugin-$id/expand" -n -t bool -s false
      return 0
    fi
  done
  return 1
}

fix_appmenu_expand || true
# 插件有时在首次设置后又写回 true，再补一次
sleep 2
fix_appmenu_expand || true
EOF
chmod +x ~/.local/bin/appmenu-no-expand.sh
```

脚本会自动找名为 `appmenu` 的插件，不写死 ID。

### 4.2 开机自启

```bash
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/appmenu-left-align.desktop <<EOF
[Desktop Entry]
Type=Application
Name=AppMenu Disable Expand
Comment=Prevent AppMenu from forcing Expand on login
Exec=$HOME/.local/bin/appmenu-no-expand.sh
OnlyShowIn=XFCE;
X-GNOME-Autostart-enabled=true
EOF
```

文件名可以叫别的；关键是 `Exec` 指向上面的脚本，且 `X-GNOME-Autostart-enabled=true`。

验证：

```bash
~/.local/bin/appmenu-no-expand.sh
xfconf-query -c xfce4-panel -l -v | grep -E 'plugin-.*/expand|appmenu'
```

期望类似：

```text
/plugins/plugin-2                                         appmenu
/plugins/plugin-2/expand                                  false
/plugins/plugin-2/plugins/plugin-2/expand                 false
/plugins/plugin-23/expand                                 true   # 后面那个分隔符，保持 true
```

注销再登录，菜单标题应仍靠左。

---

## 5. 踩过的坑

### 5.1 坏掉的 autostart

曾经有过一个 `appmenu-left-align.desktop`，`Exec` 指向不存在的路径或错误命令——会话里等于没跑。  
若「写了自启却无效」，先：

```bash
cat ~/.config/autostart/appmenu*.desktop
ls -l ~/.local/bin/appmenu-no-expand.sh
```

确认可执行、路径一致。

### 5.2 只改了一处 expand

只改 `/plugins/plugin-N/expand` 或只改嵌套路径，表现会不稳定。脚本里两处都写。

### 5.3 Compact mode

属性里还有 **Compact mode**：菜单更挤一点，**解决不了** Expand 居中问题。居中靠 Expand + 分隔符布局，不靠 Compact。

### 5.4 和 Window Buttons / Windowck 的区别

| 插件 | 作用 |
|---|---|
| **AppMenu** | 全局菜单（File / Edit…） |
| **Window Buttons / Windowck** | 窗口按钮或标题相关，不是全局菜单 |

换「标题样式」插件解决不了 AppMenu 的 Expand 写回；那是另一类需求。

---

## 6. 小结

| 点 | 结论 |
|---|---|
| 居中原因 | AppMenu 开了 **Expand**，占满中间空白 |
| 靠右托盘 | Expand **分隔符**，不要 Expand AppMenu |
| 重启又开 | 插件启动默认写回 `expand=true` |
| 持久办法 | 登录后 autostart 脚本把两处 expand 写成 `false`（并再补一次） |

装好全局菜单本身不难；难的是这个默认 Expand 会自己写回来。压住之后，顶栏就会稳定成「菜单靠左、托盘靠右」。
