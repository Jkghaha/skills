import argparse
import json
import locale
import mimetypes
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Iterable, NoReturn

if sys.platform == "win32":
    import winreg


ENV_HOST = "OPENCODE_EMAIL_SMTP_HOST"
ENV_PORT = "OPENCODE_EMAIL_SMTP_PORT"
ENV_USERNAME = "OPENCODE_EMAIL_SMTP_USERNAME"
ENV_PASSWORD = "OPENCODE_EMAIL_SMTP_PASSWORD"


def print_json(data: dict[str, Any], *, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(data, ensure_ascii=False) + "\n")


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def decode_stdin_bytes(raw: bytes) -> str:
    encodings = ["utf-8-sig", "utf-8"]
    preferred = locale.getpreferredencoding(False)
    if preferred and preferred.lower() not in {encoding.lower() for encoding in encodings}:
        encodings.append(preferred)
    if sys.platform == "win32":
        encodings.extend(["gbk", "cp936"])

    tried: list[str] = []
    for encoding in encodings:
        if encoding.lower() in {item.lower() for item in tried}:
            continue
        tried.append(encoding)
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue

    fail("stdin 不是可识别编码的文本。", code="invalid_stdin_encoding", details={"tried": tried})


def fail(message: str, *, code: str = "error", details: dict[str, Any] | None = None) -> NoReturn:
    payload: dict[str, Any] = {"status": "error", "code": code, "message": message}
    if details:
        payload["details"] = details
    print_json(payload, stream=sys.stderr)
    raise SystemExit(1)


def read_stdin_json() -> dict[str, Any]:
    raw_bytes = sys.stdin.buffer.read()
    raw = decode_stdin_bytes(raw_bytes)
    if not raw.strip():
        fail("stdin 为空，未收到 JSON 载荷。", code="empty_stdin")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail("stdin 不是合法 JSON。", code="invalid_json", details={"reason": str(exc)})

    if not isinstance(payload, dict):
        fail("JSON 根节点必须是对象。", code="invalid_payload_type")

    return payload


def read_user_environment_variable(name: str) -> str | None:
    if sys.platform != "win32":
        return None

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
    except FileNotFoundError:
        return None
    except OSError:
        return None

    if isinstance(value, str) and value.strip():
        return value
    return None


def get_config_value(name: str) -> str | None:
    return os.getenv(name) or read_user_environment_variable(name)


def read_env_config() -> dict[str, Any]:
    host = get_config_value(ENV_HOST)
    port_raw = get_config_value(ENV_PORT)
    username = get_config_value(ENV_USERNAME)
    password = get_config_value(ENV_PASSWORD)

    missing = [
        name
        for name, value in (
            (ENV_HOST, host),
            (ENV_PORT, port_raw),
            (ENV_USERNAME, username),
            (ENV_PASSWORD, password),
        )
        if not value
    ]
    if missing:
        fail("缺少 SMTP 环境变量。", code="missing_env", details={"missing": missing})

    try:
        port = int(port_raw)
    except ValueError:
        fail("SMTP 端口不是合法整数。", code="invalid_port", details={"value": port_raw})

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
    }


def normalize_recipients(value: Any) -> list[str]:
    if isinstance(value, str):
        candidates = [item.strip() for item in value.replace(";", ",").split(",")]
    elif isinstance(value, list):
        candidates = []
        for item in value:
            if not isinstance(item, str):
                fail("收件人列表必须全部为字符串。", code="invalid_recipients")
            candidates.append(item.strip())
    else:
        fail("to 必须是字符串或字符串数组。", code="invalid_recipients")

    recipients = [item for item in candidates if item]
    if not recipients:
        fail("至少需要一个有效收件人。", code="missing_recipients")

    invalid = [item for item in recipients if "@" not in item or item.startswith("@") or item.endswith("@")]
    if invalid:
        fail("存在明显无效的收件人地址。", code="invalid_recipients", details={"invalid": invalid})

    return recipients


def normalize_attachments(value: Any) -> list[Path]:
    if value is None:
        return []

    if isinstance(value, str):
        raw_items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, list):
        raw_items = []
        for item in value:
            if not isinstance(item, str):
                fail("attachments 必须是字符串数组。", code="invalid_attachments")
            cleaned = item.strip()
            if cleaned:
                raw_items.append(cleaned)
    else:
        fail("attachments 必须是字符串或字符串数组。", code="invalid_attachments")

    paths = [Path(item) for item in raw_items]
    for path in paths:
        if not path.is_absolute():
            fail("附件路径必须是绝对路径。", code="relative_attachment_path", details={"path": str(path)})
        if not path.exists():
            fail("附件不存在。", code="attachment_not_found", details={"path": str(path)})
        if not path.is_file():
            fail("附件路径不是文件。", code="attachment_not_file", details={"path": str(path)})
    return paths


