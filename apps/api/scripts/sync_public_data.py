"""전체 목록이 정상 수집됐을 때만 해당 범위의 스냅샷을 원자적으로 교체한다."""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

API_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_DIR))

from app.services.public_data import PublicDataClient, PublicDataError, read_key
from scripts.build_welfare_subset import _local


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'services': []}


def _scope(service: dict, province: str) -> bool:
    return service.get('source') == '지자체복지서비스' and (not province or service.get('ctpv') == province)


def _all_rows(client, province: str) -> tuple[list[dict], int]:
    rows, total, page = [], None, 1
    while True:
        batch, count = client.list_services(province, page)
        if total is not None and count != total:
            raise PublicDataError('수집 중 전체 건수가 변경돼 기존 캐시를 유지해요. 다시 수집해 주세요.')
        total = count
        rows.extend(batch)
        if page * 100 >= total:
            break
        if not batch:
            raise PublicDataError('목록이 중간에 비어 있어 기존 캐시를 유지해요.')
        page += 1
    ids = [row.get('servId') for row in rows]
    if len(rows) != total or len(set(ids)) != total or any(not x for x in ids):
        raise PublicDataError('전체 목록 건수·고유 ID가 일치하지 않아 기존 캐시를 유지해요.')
    return rows, total


def sync(province: str, key_file: Path, output: Path) -> int:
    previous = _read(output)
    baseline = _read(API_DIR / 'app/data/welfare_subset.json')
    existing = {s['id']: {**s, 'checked_at': s.get('checked_at', baseline.get('data_as_of'))} for s in baseline['services']}
    existing.update({s['id']: {**s, 'checked_at': s.get('checked_at', previous.get('data_as_of'))} for s in previous['services']})
    stamp = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    updated = {sid: s for sid, s in existing.items() if not _scope(s, province)}
    with httpx.Client(timeout=30) as http:
        client = PublicDataClient(read_key(key_file), http)
        rows, total = _all_rows(client, province)
        listed = {row['servId'] for row in rows}
        for row in rows:
            sid = row['servId']
            if sid not in existing and not _local(row, {}):
                continue
            # 기본 자료와 기존 캐시도 상세를 다시 조회한다. 실패하면 전체 교체를 중단한다.
            detail = client.detail(sid)
            service = _local(row, detail, select=False)
            service.update(checked_at=stamp, availability='active')
            updated[sid] = service
        for sid, service in existing.items():
            if _scope(service, province) and sid not in listed:
                updated[sid] = {**service, 'availability': 'not_listed', 'unavailable_checked_at': stamp}
    data = {'source': '한국사회보장정보원 지자체복지서비스 · data.go.kr/15108347',
            'data_as_of': stamp, 'services': list(updated.values()),
            'collection': {'scope': province or '전국', 'listed': total,
                           'note': '기존 사업 재조회. 신규·내용 변경 사업은 원문 검토 전까지 추천하지 않음.'}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(output)
    print(json.dumps({'scope': province or '전국', 'listed': total, 'stored': len(updated)}, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--province', default='세종특별자치시')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--key-file', type=Path, default=API_DIR.parents[1] / '공공데이터포털 api 키.txt')
    parser.add_argument('--output', type=Path, default=API_DIR / 'app/data/public_data_cache.json')
    args = parser.parse_args()
    try:
        sys.exit(sync('' if args.all else args.province, args.key_file, args.output))
    except (PublicDataError, OSError, ValueError, KeyError, TypeError):
        print('수집에 실패해 기존 캐시를 유지했어요. API 응답·파일·활용 승인을 확인해 주세요.', file=sys.stderr)
        sys.exit(1)
