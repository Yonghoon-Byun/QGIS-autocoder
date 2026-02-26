# -*- coding: utf-8 -*-
"""
Ollama Provider
로컬 Ollama 서버 연동
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


class OllamaProvider(BaseLLMProvider):
    """Ollama 로컬 모델 제공자"""

    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_MODELS = [
        "llama3.1:latest",
        "codellama:latest",
        "deepseek-coder:latest",
        "mistral:latest",
        "qwen2.5-coder:latest"
    ]

    def __init__(self, api_key: str = "", model: str = "llama3.1:latest",
                 base_url: str = ""):
        # Ollama는 API 키 불필요
        super().__init__("", model, base_url or self.DEFAULT_BASE_URL)

    def get_provider_name(self) -> str:
        return "Ollama"

    def get_available_models(self) -> List[str]:
        """로컬 Ollama 서버에서 모델 목록을 가져옵니다."""
        try:
            url = f"{self.base_url}/api/tags"
            if HAS_REQUESTS:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return models if models else self.DEFAULT_MODELS
            else:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    models = [m["name"] for m in data.get("models", [])]
                    return models if models else self.DEFAULT_MODELS
        except Exception:
            pass
        return self.DEFAULT_MODELS

    def validate_config(self) -> Tuple[bool, str]:
        valid, msg = super().validate_config()
        if not valid:
            return valid, msg

        # Ollama 서버 연결 확인
        try:
            url = f"{self.base_url}/api/tags"
            if HAS_REQUESTS:
                response = requests.get(url, timeout=5)
                if response.status_code != 200:
                    return False, f"Ollama 서버에 연결할 수 없습니다: {self.base_url}"
            else:
                req = urllib.request.Request(url)
                urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            return False, f"Ollama 서버에 연결할 수 없습니다: {str(e)}"

        return True, ""

    def generate(self, messages: List[Dict[str, str]],
                 system_prompt: str = "") -> str:
        """Ollama Chat API 호출"""

        # 메시지 구성
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": api_messages,
            "stream": False,
            "options": {
                "temperature": 0.1
            }
        }

        url = f"{self.base_url}/api/chat"
        headers = {"Content-Type": "application/json"}

        try:
            if HAS_REQUESTS:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=300  # 로컬 모델은 더 오래 걸릴 수 있음
                )
                if response.status_code != 200:
                    raise LLMProviderError(
                        f"API 오류: {response.text}",
                        provider=self.get_provider_name(),
                        status_code=response.status_code
                    )
                result = response.json()
            else:
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=300) as response:
                    result = json.loads(response.read().decode('utf-8'))

            return result.get("message", {}).get("content", "")

        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                f"요청 실패: {str(e)}",
                provider=self.get_provider_name()
            )
