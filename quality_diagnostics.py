"""수집 체계 변경이 시계열에 남긴 흔적을 진단하고 오염에 강한 보조 지표를 만든다.

산출물
  data/processed/cohort_survival.csv      고정 코호트 잔존율(레벨 시프트에 영향받지 않는 시계열)
  data/processed/registration_lag.csv     업소번호 발급 → 최초 수록까지의 지연 분포
  data/processed/population_stability.csv 회차 전이별 모집단 안정성 진단
  data/processed/region_cross_check.csv   대전·경기 교차 검증(경기 원본이 있을 때만)
  images/07_cohort_survival.png
  images/08_registration_lag.png
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path
from statistics import median

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "processed"
IMAGES = ROOT / "images"
DAEJEON = "00. 대전 상권 데이터/소상공인시장진흥공단_상가(상권)정보_대전_{}.csv"
GYEONGGI = "01. 경기도 상권 데이터/소상공인시장진흥공단_상가(상권)정보_경기_{}.csv"
STAMPS = ["202403", "202406", "202409", "202412", "202503",
          "202506", "202510", "202512", "202603", "202606"]
COHORT_CUT = "202406"  # 수집이 멈추기 직전, 구 체계가 마지막으로 온전했던 발급월
STORE_ID_YM = re.compile(r"MA\d{4}(\d{6})")

INK = "#17212b"
MUTED = "#687582"
GRID = "#e4e9ee"
BLUE = "#1769e0"
TEAL = "#008c7a"
RED = "#d84848"

plt.rcParams.update({
    "font.family": "Malgun Gothic",
    "axes.unicode_minus": False,
    "axes.edgecolor": "#aab4bf",
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def label(stamp: str) -> str:
    return f"{stamp[:4]}-{stamp[4:]}"


def months(stamp: str) -> int:
    return int(stamp[:4]) * 12 + int(stamp[4:]) - 1


def write_csv(name: str, rows: list[dict]) -> None:
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def read_stores(pattern: str, stamp: str) -> list[tuple[str, str]]:
    """(업소번호, 업종 대분류)를 읽는다."""
    with (ROOT / pattern.format(stamp)).open(encoding="utf-8-sig", newline="") as f:
        return [(r["상가업소번호"], r["상권업종대분류명"]) for r in csv.DictReader(f)]


def issued(store_id: str) -> str | None:
    m = STORE_ID_YM.match(store_id)
    return m.group(1) if m else None


def load_daejeon() -> tuple[dict, dict, dict, dict, dict]:
    ids, cats, eligible, first_seen = {}, {}, {}, {}
    for stamp in STAMPS:
        records = read_stores(DAEJEON, stamp)
        ids[stamp] = {sid for sid, _ in records}
        cats[stamp] = Counter(cat for _, cat in records)
        eligible[stamp] = {sid for sid, _ in records
                           if (ym := issued(sid)) and ym <= COHORT_CUT}
        for sid, _ in records:
            first_seen.setdefault(sid, stamp)
    baseline = ids[STAMPS[0]]
    cohorts = {stamp: current & baseline for stamp, current in ids.items()}
    return ids, cats, cohorts, eligible, first_seen


def cohort_survival(ids: dict, cohorts: dict) -> list[dict]:
    base = len(cohorts[STAMPS[0]])
    rows, previous = [], None
    for stamp in STAMPS:
        size = len(cohorts[stamp])
        rows.append({
            "period": f"{stamp[:4]}-{stamp[4:]}-01",
            "total_stores": len(ids[stamp]),
            "cohort_stores": size,
            "cohort_change": size - previous if previous else "",
            "cohort_qoq_pct": round((size / previous - 1) * 100, 2) if previous else "",
            "survival_pct": round(size / base * 100, 2),
        })
        previous = size
    return rows


def registration_lag(first_seen: dict) -> tuple[list[dict], list[int]]:
    """발급 → 최초 수록 지연. 첫 회차 수록분은 좌측 절단이므로 제외한다."""
    by_period: dict[str, list[int]] = {}
    everything: list[int] = []
    for sid, stamp in first_seen.items():
        if stamp == STAMPS[0] or not (ym := issued(sid)):
            continue
        lag = months(stamp) - months(ym)
        by_period.setdefault(stamp, []).append(lag)
        everything.append(lag)
    rows = []
    for stamp in STAMPS[1:]:
        lags = sorted(by_period.get(stamp, []))
        if not lags:
            continue
        rows.append({
            "period": f"{stamp[:4]}-{stamp[4:]}-01",
            "new_stores": len(lags),
            "lag_median_months": round(median(lags), 1),
            "lag_p90_months": lags[int(len(lags) * 0.9)],
            "over_12m_pct": round(sum(x > 12 for x in lags) / len(lags) * 100, 1),
            "over_24m_pct": round(sum(x > 24 for x in lags) / len(lags) * 100, 1),
        })
    return rows, everything


def population_stability(ids: dict, cats: dict, eligible: dict) -> list[dict]:
    rows = []
    for before, after in zip(STAMPS, STAMPS[1:]):
        appeared = len(ids[after] - ids[before])
        disappeared = len(ids[before] - ids[after])
        cohort_change = len(eligible[after]) - len(eligible[before])
        total_before, total_after = sum(cats[before].values()), sum(cats[after].values())
        shifts = {c: cats[after][c] / total_after * 100 - cats[before][c] / total_before * 100
                  for c in cats[after]}
        top, shift = max(shifts.items(), key=lambda kv: abs(kv[1]))
        inflow = appeared / len(ids[before]) * 100
        contaminated = cohort_change > 0 or inflow > 5 or abs(shift) > 0.5
        rows.append({
            "previous_period": f"{before[:4]}-{before[4:]}-01",
            "period": f"{after[:4]}-{after[4:]}-01",
            "appeared": appeared,
            "disappeared": disappeared,
            "inflow_pct": round(inflow, 2),
            "churn_pct": round((appeared + disappeared) / len(ids[before]) * 100, 2),
            "cohort_change": cohort_change,
            "max_share_shift_category": top,
            "max_share_shift_pp": round(shift, 2),
            "verdict": "모집단 변경 의심" if contaminated else "안정",
        })
    return rows


def region_cross_check() -> list[dict]:
    """경기 원본이 있으면 2024-09→2024-12 업종별 증감을 대전과 나란히 둔다."""
    if not (ROOT / GYEONGGI.format("202409")).exists():
        return []
    rows = []
    for region, pattern in (("대전", DAEJEON), ("경기", GYEONGGI)):
        before = Counter(c for _, c in read_stores(pattern, "202409"))
        after = Counter(c for _, c in read_stores(pattern, "202412"))
        for category in sorted(after, key=lambda c: -(after[c] - before[c])):
            rows.append({
                "region": region,
                "category": category,
                "count_202409": before[category],
                "count_202412": after[category],
                "change": after[category] - before[category],
                "change_pct": round((after[category] / before[category] - 1) * 100, 2)
                if before[category] else "",
            })
    return rows


def draw_cohort(rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.2))
    x = range(len(rows))
    total = [r["total_stores"] for r in rows]
    cohort = [r["cohort_stores"] for r in rows]

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)

    for index, name in ((3, "2024-12\n1차 편입"), (6, "2025-10\n2차 편입")):
        ax.axvline(index, color=RED, linewidth=1, linestyle="--", alpha=.55)
        ax.text(index, max(total) * 1.045, name, color=RED, fontsize=9,
                ha="center", va="bottom", linespacing=1.35)

    ax.plot(x, total, color=BLUE, linewidth=2, marker="o", markersize=6,
            markeredgecolor="white", markeredgewidth=1.5, label="수록 총수")
    ax.plot(x, cohort, color=TEAL, linewidth=2, marker="s", markersize=6,
            markeredgecolor="white", markeredgewidth=1.5, label="고정 코호트(2024-03 수록 업소)")

    ax.annotate(f"{total[3]:,}", (3, total[3]), textcoords="offset points",
                xytext=(0, 12), ha="center", fontsize=9, color=INK)
    ax.annotate("기준 회차 수록 업소만 고정해 추적\n(이후 신규·지연 편입은 추가하지 않음)",
                (1, cohort[1]), textcoords="offset points", xytext=(8, -46),
                ha="left", fontsize=8.5, color=MUTED, linespacing=1.4,
                arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=.9,
                                shrinkA=0, shrinkB=4))
    ax.annotate(f"{cohort[-1]:,}\n(잔존율 {rows[-1]['survival_pct']:.1f}%)",
                (len(rows) - 1, cohort[-1]), textcoords="offset points",
                xytext=(-6, -30), ha="center", fontsize=9, color=INK, linespacing=1.35)

    ax.set_xticks(list(x))
    ax.set_xticklabels([label(s) for s in STAMPS], fontsize=9)
    ax.set_ylabel("업소 수")
    ax.set_ylim(min(cohort) * .93, max(total) * 1.12)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
    ax.set_title("수록 총수는 편입 때마다 튀지만 고정 코호트는 완만히 감소한다",
                 fontsize=13, pad=34, loc="left", color=INK)
    ax.legend(frameon=False, fontsize=10, loc="lower left")
    fig.tight_layout()
    fig.savefig(IMAGES / "07_cohort_survival.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def draw_lag(lags: list[int], rows: list[dict]) -> None:
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.8),
                                      gridspec_kw={"width_ratios": [1, 1.15]})
    bands = [(0, 3, "3개월 이하"), (4, 6, "4~6개월"), (7, 12, "7~12개월"),
             (13, 24, "13~24개월"), (25, 36, "25~36개월"), (37, 999, "37개월 이상")]
    counts = [sum(low <= x <= high for x in lags) for low, high, _ in bands]
    share = [c / len(lags) * 100 for c in counts]

    for ax in (left, right):
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        ax.set_axisbelow(True)

    left.grid(axis="y", color=GRID, linewidth=1)
    left.bar(range(len(bands)), share, color=BLUE, width=.62)
    for i, (value, count) in enumerate(zip(share, counts)):
        left.text(i, value + .8, f"{value:.1f}%\n{count:,}건", ha="center",
                  fontsize=8.5, color=INK, linespacing=1.3)
    left.set_xticks(range(len(bands)))
    left.set_xticklabels([b[2] for b in bands], fontsize=8.5, rotation=20, ha="right")
    left.set_ylabel("비중(%)")
    left.set_ylim(0, max(share) * 1.28)
    left.set_title(f"발급에서 최초 수록까지 걸린 기간 (n={len(lags):,})",
                   fontsize=11.5, loc="left", pad=12)

    right.grid(axis="y", color=GRID, linewidth=1)
    over = [r["over_12m_pct"] for r in rows]
    labels = [r["period"][:7] for r in rows]
    colors = [RED if v > 20 else BLUE for v in over]
    right.bar(range(len(rows)), over, color=colors, width=.6)
    for i, value in enumerate(over):
        right.text(i, value + 1.6, f"{value:.0f}%", ha="center", fontsize=9, color=INK)
    right.set_xticks(range(len(rows)))
    right.set_xticklabels(labels, fontsize=8.5, rotation=20, ha="right")
    right.set_ylabel("1년 초과 비중(%)")
    right.set_ylim(0, max(over) * 1.25)
    right.set_title("밀린 물량은 특정 회차에 몰려 들어온다\n회차별 신규 수록분 중 발급 후 1년 넘게 지난 건의 비중",
                    fontsize=11.5, loc="left", pad=12)

    fig.tight_layout()
    fig.savefig(IMAGES / "08_registration_lag.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ids, cats, cohorts, eligible, first_seen = load_daejeon()

    survival = cohort_survival(ids, cohorts)
    write_csv("cohort_survival.csv", survival)

    lag_rows, lags = registration_lag(first_seen)
    write_csv("registration_lag.csv", lag_rows)

    stability = population_stability(ids, cats, eligible)
    write_csv("population_stability.csv", stability)

    cross = region_cross_check()
    if cross:
        write_csv("region_cross_check.csv", cross)

    draw_cohort(survival)
    draw_lag(lags, lag_rows)

    unstable = [r for r in stability if r["verdict"] != "안정"]
    print(f"고정 코호트 잔존율 {survival[0]['survival_pct']:.1f}% → {survival[-1]['survival_pct']:.1f}%")
    print(f"등재 지연 중앙값 {median(lags):.0f}개월 · 1년 초과 "
          f"{sum(x > 12 for x in lags) / len(lags) * 100:.1f}%")
    print("모집단 변경 의심 구간: " + ", ".join(r["period"][:7] for r in unstable))
    print(f"경기 교차 검증 {'포함' if cross else '건너뜀(원본 없음)'}")
    print("images/07_cohort_survival.png, images/08_registration_lag.png 생성 완료")


if __name__ == "__main__":
    main()
