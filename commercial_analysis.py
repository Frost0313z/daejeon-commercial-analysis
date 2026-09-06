"""행정동 단위 상권 공급 구조 지표를 산출한다.

업종 분류는 analysis.ipynb가 만든 normalized_store_records.csv.gz의 정규화 결과를
그대로 이어받아 리포트 전체에서 같은 업종명을 쓴다. 행정동은 원본 CSV에서 읽어 붙이고,
행정안전부 주민등록 인구(월별 다운로드분)에서 상가 데이터의 10개 관측 시점과
정확히 일치하는 월말 파일을 골라 배후수요 지표의 분모로 쓴다.

산출물
  data/processed/dong_panel.csv       행정동 × 업종 × 시점 패널
  data/processed/dong_population.csv  행정동 × 시점 인구·연령 구조
  data/processed/dong_indicators.csv  행정동별 LQ·HHI·공급밀도·인구구조(2026-03 단면)
  data/processed/dong_indicators_timeseries.csv  행정동 지표 10개 시점
  data/processed/dong_survival.csv    2024-03 고정 코호트의 행정동별 잔존율
"""

from __future__ import annotations

import calendar
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "processed"
RECORDS = OUT / "normalized_store_records.csv.gz"
TIMESERIES = OUT / "daejeon_timeseries.csv"
POP_DIR = ROOT / "01. 인구 데이터"
RAW_PATTERN = "*대전_20[0-9][0-9][0-9][0-9].csv"
STAMPS = ["202403", "202406", "202409", "202412", "202503",
          "202506", "202510", "202512", "202603", "202606"]
FOCUS = "2026-03-01"  # 주 분석 시점. 품질 진단에서 확인한 신뢰 구간의 끝
STAMP_IN_NAME = re.compile(r"_(20\d{4})\.csv$")
AGE_COL = re.compile(r"^(\d+)세(?:남자|여자)$")
AGE_TOP = re.compile(r"^110세이상\s*(?:남자|여자)$")


def read_gzip_records() -> dict[tuple[str, str], str]:
    """(시점, 업소번호) → 정규화 업종 대분류명."""
    import gzip

    with gzip.open(RECORDS, "rt", encoding="utf-8-sig", newline="") as f:
        return {(r["period"], r["상가업소번호"]): r["normalized_major_name"]
                for r in csv.DictReader(f)}


def read_dong() -> dict[tuple[str, str], tuple[str, str, str]]:
    """(시점, 업소번호) → (자치구, 행정동코드, 행정동명)."""
    result = {}
    for path in sorted(ROOT.rglob(RAW_PATTERN)):
        if "processed" in path.parts:
            continue
        stamp = STAMP_IN_NAME.search(path.name).group(1)
        period = f"{stamp[:4]}-{stamp[4:]}-01"
        with path.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                result[(period, r["상가업소번호"])] = (
                    r["시군구명"], r["행정동코드"], r["행정동명"])
    return result


def build_panel(categories: dict, dongs: dict) -> tuple[list[dict], dict]:
    """행정동 × 업종 × 시점의 0값까지 포함한 균형 패널을 만든다."""
    counts: dict[tuple, int] = Counter()
    names: dict[str, tuple[str, str]] = {}
    missing = 0
    for key, category in categories.items():
        location = dongs.get(key)
        if location is None:
            missing += 1
            continue
        district, code, dong = location
        counts[(key[0], code, category)] += 1
        names[code] = (district, dong)
    assert missing == 0, f"행정동을 찾지 못한 업소 {missing:,}건"
    periods = sorted({period for period, _ in categories})
    category_names = sorted(set(categories.values()))
    panel = [{"period": period, "dong_code": code, "district": names[code][0],
              "dong": names[code][1], "category": category,
              "store_count": counts[(period, code, category)]}
             for period in periods for code in sorted(names) for category in category_names]
    assert len(panel) == len(periods) * len(names) * len(category_names)
    return panel, names