def require_string(payload: dict[str, Any], key: str, *, required: bool = True) -> str | None:
    value = payload.get(key)
    if value is None:
        if required:
            fail(f"缺少必填字段: {key}", code="missing_field", details={"field": key})
        return None
    if not isinstance(value, str):
        fail(f"字段 {key} 必须是字符串。", code="invalid_field_type", details={"field": key})
    normalized = value.strip()
    if required and not normalized:
        fail(f"字段 {key} 不能为空。", code="empty_field", details={"field": key})
    return normalized or None


def build_message(
    sender: str,
    recipients: Iterable[str],
    subject: str,
    text_body: str | None,
    html_body: str | None,
    attachments: list[Path],
) -> EmailMessage:
    if not text_body and not html_body:
        fail("text_body 和 html_body 至少要提供一个。", code="missing_body")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject

    if text_body:
        message.set_content(text_body)
    else:
        message.set_content("此邮件包含 HTML 内容，请使用支持 HTML 的客户端查看。")

    if html_body:
        message.add_alternative(html_body, subtype="html")

    for attachment_path in attachments:
        mime_type, _ = mimetypes.guess_type(attachment_path.name)
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"

        with attachment_path.open("rb") as file:
            message.add_attachment(
                file.read(),
                maintype=maintype,
                subtype=subtype,
                filename=attachment_path.name,
            )

    return message


def send_message(config: dict[str, Any], message: EmailMessage, recipients: list[str]) -> None:
    host = config["host"]
    port = config["port"]
    username = config["username"]
    password = config["password"]

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=30, context=ssl.create_default_context()) as server:
                server.login(username, password)
                server.send_message(message, from_addr=username, to_addrs=recipients)
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(username, password)
                server.send_message(message, from_addr=username, to_addrs=recipients)
    except smtplib.SMTPAuthenticationError:
        fail("SMTP 认证失败，请检查邮箱账号或授权码。", code="smtp_auth_failed")
    except smtplib.SMTPException as exc:
        fail("SMTP 发送失败。", code="smtp_error", details={"reason": str(exc)})
    except OSError as exc:
        fail("连接 SMTP 服务器失败。", code="smtp_connection_error", details={"reason": str(exc)})


def main() -> None:
    configure_stdio()
    parser = argparse.ArgumentParser(description="通过 SMTP 发送邮件。")
    parser.add_argument("--stdin-json", action="store_true", help="从 stdin 读取 JSON 载荷")
    parser.add_argument("--validate-config", action="store_true", help="仅校验环境变量配置")
    parser.add_argument("--dry-run", action="store_true", help="仅校验输入并输出摘要，不真正发送")
    args = parser.parse_args()

    config = read_env_config()

    if args.validate_config:
        print_json(
            {
                "status": "ok",
                "message": "SMTP 环境变量已就绪。",
                "host": config["host"],
                "port": config["port"],
                "username": config["username"],
            }
        )
        return

    if not args.stdin_json:
        fail("请使用 --stdin-json 并通过 stdin 提供 JSON 载荷。", code="missing_input_mode")

    payload = read_stdin_json()
    recipients = normalize_recipients(payload.get("to"))
    subject = require_string(payload, "subject")
    text_body = require_string(payload, "text_body", required=False)
    html_body = require_string(payload, "html_body", required=False)
    attachments = normalize_attachments(payload.get("attachments"))

    message = build_message(
        sender=config["username"],
        recipients=recipients,
        subject=subject or "",
        text_body=text_body,
        html_body=html_body,
        attachments=attachments,
    )

    summary = {
        "status": "validated" if args.dry_run else "sent",
        "to": recipients,
        "subject": subject,
        "has_text_body": bool(text_body),
        "has_html_body": bool(html_body),
        "attachments": [str(path) for path in attachments],
        "attachment_count": len(attachments),
    }

    if args.dry_run:
        print_json(summary)
        return

    send_message(config, message, recipients)
    print_json(summary)


if __name__ == "__main__":
    main()
