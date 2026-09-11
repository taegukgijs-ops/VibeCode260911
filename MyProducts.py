import sqlite3
from pathlib import Path
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Font
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


DB_PATH = Path(__file__).with_name("products.db")


def get_connection() -> sqlite3.Connection:
    """Return a connection configured to access rows by column name."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    """Create the Products table if it does not already exist."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS Products (
                productID INTEGER PRIMARY KEY AUTOINCREMENT,
                productName TEXT NOT NULL,
                productPrice INTEGER NOT NULL CHECK (productPrice >= 0)
            )
            """
        )


def add_product(product_name: str, product_price: int) -> int:
    """Insert a product and return its automatically generated ID."""
    validate_product(product_name, product_price)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO Products (productName, productPrice)
            VALUES (?, ?)
            """,
            (product_name.strip(), product_price),
        )
        return cursor.lastrowid


def update_product(
    product_id: int, product_name: str, product_price: int
) -> bool:
    """Update a product and return whether a row was changed."""
    validate_product(product_name, product_price)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE Products
            SET productName = ?, productPrice = ?
            WHERE productID = ?
            """,
            (product_name.strip(), product_price, product_id),
        )
        return cursor.rowcount > 0


def delete_product(product_id: int) -> bool:
    """Delete a product and return whether a row was removed."""
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM Products WHERE productID = ?",
            (product_id,),
        )
        return cursor.rowcount > 0


def get_product(product_id: int) -> Optional[dict]:
    """Return one product as a dictionary, or None when it does not exist."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT productID, productName, productPrice FROM Products "
            "WHERE productID = ?",
            (product_id,),
        ).fetchone()
        return dict(row) if row else None


def search_products(keyword: str = "") -> list[dict]:
    """Search product names; an empty keyword returns every product."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT productID, productName, productPrice
            FROM Products
            WHERE productName LIKE ?
            ORDER BY productID
            """,
            (f"%{keyword.strip()}%",),
        ).fetchall()
        return [dict(row) for row in rows]


def validate_product(product_name: str, product_price: int) -> None:
    if not product_name or not product_name.strip():
        raise ValueError("제품명은 비어 있을 수 없습니다.")
    if not isinstance(product_price, int) or isinstance(product_price, bool):
        raise ValueError("제품 가격은 정수여야 합니다.")
    if product_price < 0:
        raise ValueError("제품 가격은 0 이상이어야 합니다.")


def print_products(products: list[dict]) -> None:
    if not products:
        print("검색 결과가 없습니다.")
        return

    print("\nID | 제품명 | 가격")
    print("-" * 30)
    for product in products:
        print(
            f"{product['productID']} | {product['productName']} | "
            f"{product['productPrice']:,}원"
        )


def run_menu() -> None:
    initialize_database()

    while True:
        print("\n[제품 관리]")
        print("1. 제품 입력")
        print("2. 제품 수정")
        print("3. 제품 삭제")
        print("4. 제품 검색")
        print("0. 종료")

        choice = input("메뉴를 선택하세요: ").strip()

        try:
            if choice == "1":
                name = input("제품명: ")
                price = int(input("제품 가격: "))
                product_id = add_product(name, price)
                print(f"제품이 입력되었습니다. productID: {product_id}")
            elif choice == "2":
                product_id = int(input("수정할 productID: "))
                name = input("새 제품명: ")
                price = int(input("새 제품 가격: "))
                if update_product(product_id, name, price):
                    print("제품이 수정되었습니다.")
                else:
                    print("해당 productID의 제품이 없습니다.")
            elif choice == "3":
                product_id = int(input("삭제할 productID: "))
                if delete_product(product_id):
                    print("제품이 삭제되었습니다.")
                else:
                    print("해당 productID의 제품이 없습니다.")
            elif choice == "4":
                keyword = input("검색할 제품명 (전체 검색은 Enter): ")
                print_products(search_products(keyword))
            elif choice == "0":
                print("프로그램을 종료합니다.")
                break
            else:
                print("올바른 메뉴 번호를 입력하세요.")
        except ValueError as error:
            print(f"입력 오류: {error}")
        except sqlite3.Error as error:
            print(f"데이터베이스 오류: {error}")


class ProductWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        initialize_database()

        self.setWindowTitle("제품 관리")
        self.resize(860, 600)
        self.selected_product_id: Optional[int] = None

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("제품명을 입력하세요")

        self.price_input = QSpinBox()
        self.price_input.setRange(0, 2_147_483_647)
        self.price_input.setSingleStep(1000)
        self.price_input.setSuffix(" 원")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("제품명으로 검색")

        self.product_table = QTableWidget(0, 3)
        self.product_table.setHorizontalHeaderLabels(
            ["productID", "제품명", "제품가격"]
        )
        self.product_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.product_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.product_table.setAlternatingRowColors(True)
        self.product_table.horizontalHeader().setStretchLastSection(True)
        self.product_table.itemSelectionChanged.connect(
            self.select_product_from_table
        )

        form_layout = QFormLayout()
        form_layout.addRow("제품명", self.name_input)
        form_layout.addRow("제품가격", self.price_input)

        add_button = QPushButton("입력")
        add_button.setObjectName("addButton")
        add_button.clicked.connect(self.add_product_from_form)

        update_button = QPushButton("수정")
        update_button.setObjectName("updateButton")
        update_button.clicked.connect(self.update_selected_product)

        delete_button = QPushButton("삭제")
        delete_button.setObjectName("deleteButton")
        delete_button.clicked.connect(self.delete_selected_product)

        clear_button = QPushButton("입력 초기화")
        clear_button.setObjectName("clearButton")
        clear_button.clicked.connect(self.clear_form)

        form_buttons = QHBoxLayout()
        form_buttons.addWidget(add_button)
        form_buttons.addWidget(update_button)
        form_buttons.addWidget(delete_button)
        form_buttons.addWidget(clear_button)

        search_button = QPushButton("검색")
        search_button.setObjectName("searchButton")
        search_button.clicked.connect(self.load_products)
        self.search_input.returnPressed.connect(self.load_products)

        export_button = QPushButton("엑셀로 저장")
        export_button.setObjectName("exportButton")
        export_button.clicked.connect(self.export_to_excel)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("검색"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)
        search_layout.addStretch()
        search_layout.addWidget(export_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addLayout(form_buttons)
        main_layout.addLayout(search_layout)
        main_layout.addWidget(self.product_table)

        container = QWidget()
        container.setObjectName("mainContainer")
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #edf2f7;
            }
            QWidget#mainContainer {
                background-color: #edf2f7;
                color: #243447;
            }
            QLabel {
                color: #334e68;
                font-size: 13px;
                font-weight: 600;
            }
            QLineEdit, QSpinBox {
                background-color: #ffffff;
                border: 1px solid #bcccdc;
                border-radius: 7px;
                color: #243447;
                font-size: 14px;
                padding: 9px 11px;
                selection-background-color: #3b82f6;
            }
            QLineEdit:focus, QSpinBox:focus {
                border: 2px solid #3b82f6;
                padding: 8px 10px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 22px;
                border: none;
                background-color: #e7eef7;
            }
            QPushButton {
                background-color: #486581;
                border: none;
                border-radius: 7px;
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                min-height: 38px;
                padding: 0 18px;
            }
            QPushButton:hover {
                background-color: #334e68;
            }
            QPushButton:pressed {
                background-color: #243b53;
            }
            QPushButton#addButton {
                background-color: #168aad;
            }
            QPushButton#addButton:hover {
                background-color: #0f7190;
            }
            QPushButton#updateButton {
                background-color: #40916c;
            }
            QPushButton#updateButton:hover {
                background-color: #277653;
            }
            QPushButton#deleteButton {
                background-color: #d1495b;
            }
            QPushButton#deleteButton:hover {
                background-color: #b9384a;
            }
            QPushButton#clearButton {
                background-color: #829ab1;
            }
            QPushButton#exportButton {
                background-color: #217346;
                padding: 0 22px;
            }
            QPushButton#exportButton:hover {
                background-color: #185c37;
            }
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f3f7fb;
                border: 1px solid #bcccdc;
                border-radius: 8px;
                color: #243447;
                font-size: 13px;
                gridline-color: #d9e2ec;
                outline: none;
                selection-background-color: #bfdbfe;
                selection-color: #102a43;
            }
            QHeaderView::section {
                background-color: #243b53;
                border: none;
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                padding: 10px 8px;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #bfdbfe;
                color: #102a43;
            }
            """
        )
        self.load_products()

    def load_products(self) -> None:
        products = search_products(self.search_input.text())
        self.product_table.setRowCount(0)

        for product in products:
            row = self.product_table.rowCount()
            self.product_table.insertRow(row)
            values = (
                product["productID"],
                product["productName"],
                f"{product['productPrice']:,}원",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column in (0, 2):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                self.product_table.setItem(row, column, item)

        self.product_table.resizeColumnsToContents()
        self.product_table.setColumnWidth(0, max(110, self.product_table.columnWidth(0)))
        self.product_table.setColumnWidth(1, max(300, self.product_table.columnWidth(1)))

    def select_product_from_table(self) -> None:
        selected_rows = self.product_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        self.selected_product_id = int(
            self.product_table.item(row, 0).text()
        )
        self.name_input.setText(self.product_table.item(row, 1).text())
        price_text = self.product_table.item(row, 2).text().replace(",", "")
        self.price_input.setValue(int(price_text.replace("원", "")))

    def add_product_from_form(self) -> None:
        try:
            product_id = add_product(
                self.name_input.text(), self.price_input.value()
            )
            self.load_products()
            self.clear_form()
            self.show_information(
                "입력 완료", f"제품이 입력되었습니다. productID: {product_id}"
            )
        except (ValueError, sqlite3.Error) as error:
            self.show_error(str(error))

    def update_selected_product(self) -> None:
        if self.selected_product_id is None:
            self.show_error("수정할 제품을 하단 목록에서 선택하세요.")
            return

        try:
            updated = update_product(
                self.selected_product_id,
                self.name_input.text(),
                self.price_input.value(),
            )
            if updated:
                self.load_products()
                self.clear_form()
                self.show_information("수정 완료", "제품이 수정되었습니다.")
            else:
                self.show_error("해당 제품을 찾을 수 없습니다.")
        except (ValueError, sqlite3.Error) as error:
            self.show_error(str(error))

    def delete_selected_product(self) -> None:
        if self.selected_product_id is None:
            self.show_error("삭제할 제품을 하단 목록에서 선택하세요.")
            return

        answer = QMessageBox.question(
            self,
            "삭제 확인",
            "선택한 제품을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            if delete_product(self.selected_product_id):
                self.load_products()
                self.clear_form()
                self.show_information("삭제 완료", "제품이 삭제되었습니다.")
            else:
                self.show_error("해당 제품을 찾을 수 없습니다.")
        except sqlite3.Error as error:
            self.show_error(str(error))

    def clear_form(self) -> None:
        self.selected_product_id = None
        self.name_input.clear()
        self.price_input.setValue(0)
        self.product_table.clearSelection()

    def export_to_excel(self) -> None:
        if self.product_table.rowCount() == 0:
            self.show_error("엑셀로 저장할 제품 데이터가 없습니다.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "엑셀 파일 저장",
            "products.xlsx",
            "Excel 파일 (*.xlsx)",
        )
        if not file_path:
            return

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Products"
        headers = ["productID", "productName", "productPrice"]
        worksheet.append(headers)
        for cell in worksheet[1]:
            cell.font = Font(bold=True)

        for row in range(self.product_table.rowCount()):
            product_id = int(self.product_table.item(row, 0).text())
            product_name = self.product_table.item(row, 1).text()
            product_price = int(
                self.product_table.item(row, 2).text()
                .replace(",", "")
                .replace("원", "")
            )
            worksheet.append([product_id, product_name, product_price])

        worksheet.column_dimensions["A"].width = 14
        worksheet.column_dimensions["B"].width = 24
        worksheet.column_dimensions["C"].width = 16
        try:
            workbook.save(file_path)
            self.show_information(
                "저장 완료", f"엑셀 파일이 저장되었습니다.\n{file_path}"
            )
        except OSError as error:
            self.show_error(f"엑셀 파일을 저장할 수 없습니다.\n{error}")

    def show_information(self, title: str, message: str) -> None:
        QMessageBox.information(self, title, message)

    def show_error(self, message: str) -> None:
        QMessageBox.warning(self, "확인 필요", message)


def run_gui() -> None:
    app = QApplication.instance() or QApplication([])
    window = ProductWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    run_gui()
