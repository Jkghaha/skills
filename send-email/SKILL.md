---
name: send-email
description: 使用本机 Python 脚本通过 QQ SMTP 发送邮件，支持纯文本、HTML 和附件。
allowedTools:
  - Bash(*)
---

# send-email

这个 skill 用于通过本机 Python 脚本发送邮件。

脚本路径：`send_email.py`

## 何时使用

- 用户明确要求“发邮件”“发送邮件”“邮件通知”“把这段内容发到邮箱”。
- 已经具备收件人、主题，以及正文或可由上下文可靠起草的正文。
- 需要发送纯文本、HTML 邮件或带附件的邮件。

## 行为规则

- 当用户明确要求发送邮件且必要信息完整时，可以**直接发送**，无需额外确认。
- 默认收件邮箱是 `3972766883@qq.com`。如果用户没有特别说明收件人，就使用这个邮箱作为默认收件地址。
- 如果缺少主题，或正文内容无法从上下文可靠生成，先向用户补问缺失信息。
- 可以代写邮件内容，但**不要编造事实、时间、承诺、报价、附件内容或收件人信息**。
- 如果用户要发 HTML 邮件，优先同时提供 `text_body` 作为纯文本回退；如果没有，脚本会自动补一个简短的纯文本回退正文，再附上 HTML 正文。
- 附件路径必须是**绝对路径**。如果附件不存在，不要继续发送，直接返回错误。

## 环境变量

脚本从环境变量读取 SMTP 配置：

- `OPENCODE_EMAIL_SMTP_HOST`
- `OPENCODE_EMAIL_SMTP_PORT`
- `OPENCODE_EMAIL_SMTP_USERNAME`
- `OPENCODE_EMAIL_SMTP_PASSWORD`

端口建议使用：

- `465`：直接使用 SSL（QQ 邮箱推荐）
- 其他端口：要求服务器支持 STARTTLS

## 自检命令

```powershell
python ".\send_email.py" --validate-config
```

## 推荐调用方式

使用 PowerShell 对象转 JSON，再通过 stdin 传给脚本，避免正文和 HTML 的转义问题。

在 Windows PowerShell 中，发送包含中文或复杂 HTML 的邮件前，建议先显式切换到 UTF-8：

```powershell
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
```

## 输入约定

stdin JSON 支持这些字段：

- `to`: 字符串或字符串数组
- `subject`: 字符串
- `text_body`: 字符串，可选
- `html_body`: 字符串，可选
- `attachments`: 字符串数组，可选，必须为绝对路径

其中 `text_body` 和 `html_body` 至少要提供一个。
