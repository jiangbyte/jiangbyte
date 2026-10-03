---
date: 2026-10-01
description: "机器上同时有三套 Python 很容易搅在一起："
categories: ["工具"]
tags: ["工具"]
---

## 先说目标

机器上同时有三套 Python 很容易搅在一起：

1. 系统自带的 `/usr/bin/python3`
2. conda 的 `base`
3. 自己建的业务 / 学习环境

想要的结果很简单：**不管终端还是 Cursor，一律只用名为 `normal` 的 conda 环境**，不要再落到 `base` 或系统 Python 上。

下面以 miniforge（路径 `/home/charlie/miniforge3`）为例，过程对 Anaconda / Miniconda 同样适用，改一下前缀即可。

## 创建 `normal` 环境

选用相对稳妥的 3.12：

```bash
conda create -n normal python=3.12 -y
```

创建完成后确认：

```bash
conda env list
# base                     /home/charlie/miniforge3
# normal                   /home/charlie/miniforge3/envs/normal
```

解释器路径固定为：

```text
/home/charlie/miniforge3/envs/normal/bin/python
```

网络不稳时下载可能被 `Connection reset by peer` 打断，直接重跑同一条 `conda create` 即可，已下完的包会复用缓存。

## 关掉 base 自动激活

默认安装后，新开 shell 会进 `base`。先关掉：

```bash
conda config --set auto_activate_base false
```

新版 conda 会把这个键写成 `auto_activate`。`~/.condarc` 里最终可以是：

```yaml
auto_activate: false
```

这样登录时不会再默认进 `base`。

## 让 bash 登录后自动进 `normal`

在 `~/.bashrc` 的 conda initialize 块末尾加上激活语句：

```bash
# >>> conda initialize >>>
__conda_setup="$('/home/charlie/miniforge3/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/home/charlie/miniforge3/etc/profile.d/conda.sh" ]; then
        . "/home/charlie/miniforge3/etc/profile.d/conda.sh"
    else
        export PATH="/home/charlie/miniforge3/bin:$PATH"
    fi
fi
unset __conda_setup
# Always use the `normal` env (never conda base / system Python)
conda activate normal 2>/dev/null
# <<< conda initialize <<<
```

要点：

- 必须写在 `conda` hook 初始化**之后**，否则 `conda activate` 可能不可用
- `2>/dev/null` 避免环境尚未创建时刷一堆报错
- 新开终端后提示符应显示 `(normal)`

已打开的旧终端不会自动生效，手动执行一次：

```bash
conda activate normal
```

## 让 Cursor 也指向 `normal`

只改 shell 不够，编辑器里跑 Python / 选解释器时仍可能跳到别的环境。在 Cursor 用户设置里加上：

```json
{
  "python.defaultInterpreterPath": "/home/charlie/miniforge3/envs/normal/bin/python",
  "python.terminal.activateEnvironment": true,
  "terminal.integrated.env.linux": {
    "CONDA_DEFAULT_ENV": "normal"
  }
}
```

路径按本机 conda 前缀调整。改完后重开集成终端，或在命令面板里重新选一次解释器确认。

## 验收

干净登录测一下（或新开一个终端）：

```bash
echo "$CONDA_DEFAULT_ENV"   # 期望：normal
which python                # .../envs/normal/bin/python
python --version            # Python 3.12.x
conda env list              # normal 前有 *
```

再确认没有误用系统解释器：

```bash
command -v python
command -v python3
# 两者都应落在 .../envs/normal/bin/ 下
```

系统里的 `/usr/bin/python3` 可以还在，但只要 PATH 里 `normal` 在前，日常敲 `python` / `python3` 就不会撞上它。

## The End

| 项       | 做法                                                 |
| ------- | -------------------------------------------------- |
| 独立环境    | `conda create -n normal python=3.12`               |
| 禁用 base | `auto_activate: false`                             |
| 终端默认    | `~/.bashrc` 里 `conda activate normal`              |
| 编辑器默认   | Cursor `python.defaultInterpreterPath` 指向 `normal` |


之后装包、写脚本、跑实验，默认都进 `normal`；需要隔离的项目再单独 `conda create -n xxx`，用完切回来即可。
