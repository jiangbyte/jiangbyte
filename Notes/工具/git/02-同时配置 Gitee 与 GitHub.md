---
title: "同时配置 Gitee 与 GitHub"
description: "开发机上经常要同时推 Gitee、GitHub，有时还要接阿里云 Codeup。默认只会用 ~/.ssh/idrsa，多平台共用一把钥匙容易乱；更稳妥的做法是：每平台一把密钥，用 ~/.ssh/config 按 Host 分流。"
permalink: /blog/工具/git/同时配置 Gitee 与 GitHub/
createTime: 2026-10-01
tags: ["工具"]
type: post
---
开发机上经常要同时推 Gitee、GitHub，有时还要接阿里云 Codeup。默认只会用 `~/.ssh/id_rsa`，多平台共用一把钥匙容易乱；更稳妥的做法是：**每平台一把密钥，用 `~/.ssh/config` 按 Host 分流**。

## 全局 Git 身份

提交作者信息与 SSH 无关，但新环境一般先配好：

```bash
git config --global user.name "jiangbyte"
git config --global user.email "your@email.com"
git config --global --list
```

确认输出里有 `user.name` / `user.email`。若某仓库要用不同邮箱，再在该仓库里用 `git config user.email`（不加 `--global`）覆盖即可。

## 为各平台分别生成 SSH 密钥

目录权限先保证：

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
```

分别生成三把密钥（文件名自定义，别互相覆盖）：

```bash
ssh-keygen -t rsa -C 'your@email.com' -f ~/.ssh/id_rsa.gitee
ssh-keygen -t rsa -C 'your@email.com' -f ~/.ssh/id_rsa.github
ssh-keygen -t rsa -C 'your@email.com' -f ~/.ssh/id_rsa.codeup
```

提示 passphrase 时可直接回车（无密码），或设一个口令更安全。生成后每个平台会有一对文件，例如：

| 文件 | 用途 |
|------|------|
| `id_rsa.gitee` / `id_rsa.gitee.pub` | Gitee 私钥 / 公钥 |
| `id_rsa.github` / `id_rsa.github.pub` | GitHub 私钥 / 公钥 |
| `id_rsa.codeup` / `id_rsa.codeup.pub` | Codeup 私钥 / 公钥 |

**私钥不要提交、不要发聊天工具**；上传到网站的永远是 `.pub`。

## 配置 SSH Host 分流

用 `~/.ssh/config` 告诉 SSH：连哪个域名时用哪把钥匙。

```bash
cat > ~/.ssh/config << 'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_rsa.github

Host gitee.com
    HostName gitee.com
    User git
    IdentityFile ~/.ssh/id_rsa.gitee

Host codeup.aliyun.com
    HostName codeup.aliyun.com
    User git
    IdentityFile ~/.ssh/id_rsa.codeup
EOF

chmod 600 ~/.ssh/config
cat ~/.ssh/config
```

要点：

- `Host` 要和远程 URL 里的域名一致（`git@github.com:...` 会对上 `Host github.com`）
- `IdentityFile` 指向对应**私钥**
- 权限建议：`~/.ssh` 为 `700`，密钥与 `config` 为 `600`

## 把公钥加到各平台

分别查看公钥内容，复制到对应网站的 SSH Key 设置页：

```bash
cat ~/.ssh/id_rsa.gitee.pub
cat ~/.ssh/id_rsa.github.pub
cat ~/.ssh/id_rsa.codeup.pub
```

常见入口：

- **GitHub**：Settings → SSH and GPG keys → New SSH key
- **Gitee**：设置 → SSH 公钥
- **Codeup（阿里云）**：个人设置 / 代码源里的 SSH 公钥管理

三把公钥可以标题标成 `dev-gitee`、`dev-github`、`dev-codeup`，以后好辨认。

## 验证连通

先粗测能否握手（`-v` 可看用了哪把钥匙）：

```bash
ssh -v git@gitee.com
ssh -v git@github.com
ssh -v git@codeup.aliyun.com
```

再做平台自检（成功时一般会提示欢迎或认证通过，不必真正进 shell）：

```bash
ssh -T git@github.com
ssh -T git@gitee.com
ssh -T git@codeup.aliyun.com
```

若报 `Permission denied (publickey)`，按这个顺序查：

- 公钥是否已保存到对应平台
- `IdentityFile` 路径是否写对、文件是否存在
- `ssh -v` 输出里是否出现 `Offering public key: .../id_rsa.xxx`

## 克隆与远程地址

配置完成后，照常使用各平台的 SSH 地址即可，例如：

```bash
git clone git@github.com:jiangbyte/xxx.git
git clone git@gitee.com:jiangbyte/xxx.git
git clone git@codeup.aliyun.com:组织/项目/仓库.git
```

同一本地仓库挂多个远程时：

```bash
git remote add origin git@github.com:jiangbyte/xxx.git
git remote add gitee git@gitee.com:jiangbyte/xxx.git
git push origin main
git push gitee main
```