def build_survival(dongs: dict, names: dict[str, tuple[str, str]]) -> list[dict]:
    """2024-03 수록 업소를 기준 코호트로 고정하고 최초 행정동별 잔존율을 센다."""
    base_period = "2024-03-01"
    periods = sorted({period for period, _ in dongs})
    present = {period: {store_id for p, store_id in dongs if p == period}
               for period in periods}
    base: dict[str, set[str]] = defaultdict(set)
    for (period, store_id), (_, code, _) in dongs.items():
        if period == base_period:
            base[code].add(store_id)
    rows = []
    for period in periods:
        for code in sorted(names):
            cohort = base[code]
            alive = len(cohort & present[period])
            rows.append({"period": period, "dong_code": code,
                         "district": names[code][0], "dong": names[code][1],
                         "baseline_stores": len(cohort), "surviving_stores": alive,
                         "survival_pct": round(alive / len(cohort) * 100, 2)})
    assert all(r["survival_pct"] == 100 for r in rows if r["period"] == base_period)
    return rows


def verify(panel: list[dict]) -> None:
    """행정동 합계가 기존 자치구 패널과 일치하는지 독립 대조한다."""
    mine: dict[tuple[str, str], int] = Counter()
    for row in panel:
        mine[(row["period"], row["district"])] += row["store_count"]
    theirs: dict[tuple[str, str], int] = Counter()
    with TIMESERIES.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            theirs[(r["period"], r["district"])] += int(float(r["store_count"]))
    assert mine == theirs, "행정동 합계가 자치구 패널과 어긋납니다"
    print(f"검증 통과: {len(mine)}개 (시점×자치구) 조합이 기존 패널과 일치")


# ---------------------------------------------------------------------------
# 인구
# ---------------------------------------------------------------------------

def population_file(period: str) -> Path:
    """상가 데이터 관측월의 마지막 날짜에 해당하는 인구 파일을 찾는다.

    2024-01~2026-07을 월별로 받아 두었으므로 10개 관측 시점 전부 정확히
    일치하는 월말 파일이 존재한다. 분기 보간은 필요 없다.
    """
    year, month = int(period[:4]), int(period[5:7])
    last_day = calendar.monthrange(year, month)[1]
    name = f"행정안전부_지역별(행정동) 성별 연령별 주민등록 인구수_{year}{month:02d}{last_day:02d}.csv"
    path = POP_DIR / name
    assert path.exists(), f"인구 파일을 찾을 수 없습니다: {name}"
    return path


def age_buckets(header: list[str]) -> dict[str, list[int]]:
    """연령별 컬럼 인덱스를 유소년(0-14)·생산연령(15-64)·청년(20-39)·고령(65+)으로 묶는다."""
    buckets = {"age_0_14": [], "age_15_64": [], "age_20_39": [], "age_65_plus": []}
    for i, name in enumerate(header):
        match = AGE_COL.match(name)
        if match:
            age = int(match.group(1))
        elif AGE_TOP.match(name):
            age = 110
        else:
            continue
        if age <= 14:
            buckets["age_0_14"].append(i)
        if 15 <= age <= 64:
            buckets["age_15_64"].append(i)
        if 20 <= age <= 39:
            buckets["age_20_39"].append(i)
        if age >= 65:
            buckets["age_65_plus"].append(i)
    return buckets


def read_population(period: str) -> dict[str, dict]:
    """행정동코드(8자리) → 총인구·연령대별 인구. 대전 82개 행정동만 남긴다."""
    with population_file(period).open(encoding="cp949", newline="") as f:
        reader = csv.reader(f)
        buckets = age_buckets(next(reader))
        result = {}
        for row in reader:
            if row[2] != "대전광역시":
                continue
            code = row[0][:8]  # 인구 코드는 행정동 8자리 + '00'
            result[code] = {"total": int(row[5]),
                            **{name: sum(int(row[i]) for i in idxs)
                               for name, idxs in buckets.items()}}
    assert len(result) == 82, f"{period}: 행정동 {len(result)}개 (82개 기대)"
    return result


