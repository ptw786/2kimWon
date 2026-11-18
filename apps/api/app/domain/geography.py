"""지역명 비교. 원문은 보존하고 검증된 별칭만 비교용으로 정리한다 (I/O 없음)."""
import re

PROVINCES = {
    '서울특별시': ('11', '서울'), '부산광역시': ('26', '부산'), '대구광역시': ('27', '대구'),
    '인천광역시': ('28', '인천'), '광주광역시': ('29', '광주'), '대전광역시': ('30', '대전'),
    '울산광역시': ('31', '울산'), '세종특별자치시': ('36', '세종'), '경기도': ('41', '경기'),
    '강원특별자치도': ('51', '강원도', '강원'), '충청북도': ('43', '충북'), '충청남도': ('44', '충남'),
    '전북특별자치도': ('52', '전라북도', '전북'), '전라남도': ('46', '전남'),
    '경상북도': ('47', '경북'), '경상남도': ('48', '경남'), '제주특별자치도': ('50', '제주도', '제주'),
}
MERGED = '전남광주통합특별시'


def normalize(region: str | None, aliases: dict | None = None) -> str:
    text = ' '.join((region or '').split())
    if aliases and text in aliases:
        return aliases[text]
    if text.startswith(MERGED + ' '):
        # KOSIS에는 하위에 광주광역시/전라남도가 명시된다. 그 외는 임의로 풀지 않는다.
        tail = text[len(MERGED) + 1:]
        if tail.startswith(('광주광역시', '전라남도')):
            return tail
        return text
    for province, values in PROVINCES.items():
        for alias in (province, *values[1:]):
            if text == alias or text.startswith(alias + ' '):
                return province + text[len(alias):]
    return text


def split(region: str | None) -> tuple[str, str]:
    parts = normalize(region).split(maxsplit=1)
    return (parts[0] if parts else '', parts[1] if len(parts) > 1 else '')


def area_key(region: str | None) -> tuple[str, str]:
    province, district = split(region)
    code = PROVINCES.get(province, ('',))[0]
    return code, re.sub(r'\s+', '', district)
