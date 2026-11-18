import openpyxl

from scripts.import_kosis import convert


def test_import_preserves_year_hierarchy_and_household_units(tmp_path):
    path = tmp_path / 'kosis.xlsx'
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(['행정구역별(1)', '행정구역별(2)', '행정구역별(3)', '2025'])
    sheet.append([None, None, None, '비율', '65세이상 1인가구(A) (가구)', '전체 일반가구'])
    sheet.append(['전국', '소계', '소계', 10.9, 2455947, 22495096])
    sheet.append(['서울특별시', '소계', '소계', 9.1, 382064, 4194215])
    sheet.append(['', '중구', '소계', 10.9, 6445, 59346])
    sheet.append(['', '중구', '미제공', '-', '-', '-'])
    book.save(path)
    result = convert(path)
    assert result['year'] == 2025 and len(result['regions']) == 3
    assert result['regions'][0]['elderly_single_households'] == 2455947
    assert result['regions'][2]['region'] == '서울특별시 중구'
    assert result['regions'][2]['level'] == 'district'