def build_population_panel(names: dict[str, tuple[str, str]]) -> list[dict]:
    rows = []
    for stamp in STAMPS:
        period = f"{stamp[:4]}-{stamp[4:]}-01"
        population = read_population(period)
        assert set(population) == set(names), f"{period}: 행정동 코드가 상가 패널과 어긋납니다"
        for code, (district, dong) in sorted(names.items()):
            p = population[code]
            rows.append({
                "period": period, "dong_code": code, "district": district, "dong": dong,
                "population": p["total"], "age_0_14": p["age_0_14"],
                "age_15_64": p["age_15_64"], "age_20_39": p["age_20_39"],
                "age_65_plus": p["age_65_plus"],
                "elderly_share_pct": round(p["age_65_plus"] / p["total"] * 100, 2),
                "youth_share_pct": round(p["age_20_39"] / p["total"] * 100, 2),
            })
    return rows


# ---------------------------------------------------------------------------
# 지표
# ---------------------------------------------------------------------------

def indicators(panel: list[dict], population: dict[str, dict], period: str) -> list[dict]:
    """LQ·HHI·공급밀도·인구구조를 한 시점에 대해 산출한다."""
    rows = [r for r in panel if r["period"] == period]
    by_dong: dict[str, Counter] = defaultdict(Counter)
    city = Counter()
    names = {}
    for r in rows:
        by_dong[r["dong_code"]][r["category"]] += r["store_count"]
        city[r["category"]] += r["store_count"]
        names[r["dong_code"]] = (r["district"], r["dong"])
    city_total = sum(city.values())

    result = []
    for code, categories in sorted(by_dong.items()):
        total = sum(categories.values())
        shares = {c: n / total for c, n in categories.items()}
        hhi = sum(s * s for s in shares.values())
        leading = max(categories.items(), key=lambda kv: kv[1])
        pop = population[code]
        low_population = pop["population"] < 1000
        row = {"dong_code": code, "district": names[code][0], "dong": names[code][1],
               "store_count": total, "population": pop["population"],
               "supply_density_per_1000": None if low_population else
                   round(total / pop["population"] * 1000, 2),
               "low_population_flag": low_population,
               "elderly_share_pct": pop["elderly_share_pct"],
               "youth_share_pct": pop["youth_share_pct"],
               "hhi": round(hhi, 4), "leading_category": leading[0],
               "leading_share_pct": round(leading[1] / total * 100, 2)}
        for category in sorted(city):
            share = shares.get(category, 0.0)
            city_share = city[category] / city_total
            row[f"lq_{category}"] = round(share / city_share, 3)
        result.append(row)
    return result


def check_lq(rows: list[dict], panel: list[dict], period: str) -> None:
    """업소 수로 가중한 LQ 평균은 정의상 1.0이어야 한다."""
    categories = sorted({r["category"] for r in panel if r["period"] == period})
    total = sum(r["store_count"] for r in rows)
    for category in categories:
        weighted = sum(r[f"lq_{category}"] * r["store_count"] for r in rows) / total
        assert abs(weighted - 1) < 0.01, f"{category} 가중 LQ {weighted:.4f}"
    print(f"검증 통과: {len(categories)}개 업종 모두 가중 LQ 평균 1.0")


