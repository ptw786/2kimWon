"""신규·변경 사업의 원문을 확인하고 내용 해시에 묶인 검토 기록을 저장한다."""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))
from app.domain.welfare_policy import fingerprint
from app.services import welfare


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('id', nargs='?', help='생략하면 검토 대기 사업 목록')
    parser.add_argument('--decision', choices=['include', 'exclude'])
    parser.add_argument('--needs', nargs='+', choices=['meal_difficulty', 'help_request', 'loneliness', 'sleep_problem'])
    parser.add_argument('--reason')
    parser.add_argument('--evidence', help='지원대상·지원내용 원문에서 복사한 근거 구절')
    parser.add_argument('--check', action='append', default=[], help='기관 확인이 필요한 조건 (반복 가능)')
    parser.add_argument('--min-age', type=int)
    parser.add_argument('--max-age', type=int)
    parser.add_argument('--clear-age-limits', action='store_true', help='기존 연령 제한을 명시적으로 해제')
    parser.add_argument('--region', help='원문·지역 대응표로 확인한 적용 지역')
    args = parser.parse_args()
    services, aliases = welfare.catalog()
    if not args.id:
        for s in services:
            if s['_review'].get('source_sha256') != fingerprint(s):
                print(json.dumps({k:v for k,v in s.items() if not k.startswith('_')}, ensure_ascii=False))
        return
    service = next((s for s in services if s['id'] == args.id), None)
    if service is None:
        parser.error('자료에 없는 서비스 ID예요.')
    if not args.decision:
        print(json.dumps({**{k:v for k,v in service.items() if not k.startswith('_')}, 'existing_review': service['_review']}, ensure_ascii=False, indent=2))
        return
    if not args.reason:
        parser.error('검토 이유를 --reason으로 적어 주세요.')
    if args.decision == 'include':
        original = '\n'.join(service.get(k) or '' for k in ('target','criteria','content','summary'))
        if not args.needs or not args.evidence or args.evidence not in original or not args.check:
            parser.error('후보 편입은 --needs, 원문 안의 --evidence, --check 조건이 필요해요.')
    if args.min_age is not None and args.max_age is not None and args.min_age > args.max_age:
        parser.error('최소 나이는 최대 나이보다 클 수 없어요.')
    data = json.loads(welfare.REVIEW_PATH.read_text(encoding='utf-8'))
    from app.domain.geography import normalize
    raw_area = ' '.join(x for x in (service.get('ctpv'),service.get('sgg')) if x)
    previous = data['services'].get(args.id, {})
    minimum = args.min_age if args.min_age is not None else previous.get('min_age')
    maximum = args.max_age if args.max_age is not None else previous.get('max_age')
    if args.clear_age_limits:
        if args.min_age is not None or args.max_age is not None:
            parser.error('--clear-age-limits와 연령 숫자는 함께 쓸 수 없어요.')
        minimum = maximum = None
    if any(x is not None and not 0 <= x <= 130 for x in (minimum, maximum)):
        parser.error('연령 제한은 0~130세 범위여야 해요.')
    if minimum is not None and maximum is not None and minimum > maximum:
        parser.error('기존 조건을 포함한 최소 나이가 최대 나이보다 커요.')
    if args.region is not None and not args.region.strip():
        parser.error('적용 지역을 빈 값으로 지울 수 없어요.')
    data['services'][args.id] = {
        'source_sha256':fingerprint(service), 'decision':args.decision, 'needs':args.needs or [],
        'reason':args.reason, 'evidence':args.evidence, 'checks':args.check,
        'min_age':minimum, 'max_age':maximum,
        'match_region':args.region or previous.get('match_region') or normalize(raw_area, aliases),
        'reviewed_at':date.today().isoformat(), 'reviewer':'원문 확인 CLI 검토 (기관 자격 심사 아님)',
    }
    temp = welfare.REVIEW_PATH.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temp.replace(welfare.REVIEW_PATH)
    print(f'{args.id} 검토 기록을 저장했어요. 기관의 최종 선정·신청 자격 확인은 별도예요.')


if __name__ == '__main__':
    main()
