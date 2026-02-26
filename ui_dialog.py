# -*- coding: utf-8 -*-
"""
UI Dialog
QGIS AI Auto-Coder 팝업 다이얼로그 UI
reference/prompt.md 디자인 시스템 적용
"""

from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QFont, QTextCursor, QIcon
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QTextEdit, QPlainTextEdit, QTextBrowser, QFrame,
    QSplitter, QSizePolicy, QCheckBox, QScrollArea
)

# ============================================================
# 글로벌 스타일시트 (reference/prompt.md 기반)
# ============================================================

DIALOG_STYLESHEET = """
* {
    font-family: 'Pretendard', 'Pretendard Variable', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
    font-weight: 500;
}
QDialog {
    background-color: #f9fafb;
}
QLabel {
    color: #374151;
    font-weight: 500;
}
QComboBox {
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 8px 12px;
    background-color: #f9fafb;
    font-size: 14px;
    color: #374151;
}
QComboBox:hover {
    border-color: #9ca3af;
    background-color: white;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    border: 1px solid #d1d5db;
    background-color: white;
    selection-background-color: #e5e7eb;
}
QLineEdit {
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 8px 12px;
    background-color: #f9fafb;
    font-size: 14px;
    color: #374151;
}
QLineEdit:hover {
    border-color: #9ca3af;
}
QLineEdit:focus {
    border-color: #6b7280;
    background-color: white;
}
QPlainTextEdit {
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 8px 12px;
    background-color: white;
    font-size: 14px;
    color: #374151;
}
QPlainTextEdit:focus {
    border-color: #6b7280;
}
QCheckBox {
    font-size: 13px;
    color: #374151;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #d1d5db;
    background-color: white;
}
QCheckBox::indicator:checked {
    background-color: #1f2937;
    border-color: #1f2937;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    background-color: #f3f4f6;
    width: 10px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background-color: #9ca3af;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #6b7280;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
"""


# ============================================================
# 카드 컴포넌트
# ============================================================

class Card(QFrame):
    """카드 스타일 컨테이너"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet("""
            QFrame#card {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(12)

    def add_header(self, title: str, description: str = ""):
        """카드 헤더 추가"""
        header_label = QLabel(title)
        header_label.setStyleSheet("""
            font-size: 15px;
            font-weight: 600;
            color: #1f2937;
        """)
        self._layout.addWidget(header_label)

        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet("""
                font-size: 13px;
                color: #6b7280;
            """)
            desc_label.setWordWrap(True)
            self._layout.addWidget(desc_label)

    def add_widget(self, widget):
        """위젯 추가"""
        self._layout.addWidget(widget)

    def add_layout(self, layout):
        """레이아웃 추가"""
        self._layout.addLayout(layout)

    def add_stretch(self):
        """스트레치 추가"""
        self._layout.addStretch()


# ============================================================
# 채팅 위젯
# ============================================================

