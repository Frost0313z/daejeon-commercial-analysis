# 대전 상권 데이터 분석

> **2024~2026년 대전광역시 상가(상권)정보를 활용해 상가 수 변화와 2024년 말 급증의 성격을 검토한 시계열 분석 프로젝트입니다.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626?logo=jupyter&logoColor=white)](analysis.ipynb)
[![Data](https://img.shields.io/badge/Data-Public_Data-0B5FFF)](https://www.data.go.kr/data/15083033/fileData.do)
[![Status](https://img.shields.io/badge/Analysis-Verified-1F883D)](REPORT.md)

**바로가기:** [📈 인터랙티브 대시보드](interactive-dashboard.html) · [📘 전체 분석 리포트](REPORT.md) · [📓 실행 가능한 노트북](analysis.ipynb) · [📊 핵심 시계열 데이터](data/processed/daejeon_timeseries.csv)

---

## 프로젝트를 한눈에 보기

| 항목 | 내용 |
| --- | --- |
| 분석 대상 | 대전광역시 5개 자치구의 상가(상권)정보 |
| 분석 기간 | 2024-03 ~ 2026-06 |
| 원본 규모 | CSV 10개, 관측 행 763,839개, 고유 업소번호 114,542개 |
| 시계열 패널 | 5개 구 × 대분류 10개 × 관측월 10개 = 500행 |
| 핵심 비교 기간 | 2025-03 ~ 2026-03 |
| 시각화 | 위치 지도 포함 인터랙티브 HTML 1개, 추세·지역·업종·업소 이동 PNG 5개 |

## 한눈에 보는 결론

1. **신뢰 구간의 대전 전체 상가 수는 2025년 3월 77,904개에서 2026년 3월 78,607개로 703개(+0.90%) 증가했습니다.**
2. **증가율은 유성구(+1.30%), 절대 증가량은 서구(+299개)가 가장 높았습니다.** 업종별로는 수리 및 개인 서비스업이 +427개로 가장 많이 늘었고, 부동산업은 +9.82%로 증가율이 가장 높았습니다. 음식점업은 506개(-2.14%) 감소했습니다.
3. **2024년 9월에서 12월 사이에는 11,722개(+17.02%)가 급증했습니다.** 이때 신규 등장한 업소번호는 17,113개, 사라진 업소번호는 5,391개였습니다.

## 대표 시각화

### 전체 상가 수 추이

![대전 전체 상가 수 추이](images/01_total_store_trend.png)

2024년 말의 불연속적인 증가를 확인한 뒤 업소번호의 등장과 소멸을 별도로 검토했습니다.

### 자치구별 추이

![자치구별 상가 수 추이](images/02_district_trend.png)

### 업종별 증감

![업종별 증감](images/03_category_growth.png)

기간과 항목을 바꿔 보려면 [인터랙티브 대시보드](interactive-dashboard.html)를 내려받아 브라우저에서 여세요. 2026년 3월 위치 지도에서는 자치구·업종을 선택하고 파랑·보라·빨강 밀도 체크박스를 켜고 끌 수 있습니다. 나머지 시각화와 수치별 해석은 [REPORT.md](REPORT.md)에서 확인할 수 있습니다.

## 무엇을 질문했나

1. 2025년 3월부터 2026년 3월까지 대전 전체 상가 수는 어떻게 변했는가?
2. 어느 자치구와 업종이 전체 증가를 주도했는가?
3. 어느 업종의 증가량과 증가율이 가장 높았는가?
4. 2024년 말 급증과 업소번호 교체는 어떻게 해석해야 하는가?

## 2024년 말 급증은 어떻게 해석했나

| 점검 항목 | 결과 | 해석 범위 |
| --- | ---: | --- |
| 전체 상가 수 변화 | +11,722개 (+17.02%) | 관측된 순증 |
| 등장 업소번호 | 17,113개 | 실제 창업·신규 수집·ID 재발급 등이 섞일 수 있음 |
| 사라진 업소번호 | 5,391개 | 실제 폐업·수집 누락·ID 교체 등이 섞일 수 있음 |

전체 +11,722개는 업소번호 집합의 변화로 계산되지만, 제공된 파일만으로 실제 개·폐업과 전체 데이터 수집범위 변화의 몫을 나눌 수는 없습니다.

## 데이터 구성과 주의점

원본은 [공공데이터포털의 소상공인시장진흥공단 상가(상권)정보](https://www.data.go.kr/data/15083033/fileData.do)에서 받은 대전 지역 CSV입니다. 원본 파일은 수정하지 않았으며 Git 저장소에는 용량과 재배포 조건을 고려해 포함하지 않았습니다. 재현 시 내려받은 파일을 `data/raw/`에 배치합니다.

> [!IMPORTANT]
> 관측월은 `202403, 202406, 202409, 202412, 202503, 202506, 202510, 202512, 202603, 202606`입니다. 2025년 9월 자료가 없고 10월 자료가 있으므로, 2025년 10월은 보조 관측치로만 사용했습니다.

> [!NOTE]
> 패널은 500행으로 과제의 100개 이상 데이터 포인트 조건을 충족하지만, 독립적인 분기말 시점은 9개입니다. 누락 분기를 보간하거나 임의로 만들지 않았습니다.

> [!CAUTION]
> 상가 수 증가는 실제 창업 수와 같지 않습니다. 등록 지연, 업소번호 교체, 수집범위 변화가 포함될 수 있습니다.

## 빠르게 결과 확인하기

코드를 실행하지 않아도 다음 네 파일만 보면 분석 전체를 파악할 수 있습니다.

1. [interactive-dashboard.html](interactive-dashboard.html) — 기간 내 전체·자치구·업종 추이를 바꿔 보는 단일 HTML
2. [REPORT.md](REPORT.md) — 질문, 전처리, 그래프, 관찰과 해석, 한계, AI 사용 로그
3. [analysis.ipynb](analysis.ipynb) — 전처리부터 검증까지 실행 결과가 저장된 노트북
4. [daejeon_timeseries.csv](data/processed/daejeon_timeseries.csv) — 구 × 대분류 × 관측월 기준 핵심 패널

## 직접 재현하기

### 1. 저장소와 환경 준비

```powershell
git clone https://github.com/Frost0313z/daejeon-commercial-analysis.git
cd daejeon-commercial-analysis
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

검증 환경은 Python 3.14.6 / Windows이며, 코드는 Python 3.10 이상을 대상으로 합니다.

### 2. 원본 데이터 배치

공공데이터포털에서 대전 지역 CSV를 내려받아 `data/raw/`에 넣습니다. 필요한 기준월은 아래 10개입니다.

```text
202403  202406  202409  202412  202503
202506  202510  202512  202603  202606
```

파일명은 `소상공인시장진흥공단_상가(상권)정보_대전_YYYYMM.csv` 형식을 사용합니다. 다른 배포본을 사용하면 [file_audit.csv](data/processed/file_audit.csv)의 행 수와 SHA-256을 먼저 비교하세요.

### 3. 분석 실행

```powershell
# Jupyter에서 단계별 확인
.\.venv\Scripts\python.exe -m jupyter notebook analysis.ipynb

# 전체 자동 재실행
.\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 analysis.ipynb

# 인터랙티브 HTML 재생성
.\.venv\Scripts\python.exe dashboard.py
```

노트북은 가공 데이터와 정적 그래프를, `dashboard.py`는 신뢰 구간 요약 CSV와 `interactive-dashboard.html`을 갱신합니다.

## 결과물 안내

### 핵심 파일

| 파일 | 역할 |
| --- | --- |
| [REPORT.md](REPORT.md) | 제출용 분석 리포트 |
| [analysis.ipynb](analysis.ipynb) | 전체 분석 코드와 실행 결과 |
| [interactive-dashboard.html](interactive-dashboard.html) | 브라우저에서 바로 여는 인터랙티브 시각화 |
| [dashboard.py](dashboard.py) | 대시보드와 신뢰 구간 요약 CSV 생성 |
| [requirements.txt](requirements.txt) | 재현용 Python 의존성 |

### 주요 가공 데이터

| 파일 | 내용 |
| --- | --- |
| [daejeon_timeseries.csv](data/processed/daejeon_timeseries.csv) | 구 × 대분류 × 관측월 500행 패널 |
| [reliable_period_summary.csv](data/processed/reliable_period_summary.csv) | 2025-03~2026-03 전체 증감 요약 |
| [reliable_period_district_growth.csv](data/processed/reliable_period_district_growth.csv) | 신뢰 구간 자치구별 증감 |
| [reliable_period_category_growth.csv](data/processed/reliable_period_category_growth.csv) | 신뢰 구간 업종별 증감 |
| [store_location_grid_202603.csv](data/processed/store_location_grid_202603.csv) | 2026년 3월 좌표를 0.01도 격자로 집계한 지도 데이터 |
| [category_change_decomposition.csv](data/processed/category_change_decomposition.csv) | 업소 등장·이탈·유지·업종 이동 분해 |

<details>
<summary><strong>전체 processed 데이터 설명 보기</strong></summary>

- `total_quarterly.csv`, `total_observed.csv`: 분기말 및 전체 관측월 총계
- `district_timeseries.csv`, `category_timeseries.csv`: 지역·업종별 수준과 변화율
- `district_growth.csv`, `category_growth.csv`: 핵심 비교 기간의 증감
- `small_category_timeseries.csv`, `middle_category_timeseries.csv`: 소·중분류 집계
- `id_transitions.csv`, `common_reclassification_flows.csv`: 업소번호 이동과 대분류 변경 흐름
- `schema.csv`, `missing_values.csv`, `administrative_*.csv`, `environment.json`: 데이터·실행 환경 품질 점검
- `sensitivity.csv`: 종료 시점을 바꾼 민감도 분석

</details>

## 폴더 구조

```text
daejeon-commercial-analysis/
├─ data/
│  ├─ raw/                     # 직접 내려받은 원본 CSV, Git 제외
│  └─ processed/               # 집계·품질 점검 결과
├─ images/                     # 리포트 시각화 5개
├─ analysis.ipynb              # 메인 분석
├─ dashboard.py                # 인터랙티브 HTML 생성
├─ interactive-dashboard.html  # 브라우저에서 바로 실행
├─ REPORT.md                   # 최종 분석 리포트
├─ README.md
└─ requirements.txt
```

## 검증 상태

- 원본 10개 파일의 행 수·해시·관측월 감사
- 집계 합계, 증감률, 결측과 분모 0 처리 검증
- 리포트·PNG 5개·인터랙티브 HTML을 신뢰 구간 계산 결과에 맞춰 갱신

## 분석의 한계

- 독립적인 분기말 시점이 9개라 장기 계절성이나 예측 모델을 안정적으로 추정하기 어렵습니다.
- 2025년 9월이 없어 10월 관측치를 분기말 자료처럼 사용하지 않았습니다.
- 지도는 위치 분포를 읽기 위한 격자 집계이며 개별 점포의 정확한 위치나 상권 경계를 나타내지 않습니다. OpenStreetMap 배경을 표시하려면 인터넷 연결이 필요합니다.
- 업소번호의 등장·이탈만으로 실제 개업·폐업과 행정·수집 과정의 변화를 구분할 수 없습니다.
- 외부 경기, 인구, 금리, 유동인구 등 설명 변수를 결합하지 않아 변화 원인은 가설 수준으로 해석했습니다.

분석 과정에서 AI는 전처리·시각화 코드 초안, 대안 탐색, 문장 정리에 사용했으며, 모든 수치는 노트북 재실행과 집계 대조로 검증했습니다. 상세 사용 범위와 검증 방법은 [REPORT.md의 AI 사용 로그](REPORT.md#10-ai-사용-로그)에 기록했습니다.
