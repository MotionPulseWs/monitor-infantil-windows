"""Envio de correo (spec §6).

Un correo AL DIA (resumen), no por hora. SMTP generico configurado en config.ini
(host/puerto/usuario/contrasena — nunca hardcodeado).

Si la PC estuvo apagada varios dias y quedaron reportes pendientes, se combinan
en UN SOLO correo con secciones por fecha (no uno por dia).

Por ahora NO hay alertas inmediatas: dejar la funcion send_report reutilizable
para poder anadir despues un modo de alerta inmediata sin rediseñar.
"""
from __future__ import annotations

from pathlib import Path

from src.config import ReportConfig, SmtpConfig


def send_report(
    smtp: SmtpConfig,
    report: ReportConfig,
    subject: str,
    html_body: str,
    excel_attachment: Path | None = None,
) -> None:
    """Envia el reporte HTML (con adjunto Excel opcional) via SMTP con STARTTLS."""
    # TODO: construir EmailMessage (email.message); set_content texto plano +
    #       add_alternative(html_body, subtype='html'); adjuntar xlsx si aplica;
    #       smtplib.SMTP(host, port) -> starttls() -> login() -> send_message().
    raise NotImplementedError
