"""행정동 지표(commercial_analysis.py 산출물)를 시각화한다.

노트북(analysis.ipynb)의 팔레트·스타일 관례를 그대로 따른다:
양수/특화 = #185b79, 음수/취약 = #bb5b28, 보조색 = #5f793e·#7b5596·#747474.

산출물
  images/09_dong_supply_density.png   인구 대비 공급 밀도 상·하위 15개 동
  images/10_dong_lq_heatmap.png       행정동 × 업종 입지계수(LQ) 히트맵
  images/11_diversity_vs_density.png  다양성(HHI) × 공급밀도 4분면
  images/12_dong_survival.png         행정동별 2024-03 고정 코호트 잔존율
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "processed"
IMAGES = ROOT / "images"

BLUE = "#185b79"   # 특화·과밀 (LQ>1, 밀도 높음)
ORANGE = "#bb5b28"  # 취약·과소 (LQ<1, 밀도 낮음)
GREEN = "#5f793e"
PURPLE = "#7b5596"
GRAY = "#747474"
DISTRICT_COLOR = {"동구": BLUE, "중구": ORANGE, "서구": GREEN,
                   "유성구": PURPLE, "대덕구": GRAY}
DISTRICT_ORDER = ["동구", "중구", "서구", "유성구", "대덕구"]

plt.rcParams.update({
    "font.family": "Malgun Gothic",
    "axes.unicode_minus": False,
    "figure.dpi": 110,
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def read_indicators() -> list[dict]:
    with (OUT / "dong_indicators.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["store_count"] = int(r["store_count"])
        r["population"] = int(r["population"])
        r["supply_density_per_1000"] = float(r["supply_density_per_1000"])
        r["hhi"] = float(r["hhi"])
        r["leading_share_pct"] = float(r["leading_share_pct"])
        r["elderly_share_pct"] = float(r["elderly_share_pct"])
        r["youth_share_pct"] = float(r["youth_share_pct"])
        r["baseline_stores"] = int(r["baseline_stores"])
        r["surviving_stores"] = int(r["surviving_stores"])
        r["survival_pct"] = float(r["survival_pct"])
    return rows


def lq_categories(rows: list[dict]) -> list[str]:
    return sorted(k[3:] for k in rows[0] if k.startswith("lq_"))


def save(fig, filename: str) -> None:
    fig.savefig(IMAGES / filename, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def draw_density(rows: list[dict]) -> None:
    ranked = sorted(rows, key=lambda r: -r["supply_density_per_1000"])
    top, bottom = ranked[:15], list(reversed(ranked[-15:]))

    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 6.5))
    for ax, group, title in ((left, top, "공급 밀도 상위 15개 행정동"),
                              (right, bottom, "공급 밀도 하위 15개 행정동")):
        labels = [f"{r['district']} {r['dong']}" for r in group]
        values = [r["supply_density_per_1000"] for r in group]
        y = range(len(group))
        ax.barh(y, [v - 1 for v in values], left=1, color=BLUE, height=.62)
        ax.set_yticks(list(y))
        ax.set_yticklabels(labels, fontsize=8.5)
        ax.invert_yaxis()
        ax.set_xscale("log")
        ax.grid(axis="x", color="#e4e9ee", linewidth=1, which="both")
        ax.set_axisbelow(True)
        ax.set_title(title, fontsize=12, loc="left", pad=10)
        ax.set_xlabel("인구 1,000명당 업소 수 (로그 스케일)")
        for yi, v in zip(y, values):
            ax.text(v + max(values) * .015, yi, f"{v:.1f}", va="center", fontsize=8)
        ax.set_xlim(max(1, min(values) * .65), max(values) * 1.45)

    fig.suptitle("행정동 인구 대비 공급 밀도 — 2026년 3월", fontsize=13, x=.02, ha="left", y=1.02)
    fig.text(.02, -.02,
             "동구 중앙동(585.3개)·중구 대흥동(147.1개)은 원도심 상업지구로 상주인구가 적어 값이 크게 나온다. "
             "인구 1,000명 미만 행정동은 없어 전부 82개를 대상으로 순위를 매겼다.",
             fontsize=8.5, color="#687582")
    fig.tight_layout()
    save(fig, "09_dong_supply_density.png")


def draw_lq_heatmap(rows: list[dict], categories: list[str]) -> None:
    ordered = sorted(rows, key=lambda r: (DISTRICT_ORDER.index(r["district"]), r["dong"]))
    matrix = [[r[f"lq_{c}"] if isinstance(r[f"lq_{c}"], float) else float(r[f"lq_{c}"])
              for c in categories] for r in ordered]
    import math
    log_matrix = [[max(-2, min(2, math.log2(v))) if v > 0 else -2 for v in row]
                  for row in matrix]

    cmap = LinearSegmentedColormap.from_list("lq_diverging", [ORANGE, "#f4f2ee", BLUE])
    norm = Normalize(vmin=-2, vmax=2)  # LQ 0.25배~4배를 대칭 스케일로

    fig, ax = plt.subplots(figsize=(9.5, 19))
    im = ax.imshow(log_matrix, cmap=cmap, norm=norm, aspect="auto")

    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(categories, rotation=40, ha="right", fontsize=9)
    ax.set_yticks(range(len(ordered)))
    ax.set_yticklabels([f"{r['district']} {r['dong']}" for r in ordered], fontsize=7)

    boundary = 0
    for district in DISTRICT_ORDER[:-1]:
        boundary += sum(1 for r in ordered if r["district"] == district)
        ax.axhline(boundary - .5, color="white", linewidth=2.4)

    cbar = fig.colorbar(im, ax=ax, shrink=.35, pad=.02, ticks=[-2, -1, 0, 1, 2])
    cbar.ax.set_yticklabels(["0.25×", "0.5×", "1×(평균)", "2×", "4×"], fontsize=8)
    cbar.set_label("입지계수 LQ (대전 평균 대비 배율)", fontsize=9)

    ax.set_title("행정동 × 업종 입지계수(LQ) — 2026년 3월\n"
                 "진한 파랑=특화(평균보다 밀집), 진한 주황=취약(평균보다 희박)",
                 fontsize=12, loc="left", pad=14)
    fig.tight_layout()
    save(fig, "10_dong_lq_heatmap.png")


def draw_diversity_scatter(rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 7))
    x = [r["supply_density_per_1000"] for r in rows]
    y = [r["hhi"] for r in rows]
    x_med, y_med = sorted(x)[len(x) // 2], sorted(y)[len(y) // 2]

    for district in DISTRICT_ORDER:
        group = [r for r in rows if r["district"] == district]
        ax.scatter([r["supply_density_per_1000"] for r in group],
                  [r["hhi"] for r in group], s=46, color=DISTRICT_COLOR[district],
                  edgecolor="white", linewidth=.8, label=district, alpha=.9, zorder=3)

    ax.axvline(x_med, color=GRAY, linewidth=1.3, linestyle="--", zorder=2)
    ax.axhline(y_med, color=GRAY, linewidth=1.3, linestyle="--", zorder=2)
    ax.text(x_med, 1.002, f"밀도 중앙값 {x_med:.0f}", transform=ax.get_xaxis_transform(),
           fontsize=8, color=GRAY, ha="center", va="bottom")
    ax.set_xscale("log")

    quad_style = dict(fontsize=9.5, color="#687582", ha="center", style="italic")
    x_lo, x_hi = min(x) * .85, max(x) * 1.15
    y_lo, y_hi = min(y) * .9, max(y) * 1.08
    ax.text((x_med + x_hi) / 2, y_hi * .98, "특화 밀집 상권", **quad_style, va="top")
    ax.text((x_lo + x_med) / 2, y_hi * .98, "저활성·단일업종", **quad_style, va="top")
    ax.text((x_med + x_hi) / 2, y_lo * 1.02, "종합 상권", **quad_style, va="bottom")
    ax.text((x_lo + x_med) / 2, y_lo * 1.02, "생활 분산형", **quad_style, va="bottom")

    notable = sorted(rows, key=lambda r: -r["supply_density_per_1000"])[:2] + \
              sorted(rows, key=lambda r: -r["hhi"])[:1] + \
              sorted(rows, key=lambda r: r["hhi"])[:1]
    for r in notable:
        ax.annotate(f"{r['district']} {r['dong']}",
                    (r["supply_density_per_1000"], r["hhi"]),
                    textcoords="offset points", xytext=(6, 5), fontsize=8, color="#17212b")

    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.set_xlabel("인구 1,000명당 업소 수 (로그 스케일)")
    ax.set_ylabel("업종 다양성 HHI (낮을수록 다양)")
    ax.set_title("행정동 상권 유형 — 공급 밀도 × 업종 다양성 (2026년 3월)",
                 fontsize=12.5, loc="left", pad=12)
    ax.grid(color="#e4e9ee", linewidth=1, zorder=0)
    ax.legend(frameon=False, fontsize=9, loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.tight_layout()
    save(fig, "11_diversity_vs_density.png")


def draw_survival(rows: list[dict]) -> None:
    """기준 코호트가 작은 동의 비율 과장을 막고 상·하위 잔존율을 비교한다."""
    eligible = [r for r in rows if r["baseline_stores"] >= 100]
    ranked = sorted(eligible, key=lambda r: (-r["survival_pct"], -r["baseline_stores"]))
    selected = ranked[:10] + ranked[-10:]
    selected.sort(key=lambda r: r["survival_pct"])
    labels = [f"{r['district']} {r['dong']}" for r in selected]
    values = [r["survival_pct"] for r in selected]
    colors = [ORANGE if i < 10 else BLUE for i in range(len(selected))]

    fig, ax = plt.subplots(figsize=(8.5, 7.5))
    y = range(len(selected))
    ax.barh(y, values, color=colors, height=.64)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlim(min(values) - 3, 100)
    ax.grid(axis="x", color="#e4e9ee", linewidth=1)
    ax.set_axisbelow(True)
    ax.set_xlabel("2024-03 기준 코호트 잔존율(%)")
    for yi, value, row in zip(y, values, selected):
        ax.text(value + .3, yi, f"{value:.1f}% (n={row['baseline_stores']:,})",
                va="center", fontsize=8)
    ax.set_title("행정동별 고정 코호트 잔존율 — 2024년 3월 → 2026년 3월",
                 fontsize=12.5, loc="left", pad=12)
    fig.text(.02, .01, "2024년 3월에 수록된 업소를 최초 행정동별로 고정해 추적했다. 기준 업소 100개 이상인 행정동만 순위에 포함했다.",
             fontsize=8.5, color="#687582")
    fig.tight_layout(rect=(0, .035, 1, 1))
    save(fig, "12_dong_survival.png")


def main() -> None:
    rows = read_indicators()
    categories = lq_categories(rows)
    draw_density(rows)
    draw_lq_heatmap(rows, categories)
    draw_diversity_scatter(rows)
    draw_survival(rows)
    print("images/09_dong_supply_density.png")
    print("images/10_dong_lq_heatmap.png")
    print("images/11_diversity_vs_density.png")
    print("images/12_dong_survival.png")


if __name__ == "__main__":
    main()