def correlation(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    return cov / (var_x * var_y) ** 0.5


def population_correlations(rows: list[dict], categories: list[str]) -> list[dict]:
    """행정동 82개를 표본으로 인구 구조와 업종 LQ의 상관을 업종별로 낸다."""
    elderly = [r["elderly_share_pct"] for r in rows]
    youth = [r["youth_share_pct"] for r in rows]
    result = []
    for category in categories:
        lq = [r[f"lq_{category}"] for r in rows]
        result.append({"category": category,
                       "corr_elderly_share": round(correlation(elderly, lq), 3),
                       "corr_youth_share": round(correlation(youth, lq), 3)})
    return sorted(result, key=lambda r: -abs(r["corr_elderly_share"]))


def write_csv(name: str, rows: list[dict]) -> None:
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    categories = read_gzip_records()
    dongs = read_dong()
    panel, names = build_panel(categories, dongs)
    write_csv("dong_panel.csv", panel)
    verify(panel)

    periods = sorted({r["period"] for r in panel})
    category_count = len({r["category"] for r in panel})
    assert len(panel) == len(periods) * len(names) * category_count == 8200
    print(f"균형 패널 {len(panel):,}행 · 행정동 {len(names)}개 · "
          f"업종 {category_count}개 · 시점 {len(periods)}개")

    population_panel = build_population_panel(names)
    write_csv("dong_population.csv", population_panel)
    total_2026_03 = sum(r["population"] for r in population_panel if r["period"] == FOCUS)
    print(f"인구 결합 완료: {len(STAMPS)}개 시점 모두 월말 파일 정확히 매칭 "
          f"(2026-03 대전 인구 합계 {total_2026_03:,}명)")

    survival = build_survival(dongs, names)
    write_csv("dong_survival.csv", survival)
    survival_lookup = {(r["period"], r["dong_code"]): r for r in survival}

    indicator_series = []
    for period in periods:
        population_by_dong = {r["dong_code"]: r for r in population_panel
                              if r["period"] == period}
        period_rows = indicators(panel, population_by_dong, period)
        for row in period_rows:
            cohort = survival_lookup[(period, row["dong_code"])]
            row.update({"period": period,
                        "baseline_stores": cohort["baseline_stores"],
                        "surviving_stores": cohort["surviving_stores"],
                        "survival_pct": cohort["survival_pct"]})
        indicator_series.extend(period_rows)
    write_csv("dong_indicators_timeseries.csv", indicator_series)

    rows = [r for r in indicator_series if r["period"] == FOCUS]
    check_lq(rows, panel, FOCUS)
    write_csv("dong_indicators.csv", rows)

    low = [r for r in rows if r["low_population_flag"]]
    print(f"인구 1,000명 미만 행정동 {len(low)}개" + (f": {[r['dong'] for r in low]}" if low else ""))

    ranked = sorted((r for r in rows if not r["low_population_flag"]),
                    key=lambda r: -r["supply_density_per_1000"])
    print(f"\n{FOCUS[:7]} 인구 1,000명당 업소 수 상위 5개 행정동")
    for r in ranked[:5]:
        print(f"  {r['district']} {r['dong']:<8}{r['supply_density_per_1000']:>6.1f}개 "
              f"(업소 {r['store_count']:,} / 인구 {r['population']:,})")
    print(f"\n{FOCUS[:7]} 인구 1,000명당 업소 수 하위 5개 행정동")
    for r in ranked[-5:]:
        print(f"  {r['district']} {r['dong']:<8}{r['supply_density_per_1000']:>6.1f}개 "
              f"(업소 {r['store_count']:,} / 인구 {r['population']:,})")

    categories = sorted({r["category"] for r in panel if r["period"] == FOCUS})
    corr_rows = population_correlations(rows, categories)
    write_csv("population_category_correlation.csv", corr_rows)
    print(f"\n인구 구조 ↔ 업종 LQ 상관계수 (행정동 {len(rows)}개, |고령 상관| 큰 순)")
    print(f"{'업종':<26}{'고령비율':>10}{'청년비율':>10}")
    for r in corr_rows:
        print(f"{r['category']:<26}{r['corr_elderly_share']:>+10.3f}{r['corr_youth_share']:>+10.3f}")


if __name__ == "__main__":
    main()