class ChatWidget(QTextBrowser):
    """채팅 스타일 대화 표시 위젯"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenExternalLinks(False)
        self.setReadOnly(True)
        self.setMinimumHeight(200)

        self.setStyleSheet("""
            QTextBrowser {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }
        """)

    def add_user_message(self, message: str):
        """사용자 메시지 추가"""
        html = f'''
        <div style="margin: 12px 0; text-align: right;">
            <div style="display: inline-block; max-width: 85%; text-align: left;">
                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">나</div>
                <div style="background-color: #1f2937; color: white; padding: 12px 16px;
                            border-radius: 12px 12px 4px 12px; font-size: 14px;">
                    {self._escape_html(message)}
                </div>
            </div>
        </div>
        '''
        self.append(html)
        self._scroll_to_bottom()

    def add_assistant_message(self, message: str, is_code: bool = False):
        """AI 응답 추가"""
        if is_code:
            content = f'''<pre style="background-color: #1f2937; color: #e5e7eb;
                          padding: 12px; border-radius: 6px; overflow-x: auto;
                          font-family: 'Consolas', 'Monaco', monospace; font-size: 13px;
                          margin: 8px 0; white-space: pre-wrap;">{self._escape_html(message)}</pre>'''
        else:
            content = self._escape_html(message)

        html = f'''
        <div style="margin: 12px 0; text-align: left;">
            <div style="display: inline-block; max-width: 85%; text-align: left;">
                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">AI 어시스턴트</div>
                <div style="background-color: #f3f4f6; color: #374151; padding: 12px 16px;
                            border-radius: 12px 12px 12px 4px; font-size: 14px;">
                    {content}
                </div>
            </div>
        </div>
        '''
        self.append(html)
        self._scroll_to_bottom()

    def add_system_message(self, message: str, is_error: bool = False):
        """시스템 메시지 추가"""
        if is_error:
            bg_color = "#fef2f2"
            border_color = "#fecaca"
            text_color = "#dc2626"
            icon = "⚠️"
        else:
            bg_color = "#f0fdf4"
            border_color = "#86efac"
            text_color = "#166534"
            icon = "✓"

        html = f'''
        <div style="margin: 12px 0; text-align: center;">
            <div style="display: inline-block; background-color: {bg_color};
                        border: 1px solid {border_color}; padding: 8px 16px;
                        border-radius: 6px; font-size: 13px; color: {text_color};">
                {icon} {self._escape_html(message)}
            </div>
        </div>
        '''
        self.append(html)
        self._scroll_to_bottom()

    def _escape_html(self, text: str) -> str:
        return (text.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('\n', '<br>'))

    def _scroll_to_bottom(self):
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_chat(self):
        self.clear()


# ============================================================
# 코드 에디터 위젯
# ============================================================

class CodeEditorWidget(QPlainTextEdit):
    """코드 편집 위젯"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(False)
        self.setMinimumHeight(120)

        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)

        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1f2937;
                color: #e5e7eb;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 12px;
                font-size: 13px;
                selection-background-color: #4b5563;
            }
        """)
        self.setTabStopDistance(40)

    def set_code(self, code: str):
        self.setPlainText(code)

    def get_code(self) -> str:
        return self.toPlainText()


# ============================================================
# 로그 위젯
# ============================================================

class LogWidget(QTextEdit):
    """실행 로그 위젯"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumHeight(120)

        font = QFont("Consolas", 11)
        self.setFont(font)

        self.setStyleSheet("""
            QTextEdit {
                background-color: #f9fafb;
                color: #374151;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
        """)

    def log(self, message: str, level: str = "info"):
        color_map = {
            "info": "#374151",
            "error": "#dc2626",
            "warning": "#d97706",
            "success": "#059669"
        }
        color = color_map.get(level, "#374151")
        prefix_map = {
            "info": "ℹ",
            "error": "✖",
            "warning": "⚠",
            "success": "✓"
        }
        prefix = prefix_map.get(level, "•")

        html = f'<div style="color: {color}; margin: 2px 0;">{prefix} {message}</div>'
        self.append(html)

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)

    def clear_log(self):
        self.clear()


# ============================================================
# 버튼 스타일
# ============================================================

def create_primary_button(text: str) -> QPushButton:
    """주요 액션 버튼 생성"""
    btn = QPushButton(text)
    btn.setStyleSheet("""
        QPushButton {
            background-color: #1f2937;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 14px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #374151;
        }
        QPushButton:pressed {
            background-color: #1f2937;
        }
        QPushButton:disabled {
            background-color: #9ca3af;
            color: #e5e7eb;
        }
    """)
    return btn


def create_secondary_button(text: str) -> QPushButton:
    """보조 버튼 생성"""
    btn = QPushButton(text)
    btn.setStyleSheet("""
        QPushButton {
            background-color: white;
            color: #374151;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 14px;
            font-weight: 500;
        }
        QPushButton:hover {
            background-color: #f9fafb;
            border-color: #9ca3af;
        }
        QPushButton:pressed {
            background-color: #f3f4f6;
        }
        QPushButton:disabled {
            color: #9ca3af;
            background-color: #f9fafb;
        }
    """)
    return btn


