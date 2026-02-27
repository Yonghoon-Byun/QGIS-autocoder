# -*- coding: utf-8 -*-
"""
Claude Provider
Anthropic Claude API 연동 (anthropic SDK 우선, requests fallback)
"""

import json
from typing import List, Dict, Tuple, Optional, Callable

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import urllib.error

from .base_provider import BaseLLMProvider, LLMProviderError


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude API 제공자 (anthropic SDK 우선, requests fallback)"""

    DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
    DEFAULT_MODELS = [
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
    ]
    API_VERSION = "2023-06-01"

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-6",
                 base_url: str = ""):
        super().__init__(api_key, model, base_url or self.DEFAULT_BASE_URL)

    def get_provider_name(self) -> str:
        return "Claude"

    def get_available_models(self) -> List[str]:
        return self.DEFAULT_MODELS.copy()

    def validate_config(self) -> Tuple[bool, str]:
        valid, msg = super().validate_config()
        if not valid:
            return valid, msg
        if not self.api_key:
            return False, "Anthropic API 키가 필요합니다."
        if not (self.api_key.startswith("sk-ant-") or self.api_key.startswith("sk-")):
            return False, "유효하지 않은 Anthropic API 키 형식입니다."
        return True, ""

    def supports_streaming(self) -> bool:
        """anthropic SDK 설치 시 스트리밍 지원"""
        return HAS_ANTHROPIC

    def generate(self, messages: List[Dict[str, str]],
                 system_prompt: str = "") -> str:
        """Anthropic Messages API 호출 (SDK 우선, requests fallback)"""
        if HAS_ANTHROPIC:
            return self._generate_with_sdk(messages, system_prompt)
        return self._generate_with_requests(messages, system_prompt)

    def generate_stream(self, messages: List[Dict[str, str]],
                        system_prompt: str = "",
                        on_token: Optional[Callable[[str], None]] = None) -> str:
        """스트리밍 방식으로 응답 생성 (anthropic SDK 필요)"""
        if not HAS_ANTHROPIC:
            return self.generate(messages, system_prompt)

        try:
            client = anthropic.Anthropic(api_key=self.api_key)

            kwargs = {
                "model": self.model,
                "max_tokens": 4096,
                "messages": messages,
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            full_text = ""
            with client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    if on_token:
                        on_token(text)
                    full_text += text

            return full_text

        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                f"스트리밍 요청 실패: {str(e)}",
                provider=self.get_provider_name()
            )

    def _generate_with_sdk(self, messages: List[Dict[str, str]],
                           system_prompt: str = "") -> str:
        """anthropic SDK를 사용하여 응답 생성"""
        try:
            client = anthropic.Anthropic(api_key=self.api_key)

            kwargs = {
                "model": self.model,
                "max_tokens": 4096,
                "messages": messages,
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            message = client.messages.create(**kwargs)
            return message.content[0].text if message.content else ""

        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                f"요청 실패: {str(e)}",
                provider=self.get_provider_name()
            )

    def _generate_with_requests(self, messages: List[Dict[str, str]],
                                system_prompt: str = "") -> str:
        """requests/urllib을 사용하여 응답 생성 (fallback)"""
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages
        }
        if system_prompt:
            payload["system"] = system_prompt

        url = f"{self.base_url}/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION
        }

        try:
            if HAS_REQUESTS:
                response = requests.post(
                    url, headers=headers, json=payload, timeout=120
                )
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("error", {}).get("message", response.text)
                    raise LLMProviderError(
                        f"API 오류: {error_msg}",
                        provider=self.get_provider_name(),
                        status_code=response.status_code
                    )
                result = response.json()
            else:
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=120) as resp:
                    result = json.loads(resp.read().decode('utf-8'))

            content = result.get("content", [])
            return content[0].get("text", "") if content else ""

        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                f"요청 실패: {str(e)}",
                provider=self.get_provider_name()
            )
