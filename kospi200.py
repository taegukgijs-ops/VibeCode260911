from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
import requests
from bs4 import BeautifulSoup


ENTRY_URL = "https://finance.naver.com/sise/entryJongmok.naver?type=KPI200"
MAX_PAGES = 30
DEFAULT_LIMIT = 200
OUTPUT_FILE = Path(__file__).with_name("kospi200.xlsx")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}


@dataclass
class Constituent:
    name: str
    current_price: str
    change: str
    change_rate: str
    volume: str
    trading_value_million: str
    market_cap_billion: str


EXCEL_HEADERS = [
    "종목명",
    "현재가",
    "전일비",
    "등락률",
    "거래량",
    "거래대금(백만)",
    "시가총액(억)",
]


def get_soup(url: str, params: Optional[dict[str, int]] = None) -> BeautifulSoup:
    response = requests.get(url, params=params, headers=HEADERS, timeout=10)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return BeautifulSoup(response.text, "html.parser")


def clean_text(element) -> str:
    if not element:
        return ""
    return " ".join(element.get_text(" ", strip=True).split())


def parse_constituent_page(soup: BeautifulSoup) -> list[Constituent]:
    """편입종목상위 한 페이지의 종목 정보를 파싱한다."""
    table = soup.select_one("div.box_type_m table.type_1")

    if table is None:
        raise RuntimeError("편입종목상위 표를 찾지 못했습니다.")

    header_row = table.select_one("tr")
    headers = [clean_text(cell).replace(" ", "") for cell in header_row.select("th, td")]
    expected_headers = [
        "종목별",
        "현재가",
        "전일비",
        "등락률",
        "거래량",
        "거래대금(백만)",
        "시가총액(억)",
    ]
    if headers != expected_headers:
        raise RuntimeError(f"예상하지 못한 표 헤더입니다: {headers}")

    constituents = []
    for row in table.select("tr")[1:]:
        cells = row.select("td")
        values = [clean_text(cell) for cell in cells]
        if len(values) != len(expected_headers) or not values[0]:
            continue

        direction = clean_text(cells[2].select_one(".blind"))
        change_value = clean_text(cells[2].select_one(".tah"))
        change = f"{direction} {change_value}".strip()

        constituents.append(
            Constituent(
                name=values[0],
                current_price=values[1],
                change=change,
                change_rate=values[3],
                volume=values[4],
                trading_value_million=values[5],
                market_cap_billion=values[6],
            )
        )

    return constituents


def crawl_top_constituents(limit: Optional[int] = None) -> list[Constituent]:
    """네이버 금융의 코스피200 편입종목 전체 정보를 가져온다."""
    constituents: list[Constituent] = []
    target_count = DEFAULT_LIMIT if limit is None else limit

    for page in range(1, MAX_PAGES + 1):
        page_constituents = parse_constituent_page(
            get_soup(ENTRY_URL, params={"page": page})
        )
        if not page_constituents:
            break

        constituents.extend(page_constituents)
        if len(constituents) >= target_count:
            return constituents[:target_count]

    return constituents


def save_to_excel(
    constituents: list[Constituent],
    output_path: Path = OUTPUT_FILE,
) -> None:
    """편입종목 정보를 엑셀 파일로 저장한다."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "코스피200 편입종목"
    worksheet.append(EXCEL_HEADERS)

    for constituent in constituents:
        worksheet.append(
            [
                constituent.name,
                constituent.current_price,
                constituent.change,
                constituent.change_rate,
                constituent.volume,
                constituent.trading_value_million,
                constituent.market_cap_billion,
            ]
        )

    for cell in worksheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    worksheet.freeze_panes = "A2"
    column_widths = [20, 14, 14, 12, 16, 18, 18]
    for index, width in enumerate(column_widths, start=1):
        worksheet.column_dimensions[chr(64 + index)].width = width

    for row in worksheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(horizontal="right")

    workbook.save(output_path)


class Kospi200Window(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.constituents: list[Constituent] = []

        self.setWindowTitle("코스피200 편입종목")
        self.resize(1100, 700)

        self.status_label = QLabel("편입종목 정보를 불러오세요.")
        self.table = QTableWidget(0, len(EXCEL_HEADERS))
        self.table.setHorizontalHeaderLabels(EXCEL_HEADERS)
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)

        crawl_button = QPushButton("편입종목 불러오기")
        crawl_button.clicked.connect(self.load_constituents)

        save_button = QPushButton("kospi200.xlsx로 저장")
        save_button.clicked.connect(self.save_constituents)

        button_layout = QHBoxLayout()
        button_layout.addWidget(crawl_button)
        button_layout.addWidget(save_button)
        button_layout.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(button_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def load_constituents(self) -> None:
        try:
            self.constituents = crawl_top_constituents()
        except (requests.RequestException, RuntimeError) as error:
            QMessageBox.critical(self, "크롤링 실패", str(error))
            return

        self.table.setRowCount(len(self.constituents))
        for row_index, constituent in enumerate(self.constituents):
            values = [
                constituent.name,
                constituent.current_price,
                constituent.change,
                constituent.change_rate,
                constituent.volume,
                constituent.trading_value_million,
                constituent.market_cap_billion,
            ]
            for column_index, value in enumerate(values):
                self.table.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem(value),
                )

        self.status_label.setText(
            f"총 {len(self.constituents)}개 종목을 불러왔습니다."
        )

    def save_constituents(self) -> None:
        if not self.constituents:
            self.load_constituents()
            if not self.constituents:
                return

        try:
            save_to_excel(self.constituents)
        except OSError as error:
            QMessageBox.critical(self, "저장 실패", str(error))
            return

        self.status_label.setText(f"저장 완료: {OUTPUT_FILE}")
        QMessageBox.information(
            self,
            "저장 완료",
            f"{len(self.constituents)}개 종목을 저장했습니다.\n{OUTPUT_FILE}",
        )


if __name__ == "__main__":
    application = QApplication([])
    window = Kospi200Window()
    window.show()
    application.exec()
