---
title: "Claude、Codex 全自动模式"
date: 2026-10-01
draft: false
description: "\"YOLO 模式\"（或叫\"全自动模式\"）是为了让 AI 编程助手在不经你逐次确认的情况下，全自动执行指令。Codex 和 Claude Code 都有各自的开启方式，但核心逻辑和风险是一样的。"
categories: ["工具"]
tags: ["工具"]
---
"YOLO 模式"（或叫"全自动模式"）是为了让 AI 编程助手在不经你逐次确认的情况下，全自动执行指令。Codex 和 Claude Code 都有各自的开启方式，但核心逻辑和风险是一样的。

YOLO 模式主要通过两种方式开启：**命令行参数**和**配置文件**。

开启 YOLO 模式意味着将 AI 的操作权限完全放开，这虽然能极大提升效率，但也存在不小的风险。

### 速览

| 工具                          | 对应的 YOLO 标志                                             | 说明                     |
| :-------------------------- | :------------------------------------------------------ | :--------------------- |
| **Codex CLI** (OpenAI)      | `--yolo` 或 `--dangerously-bypass-approvals-and-sandbox` | 后者是其完整标志，`--yolo` 是别名。 |
| **Claude Code** (Anthropic) | `--dangerously-skip-permissions`                        | Claude Code 使用的官方标志。   |

### 如何开启 YOLO 模式

#### 1. 命令行启动

*   **对于 Codex**：在启动命令后直接加上 `--yolo` 或完整标志。
    ```bash
    codex --yolo "需求描述"
    # 或者
    codex --dangerously-bypass-approvals-and-sandbox "需求描述"
    ```

*   **对于 Claude Code**：启动时加上 `--dangerously-skip-permissions`。
    ```bash
    claude --dangerously-skip-permissions "需求描述"
    ```

#### 2. 配置文件永久生效

如果你想让某个工具默认就进入 YOLO 模式，可以修改其配置文件：

*   **Claude Code**：编辑 `~/.claude/settings.json` 文件，设置权限模式：
    ```json
    {
      "permissions": {
        "defaultMode": "bypassPermissions"
      }
    }
    ```
