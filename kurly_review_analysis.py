from __future__ import annotations

import re
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


BASE_DIR = Path(__file__).resolve().parent
PRODUCT_URL = "https://www.kurly.com/goods/5026468?collectionCode=2609-wonder-home-01"
TARGET_REVIEWS = 300
OUTPUT_DIR = BASE_DIR / "kurly_review_analysis_output"
REVIEW_DATE_PATTERN = re.compile(r"\d{4}\.\d{1,2}\.\d{1,2}")

POSITIVE_WORDS = {
    "맛있", "맛나", "최고", "추천", "만족", "훌륭", "깔끔", "진하", "깊은맛",
    "부드럽", "푸짐", "든든", "간편", "재구매", "좋아", "좋았", "신선", "알차",
    "고소", "담백", "친절", "편하", "괜찮", "감동", "대박", "강추", "잘먹",
}
NEGATIVE_WORDS = {
    "맛없", "별로", "실망", "불만", "비싸", "짜", "싱겁", "느끼", "질기", "딱딱",
    "퍽퍽", "부족", "적다", "작다", "늦", "파손", "녹아", "상했", "냄새", "비리",
    "불편", "아쉽", "아쉬", "나쁘", "재구매 안", "추천 안", "환불", "문제", "이상",
}


def build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,1200")
    options.add_argument("--lang=ko-KR")
    return webdriver.Chrome(options=options)


def clean_review_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^\[?\s*상품 후기\s*\]?\s*", "", text)
    text = re.sub(r"\d{4}\.\d{1,2}\.\d{1,2}.*?멤버스?\S*", "", text)
    return text.strip()


def extract_reviews(driver: webdriver.Chrome) -> list[str]:
    """후기 날짜와 도움돼요 문구가 함께 있는 가장 작은 DOM 부모를 수집한다."""
    script = """
    const root = document.querySelector('#review');
    if (!root) return [];
    const datePattern = /\\d{4}\\.\\d{1,2}\\.\\d{1,2}/;
    const results = [];
    const seen = new Set();
        for (const node of root.querySelectorAll('article')) {
      const text = (node.innerText || '').replace(/\\s+/g, ' ').trim();
            const dateCount = (text.match(new RegExp(datePattern.source, 'g')) || []).length;
            if (dateCount !== 1 || text.length < 80 || text.length > 5000) continue;
            if (!seen.has(text)) {
                seen.add(text);
                results.push(text);
            }
    }
    return results;
    """
    return driver.execute_script(script)


def click_more_reviews(driver: webdriver.Chrome) -> bool:
    """현재 보이는 더보기/다음 컨트롤을 한 번 누르고, 눌렀는지 반환한다."""
    clicked = driver.execute_script(
        """
        const root = document.querySelector('#review');
        if (!root) return false;
        const controls = [...root.querySelectorAll('button, a, [role="button"]')];
        const visible = (element) => {
          const style = window.getComputedStyle(element);
          return style.display !== 'none' && style.visibility !== 'hidden';
        };
        const label = (element) => (element.innerText || element.getAttribute('aria-label') || '')
          .replace(/\\s+/g, ' ').trim();
        const next = controls.find((element) => visible(element) && label(element).includes('다음'));
        const page = controls.find((element) => {
          const value = label(element);
          return visible(element) && /^[2-9]$|^[1-4][0-9]$|^50$/.test(value)
            && element.getAttribute('aria-current') !== 'true';
        });
        const more = controls.find((element) => visible(element) && label(element).includes('더보기'));
        const target = next || page || more;
        if (!target) return false;
        target.scrollIntoView({block: 'center'});
        target.click();
        return true;
        """
    )
    if clicked:
        time.sleep(1.0)
        return True

    candidates = driver.find_elements(
        By.XPATH,
        "//*[@id='review']//button | //*[@id='review']//a | //*[@id='review']//li",
    )
    for element in candidates:
        try:
            label = re.sub(r"\s+", " ", element.text).strip()
            is_page_number = label.isdigit() and 1 < int(label) <= 50
            if not (
                label in {"+더보기", "더보기", "다음", "다음 페이지"}
                or ("더보기" in label and len(label) <= 20)
                or "다음" in label
                or is_page_number
            ):
                continue
            if is_page_number and (
                element.get_attribute("aria-current") == "true"
                or "active" in (element.get_attribute("class") or "").lower()
            ):
                continue
            if not element.is_displayed() or not element.is_enabled():
                continue
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            driver.execute_script("arguments[0].click();", element)
            time.sleep(0.8)
            return True
        except (ElementClickInterceptedException, StaleElementReferenceException):
            continue
    for element in driver.find_elements(
        By.XPATH,
        "//*[@id='review']//*[contains(@aria-label, '다음') or contains(@title, '다음')]",
    ):
        try:
            if element.is_displayed() and element.is_enabled():
                driver.execute_script("arguments[0].click();", element)
                time.sleep(0.8)
                return True
        except (ElementClickInterceptedException, StaleElementReferenceException):
            continue
    return False


