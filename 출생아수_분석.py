from pathlib import Path
import re

import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "출생아수__합계출산율__자연증가_등_20260825135750.xlsx"
OUTPUT_DIR = BASE_DIR / "출생아수_분석_output"
START_YEAR = 1970
END_YEAR = 2025


def clean_data(file_path: Path) -> pd.DataFrame:
    """엑셀의 가로형 통계표를 연도별 분석용 데이터로 정제한다."""
    raw = pd.read_excel(file_path, sheet_name="데이터", header=0)
    raw = raw.rename(columns={raw.columns[0]: "지표"})

    data = raw.set_index("지표").transpose().reset_index()
    data = data.rename(columns={"index": "연도"})

    # '2025 p)'처럼 주석이 포함된 연도 헤더에서 숫자만 추출한다.
    data["연도"] = pd.to_numeric(
        data["연도"].astype("string").str.extract(r"(\d{4})")[0],
        errors="coerce",
    )

    numeric_columns = [column for column in data.columns if column != "연도"]
    for column in numeric_columns:
        cleaned = data[column].astype("string").str.replace(",", "", regex=False)
        cleaned = cleaned.str.replace(r"[^0-9.\-]", "", regex=True)
        data[column] = pd.to_numeric(cleaned, errors="coerce")

    required_columns = ["연도", "출생아수(명)"]
    missing_columns = [column for column in required_columns if column not in data]
    if missing_columns:
        raise KeyError(f"필수 컬럼이 없습니다: {', '.join(missing_columns)}")

    data = (
        data.dropna(subset=required_columns)
        .assign(연도=lambda frame: frame["연도"].astype(int))
        .drop_duplicates(subset="연도")
        .sort_values("연도")
    )
    return data[data["연도"].between(START_YEAR, END_YEAR)].reset_index(drop=True)


def analyze_data(data: pd.DataFrame) -> pd.DataFrame:
    """출생아수의 전년 대비 증감과 5년 이동평균을 계산한다."""
    result = data.copy()
    result["전년 대비 증감수"] = result["출생아수(명)"].diff()
    result["전년 대비 증감률(%)"] = result["출생아수(명)"].pct_change() * 100
    result["5년 이동평균(명)"] = result["출생아수(명)"].rolling(5).mean()
    return result


def print_analysis(data: pd.DataFrame) -> None:
    """정제된 데이터의 기본 통계와 주요 변화를 출력하고 저장한다."""
    births = data["출생아수(명)"]
    first_year = data.iloc[0]
    last_year = data.iloc[-1]
    lowest = data.loc[data["출생아수(명)"].idxmin()]
    highest = data.loc[data["출생아수(명)"].idxmax()]

    print("=== 출생아수 분석 ===")
    print(f"분석 기간: {int(first_year['연도'])}~{int(last_year['연도'])}")
    print(f"분석 연도 수: {len(data):,}년")
    print(f"출생아수 평균: {births.mean():,.0f}명")
    print(f"최고 출생아수: {highest['출생아수(명)']:,.0f}명 ({int(highest['연도'])}년)")
    print(f"최저 출생아수: {lowest['출생아수(명)']:,.0f}명 ({int(lowest['연도'])}년)")
    print(
        f"{int(first_year['연도'])}년 대비 {int(last_year['연도'])}년 변화율: "
        f"{(last_year['출생아수(명)'] / first_year['출생아수(명)'] - 1) * 100:.2f}%"
    )
    print("\n=== 정제 후 결측치 ===")
    print(data.isna().sum().to_string())

    OUTPUT_DIR.mkdir(exist_ok=True)
    data.to_csv(OUTPUT_DIR / "출생아수_정제_분석데이터.csv", index=False, encoding="utf-8-sig")


def draw_births_chart(data: pd.DataFrame) -> None:
    """1970~2025년 출생아수와 5년 이동평균을 라인 그래프로 저장한다."""
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]

    figure, axis = plt.subplots(figsize=(14, 7))
    axis.plot(
        data["연도"],
        data["출생아수(명)"],
        marker="o",
        markersize=3,
        linewidth=1.8,
        color="#176B87",
        label="출생아수",
    )
    axis.plot(
        data["연도"],
        data["5년 이동평균(명)"],
        linewidth=2,
        color="#E07A5F",
        label="5년 이동평균",
    )
    axis.set_title("1970~2025년 출생아수 추이", fontsize=16)
    axis.set_xlabel("연도")
    axis.set_ylabel("출생아수 (명)")
    axis.set_xticks(range(START_YEAR, END_YEAR + 1, 5))
    axis.ticklabel_format(axis="y", style="plain")
    axis.grid(alpha=0.25)
    axis.legend()
    figure.tight_layout()

    OUTPUT_DIR.mkdir(exist_ok=True)
    chart_path = OUTPUT_DIR / "1970_2025_출생아수_라인그래프.png"
    figure.savefig(chart_path, dpi=150)
    print(f"\n그래프 저장: {chart_path}")
    plt.show()
    plt.close(figure)


def main() -> None:
    data = analyze_data(clean_data(INPUT_FILE))
    print_analysis(data)
    draw_births_chart(data)


if __name__ == "__main__":
    main()