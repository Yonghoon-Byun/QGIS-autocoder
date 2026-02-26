# -*- coding: utf-8 -*-
"""
API Worker
QThread 기반 비동기 LLM API 호출
"""

from typing import List, Dict, Optional
from PyQt5.QtCore import QThread, pyqtSignal


class ApiWorker(QThread):
    """비동기 LLM API 호출 워커"""

    # 시그널 정의
    started_signal = pyqtSignal()  # 요청 시작
    response_received = pyqtSignal(str)  # 응답 수신 (코드)
    error_occurred = pyqtSignal(str)  # 에러 발생
    finished_signal = pyqtSignal()  # 완료

    def __init__(self, parent=None):
        super().__init__(parent)
        self.provider = None
        self.messages: List[Dict[str, str]] = []
        self.system_prompt: str = ""
        self._is_cancelled = False

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

            # API 호출
            response = self.provider.generate(
                messages=self.messages,
                system_prompt=self.system_prompt
            )

            if self._is_cancelled:
                self.finished_signal.emit()
                return

            self.response_received.emit(response)

        except Exception as e:
            if not self._is_cancelled:
                self.error_occurred.emit(str(e))

        finally:
            self.finished_signal.emit()

    def cancel(self):
        """요청 취소"""
        self._is_cancelled = True

    def is_cancelled(self) -> bool:
        """취소 여부 확인"""
        return self._is_cancelled
