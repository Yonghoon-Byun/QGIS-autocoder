# -*- coding: utf-8 -*-
"""
OpenAI Compatible Provider
LM Studio, LocalAI 등 OpenAI 호환 API 연동
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


class OpenAICompatProvider(BaseLLMProvider):
    """OpenAI 호환 API 제공자 (LM Studio, LocalAI 등)"""

    DEFAULT_BASE_URL = "http://localhost:1234/v1"
    DEFAULT_MODELS = [
        "local-model"
    ]

    def __init__(self, api_key: str = "", model: str = "local-model",
                 base_url: str = ""):
        super().__init__(api_key, model, base_url or self.DEFAULT_BASE_URL)

    def get_provider_name(self) -> str:
        return "OpenAI 호환"

    def get_available_models(self) -> List[str]:
        """서버에서 모델 목록을 가져옵니다."""
        try:
            url = f"{self.base_url}/models"
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            if HAS_REQUESTS:
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    models = [m["id"] for m in data.get("data", [])]
                    return models if models else self.DEFAULT_MODELS
            else:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    models = [m["id"] for m in data.get("data", [])]
                    return models if models else self.DEFAULT_MODELS
        except Exception:
            pass
        return self.DEFAULT_MODELS

    def validate_config(self) -> Tuple[bool, str]:
        valid, msg = super().validate_config()
        if not valid:
            return valid, msg

        if not self.base_url:
            return False, "API 엔드포인트 URL이 필요합니다."

        # 서버 연결 확인
        try:
            url = f"{self.base_url}/models"
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            if HAS_REQUESTS:
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code not in [200, 401]:  # 401은 인증 필요
                    return False, f"서버에 연결할 수 없습니다: {self.base_url}"
            else:
                req = urllib.request.Request(url, headers=headers)
                urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            return False, f"서버에 연결할 수 없습니다: {str(e)}"

        return True, ""

    def generate(self, messages: List[Dict[str, str]],
                 system_prompt: str = "") -> str:
        """OpenAI 호환 Chat Completions API 호출"""

        # 메시지 구성
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": api_messages,
            "temperature": 0.1,
            "max_tokens": 4096
        }

        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            if HAS_REQUESTS:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=300
                )
                if response.status_code != 200:
                    error_text = response.text
                    try:
                        error_data = response.json()
                        error_text = error_data.get("error", {}).get("message",
                                                                      error_text)
                    except Exception:
                        pass
                    raise LLMProviderError(
                        f"API 오류: {error_text}",
                        provider=self.get_provider_name(),
                        status_code=response.status_code
                    )
                result = response.json()
            else:
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=300) as response:
                    result = json.loads(response.read().decode('utf-8'))

            return result["choices"][0]["message"]["content"]

        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                f"요청 실패: {str(e)}",
                provider=self.get_provider_name()
            )
