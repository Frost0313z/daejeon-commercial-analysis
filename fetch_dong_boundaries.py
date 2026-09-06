"""2026-03 분석용 대전 행정동 경계를 내려받아 82개 코드만 저장한다."""

import csv
import json
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "processed"
URL = ("https://raw.githubusercontent.com/vuski/admdongkor/master/"
       "ver20260401/HangJeongDong_ver20260401.geojson")


def main() -> None:
    with (OUT / "dong_indicators.csv").open(encoding="utf-8-sig", newline="") as f:
        expected = {row["dong_code"] for row in csv.DictReader(f)}
    with urlopen(Request(URL, headers={"User-Agent": "daejeon-commercial-analysis"}),
                 timeout=120) as response:
        source = json.load(response)

    features = []
    for feature in source["features"]:
        properties = feature["properties"]
        if str(properties.get("adm_cd2", ""))[:2] != "30":
            continue
        features.append({
            "type": "Feature",
            "properties": {
                "dong_code": str(properties["adm_cd2"])[:8],
                "district": properties["sggnm"],
                "dong": properties["adm_nm"].split()[-1],
                "source_adm_cd": properties["adm_cd"],
                "source_adm_cd2": properties["adm_cd2"],
            },
            "geometry": feature["geometry"],
        })
    actual = {f["properties"]["dong_code"] for f in features}
    assert len(features) == len(actual) == 82
    assert actual == expected, {"missing": expected - actual, "extra": actual - expected}

    result = {
        "type": "FeatureCollection",
        "source": "vuski/admdongkor ver20260401; SGIS·행정안전부 경계 기반",
        "source_url": "https://github.com/vuski/admdongkor",
        "license": "MIT",
        "analysis_date": "2026-03",
        "features": features,
    }
    path = OUT / "daejeon_dong_boundaries.geojson"
    path.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")
    print(f"{path.relative_to(ROOT)}: 행정동 {len(features)}개 저장 완료")


if __name__ == "__main__":
    main()
