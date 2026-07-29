"""Recordatorio diario de prestamos atrasados.

Corre desde un LaunchAgent del Mac mini, **no** desde un cron dentro de uvicorn
(§7 del plan): un temporizador dentro del proceso web se dispara tantas veces
como trabajadores haya y se pierde en cada reinicio.

Ejecutar desde `backend/` (las rutas de base y uploads son relativas al cwd):

    python scripts/recordatorios_vencimiento.py
    python scripts/recordatorios_vencimiento.py --simular   # no manda nada

Seguro de correr varias veces el mismo dia: el tipo de notificacion lleva el dia
civil de CDMX (`vencimiento:2026-07-30`), asi que el UNIQUE de `notification_log`
significa "un aviso por prestamo, por destinatario, por dia". Dos corridas el
mismo dia no duplican correos; la de mañana si manda uno nuevo, que es lo que
pide un recordatorio diario.
"""

import argparse
import os
import sys
from pathlib import Path

# El script vive en backend/scripts/ pero se ejecuta con cwd = backend/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app import mailer, notificaciones, plantillas_correo as pl, tz  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models_equipos import EstadoPrestamo, Loan  # noqa: E402


def prestamos_atrasados(db, referencia=None) -> list[Loan]:
    """Prestamos entregados cuya fecha de regreso ya paso.

    Solo `prestado`: uno en `pendiente_confirmacion` ya volvio fisicamente y lo
    que falta es el visto bueno del aprobador, no que la persona traiga el
    equipo. Mandarle un recordatorio de vencimiento seria confundirla.
    """
    referencia = referencia or tz.hoy()
    return (
        db.query(Loan)
        .filter(Loan.is_deleted.is_(False))
        .filter(Loan.estado == EstadoPrestamo.PRESTADO.value)
        .filter(Loan.fecha_regreso_esperada.isnot(None))
        .filter(Loan.fecha_regreso_esperada < referencia)
        .order_by(Loan.id)
        .all()
    )


def destinatarios_de(db, prestamo: Loan) -> list[str]:
    """Responsable + aprobadores (§7). Sin repetir si coinciden."""
    correos: list[str] = []
    if prestamo.responsable_email:
        correos.append(prestamo.responsable_email)
    correos.extend(u.email for u in notificaciones.aprobadores(db) if u.email)
    return list(dict.fromkeys(correos))


def correr(db, *, simular: bool = False, referencia=None) -> dict:
    referencia = referencia or tz.hoy()
    tipo = notificaciones.tipo_vencimiento(referencia)

    atrasados = prestamos_atrasados(db, referencia)
    resumen = {"atrasados": len(atrasados), "encolados": 0, "enviados": 0, "tipo": tipo}

    for prestamo in atrasados:
        correos = destinatarios_de(db, prestamo)
        if not correos:
            print(f"  ! {prestamo.folio}: sin destinatarios, no se avisa a nadie")
            continue

        filas = notificaciones.encolar(db, tipo, prestamo, None, destinatarios=correos)
        resumen["encolados"] += len(filas)

        dias = tz.dias_de_atraso(prestamo.fecha_regreso_esperada, referencia)
        print(f"  - {prestamo.folio}: {dias} dia(s) de atraso, {len(filas)} aviso(s) por mandar")

        if simular:
            continue

        _, cuerpo = pl.construir(tipo, notificaciones.datos_de_prestamo(db, prestamo))
        for fila in filas:
            if notificaciones.procesar_pendiente(fila.id, cuerpo):
                resumen["enviados"] += 1

    return resumen


def main() -> None:
    parser = argparse.ArgumentParser(description="Recordatorio diario de prestamos atrasados.")
    parser.add_argument(
        "--simular",
        action="store_true",
        help="Registra los avisos pero no intenta enviarlos.",
    )
    args = parser.parse_args()

    cfg = mailer.config()
    print(f"=== Recordatorios de vencimiento — {tz.hoy().isoformat()} (CDMX) ===")
    print(f"  NOTIF_ENABLED={cfg.habilitado} SMTP_HOST={cfg.host or '(sin configurar)'}")
    if not cfg.habilitado and not args.simular:
        print("  ! Las notificaciones estan apagadas: se registran pero no se envian.")

    db = SessionLocal()
    try:
        resumen = correr(db, simular=args.simular)
    finally:
        db.close()

    print(
        f"Listo: {resumen['atrasados']} prestamo(s) atrasado(s), "
        f"{resumen['encolados']} aviso(s) registrado(s), {resumen['enviados']} enviado(s)."
    )
    # Codigo de salida 0 aunque no se envie nada: para el LaunchAgent, "no hay
    # atrasados" es exito, no fallo.


if __name__ == "__main__":
    main()