def create_icon_button(text: str) -> QPushButton:
    """아이콘 버튼 생성"""
    btn = QPushButton(text)
    btn.setFixedSize(36, 36)
    btn.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #6b7280;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            font-size: 16px;
        }
        QPushButton:hover {
            background-color: #f3f4f6;
            color: #374151;
        }
    """)
    return btn


# ============================================================
# 설정 패널
# ============================================================

class SettingsPanel(QWidget):
    """설정 패널 위젯"""

    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # LLM 제공자 카드
        provider_card = Card()
        provider_card.add_header(
            "LLM 제공자 설정",
            "AI 모델 연결 설정을 구성합니다."
        )

        # 제공자 선택
        provider_row = QHBoxLayout()
        provider_label = QLabel("제공자")
        provider_label.setStyleSheet("font-size: 14px; min-width: 80px;")
        provider_row.addWidget(provider_label)
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["OpenAI", "Claude", "Ollama", "OpenAI 호환"])
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_row.addWidget(self.provider_combo, 1)
        provider_card.add_layout(provider_row)

        # API 키
        api_row = QHBoxLayout()
        api_label = QLabel("API 키")
        api_label.setStyleSheet("font-size: 14px; min-width: 80px;")
        api_row.addWidget(api_label)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("sk-...")
        api_row.addWidget(self.api_key_edit, 1)
        provider_card.add_layout(api_row)

        # Base URL
        url_row = QHBoxLayout()
        self.base_url_label = QLabel("Base URL")
        self.base_url_label.setStyleSheet("font-size: 14px; min-width: 80px;")
        url_row.addWidget(self.base_url_label)
        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("http://localhost:11434")
        url_row.addWidget(self.base_url_edit, 1)
        provider_card.add_layout(url_row)

        # 모델 선택
        model_row = QHBoxLayout()
        model_label = QLabel("모델")
        model_label.setStyleSheet("font-size: 14px; min-width: 80px;")
        model_row.addWidget(model_label)
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        model_row.addWidget(self.model_combo, 1)
        self.refresh_models_btn = create_icon_button("↻")
        self.refresh_models_btn.setToolTip("모델 목록 새로고침")
        model_row.addWidget(self.refresh_models_btn)
        provider_card.add_layout(model_row)

        layout.addWidget(provider_card)

        # 실행 옵션 카드
        options_card = Card()
        options_card.add_header(
            "실행 옵션",
            "코드 생성 및 실행 동작을 설정합니다."
        )

        self.auto_execute_check = QCheckBox("코드 생성 후 자동 실행")
        options_card.add_widget(self.auto_execute_check)

        self.show_code_check = QCheckBox("생성된 코드 표시")
        self.show_code_check.setChecked(True)
        options_card.add_widget(self.show_code_check)

        self.auto_retry_check = QCheckBox("에러 시 자동 재시도")
        options_card.add_widget(self.auto_retry_check)

        layout.addWidget(options_card)

        # 저장 버튼
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.save_btn = create_primary_button("설정 저장")
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

        layout.addStretch()

        self._on_provider_changed(self.provider_combo.currentText())

    def _on_provider_changed(self, provider: str):
        self.api_key_edit.setEnabled(provider != "Ollama")
        if provider == "Ollama":
            self.api_key_edit.setPlaceholderText("(필요 없음)")
        elif provider == "OpenAI":
            self.api_key_edit.setPlaceholderText("sk-...")
        elif provider == "Claude":
            self.api_key_edit.setPlaceholderText("sk-ant-...")
        else:
            self.api_key_edit.setPlaceholderText("(선택 사항)")

        if provider == "Ollama":
            self.base_url_edit.setPlaceholderText("http://localhost:11434")
        elif provider == "OpenAI 호환":
            self.base_url_edit.setPlaceholderText("http://localhost:1234/v1")
        else:
            self.base_url_edit.setPlaceholderText("(기본값 사용)")

        self._update_model_list(provider)

    def _update_model_list(self, provider: str):
        self.model_combo.clear()
        models = {
            "OpenAI": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
            "Claude": ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022",
                       "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
            "Ollama": ["llama3.1:latest", "codellama:latest", "deepseek-coder:latest",
                       "mistral:latest", "qwen2.5-coder:latest"],
            "OpenAI 호환": ["local-model"]
        }
        self.model_combo.addItems(models.get(provider, []))

    def get_settings(self) -> dict:
        return {
            "provider": self.provider_combo.currentText(),
            "api_key": self.api_key_edit.text(),
            "base_url": self.base_url_edit.text(),
            "model": self.model_combo.currentText(),
            "auto_execute": self.auto_execute_check.isChecked(),
            "show_code": self.show_code_check.isChecked(),
            "auto_retry": self.auto_retry_check.isChecked()
        }

    def set_settings(self, settings: dict):
        if "provider" in settings:
            index = self.provider_combo.findText(settings["provider"])
            if index >= 0:
                self.provider_combo.setCurrentIndex(index)
        if "api_key" in settings:
            self.api_key_edit.setText(settings["api_key"])
        if "base_url" in settings:
            self.base_url_edit.setText(settings["base_url"])
        if "model" in settings:
            self.model_combo.setCurrentText(settings["model"])
        if "auto_execute" in settings:
            self.auto_execute_check.setChecked(settings["auto_execute"])
        if "show_code" in settings:
            self.show_code_check.setChecked(settings["show_code"])
        if "auto_retry" in settings:
            self.auto_retry_check.setChecked(settings["auto_retry"])


# ============================================================
# 채팅 패널
# ============================================================

class ChatPanel(QWidget):
    """채팅 패널 위젯"""

    send_requested = pyqtSignal(str)
    execute_requested = pyqtSignal(str)
    clear_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 메인 스플리터
        splitter = QSplitter(Qt.Vertical)

        # 채팅 영역
        self.chat_widget = ChatWidget()
        splitter.addWidget(self.chat_widget)

        # 코드 영역
        self.code_container = QWidget()
        code_layout = QVBoxLayout(self.code_container)
        code_layout.setContentsMargins(0, 0, 0, 0)
        code_layout.setSpacing(8)

        code_header = QHBoxLayout()
        self.code_toggle_btn = QPushButton("▼ 생성된 코드")
        self.code_toggle_btn.setCheckable(True)
        self.code_toggle_btn.setChecked(True)
        self.code_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #6b7280;
                border: none;
                font-size: 13px;
                font-weight: 600;
                text-align: left;
                padding: 4px 0;
            }
            QPushButton:hover {
                color: #374151;
            }
        """)
        self.code_toggle_btn.clicked.connect(self._toggle_code_view)
        code_header.addWidget(self.code_toggle_btn)
        code_header.addStretch()
        code_layout.addLayout(code_header)

        self.code_editor = CodeEditorWidget()
        code_layout.addWidget(self.code_editor)
        splitter.addWidget(self.code_container)

        # 로그 영역
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(4)

        log_label = QLabel("실행 로그")
        log_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #6b7280;")
        log_layout.addWidget(log_label)
        self.log_widget = LogWidget()
        log_layout.addWidget(self.log_widget)
        splitter.addWidget(log_container)

        splitter.setSizes([300, 150, 100])
        layout.addWidget(splitter, 1)

        # 입력 영역
        input_card = Card()

        self.input_edit = QPlainTextEdit()
        self.input_edit.setMaximumHeight(80)
        self.input_edit.setPlaceholderText(
            "원하는 작업을 자연어로 입력하세요...\n"
            "예: '현재 프로젝트의 모든 레이어 이름을 출력해줘'"
        )
        self.input_edit.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 12px;
                background-color: #f9fafb;
                font-size: 14px;
            }
            QPlainTextEdit:focus {
                border-color: #6b7280;
                background-color: white;
            }
        """)
        input_card.add_widget(self.input_edit)

        # 버튼 영역
        btn_layout = QHBoxLayout()

        self.clear_btn = create_secondary_button("초기화")
        self.clear_btn.clicked.connect(self.clear_requested.emit)
        btn_layout.addWidget(self.clear_btn)

        btn_layout.addStretch()

        self.cancel_btn = create_secondary_button("취소")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)
        btn_layout.addWidget(self.cancel_btn)

        self.execute_btn = create_secondary_button("실행")
        self.execute_btn.setEnabled(False)
        self.execute_btn.clicked.connect(self._on_execute_clicked)
        btn_layout.addWidget(self.execute_btn)

        self.send_btn = create_primary_button("전송")
        self.send_btn.clicked.connect(self._on_send_clicked)
        btn_layout.addWidget(self.send_btn)

        input_card.add_layout(btn_layout)
        layout.addWidget(input_card)

        self.input_edit.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.input_edit and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
                self._on_send_clicked()
                return True
        return super().eventFilter(obj, event)

    def _on_send_clicked(self):
        text = self.input_edit.toPlainText().strip()
        if text:
            self.send_requested.emit(text)
            self.input_edit.clear()

    def _on_execute_clicked(self):
        code = self.code_editor.get_code()
        if code.strip():
            self.execute_requested.emit(code)

    def _toggle_code_view(self):
        visible = self.code_toggle_btn.isChecked()
        self.code_editor.setVisible(visible)
        self.code_toggle_btn.setText(
            "▼ 생성된 코드" if visible else "▶ 생성된 코드"
        )

    def set_code(self, code: str):
        self.code_editor.set_code(code)
        self.execute_btn.setEnabled(bool(code.strip()))

    def set_loading(self, loading: bool):
        self.send_btn.setEnabled(not loading)
        self.cancel_btn.setEnabled(loading)
        self.input_edit.setEnabled(not loading)
        self.send_btn.setText("생성 중..." if loading else "전송")

    def show_code_area(self, show: bool):
        self.code_container.setVisible(show)


# ============================================================
# 메인 다이얼로그
# ============================================================

class AiAutoCoderDialog(QDialog):
    """AI Auto-Coder 메인 팝업 다이얼로그"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QGIS AI Auto-Coder")
        self.setMinimumSize(700, 650)
        self.resize(800, 700)
        self.setStyleSheet(DIALOG_STYLESHEET)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 헤더
        header = self._create_header()
        layout.addWidget(header)

        # 메인 컨텐츠 (좌: 채팅, 우: 설정)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # 채팅 패널 (메인)
        self.chat_panel = ChatPanel()
        content_layout.addWidget(self.chat_panel, 2)

        # 설정 패널 (사이드)
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        settings_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        settings_scroll.setFixedWidth(320)

        self.settings_panel = SettingsPanel()
        settings_scroll.setWidget(self.settings_panel)
        content_layout.addWidget(settings_scroll)

        layout.addLayout(content_layout, 1)

        # 푸터
        footer = self._create_footer()
        layout.addWidget(footer)

    def _create_header(self) -> QWidget:
        """헤더 생성"""
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 8)

        # 타이틀
        title = QLabel("AI Auto-Coder")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: 700;
            color: #1f2937;
        """)
        header_layout.addWidget(title)

        # 부제목
        subtitle = QLabel("자연어로 PyQGIS 코드를 생성하고 실행합니다")
        subtitle.setStyleSheet("""
            font-size: 13px;
            color: #6b7280;
            margin-left: 12px;
        """)
        header_layout.addWidget(subtitle)

        header_layout.addStretch()

        return header

    def _create_footer(self) -> QWidget:
        """푸터 생성"""
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 8, 0, 0)

        # 안내 메시지
        info = QLabel("💡 Shift+Enter로 줄바꿈, Enter로 전송")
        info.setStyleSheet("font-size: 12px; color: #9ca3af;")
        footer_layout.addWidget(info)

        footer_layout.addStretch()

        # 닫기 버튼
        self.close_btn = create_secondary_button("닫기")
        self.close_btn.clicked.connect(self.close)
        footer_layout.addWidget(self.close_btn)

        return footer

    def get_chat_panel(self) -> ChatPanel:
        return self.chat_panel

    def get_settings_panel(self) -> SettingsPanel:
        return self.settings_panel
