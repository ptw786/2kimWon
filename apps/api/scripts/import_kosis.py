"""KOSIS 독거노인가구비율 Excel을 출처·연도와 함께 가져온다 (점수에는 사용하지 않음)."""
import argparse
import json
from pathlib import Path

import openpyxl


def convert(path: Path) -> dict:
    book = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        book.worksheets[0].reset_dimensions()
        table = list(book.worksheets[0].values)
        year = str(table[0][3])
        if not year.isdigit() or '65세이상' not in str(table[1][4]).replace(' ', ''):
            raise ValueError('지원하지 않는 KOSIS 표 구조입니다.')
        rows = []
        province, district = '', ''
        for row in table[2:]:
            p, d, sub, ratio, count, total = row[:6]
            if p:
                province, district = str(p), ''
            if d:
                district = '' if d == '소계' else str(d)
            if not all(isinstance(v, (int, float)) for v in (ratio, count, total)):
                continue
            region = ' '.join(x for x in (province, district, sub if sub not in ('소계', '', None) else '') if x)
            rows.append({'region': region, 'level': 'national' if province == '전국' else
                         ('province' if not district else ('district' if sub == '소계' else 'subdistrict')),
                         'elderly_single_households': int(count), 'all_households': int(total),
                         'ratio_percent': ratio})
        return {'source': 'KOSIS 독거노인가구비율(시도/시/군/구)', 'year': int(year),
                'source_file': path.name, 'regions': rows}
    finally:
        book.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'app/data/kosis_households.json')
    args = parser.parse_args()
    data = convert(args.file)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'year': data['year'], 'regions': len(data['regions']), 'national': data['regions'][0]}, ensure_ascii=True))
