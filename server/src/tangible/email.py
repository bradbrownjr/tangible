"""SMTP email delivery for Tangible alert notifications."""

from __future__ import annotations

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from tangible.config import Settings

log = structlog.get_logger(__name__)


def _smtp_configured(settings: Settings) -> bool:
    return bool(settings.smtp_host and settings.smtp_from)


def send_alert_digest(
    *,
    settings: Settings,
    to_email: str,
    username: str,
    alerts: list[dict],
) -> None:
    """Send a digest email of pending alerts to one user.

    ``alerts`` is a list of dicts with keys: kind, title, due_at, details.
    Does nothing if SMTP is not configured.
    """
    if not _smtp_configured(settings):
        log.debug("smtp_not_configured_skip_email")
        return
    if not to_email:
        return

    subject = f"Tangible — {len(alerts)} alert{'s' if len(alerts) != 1 else ''} need attention"
    body_text = _render_text(username, alerts)
    body_html = _render_html(username, alerts, settings.public_url)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from  # type: ignore[assignment]
    msg["To"] = to_email
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        if settings.smtp_starttls:
            ctx = ssl.create_default_context()
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:  # type: ignore[arg-type]
                smtp.ehlo()
                smtp.starttls(context=ctx)
                smtp.ehlo()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password or "")
                smtp.sendmail(settings.smtp_from, to_email, msg.as_string())
        else:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=ctx) as smtp:  # type: ignore[arg-type]
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password or "")
                smtp.sendmail(settings.smtp_from, to_email, msg.as_string())
        log.info("alert_email_sent", to=to_email, count=len(alerts))
    except Exception as exc:
        log.warning("alert_email_failed", to=to_email, error=str(exc))


def test_smtp_connection(settings: Settings, to_email: str) -> tuple[bool, str]:
    """Open an SMTP connection, authenticate, and send a test email.

    Returns (True, "OK") on success or (False, error_message) on failure.
    """
    from email.mime.text import MIMEText as _MIMEText

    msg = _MIMEText("This is a test email from Tangible to verify your SMTP configuration.", "plain", "utf-8")
    msg["Subject"] = "Tangible — SMTP test"
    msg["From"] = settings.smtp_from  # type: ignore[assignment]
    msg["To"] = to_email

    try:
        if settings.smtp_starttls:
            ctx = ssl.create_default_context()
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:  # type: ignore[arg-type]
                smtp.ehlo()
                smtp.starttls(context=ctx)
                smtp.ehlo()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password or "")
                smtp.sendmail(settings.smtp_from, to_email, msg.as_string())
        else:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=ctx) as smtp:  # type: ignore[arg-type]
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password or "")
                smtp.sendmail(settings.smtp_from, to_email, msg.as_string())
        log.info("smtp_test_sent", to=to_email)
        return True, f"Test email sent to {to_email}"
    except Exception as exc:
        log.warning("smtp_test_failed", error=str(exc))
        return False, str(exc)


_KIND_LABELS = {
    "maintenance_due": "Maintenance due",
    "chore_due": "Chore due",
    "item_use_by": "Item use-by",
    "item_expires": "Item expires",
    "lot_use_by": "Package use-by",
    "low_stock": "Low stock",
}


def _render_text(username: str, alerts: list[dict]) -> str:
    lines = [f"Hi {username},", "", "The following items need your attention:", ""]
    for a in alerts:
        label = _KIND_LABELS.get(a["kind"], a["kind"])
        line = f"  [{label}] {a['title']}"
        if a.get("due_at"):
            line += f"  (due {a['due_at'][:10]})"
        if a.get("details"):
            line += f"\n    {a['details']}"
        lines.append(line)
    lines += ["", "View your full maintenance agenda at your Tangible instance.", ""]
    return "\n".join(lines)


def _render_html(username: str, alerts: list[dict], public_url: str) -> str:
    rows = []
    for a in alerts:
        label = _KIND_LABELS.get(a["kind"], a["kind"])
        due = f"<small>{a['due_at'][:10]}</small>" if a.get("due_at") else ""
        detail = f"<br><small>{a['details']}</small>" if a.get("details") else ""
        rows.append(
            f"<tr>"
            f"<td style='padding:6px 12px;color:#6b7280'>{label}</td>"
            f"<td style='padding:6px 12px'><strong>{a['title']}</strong>{detail}</td>"
            f"<td style='padding:6px 12px;color:#6b7280'>{due}</td>"
            f"</tr>"
        )
    rows_html = "\n".join(rows)
    maintenance_url = f"{public_url.rstrip('/')}/maintenance"
    return f"""<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;color:#111;max-width:600px;margin:0 auto">
<h2>Tangible — alerts for {username}</h2>
<p>The following items need your attention:</p>
<table style="width:100%;border-collapse:collapse">
<thead>
<tr style="background:#f3f4f6">
<th style="padding:8px 12px;text-align:left">Type</th>
<th style="padding:8px 12px;text-align:left">Alert</th>
<th style="padding:8px 12px;text-align:left">Due</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
<p style="margin-top:1.5rem">
<a href="{maintenance_url}" style="color:#4f46e5">View full maintenance agenda</a>
</p>
<hr style="border:none;border-top:1px solid #e5e7eb;margin-top:2rem">
<p style="font-size:0.75rem;color:#9ca3af">
You are receiving this because you have alert notifications enabled in Tangible settings.
</p>
</body>
</html>"""
