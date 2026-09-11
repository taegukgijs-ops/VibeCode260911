from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "S&P 500 과거 데이터.csv"
OUTPUT_DIR = BASE_DIR / "sp500_analysis_output"
START_DATE = "2000-01-01"
END_DATE = "2019-12-31"


def clean_data(file_path: Path) -> pd.DataFrame:
    """CSV를 읽고 날짜·가격·수익률 컬럼을 분석 가능한 형식으로 변환한다."""
    data = pd.read_csv(file_path)
    data.columns = data.columns.str.strip()

    data["날짜"] = pd.to_datetime(
        data["날짜"].astype("string").str.replace(" ", "", regex=False),
        errors="coerce",
    )

    numeric_columns = [column for column in data.columns if column != "날짜"]
    for column in numeric_columns:
        cleaned = data[column].astype("string").str.replace(",", "", regex=False)
        cleaned = cleaned.str.replace("%", "", regex=False)
        data[column] = pd.to_numeric(cleaned, errors="coerce")

    data = (
        data.dropna(subset=["날짜", "종가"])
        .drop_duplicates(subset="날짜")
        .sort_values("날짜")
        .set_index("날짜")
    )
    return data.loc[START_DATE:END_DATE].copy()


def add_analysis_columns(data: pd.DataFrame) -> pd.DataFrame:
    """가격에서 수익률, 이동평균, 변동성, 누적수익률, 낙폭을 계산한다."""
    data = data.copy()
    data["일간수익률"] = data["종가"].pct_change()
    data["누적수익률"] = (1 + data["일간수익률"].fillna(0)).cumprod() - 1
    data["5일이동평균"] = data["종가"].rolling(5).mean()
    data["20일이동평균"] = data["종가"].rolling(20).mean()
    data["60일이동평균"] = data["종가"].rolling(60).mean()
    data["연환산변동성"] = data["일간수익률"].rolling(252).std() * (252**0.5)
    data["고점"] = data["종가"].cummax()
    data["낙폭"] = data["종가"] / data["고점"] - 1
    return data


def print_analysis(data: pd.DataFrame) -> None:
    """주요 통계와 연도별·월별 분석 결과를 출력한다."""
    daily_returns = data["일간수익률"].dropna()
    annual_summary = data["종가"].resample("YE").agg(["first", "last", "min", "max"])
    annual_summary["수익률"] = annual_summary["last"] / annual_summary["first"] - 1
    annual_summary["평균종가"] = data["종가"].resample("YE").mean()
    annual_summary["변동성"] = daily_returns.resample("YE").std() * (252**0.5)

    monthly_returns = data["종가"].resample("ME").last().pct_change().dropna()
    correlation = data[["종가", "시가", "고가", "저가"]].corr()

    print("=== 데이터 개요 ===")
    print(f"분석 기간: {data.index.min():%Y-%m-%d} ~ {data.index.max():%Y-%m-%d}")
    print(f"거래일 수: {len(data):,}일")
    print(f"결측치 수(컬럼별):\n{data.isna().sum()}")

    print("\n=== 핵심 성과 지표 ===")
    print(f"전체 누적수익률: {data['누적수익률'].iloc[-1]:.2%}")
    print(f"연환산 수익률(CAGR): {(data['종가'].iloc[-1] / data['종가'].iloc[0]) ** (252 / len(daily_returns)) - 1:.2%}")
    print(f"연환산 변동성: {daily_returns.std() * (252**0.5):.2%}")
    print(f"최대 낙폭(MDD): {data['낙폭'].min():.2%}")
    print(f"최고 종가: {data['종가'].max():,.2f} ({data['종가'].idxmax():%Y-%m-%d})")
    print(f"최저 종가: {data['종가'].min():,.2f} ({data['종가'].idxmin():%Y-%m-%d})")

    print("\n=== 연도별 요약 ===")
    print(annual_summary.to_string(float_format=lambda value: f"{value:,.4f}"))

    print("\n=== 월별 수익률 상위·하위 5개 ===")
    print("[상위]\n", monthly_returns.nlargest(5).to_string(float_format=lambda value: f"{value:.2%}"))
    print("[하위]\n", monthly_returns.nsmallest(5).to_string(float_format=lambda value: f"{value:.2%}"))

    print("\n=== 가격 컬럼 상관관계 ===")
    print(correlation.to_string(float_format=lambda value: f"{value:.4f}"))

    OUTPUT_DIR.mkdir(exist_ok=True)
    annual_summary.to_csv(OUTPUT_DIR / "연도별_요약.csv", encoding="utf-8-sig")
    data.to_csv(OUTPUT_DIR / "정제_분석데이터.csv", encoding="utf-8-sig")


def draw_charts(data: pd.DataFrame) -> None:
    """종가 중심의 기간 그래프와 보조 분석 그래프를 저장하고 표시한다."""
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]

    figure, axes = plt.subplots(2, 2, figsize=(16, 10), constrained_layout=True)

    axes[0, 0].plot(data.index, data["종가"], color="#12355B", linewidth=1.2)
    axes[0, 0].set_title("S&P 500 종가 (2000~2019)")
    axes[0, 0].set_ylabel("지수")

    axes[0, 1].plot(data.index, data["종가"], label="종가", color="#12355B", linewidth=1)
    axes[0, 1].plot(data.index, data["20일이동평균"], label="20일 이동평균", color="#E07A5F")
    axes[0, 1].plot(data.index, data["60일이동평균"], label="60일 이동평균", color="#3D9970")
    axes[0, 1].set_title("종가와 이동평균")
    axes[0, 1].legend()

    axes[1, 0].plot(data.index, data["누적수익률"] * 100, color="#3D9970")
    axes[1, 0].set_title("누적수익률")
    axes[1, 0].set_ylabel("수익률 (%)")

    axes[1, 1].fill_between(data.index, data["낙폭"] * 100, 0, color="#C44536", alpha=0.75)
    axes[1, 1].set_title("고점 대비 낙폭")
    axes[1, 1].set_ylabel("낙폭 (%)")

    for axis in axes.flat:
        axis.grid(alpha=0.25)
        axis.set_xlabel("날짜")

    figure.suptitle("S&P 500 다각도 분석", fontsize=16)
    chart_path = OUTPUT_DIR / "S&P500_분석_그래프.png"
    figure.savefig(chart_path, dpi=150)
    print(f"\n그래프 저장: {chart_path}")
    plt.show()


def main() -> None:
    data = add_analysis_columns(clean_data(INPUT_FILE))
    print_analysis(data)
    draw_charts(data)


if __name__ == "__main__":
    main()