def crawl_reviews(url: str = PRODUCT_URL, limit: int = TARGET_REVIEWS) -> pd.DataFrame:
    driver = build_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "review")))
        driver.execute_script("document.querySelector('#review').scrollIntoView();")

        reviews: list[str] = []
        unchanged_rounds = 0
        for _ in range(100):
            current = extract_reviews(driver)
            before = len(reviews)
            for review in current:
                if review not in reviews:
                    reviews.append(review)
                if len(reviews) >= limit:
                    break
            if len(reviews) >= limit:
                break
            unchanged_rounds = unchanged_rounds + 1 if len(reviews) == before else 0
            if unchanged_rounds >= 3 or not click_more_reviews(driver):
                break

        if not reviews:
            raise RuntimeError("후기 항목을 찾지 못했습니다. 컬리 페이지 구조가 변경되었을 수 있습니다.")
        if len(reviews) < limit:
            raise RuntimeError(
                f"후기 {len(reviews)}개만 수집했습니다. 페이지 이동 컨트롤이 변경되었을 수 있습니다."
            )
        return pd.DataFrame({"후기": [clean_review_text(review) for review in reviews[:limit]]})
    except TimeoutException as error:
        raise RuntimeError("상품 후기 영역을 불러오지 못했습니다.") from error
    finally:
        driver.quit()


def classify_sentiment(review: str) -> tuple[str, int]:
    positive_score = sum(review.count(word) for word in POSITIVE_WORDS)
    negative_score = sum(review.count(word) for word in NEGATIVE_WORDS)
    score = positive_score - negative_score
    if score > 0:
        return "긍정", score
    if score < 0:
        return "부정", score
    return "중립", score


def analyze_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    result = reviews.copy()
    result[["감성", "감성점수"]] = result["후기"].apply(
        lambda review: pd.Series(classify_sentiment(review))
    )
    return result


def draw_charts(data: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]

    sentiment_counts = data["감성"].value_counts().reindex(["긍정", "중립", "부정"], fill_value=0)
    word_counts = (
        data["후기"].str.split().explode().str.replace(r"[^가-힣]", "", regex=True)
        .loc[lambda words: words.str.len() >= 2]
        .value_counts()
        .head(15)
    )

    figure, axes = plt.subplots(1, 3, figsize=(18, 6), constrained_layout=True)
    axes[0].bar(sentiment_counts.index, sentiment_counts.values, color=["#2A9D8F", "#A8A8A8", "#E76F51"])
    axes[0].set_title("후기 감성 분포")
    axes[0].set_ylabel("후기 수")
    axes[0].grid(axis="y", alpha=0.25)

    axes[1].pie(
        sentiment_counts.values,
        labels=sentiment_counts.index,
        autopct="%1.1f%%",
        colors=["#2A9D8F", "#A8A8A8", "#E76F51"],
        startangle=90,
    )
    axes[1].set_title("긍정·부정·중립 비율")

    word_counts.sort_values().plot.barh(ax=axes[2], color="#457B9D")
    axes[2].set_title("후기 단어 빈도 상위 15개")
    axes[2].set_xlabel("빈도")
    axes[2].grid(axis="x", alpha=0.25)

    chart_path = OUTPUT_DIR / "컬리_후기_감성분석_차트.png"
    figure.savefig(chart_path, dpi=150)
    plt.show()
    plt.close(figure)
    print(f"차트 저장: {chart_path}")


def main() -> None:
    print(f"컬리 후기 {TARGET_REVIEWS}개 수집을 시작합니다...")
    data = analyze_reviews(crawl_reviews())
    OUTPUT_DIR.mkdir(exist_ok=True)
    data.to_csv(OUTPUT_DIR / "컬리_후기_감성분석.csv", index=False, encoding="utf-8-sig")
    print(f"수집 후기 수: {len(data):,}개")
    print("감성 분포:")
    print(data["감성"].value_counts().to_string())
    draw_charts(data)


if __name__ == "__main__":
    main()