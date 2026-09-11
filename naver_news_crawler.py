from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
import requests
from bs4 import BeautifulSoup


SEARCH_URL = "https://search.naver.com/search.naver"
RESULT_FILE = Path(__file__).with_name("naverResult.xlsx")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}


@dataclass
class NewsArticle:
    title: str
    link: str
    summary: str
    content: Optional[str] = None


def get_soup(url: str, params: Optional[dict[str, str]] = None) -> BeautifulSoup:
    response = requests.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return BeautifulSoup(response.text, "html.parser")


def clean_text(element) -> str:
    if not element:
        return ""
    text = " ".join(element.get_text(" ", strip=True).split())
    return text.replace("새 창 열림", "").strip()


def get_news_search_results(keyword: str, limit: int = 10) -> list[NewsArticle]:
    """네이버 검색 결과에서 뉴스 제목, 링크, 요약을 가져온다."""
    soup = get_soup(
        SEARCH_URL,
        params={"where": "news", "query": keyword},
    )
    articles: list[NewsArticle] = []

    title_links = soup.select(
        '.fds-news-item-list-desk a[data-heatmap-target=".tit"], '
        '.fds-news-item-list-tab a[data-heatmap-target=".tit"], '
        "a.news_tit"
    )
    for title_link in title_links:
        link = title_link.get("href", "")
        if not link or link.startswith(("#", "javascript:")):
            continue

        article_item = title_link.find_parent(
            "div", class_=lambda value: value and "BUUmpSvoP_koqxCo" in value
        )
        summary_element = (
            article_item.select_one('a[data-heatmap-target=".body"]')
            if article_item
            else None
        )
        articles.append(
            NewsArticle(
                title=clean_text(title_link),
                link=urljoin(SEARCH_URL, link),
                summary=clean_text(summary_element),
            )
        )
        if len(articles) >= limit:
            break

    return articles


def get_article_content(article_url: str) -> str:
    """기사 페이지에서 본문으로 사용되는 영역의 텍스트를 가져온다."""
    soup = get_soup(article_url)
    content_element = soup.select_one(
        "#dic_area, .go_trans._article_content, "
        ".article_body, .article_view, #articleBodyContents, "
        ".textBody, article, [id*='articleBody'], [class*='article_body']"
    )
    return clean_text(content_element)


def crawl_news(keyword: str, limit: int = 10) -> list[dict[str, str]]:
    """검색 결과와 가능한 경우 기사의 본문까지 수집한다."""
    articles = get_news_search_results(keyword, limit)
    results = []

    for article in articles:
        try:
            article.content = get_article_content(article.link)
        except requests.RequestException as error:
            print(f"본문 요청 실패: {article.link} ({error})")

        results.append(asdict(article))

    return results


def save_to_excel(
    articles: list[dict[str, str]],
    output_path: Path = RESULT_FILE,
) -> None:
    """크롤링 결과를 엑셀 파일로 저장한다."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "네이버 뉴스"

    headers = ["번호", "제목", "링크", "요약", "본문"]
    worksheet.append(headers)

    for index, article in enumerate(articles, start=1):
        worksheet.append(
            [
                index,
                article.get("title", ""),
                article.get("link", ""),
                article.get("summary", ""),
                article.get("content", "") or "",
            ]
        )

    for cell in worksheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    worksheet.freeze_panes = "A2"
    worksheet.column_dimensions["A"].width = 8
    worksheet.column_dimensions["B"].width = 45
    worksheet.column_dimensions["C"].width = 65
    worksheet.column_dimensions["D"].width = 70
    worksheet.column_dimensions["E"].width = 100

    for row in worksheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    workbook.save(output_path)


if __name__ == "__main__":
    articles = crawl_news("반도체", limit=5)
    save_to_excel(articles)
    print(f"크롤링 결과를 저장했습니다: {RESULT_FILE}")

    for index, article in enumerate(articles, start=1):
        print(f"\n[{index}] {article['title']}")
        print(f"링크: {article['link']}")
        print(f"요약: {article['summary']}")
        print(f"본문: {article['content'][:300] or '본문을 찾지 못했습니다.'}...")