"""2025-03~2026-03 신뢰도 우선 구간의 인터랙티브 대시보드를 생성한다."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import median


Store = tuple[str, str, str, float, float]  # 업소번호, 자치구, 업종, 위도, 경도

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "data" / "processed" / "daejeon_timeseries.csv"
OUT = ROOT / "data" / "processed"
BOUNDARIES = OUT / "daejeon_district_boundaries.geojson"
DONG_BOUNDARIES = OUT / "daejeon_dong_boundaries.geojson"
DONG_INDICATORS = OUT / "dong_indicators_timeseries.csv"
START, END = "2025-03-01", "2026-03-01"
QUARTER_MONTHS = {"03", "06", "09", "12"}
DAEJEON_BBOX = ((36.1, 36.6), (127.2, 127.7))  # 좌표계 오류 회차를 가려내기 위한 대전 외곽 범위


def read_panel() -> list[dict]:
    with SOURCE.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def aggregate(rows: list[dict], key: str) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        result[row[key]][row["period"]] += int(float(row["store_count"]))
    return {name: dict(values) for name, values in result.items()}


def growth(series: dict[str, dict[str, int]]) -> list[dict]:
    result = []
    for name, values in series.items():
        start, end = values[START], values[END]
        result.append({"name": name, "start": start, "end": end,
                       "change": end - start, "growth_pct": (end / start - 1) * 100})
    return sorted(result, key=lambda x: x["change"], reverse=True)


def write_csv(name: str, rows: list[dict]) -> None:
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def read_points(path: Path) -> list[Store]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [(r["상가업소번호"], r["시군구명"], r["상권업종대분류명"],
                 float(r["위도"]), float(r["경도"])) for r in csv.DictReader(f)]


def in_daejeon(lat: float, lon: float) -> bool:
    (lat_min, lat_max), (lon_min, lon_max) = DAEJEON_BBOX
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def repair_points(points: list[Store], neighbours: list[list[Store]]) -> list[Store]:
    """좌표계가 통째로 어긋난 회차를 인접 회차의 업소 좌표로 되돌린다."""
    reference: dict[str, tuple[float, float]] = {}
    for other in neighbours:
        for store_id, _, _, lat, lon in other:
            if store_id not in reference and in_daejeon(lat, lon):
                reference[store_id] = (lat, lon)
    shifts = [(lat - reference[s][0], lon - reference[s][1])
              for s, _, _, lat, lon in points if s in reference]
    assert shifts, "보정 기준으로 삼을 공통 업소가 없습니다"
    lat_shift = median(s[0] for s in shifts)
    lon_shift = median(s[1] for s in shifts)
    matched = sum(s in reference for s, *_ in points)
    print(f"  업소번호 매칭 {matched}/{len(points)}건, "
          f"나머지는 위도 {lat_shift:+.4f}·경도 {lon_shift:+.4f} 평행이동으로 보정")
    return [(store_id, district, category,
             *reference.get(store_id, (lat - lat_shift, lon - lon_shift)))
            for store_id, district, category, lat, lon in points]


def grid_rows(points: list[Store]) -> list[dict]:
    """격자로 묶되 대표 좌표는 격자 중심이 아니라 그 안 상가들의 무게중심으로 둔다.

    대표점이 격자 안에 머무르므로 대시보드는 좌표를 0.01도로 되돌려 격자를 복원한다.
    """
    cells: dict[tuple, list[float]] = defaultdict(lambda: [0, 0.0, 0.0])
    for _, district, category, lat, lon in points:
        cell = cells[(round(lat, 2), round(lon, 2), district, category)]
        cell[0] += 1
        cell[1] += lat
        cell[2] += lon
    # 무게중심이 격자 경계에 걸리면 되돌릴 때 이웃 격자로 넘어가므로 안쪽으로 묶는다.
    mean = lambda total, count, center: round(
        min(max(total / count, center - 0.0049), center + 0.0049), 5)
    ordered = sorted(cells.items())
    rows = [{"lat": mean(lat_sum, count, cell_lat), "lon": mean(lon_sum, count, cell_lon),
             "district": district, "category": category, "count": count}
            for (cell_lat, cell_lon, district, category), (count, lat_sum, lon_sum) in ordered]
    assert all((round(r["lat"], 2), round(r["lon"], 2)) == cell[:2]
               for r, (cell, _) in zip(rows, ordered)), "대표점이 원래 격자를 벗어났습니다"
    return rows


def spatial_grids() -> dict[str, list[dict]]:
    """시점별 격자 집계를 만든다. 원본이 없으면 이전에 저장한 격자 CSV를 읽는다."""
    raw_files = {p.name[-10:-4]: p for p in ROOT.rglob("*20[0-9][0-9][0-9][0-9].csv")
                 if "processed" not in p.parts}
    if raw_files:
        grids = {}
        stamps = sorted(raw_files)
        for i, stamp in enumerate(stamps):
            points = read_points(raw_files[stamp])
            inside = sum(in_daejeon(lat, lon) for _, _, _, lat, lon in points)
            if inside < len(points) / 2:
                print(f"{stamp}: 좌표가 대전 범위를 벗어나 인접 회차 기준으로 보정합니다.")
                neighbours = [read_points(raw_files[s])
                              for s in stamps[max(i - 1, 0):i] + stamps[i + 1:i + 2]]
                points = repair_points(points, neighbours)
            rows = grid_rows(points)
            write_csv(f"store_location_grid_{stamp}.csv", rows)
            grids[f"{stamp[:4]}-{stamp[4:]}-01"] = rows
        return grids
    grids = {}
    for path in sorted(OUT.glob("store_location_grid_20[0-9][0-9][0-9][0-9].csv")):
        stamp = path.stem[-6:]
        with path.open(encoding="utf-8-sig", newline="") as f:
            grids[f"{stamp[:4]}-{stamp[4:]}-01"] = [
                {**r, "lat": float(r["lat"]), "lon": float(r["lon"]),
                 "count": int(r["count"])} for r in csv.DictReader(f)]
    return grids


def dong_metrics() -> dict[str, list[dict]]:
    """지도에 필요한 행정동 지표만 숫자로 변환해 시점별로 묶는다."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    with DONG_INDICATORS.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            grouped[row["period"]].append({
                "dong_code": row["dong_code"], "district": row["district"],
                "dong": row["dong"],
                "density": float(row["supply_density_per_1000"]),
                "hhi": float(row["hhi"]),
                "survival": float(row["survival_pct"]),
            })
    return dict(grouped)


