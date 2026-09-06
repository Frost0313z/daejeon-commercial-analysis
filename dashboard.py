"""2025-03~2026-03 신뢰도 우선 구간의 인터랙티브 대시보드를 생성한다."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "data" / "processed" / "daejeon_timeseries.csv"
OUT = ROOT / "data" / "processed"
START, END = "2025-03-01", "2026-03-01"
QUARTER_MONTHS = {"03", "06", "09", "12"}


def read_panel() -> list[dict]:
    with SOURCE.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if START <= r["period"] <= END]


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


def main() -> None:
    rows = read_panel()
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

    payload = {"periods": periods, "city": city, "districts": districts,
               "categories": categories, "districtGrowth": district_growth,
               "categoryGrowth": category_growth}
    template = (ROOT / "dashboard-template.html").read_text(encoding="utf-8")
    html = template.replace("__DASHBOARD_DATA__", json.dumps(payload, ensure_ascii=False))
    (ROOT / "interactive-dashboard.html").write_text(html, encoding="utf-8")
    print("interactive-dashboard.html 생성 완료")


if __name__ == "__main__":
    main()
