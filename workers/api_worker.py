# -*- coding: utf-8 -*-
"""
API Worker
QThread 기반 비동기 LLM API 호출 (스트리밍 지원)
"""

from typing import List, Dict, Optional
from PyQt5.QtCore import QThread, pyqtSignal


class ApiWorker(QThread):
    """비동기 LLM API 호출 워커 (스트리밍 지원)"""

    # 시그널 정의
    started_signal = pyqtSignal()       # 요청 시작
    token_received = pyqtSignal(str)    # 스트리밍 토큰 수신
    response_received = pyqtSignal(str) # 전체 응답 수신
    error_occurred = pyqtSignal(str)    # 에러 발생
    finished_signal = pyqtSignal()      # 완료

    def __init__(self, parent=None):
        super().__init__(parent)
        self.provider = None
        self.messages: List[Dict[str, str]] = []
        self.system_prompt: str = ""
        self._is_cancelled = False
        self.is_streaming = False

    def setup(self, provider, messages: List[Dict[str, str]],
              system_prompt: str = ""):
        """워커 설정

        Args:
            provider: LLM 제공자 인스턴스
            messages: 대화 히스토리
            system_prompt: 시스템 프롬프트
        """
        self.provider = provider
        self.messages = messages
        self.system_prompt = system_prompt
        self._is_cancelled = False
        self.is_streaming = False

    def run(self):
        """백그라운드에서 API 호출 실행"""
        self.started_signal.emit()

        if self._is_cancelled:
            self.finished_signal.emit()
            return

        if not self.provider:
            self.error_occurred.emit("LLM 제공자가 설정되지 않았습니다.")
            self.finished_signal.emit()
            return

        try:
            # 설정 검증
            valid, error_msg = self.provider.validate_config()
            if not valid:
                self.error_occurred.emit(error_msg)
                self.finished_signal.emit()
                return

            if self._is_cancelled:
                self.finished_signal.emit()
                return

            if self.provider.supports_streaming():
                # 스트리밍 모드
                self.is_streaming = True
                full_response = self._run_streaming()
            else:
                # 기존 방식
                self.is_streaming = False
                full_response = self.provider.generate(
                    messages=self.messages,
                    system_prompt=self.system_prompt
                )

            if not self._is_cancelled:
                self.response_received.emit(full_response)

        except Exception as e:
            if not self._is_cancelled:
                self.error_occurred.emit(str(e))

        finally:
            self.finished_signal.emit()

    def _run_streaming(self) -> str:
        """스트리밍 방식으로 API 호출"""
        full_response = ""

        def on_token(token: str):
            nonlocal full_response
            if self._is_cancelled:
                return
            full_response += token
            self.token_received.emit(token)

        self.provider.generate_stream(
            messages=self.messages,
            system_prompt=self.system_prompt,
            on_token=on_token
        )

        return full_response

    def cancel(self):
        """요청 취소"""
        self._is_cancelled = True

    def is_cancelled(self) -> bool:
        """취소 여부 확인"""
        return self._is_cancelled
