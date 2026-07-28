"""Tablas del modulo Control de Equipos: `equipment`, `equipment_audit`, `loan`,
`loan_item`, `media_asset`, `responsiva_doc`, `loan_event`, `notification_log`,
`empresa`, `folio_counter`.

Vacio a proposito en S0 (costura). El contenido entra en S2 (WP2).

Misma regla que `models_rbac.py`: **nunca importa `app.models`**. FKs por nombre
de tabla en cadena; `models.py` re-exporta este modulo al final.
"""

__all__: list[str] = []
