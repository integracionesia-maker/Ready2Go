"""Dashboard de Equipos: `GET /api/equipment/dashboard` (contrato §2).

Router aparte con el mismo prefijo que `equipment.py`, incluido **antes** que
el en `main.py`. El contrato lo advierte: "/dashboard se declara ANTES de
/{id:int} o el enrutador se lo traga como id".

Segunda defensa: las rutas por id de `equipment.py` usan `{equipment_id:int}`,
asi que "dashboard" no encaja en el patron ni por accidente. Hay una prueba que
lo verifica, porque el dia que alguien quite el `:int` para aceptar codigos de
equipo, este endpoint deja de existir en silencio.

La ruta del plan §5 decia `/api/equipos/dashboard` (español). Manda el contrato:
`/api/equipment/dashboard`. Mezclar idiomas en el mismo recurso garantiza un bug
de cliente.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud_dashboard_equipos, models, schemas_equipment
from ..database import get_db
from ..rbac import require_perm

router = APIRouter(prefix="/api/equipment", tags=["equipment"])


@router.get("/dashboard", response_model=schemas_equipment.DashboardEquiposResponse)
def dashboard_equipos(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_perm("equipos_inventario", "ver")),
):
    return crud_dashboard_equipos.resumen(db)
