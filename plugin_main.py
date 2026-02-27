# -*- coding: utf-8 -*-
"""
QGIS AI Auto-Coder Plugin
메인 플러그인 클래스 (팝업 다이얼로그 방식)
"""

import os
from typing import Optional

from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMessageBox

from .ui_dialog import AiAutoCoderDialog
from .core.context_builder import ContextBuilder
from .core.prompt_manager import PromptManager
from .core.code_executor import CodeExecutor
from .workers.api_worker import ApiWorker
from .llm_providers import (
    OpenAIProvider, ClaudeProvider, OllamaProvider, OpenAICompatProvider,
    GeminiVertexProvider
)
from .llm_providers.base_provider import LLMProviderError


class QgisAiAutoCoder:
    """QGIS AI Auto-Coder 메인 플러그인 클래스"""

    SETTINGS_PREFIX = "QgisAiAutoCoder"

    def __init__(self, iface):
        """
        Args:
            iface: QgisInterface 인스턴스
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        # .env 파일 자동 로드
        self._load_env_file()

        # 컴포넌트 초기화
        self.dialog: Optional[AiAutoCoderDialog] = None
        self.action: Optional[QAction] = None

        # 핵심 모듈
        self.context_builder = ContextBuilder(iface)
        self.prompt_manager = PromptManager()
        self.code_executor = CodeExecutor(iface)

        # LLM 제공자
        self.provider = None

        # API 워커
        self.api_worker: Optional[ApiWorker] = None

        # 설정
        self.settings = QSettings()

    def initGui(self):
        """플러그인 GUI 초기화"""
        # 아이콘 경로 (svg 또는 png)
        icon_path = os.path.join(self.plugin_dir, 'resources', 'icon.svg')
        if not os.path.exists(icon_path):
            icon_path = os.path.join(self.plugin_dir, 'resources', 'icon.png')
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            icon = QIcon()

        # 메인 액션
        self.action = QAction(
            icon,
            "AI Auto-Coder",
            self.iface.mainWindow()
        )
        self.action.triggered.connect(self._show_dialog)
        self.action.setStatusTip("AI로 PyQGIS 코드 생성 및 실행")

        # 메뉴 및 툴바에 추가
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&AI Auto-Coder", self.action)

    def unload(self):
        """플러그인 언로드"""
        # 워커 정리
        if self.api_worker and self.api_worker.isRunning():
            self.api_worker.cancel()
            self.api_worker.wait(3000)

        # 다이얼로그 제거
        if self.dialog:
            self.dialog.close()
            self.dialog.deleteLater()
            self.dialog = None

        # 메뉴 및 툴바에서 제거
        if self.action:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu("&AI Auto-Coder", self.action)
            self.action = None

    def _show_dialog(self):
        """다이얼로그 표시"""
        if self.dialog is None:
            self._create_dialog()

        # 설정 로드
        self._load_settings()

        # 다이얼로그 표시
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def _create_dialog(self):
        """다이얼로그 생성 및 설정"""
        self.dialog = AiAutoCoderDialog(self.iface.mainWindow())

        # 시그널 연결
        chat_panel = self.dialog.get_chat_panel()
        chat_panel.send_requested.connect(self._on_send_message)
        chat_panel.execute_requested.connect(self._on_execute_code)
        chat_panel.clear_requested.connect(self._on_clear_chat)
        chat_panel.cancel_requested.connect(self._on_cancel_request)

        settings_panel = self.dialog.get_settings_panel()
        settings_panel.save_btn.clicked.connect(self._save_settings)
        settings_panel.refresh_models_btn.clicked.connect(self._refresh_models)

    def _load_settings(self):
        """저장된 설정 로드"""
        if not self.dialog:
            return

        settings = {
            "provider": self.settings.value(
                f"{self.SETTINGS_PREFIX}/provider", "OpenAI"
            ),
            "api_key": self.settings.value(
                f"{self.SETTINGS_PREFIX}/api_key", ""
            ),
            "base_url": self.settings.value(
                f"{self.SETTINGS_PREFIX}/base_url", ""
            ),
            "model": self.settings.value(
                f"{self.SETTINGS_PREFIX}/model", "gpt-4o"
            ),
            "auto_execute": self.settings.value(
                f"{self.SETTINGS_PREFIX}/auto_execute", False, type=bool
            ),
            "show_code": self.settings.value(
                f"{self.SETTINGS_PREFIX}/show_code", True, type=bool
            ),
            "auto_retry": self.settings.value(
                f"{self.SETTINGS_PREFIX}/auto_retry", False, type=bool
            )
        }
        # 환경변수 우선 적용 (관리자 설정)
        admin_settings = self._get_admin_settings()
        settings.update(admin_settings)

        settings_panel = self.dialog.get_settings_panel()
        settings_panel.set_settings(settings)
        settings_panel.set_admin_mode(admin_settings)
        self._update_provider(settings)

    def _load_env_file(self):
        """플러그인 디렉토리의 .env 파일을 읽어 환경변수로 설정합니다.

        이미 설정된 시스템 환경변수는 덮어쓰지 않습니다.
        GOOGLE_APPLICATION_CREDENTIALS는 상대경로일 경우 플러그인 디렉토리 기준으로 변환합니다.
        """
        env_path = os.path.join(self.plugin_dir, '.env')
        if not os.path.exists(env_path):
            return

        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' not in line:
                        continue
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # 이미 설정된 시스템 환경변수는 유지
                    if key not in os.environ or not os.environ[key]:
                        # GCP 인증 파일 경로를 절대경로로 변환
                        if key == 'GOOGLE_APPLICATION_CREDENTIALS' and \
                           not os.path.isabs(value):
                            value = os.path.join(self.plugin_dir, value)
                        os.environ[key] = value
        except Exception:
            pass

    def _get_admin_settings(self) -> dict:
        """환경변수에서 관리자 설정을 읽습니다.

        지원 환경변수:
          QGIS_AI_PROVIDER  - LLM 제공자 (예: Claude, OpenAI, Gemini (Vertex AI))
          QGIS_AI_API_KEY   - API 키 또는 GCP 프로젝트 ID
          QGIS_AI_MODEL     - 모델명
          QGIS_AI_BASE_URL  - Base URL 또는 리전

        Returns:
            dict: 설정된 환경변수 항목만 포함 (미설정 항목은 제외)
        """
        env_map = {
            'QGIS_AI_PROVIDER': 'provider',
            'QGIS_AI_API_KEY':  'api_key',
            'QGIS_AI_MODEL':    'model',
            'QGIS_AI_BASE_URL': 'base_url',
        }
        admin = {}
        for env_key, settings_key in env_map.items():
            value = os.environ.get(env_key, '').strip()
            if value:
                admin[settings_key] = value
        return admin

    def _save_settings(self):
        """설정 저장 (관리자 환경변수 항목은 저장에서 제외)"""
        if not self.dialog:
            return

        settings = self.dialog.get_settings_panel().get_settings()
        admin_settings = self._get_admin_settings()

        # 관리자가 환경변수로 관리하는 항목은 QSettings에 저장하지 않음
        for key in ["provider", "api_key", "base_url", "model"]:
            if key not in admin_settings:
                self.settings.setValue(
                    f"{self.SETTINGS_PREFIX}/{key}", settings[key]
                )

        # 사용자 기본설정은 항상 저장
        self.settings.setValue(f"{self.SETTINGS_PREFIX}/auto_execute", settings["auto_execute"])
        self.settings.setValue(f"{self.SETTINGS_PREFIX}/show_code", settings["show_code"])
        self.settings.setValue(f"{self.SETTINGS_PREFIX}/auto_retry", settings["auto_retry"])

        self._update_provider(settings)

        # 알림
        chat_panel = self.dialog.get_chat_panel()
        chat_panel.log_widget.log("설정이 저장되었습니다.", "success")

    def _update_provider(self, settings: dict):
        """LLM 제공자 업데이트"""
        provider_name = settings.get("provider", "OpenAI")
        api_key = settings.get("api_key", "")
        base_url = settings.get("base_url", "")
        model = settings.get("model", "")

        provider_map = {
            "OpenAI": OpenAIProvider,
            "Claude": ClaudeProvider,
            "Ollama": OllamaProvider,
            "OpenAI 호환": OpenAICompatProvider,
            "Gemini (Vertex AI)": GeminiVertexProvider,
        }

        provider_class = provider_map.get(provider_name, OpenAIProvider)
        self.provider = provider_class(
            api_key=api_key,
            model=model,
            base_url=base_url
        )

    def _refresh_models(self):
        """모델 목록 새로고침"""
        if not self.dialog:
            return

        settings_panel = self.dialog.get_settings_panel()
        settings = settings_panel.get_settings()
        self._update_provider(settings)

        if self.provider:
            try:
                models = self.provider.get_available_models()
                settings_panel.model_combo.clear()
                settings_panel.model_combo.addItems(models)
                self.dialog.get_chat_panel().log_widget.log(
                    f"모델 목록 새로고침: {len(models)}개", "info"
                )
            except Exception as e:
                self.dialog.get_chat_panel().log_widget.log(
                    f"모델 목록 가져오기 실패: {e}", "error"
                )

    def _on_send_message(self, message: str):
        """메시지 전송 처리 (스트리밍 지원)"""
        if not self.dialog:
            return

        chat_panel = self.dialog.get_chat_panel()
        settings = self.dialog.get_settings_panel().get_settings()

        # 설정 업데이트
        self._update_provider(settings)

        # 설정 검증
        if self.provider:
            valid, error_msg = self.provider.validate_config()
            if not valid:
                chat_panel.chat_widget.add_system_message(error_msg, is_error=True)
                chat_panel.log_widget.log(error_msg, "error")
                return

        # 대화에 사용자 메시지 추가
        chat_panel.chat_widget.add_user_message(message)
        self.prompt_manager.add_user_message(message)

        # 컨텍스트 업데이트
        context = self.context_builder.build_context()
        self.prompt_manager.set_context(context)

        # 로딩 상태
        chat_panel.set_loading(True)
        chat_panel.log_widget.log("AI에게 요청 중...", "info")

        # 기존 워커 정리
        self._cleanup_worker()

        # API 호출 (비동기)
        self.api_worker = ApiWorker()
        self.api_worker.setup(
            provider=self.provider,
            messages=self.prompt_manager.get_messages(),
            system_prompt=self.prompt_manager.get_system_prompt()
        )

        # 스트리밍 지원 여부에 따라 시그널 연결 분기
        use_streaming = (
            self.provider is not None and
            self.provider.supports_streaming()
        )

        if use_streaming:
            # 스트리밍 모드: 토큰 수신 시 채팅 위젯 업데이트
            self.api_worker.started_signal.connect(
                chat_panel.chat_widget.begin_assistant_stream
            )
            self.api_worker.token_received.connect(
                chat_panel.chat_widget.append_stream_token
            )
            self.api_worker.response_received.connect(
                lambda response: self._on_response_received(
                    response, settings, streaming=True
                )
            )
            self.api_worker.finished_signal.connect(
                chat_panel.chat_widget.finalize_stream
            )
        else:
            # 비스트리밍 모드: 완성된 응답을 한 번에 표시
            self.api_worker.response_received.connect(
                lambda response: self._on_response_received(
                    response, settings, streaming=False
                )
            )

        self.api_worker.error_occurred.connect(self._on_api_error)
        self.api_worker.finished_signal.connect(
            lambda: chat_panel.set_loading(False)
        )

        # 워커 시작
        self.api_worker.start()

    def _on_response_received(self, response: str, settings: dict,
                              streaming: bool = False):
        """API 응답 수신 처리

        Args:
            response: 전체 응답 텍스트
            settings: 현재 설정
            streaming: True이면 채팅 위젯에 이미 스트리밍으로 표시됨
        """
        if not self.dialog:
            return

        chat_panel = self.dialog.get_chat_panel()

        # 응답을 대화 히스토리에 추가
        self.prompt_manager.add_assistant_message(response)

        # 코드 추출
        code = self.code_executor.extract_code(response)

        # 코드 영역 표시 여부
        show_code = settings.get("show_code", True)
        chat_panel.show_code_area(show_code)

        if code:
            # 코드 에디터 업데이트 (스트리밍/비스트리밍 공통)
            chat_panel.set_code(code)
            chat_panel.log_widget.log("코드 생성 완료", "success")

            if not streaming:
                # 비스트리밍 모드에서만 채팅 버블 추가 (스트리밍은 이미 표시됨)
                chat_panel.chat_widget.add_assistant_message(code, is_code=True)

            # 자동 실행
            if settings.get("auto_execute", False):
                self._on_execute_code(code)
        else:
            if not streaming:
                # 비스트리밍 모드에서만 채팅에 응답 추가
                chat_panel.chat_widget.add_assistant_message(response)
            chat_panel.log_widget.log("응답 수신 (코드 없음)", "info")

    def _on_api_error(self, error_message: str):
        """API 에러 처리"""
        if not self.dialog:
            return

        chat_panel = self.dialog.get_chat_panel()
        chat_panel.chat_widget.add_system_message(
            f"API 오류: {error_message}", is_error=True
        )
        chat_panel.log_widget.log(f"API 오류: {error_message}", "error")

    def _on_execute_code(self, code: str):
        """코드 실행"""
        if not self.dialog:
            return

        chat_panel = self.dialog.get_chat_panel()
        settings = self.dialog.get_settings_panel().get_settings()

        chat_panel.log_widget.log("코드 실행 중...", "info")

        # 코드 실행
        success, stdout, stderr = self.code_executor.execute(code)

        if success:
            if stdout:
                chat_panel.log_widget.log(f"출력:\n{stdout}", "success")
                chat_panel.chat_widget.add_system_message(f"실행 결과:\n{stdout}")
            else:
                chat_panel.log_widget.log("코드 실행 완료", "success")
                chat_panel.chat_widget.add_system_message("코드 실행 완료")
        else:
            chat_panel.log_widget.log(f"실행 오류:\n{stderr}", "error")
            chat_panel.chat_widget.add_system_message(
                f"실행 오류:\n{stderr}", is_error=True
            )

            # 자동 재시도
            if settings.get("auto_retry", False):
                self._retry_with_error(stderr)

    def _retry_with_error(self, error_message: str):
        """에러를 LLM에 전달하여 재시도"""
        if not self.dialog:
            return

        chat_panel = self.dialog.get_chat_panel()
        chat_panel.log_widget.log("에러 수정을 위해 재시도 중...", "warning")

        # 에러 피드백 추가
        self.prompt_manager.add_error_feedback(error_message)

        # 재전송 (설정 가져오기)
        settings = self.dialog.get_settings_panel().get_settings()

        # 로딩 상태
        chat_panel.set_loading(True)

        # 기존 워커 정리
        self._cleanup_worker()

        # API 호출
        self.api_worker = ApiWorker()
        self.api_worker.setup(
            provider=self.provider,
            messages=self.prompt_manager.get_messages(),
            system_prompt=self.prompt_manager.get_system_prompt()
        )

        # 시그널 연결 (자동 재시도 비활성화하여 무한 루프 방지)
        retry_settings = settings.copy()
        retry_settings["auto_retry"] = False

        use_streaming = (
            self.provider is not None and
            self.provider.supports_streaming()
        )

        if use_streaming:
            self.api_worker.started_signal.connect(
                chat_panel.chat_widget.begin_assistant_stream
            )
            self.api_worker.token_received.connect(
                chat_panel.chat_widget.append_stream_token
            )
            self.api_worker.response_received.connect(
                lambda response: self._on_response_received(
                    response, retry_settings, streaming=True
                )
            )
            self.api_worker.finished_signal.connect(
                chat_panel.chat_widget.finalize_stream
            )
        else:
            self.api_worker.response_received.connect(
                lambda response: self._on_response_received(
                    response, retry_settings, streaming=False
                )
            )

        self.api_worker.error_occurred.connect(self._on_api_error)
        self.api_worker.finished_signal.connect(
            lambda: chat_panel.set_loading(False)
        )

        self.api_worker.start()

    def _cleanup_worker(self):
        """기존 API 워커를 정리합니다."""
        if self.api_worker:
            if self.api_worker.isRunning():
                self.api_worker.cancel()
                self.api_worker.wait(1000)
            try:
                self.api_worker.disconnect()
            except TypeError:
                pass
            self.api_worker.deleteLater()
            self.api_worker = None

    def _on_cancel_request(self):
        """요청 취소"""
        if self.api_worker and self.api_worker.isRunning():
            self.api_worker.cancel()
            if self.dialog:
                self.dialog.get_chat_panel().log_widget.log("요청 취소됨", "warning")

    def _on_clear_chat(self):
        """대화 초기화"""
        if not self.dialog:
            return

        chat_panel = self.dialog.get_chat_panel()

        # 확인 대화상자
        reply = QMessageBox.question(
            self.dialog,
            "대화 초기화",
            "대화 내용을 모두 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            chat_panel.chat_widget.clear_chat()
            chat_panel.code_editor.clear()
            chat_panel.log_widget.clear_log()
            self.prompt_manager.clear_history()
            chat_panel.log_widget.log("대화가 초기화되었습니다.", "info")
