from fastapi import APIRouter

from app.core.levels import TESTABLE_LEVELS, all_levels

router = APIRouter(prefix="/levels", tags=["levels"])


@router.get("")
def list_levels():
    """Níveis CEFR oficiais. Rota pública: é conteúdo de referência."""
    return {
        "framework": "CEFR",
        "levels": all_levels(),
        "testable_levels": list(TESTABLE_LEVELS),
        "notice": "O teste inicial classifica de Pré-A1 a B2. C1 e C2 exigem avaliação avançada.",
    }
