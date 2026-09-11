import base64
import mimetypes
import os
import sys
from pathlib import Path

from openai import OpenAI
from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPixmap
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
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


SUPPORTED_IMAGE_TYPES = "이미지 파일 (*.png *.jpg *.jpeg *.webp *.gif)"


class ImageAnalysisWorker(QObject):
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, image_path: str, api_key: str) -> None:
        super().__init__()
        self.image_path = image_path
        self.api_key = api_key

    @pyqtSlot()
    def analyze(self) -> None:
        try:
            image_file = Path(self.image_path)
            mime_type = mimetypes.guess_type(image_file.name)[0] or "image/png"
            encoded_image = base64.b64encode(image_file.read_bytes()).decode(
                "ascii"
            )

            client = OpenAI(api_key=self.api_key)
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "이 사진에 있는 주요 사물을 한국어로 해석해 주세요. "
                                    "확실하게 보이는 사물 중심으로 목록을 만들고, "
                                    "각 사물의 특징과 사진 속 위치를 간단히 설명해 주세요. "
                                    "확신하기 어려운 내용은 추측이라고 표시하세요."
                                ),
                            },
                            {
                                "type": "input_image",
                                "image_url": (
                                    f"data:{mime_type};base64,{encoded_image}"
                                ),
                            },
                        ],
                    }
                ],
            )
            self.finished.emit(response.output_text)
        except Exception as error:
            self.failed.emit(str(error))


class ImageAnalyzerWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.image_path: str | None = None
        self.preview_pixmap: QPixmap | None = None
        self.analysis_thread: QThread | None = None
        self.analysis_worker: ImageAnalysisWorker | None = None

        self.setWindowTitle("사진 속 사물 해석기")
        self.resize(900, 700)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText(
            "OPENAI_API_KEY 환경 변수 또는 API 키를 입력하세요"
        )
        self.api_key_input.setText(os.getenv("OPENAI_API_KEY", ""))

        self.select_button = QPushButton("사진 선택")
        self.select_button.clicked.connect(self.select_image)

        self.analyze_button = QPushButton("사물 해석 시작")
        self.analyze_button.setEnabled(False)
        self.analyze_button.clicked.connect(self.start_analysis)

        self.file_label = QLabel("선택된 사진이 없습니다.")
        self.file_label.setWordWrap(True)

        self.preview_label = QLabel("사진 미리보기")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(400, 280)
        self.preview_label.setStyleSheet(
            "background: #f1f3f5; border: 1px dashed #adb5bd;"
        )

        self.result_text = QPlainTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("분석 결과가 여기에 표시됩니다.")

        form_layout = QFormLayout()
        form_layout.addRow("OpenAI API 키", self.api_key_input)

        image_controls = QHBoxLayout()
        image_controls.addWidget(self.select_button)
        image_controls.addWidget(self.analyze_button)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addLayout(image_controls)
        layout.addWidget(self.file_label)
        layout.addWidget(self.preview_label, stretch=1)
        layout.addWidget(QLabel("해석 결과"))
        layout.addWidget(self.result_text, stretch=1)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def select_image(self) -> None:
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "분석할 사진 선택",
            "",
            SUPPORTED_IMAGE_TYPES,
        )
        if not selected_path:
            return

        pixmap = QPixmap(selected_path)
        if pixmap.isNull():
            QMessageBox.warning(self, "사진 오류", "사진을 불러올 수 없습니다.")
            return

        self.image_path = selected_path
        self.preview_pixmap = pixmap
        self.file_label.setText(f"선택된 파일: {selected_path}")
        self.show_preview()
        self.analyze_button.setEnabled(True)
        self.result_text.clear()

    def show_preview(self) -> None:
        if self.preview_pixmap is None:
            return

        scaled_pixmap = self.preview_pixmap.scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.show_preview()

    def start_analysis(self) -> None:
        if not self.image_path:
            return

        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(
                self,
                "API 키 필요",
                "API 키를 입력하거나 OPENAI_API_KEY 환경 변수를 설정하세요.",
            )
            return

        self.select_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        self.result_text.setPlainText("사진을 분석하고 있습니다...")

        self.analysis_thread = QThread(self)
        self.analysis_worker = ImageAnalysisWorker(self.image_path, api_key)
        self.analysis_worker.moveToThread(self.analysis_thread)
        self.analysis_thread.started.connect(self.analysis_worker.analyze)
        self.analysis_worker.finished.connect(self.show_result)
        self.analysis_worker.failed.connect(self.show_error)
        self.analysis_worker.finished.connect(self.finish_analysis)
        self.analysis_worker.failed.connect(self.finish_analysis)
        self.analysis_thread.start()

    @pyqtSlot(str)
    def show_result(self, result: str) -> None:
        self.result_text.setPlainText(result)

    @pyqtSlot(str)
    def show_error(self, error: str) -> None:
        self.result_text.clear()
        QMessageBox.critical(
            self, "분석 실패", f"OpenAI API 호출에 실패했습니다.\n\n{error}"
        )

    @pyqtSlot()
    def finish_analysis(self) -> None:
        self.select_button.setEnabled(True)
        self.analyze_button.setEnabled(True)
        if self.analysis_thread is not None:
            self.analysis_thread.quit()
            self.analysis_thread.wait()
            self.analysis_thread.deleteLater()
        self.analysis_thread = None
        self.analysis_worker = None


def main() -> None:
    app = QApplication(sys.argv)
    window = ImageAnalyzerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()