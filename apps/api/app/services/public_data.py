"""공공데이터포털 XML 어댑터. 인증키·요청 URL을 오류나 로그에 노출하지 않는다."""
import os
import re
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET

import httpx

LOCAL_URL = 'https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations'
FACILITY_URL = 'https://apis.data.go.kr/B554287/sclWlfrFcltInfoInqirService2'


class PublicDataError(Exception):
    """인증키가 제거된 사용자용 오류."""


def read_key(path: Path) -> str:
    value = os.environ.get('DATA_GO_KR_SERVICE_KEY', '').strip()
    if not value:
        text = path.read_text(encoding='utf-8-sig')
        candidates = re.findall(r'[A-Za-z0-9%+/=]{40,}', text)
        if len(set(candidates)) != 1:
            raise PublicDataError('키 파일에는 인증키 한 개만 넣어 주세요.')
        value = candidates[0]
    return unquote(value)


def xml_value(element):
    """반복·중첩된 문의처도 보존한다. 키/요청 URL은 반환값에 포함하지 않는다."""
    if not len(element):
        return element.text or ''
    out = {}
    for child in element:
        value = xml_value(child)
        if child.tag in out:
            prior = out[child.tag]
            out[child.tag] = prior + [value] if isinstance(prior, list) else [prior, value]
        else:
            out[child.tag] = value
    return out


class PublicDataClient:
    def __init__(self, key: str, client: httpx.Client):
        self.key = key
        self.client = client

    def get_xml(self, operation: str, params: dict, base: str = LOCAL_URL) -> ET.Element:
        try:
            response = self.client.get(f'{base}/{operation}',
                                       params={'serviceKey': self.key, **params})
            root = ET.fromstring(response.content)
        except (httpx.HTTPError, ET.ParseError):
            raise PublicDataError('공공데이터 요청 실패: 네트워크·응답 형식을 확인해 주세요.') from None
        code = root.findtext('.//resultCode') or root.findtext('.//returnReasonCode')
        if code not in ('0', '00', '0000'):
            safe_code = code if code and re.fullmatch(r'\d{1,4}', code) else 'unknown'
            raise PublicDataError(f'공공데이터 응답 코드 {safe_code}: 활용 신청 승인과 요청변수를 확인해 주세요.')
        if response.is_error:
            raise PublicDataError('공공데이터 서버가 요청을 처리하지 못했어요.')
        return root

    def list_services(self, province: str, page: int = 1) -> tuple[list[dict], int]:
        root = self.get_xml('LcgvWelfarelist', {
            'pageNo': page, 'numOfRows': 100, 'ctpvNm': province,
        })
        rows = [{child.tag: child.text or '' for child in row} for row in root.findall('.//servList')]
        return rows, int(root.findtext('.//totalCount') or '0')

    def detail(self, service_id: str) -> dict:
        if not re.fullmatch(r'WLF\d+', service_id):
            raise PublicDataError('상세조회에는 목록에서 받은 WLF 서비스 ID가 필요해요.')
        root = self.get_xml('LcgvWelfaredetailed', {'servId': service_id})
        return xml_value(root)

    def facilities(self, region: str, operation: str) -> list[dict]:
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9]+', operation):
            raise PublicDataError('시설 API 명세에 표시된 오퍼레이션명을 입력해 주세요.')
        root = self.get_xml(operation, {
            'pageNo': 1, 'numOfRows': 100, 'jrsdSggNm': region, 'fcltKindNm': '노인',
        }, FACILITY_URL)
        return [{child.tag: child.text or '' for child in row} for row in root.findall('.//item')]