def main() -> None:
    panel = read_panel()
    totals: dict[str, int] = defaultdict(int)
    for row in panel:
        totals[row["period"]] += int(float(row["store_count"]))
    rows = [r for r in panel if START <= r["period"] <= END]
    districts = aggregate(rows, "district")
    categories = aggregate(rows, "category")
    periods = sorted({r["period"] for r in rows if r["period"][5:7] in QUARTER_MONTHS})
    city = {p: sum(values.get(p, 0) for values in districts.values()) for p in periods}
    district_growth, category_growth = growth(districts), growth(categories)
    assert sum(r["change"] for r in district_growth) == sum(r["change"] for r in category_growth) == city[END] - city[START]
    summary = [{"start_period": START, "end_period": END, "start_count": city[START],
                "end_count": city[END], "change": city[END] - city[START],
                "growth_pct": (city[END] / city[START] - 1) * 100}]
    write_csv("reliable_period_summary.csv", summary)
    write_csv("reliable_period_district_growth.csv", district_growth)
    write_csv("reliable_period_category_growth.csv", category_growth)

    map_points = spatial_grids()
    assert END in map_points
    for period, points in map_points.items():
        assert sum(r["count"] for r in points) == totals[period], period
    boundaries = json.loads(BOUNDARIES.read_text(encoding="utf-8-sig"))
    assert {f["properties"]["district"] for f in boundaries["features"]} == set(districts)
    dong_boundaries = json.loads(DONG_BOUNDARIES.read_text(encoding="utf-8-sig"))
    metrics = dong_metrics()
    dong_codes = {f["properties"]["dong_code"] for f in dong_boundaries["features"]}
    assert len(dong_codes) == 82
    assert all({r["dong_code"] for r in rows} == dong_codes for rows in metrics.values())
    assert set(metrics) == set(map_points)
    payload = {"periods": periods, "city": city, "districts": districts,
               "categories": categories, "districtGrowth": district_growth,
               "categoryGrowth": category_growth, "mapPeriods": sorted(map_points),
               "mapPoints": map_points, "boundaries": boundaries,
               "dongBoundaries": dong_boundaries, "dongMetrics": metrics}
    template = (ROOT / "dashboard-template.html").read_text(encoding="utf-8")
    html = template.replace("__DASHBOARD_DATA__", json.dumps(payload, ensure_ascii=False))
    (ROOT / "interactive-dashboard.html").write_text(html, encoding="utf-8")
    print("interactive-dashboard.html 생성 완료")


if __name__ == "__main__":
    main()
