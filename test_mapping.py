"""실제 연계표의 분리·제외·추가 및 최신 코드 항등 매핑을 검증한다."""
from pathlib import Path
import pandas as pd
from classification import read_crosswalk, build_mapping, normalize_records, aggregate_level, resolve_candidates


def test_mapping():
    path = next(p for p in Path(__file__).parent.glob('*.xlsx') if '업종분류' in p.name)
    taxonomy, original, edges = read_crosswalk(path)
    mapping = build_mapping(taxonomy, edges).set_index('source_small_code')
    assert len(original) == 891 and len(edges) == 889
    current = mapping.loc[taxonomy.small_code]
    assert current.mapping_type.eq('유지').all() and current.mapping_confidence.eq('소분류확정').all()
    assert current.normalized_small_code.tolist() == taxonomy.small_code.tolist()
    assert mapping.loc['D23A04', 'mapping_type'] == '유지'
    assert mapping.loc['D23A03', 'mapping_type'] == '통합'
    assert mapping.loc['D23A09', 'mapping_type'] == '제외'
    # 비고가 유지·통합이어도 실제 관계가 1:N이면 분리로 판정한다.
    assert mapping.loc['Q07A07', 'mapping_type'] == '분리'
    assert mapping.loc['Q07A07', 'mapping_level'] == 'none'
    assert mapping.loc['F14A03', 'mapping_level'] == 'none'
    for code in ['O03A01', 'Q03A02', 'Q10A08', 'F02A05', 'F05A02']:
        assert mapping.loc[code, 'mapping_confidence'] == '중분류확정'
        assert pd.isna(mapping.loc[code, 'normalized_small_code'])
    lookup = taxonomy.set_index('small_code', drop=False).to_dict('index')
    same_major = resolve_candidates(['G20201', 'G20301'], lookup)
    assert same_major['mapping_confidence'] == '대분류확정'
    fixtures = pd.DataFrame({'period': ['과거'] * 2, 'source_small_code': ['O03A01', 'D23A04']})
    normalized = normalize_records(fixtures, mapping.reset_index())
    assert len(normalized) == 2  # 1:N이라도 원본 행을 늘리지 않는다.
    small = aggregate_level(normalized, taxonomy, edges, 'small', ['period']).set_index('category_code')
    assert pd.isna(small.loc['I10103', 'store_count']) and pd.isna(small.loc['I10104', 'store_count'])
    assert small.loc['G20201', 'store_count'] == 1
    assert pd.isna(small.loc['Q10101', 'store_count'])  # 과거 대응 없는 추가 업종
    assert '과거대응' in small.loc['M11201', 'coverage_status']  # 추가+통합의 부분 범위도 불완전
    middle = aggregate_level(normalized, taxonomy, edges, 'middle', ['period']).set_index('category_code')
    assert middle.loc['I101', 'store_count'] == 1
    current_added = normalize_records(pd.DataFrame({'period': ['현재'], 'source_small_code': ['Q10101']}), mapping.reset_index())
    assert current_added.is_added_category.all()
    assert aggregate_level(current_added, taxonomy, edges, 'small', ['period']).set_index('category_code').loc['Q10101', 'store_count'] == 1
    unknown = normalize_records(pd.DataFrame({'source_small_code': ['UNKNOWN']}), mapping.reset_index())
    assert unknown.mapping_type.iloc[0] == '미매핑'
    print('검증 통과: 최신 코드 유지, 통합, 1:N 분리, 상위 분류, 제외, 추가 업종 결측, 미매핑')


if __name__ == '__main__':
    test_mapping()
