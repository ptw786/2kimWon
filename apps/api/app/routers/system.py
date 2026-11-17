from fastapi import APIRouter, Depends, Request

from .deps import get_conn

router = APIRouter(tags=['system'])


@router.get('/health')
def health(request: Request, conn=Depends(get_conn)):
    ok_db = conn.execute('SELECT 1').fetchone()[0] == 1
    llm = request.app.state.llm
    mode = 'ollama' if llm.mode == 'ollama' else 'rules'
    return {'ok': True, 'db': ok_db,
            'llm': {'mode': mode, 'model': llm.model if mode == 'ollama' else None, 'reachable': llm.reachable()}}
