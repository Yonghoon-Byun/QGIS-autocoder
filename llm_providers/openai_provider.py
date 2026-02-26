# -*- coding: utf-8 -*-
"""
OpenAI Provider
OpenAI API (GPT-4, GPT-4o 등) 연동
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


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API 제공자"""

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo"
    ]

    def __init__(self, api_key: str = "", model: str = "gpt-4o",
                 base_url: str = ""):
        super().__init__(api_key, model, base_url or self.DEFAULT_BASE_URL)

    def get_provider_name(self) -> str:
        return "OpenAI"

    def get_available_models(self) -> List[str]:
        return self.DEFAULT_MODELS.copy()

    def validate_config(self) -> Tuple[bool, str]:
        valid, msg = super().validate_config()
        if not valid:
            return valid, msg
        if not self.api_key:
            return False, "OpenAI API 키가 필요합니다."
        if not self.api_key.startswith("sk-"):
            return False, "유효하지 않은 OpenAI API 키 형식입니다."
        return True, ""

    def generate(self, messages: List[Dict[str, str]],
                 system_prompt: str = "") -> str:
        """OpenAI Chat Completions API 호출"""

        # 메시지 구성
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": api_messages,
            "temperature": 0.1,  # 코드 생성은 낮은 temperature
            "max_tokens": 4096
        }

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
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

            return result["choices"][0]["message"]["content"]

        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                f"요청 실패: {str(e)}",
                provider=self.get_provider_name()
            )
