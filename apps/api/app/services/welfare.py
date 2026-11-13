"""복지서비스 데이터 어댑터 (F11) — 내려받아 둔 일부(app/data/welfare_subset.json)를 한 번만 읽는다.

네트워크를 쓰지 않으므로 시연은 오프라인에서도 된다. 데이터를 새로 만들려면 scripts/build_welfare_subset.py.
"""
import json
from functools import lru_cache
from pathlib import Path

from ..domain import matching

DATA_PATH = Path(__file__).resolve().parent.parent / 'data' / 'welfare_subset.json'


@lru_cache(maxsize=1)
def load() -> dict:
    try:
        return json.loads(DATA_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'data_as_of': '', 'services': []}


def matches(needs: list[dict], region: str | None) -> list[dict]:
    """어려움 유형마다 WelfareMatch 하나 (needs 순서대로, 같은 유형은 한 번)."""
    data = load()
    seen, out = set(), []
    for n in needs:
        if n['type'] in seen:
            continue
        seen.add(n['type'])
        out.append(matching.match(n['type'], region, data['services'], data['data_as_of']))
    return out
