# -*- coding: utf-8 -*-
"""
Base LLM Provider
모든 LLM 제공자의 추상 베이스 클래스
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple


class BaseLLMProvider(ABC):
    """LLM 제공자 추상 베이스 클래스"""

    def __init__(self, api_key: str = "", model: str = "", base_url: str = ""):
        """
        Args:
            api_key: API 키
            model: 사용할 모델명
            base_url: API 엔드포인트 URL (선택)
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    @abstractmethod
    def generate(self, messages: List[Dict[str, str]],
                 system_prompt: str = "") -> str:
        """LLM에 메시지를 보내고 응답을 받습니다.

        Args:
            messages: 대화 히스토리 [{"role": "user/assistant", "content": "..."}]
            system_prompt: 시스템 프롬프트

        Returns:
            str: LLM 응답 텍스트

        Raises:
            LLMProviderError: API 호출 실패 시
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """제공자 이름을 반환합니다."""
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """사용 가능한 모델 목록을 반환합니다."""
        pass

    def validate_config(self) -> Tuple[bool, str]:
        """설정이 유효한지 검증합니다.

        Returns:
            Tuple: (유효 여부, 에러 메시지)
        """
        if not self.model:
            return False, "모델이 선택되지 않았습니다."
        return True, ""


class LLMProviderError(Exception):
    """LLM 제공자 에러"""

    def __init__(self, message: str, provider: str = "",
                 status_code: Optional[int] = None):
        self.message = message
        self.provider = provider
        self.status_code = status_code
        super().__init__(self.message)

    def __str__(self):
        if self.provider:
            return f"[{self.provider}] {self.message}"
        return self.message
