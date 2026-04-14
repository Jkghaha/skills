# OpenCode Skills

这个仓库用于集中存放我的 OpenCode 自定义 skills。

## 当前 skills

- `send-email`：使用本机 Python 脚本通过 QQ SMTP 发送邮件，支持纯文本、HTML 和附件。
- `bubble-tea-master`：根据奶茶配方文档，根据用户提供的需求和可用原料，生成详细的奶茶制作步骤。

## 仓库结构

```text
.
├─ README.md
├─ .gitignore
├─ send-email/
│   ├─ SKILL.md
│   └─ send_email.py
└─ bubble-tea-master/
    └─ SKILL.md
```

## 安装方式

将对应 skill 目录复制到：

```text
~/.config/opencode/skills/
```

例如：

```text
~/.config/opencode/skills/send-email/
```

## send-email 配置

`send-email` 通过环境变量读取 SMTP 配置：

- `OPENCODE_EMAIL_SMTP_HOST`
- `OPENCODE_EMAIL_SMTP_PORT`
- `OPENCODE_EMAIL_SMTP_USERNAME`
- `OPENCODE_EMAIL_SMTP_PASSWORD`

> 不要把真实授权码或密码提交到仓库。
