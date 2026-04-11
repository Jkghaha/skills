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

    fail("stdin 涓嶆槸鍙瘑鍒紪鐮佺殑鏂囨湰銆?, code="invalid_stdin_encoding", details={"tried": tried})


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
        fail("stdin 涓虹┖锛屾湭鏀跺埌 JSON 杞借嵎銆?, code="empty_stdin")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail("stdin 涓嶆槸鍚堟硶 JSON銆?, code="invalid_json", details={"reason": str(exc)})

    if not isinstance(payload, dict):
        fail("JSON 鏍硅妭鐐瑰繀椤绘槸瀵硅薄銆?, code="invalid_payload_type")

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
        fail("缂哄皯 SMTP 鐜鍙橀噺銆?, code="missing_env", details={"missing": missing})

    try:
        port = int(port_raw)
    except ValueError:
        fail("SMTP 绔彛涓嶆槸鍚堟硶鏁存暟銆?, code="invalid_port", details={"value": port_raw})

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
                fail("鏀朵欢浜哄垪琛ㄥ繀椤诲叏閮ㄤ负瀛楃涓层€?, code="invalid_recipients")
            candidates.append(item.strip())
    else:
        fail("to 蹇呴』鏄瓧绗︿覆鎴栧瓧绗︿覆鏁扮粍銆?, code="invalid_recipients")

    recipients = [item for item in candidates if item]
    if not recipients:
        fail("鑷冲皯闇€瑕佷竴涓湁鏁堟敹浠朵汉銆?, code="missing_recipients")

    invalid = [item for item in recipients if "@" not in item or item.startswith("@") or item.endswith("@")]
    if invalid:
        fail("瀛樺湪鏄庢樉鏃犳晥鐨勬敹浠朵汉鍦板潃銆?, code="invalid_recipients", details={"invalid": invalid})

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
                fail("attachments 蹇呴』鏄瓧绗︿覆鏁扮粍銆?, code="invalid_attachments")
            cleaned = item.strip()
            if cleaned:
                raw_items.append(cleaned)
    else:
        fail("attachments 蹇呴』鏄瓧绗︿覆鎴栧瓧绗︿覆鏁扮粍銆?, code="invalid_attachments")

    paths = [Path(item) for item in raw_items]
    for path in paths:
        if not path.is_absolute():
            fail("闄勪欢璺緞蹇呴』鏄粷瀵硅矾寰勩€?, code="relative_attachment_path", details={"path": str(path)})
        if not path.exists():
            fail("闄勪欢涓嶅瓨鍦ㄣ€?, code="attachment_not_found", details={"path": str(path)})
        if not path.is_file():
            fail("闄勪欢璺緞涓嶆槸鏂囦欢銆?, code="attachment_not_file", details={"path": str(path)})
    return paths


def require_string(payload: dict[str, Any], key: str, *, required: bool = True) -> str | None:
    value = payload.get(key)
    if value is None:
        if required:
            fail(f"缂哄皯蹇呭～瀛楁: {key}", code="missing_field", details={"field": key})
        return None
    if not isinstance(value, str):
        fail(f"瀛楁 {key} 蹇呴』鏄瓧绗︿覆銆?, code="invalid_field_type", details={"field": key})
    normalized = value.strip()
    if required and not normalized:
        fail(f"瀛楁 {key} 涓嶈兘涓虹┖銆?, code="empty_field", details={"field": key})
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
        fail("text_body 鍜?html_body 鑷冲皯瑕佹彁渚涗竴涓€?, code="missing_body")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject

    if text_body:
        message.set_content(text_body)
    else:
        message.set_content("姝ら偖浠跺寘鍚?HTML 鍐呭锛岃浣跨敤鏀寔 HTML 鐨勫鎴风鏌ョ湅銆?)

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
        fail("SMTP 璁よ瘉澶辫触锛岃妫€鏌ラ偖绠辫处鍙锋垨鎺堟潈鐮併€?, code="smtp_auth_failed")
    except smtplib.SMTPException as exc:
        fail("SMTP 鍙戦€佸け璐ャ€?, code="smtp_error", details={"reason": str(exc)})
    except OSError as exc:
        fail("杩炴帴 SMTP 鏈嶅姟鍣ㄥけ璐ャ€?, code="smtp_connection_error", details={"reason": str(exc)})


def main() -> None:
    configure_stdio()
    parser = argparse.ArgumentParser(description="閫氳繃 SMTP 鍙戦€侀偖浠躲€?)
    parser.add_argument("--stdin-json", action="store_true", help="浠?stdin 璇诲彇 JSON 杞借嵎")
    parser.add_argument("--validate-config", action="store_true", help="浠呮牎楠岀幆澧冨彉閲忛厤缃?)
    parser.add_argument("--dry-run", action="store_true", help="浠呮牎楠岃緭鍏ュ苟杈撳嚭鎽樿锛屼笉鐪熸鍙戦€?)
    args = parser.parse_args()

    config = read_env_config()

    if args.validate_config:
        print_json(
            {
                "status": "ok",
                "message": "SMTP 鐜鍙橀噺宸插氨缁€?,
                "host": config["host"],
                "port": config["port"],
                "username": config["username"],
            }
        )
        return

    if not args.stdin_json:
        fail("璇蜂娇鐢?--stdin-json 骞堕€氳繃 stdin 鎻愪緵 JSON 杞借嵎銆?, code="missing_input_mode")

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
