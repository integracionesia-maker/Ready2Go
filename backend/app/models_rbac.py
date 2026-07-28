"""Tablas del RBAC aditivo (patron Bruckner): `roles`, `role_permissions`,
`user_role_grants`.

Vacio a proposito en S0 (costura). El contenido entra en S1 (WP1).

Regla de este archivo: **nunca importa `app.models`**. Las llaves foraneas a
`users` se declaran por nombre de tabla en cadena; `models.py` re-exporta este
modulo al final para registrar las tablas en `Base.metadata`. Un import en
sentido contrario cierra el ciclo y rompe el arranque.
"""

__all__: list[str] = []
