# -*- coding: utf-8 -*-
"""
Claude Provider
Anthropic Claude API 연동
"""

import json
from typing import List, Dict, Tuple

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import urllib.error

from .base_provider import BaseLLMProvider, LLMProviderError


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude API 제공자"""

    DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
    DEFAULT_MODELS = [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307"
    ]
    API_VERSION = "2023-06-01"

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-20250514",
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
        if not self.api_key.startswith("sk-ant-"):
            return False, "유효하지 않은 Anthropic API 키 형식입니다."
        return True, ""

    def generate(self, messages: List[Dict[str, str]],
                 system_prompt: str = "") -> str:
        """Anthropic Messages API 호출"""

        # Claude API는 system을 별도 필드로 받음
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
                    url,
                    headers=headers,
                    json=payload,
                    timeout=120
                )
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("error", {}).get("message",
                                                                 response.text)
                    raise LLMProviderError(
                        f"API 오류: {error_msg}",
                        provider=self.get_provider_name(),
                        status_code=response.status_code
                    )
                result = response.json()
            else:
                # urllib fallback
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=120) as response:
                    result = json.loads(response.read().decode('utf-8'))

            # Claude 응답 형식: content[0].text
            content = result.get("content", [])
            if content and len(content) > 0:
                return content[0].get("text", "")
            return ""

        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                f"요청 실패: {str(e)}",
                provider=self.get_provider_name()
            )
