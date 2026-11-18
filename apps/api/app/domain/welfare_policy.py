"""추천용 검토의 유효성·신청 자격 확인. 개인 위험 점수와 독립적인 순수 함수."""
import hashlib
import json

SOURCE_FIELDS = ('id', 'name', 'source', 'ctpv', 'sgg', 'org', 'summary', 'target', 'criteria',
                 'content', 'apply', 'apply_method', 'contact', 'link')


def fingerprint(service: dict) -> str:
    payload = {k: service.get(k) for k in SOURCE_FIELDS}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def accepted(service: dict, review: dict | None) -> bool:
    return bool(review and review.get('decision') == 'include' and review.get('needs')
                and review.get('source_sha256') == fingerprint(service)
                and service.get('availability', 'active') == 'active')


def age_matches(age: int | None, review: dict) -> bool:
    if age is None:
        return True
    minimum, maximum = review.get('min_age'), review.get('max_age')
    return (minimum is None or age >= minimum) and (maximum is None or age <= maximum)


def eligibility(service: dict, age: int | None) -> dict:
    reasons = ['최종 신청·선정 여부는 담당 기관에서 확인해 주세요.']
    if age is None:
        reasons.append('나이 정보를 확인해 주세요.')
    if not service.get('target'):
        reasons.append('지원대상 원문이 없어 공식 상세에서 확인해야 해요.')
    reasons += service.get('_review', {}).get('checks', [])
    if any(len(service.get(k) or '') == 400 for k in ('target', 'criteria', 'content', 'apply')):
        reasons.append('제공된 자료의 원문이 일부 잘렸을 수 있어 공식 상세를 확인해 주세요.')
    return {'status': 'needs_check', 'reasons': list(dict.fromkeys(reasons))}
