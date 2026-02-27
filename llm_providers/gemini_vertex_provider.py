# -*- coding: utf-8 -*-
"""
Gemini Vertex AI Provider
Google Cloud Vertex AI Gemini API 연동
인증: Application Default Credentials (ADC)
  → 사전에 gcloud auth application-default login 실행 필요
"""

from typing import List, Dict, Tuple, Optional, Callable

import logging

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, Content, Part, GenerationConfig
    HAS_VERTEX_AI = True
except ImportError:
    HAS_VERTEX_AI = False

from .base_provider import BaseLLMProvider, LLMProviderError

logger = logging.getLogger(__name__)


class GeminiVertexProvider(BaseLLMProvider):
    """Google Cloud Vertex AI Gemini 제공자

    설정 필드 재활용:
      api_key  → GCP 프로젝트 ID (예: "my-project-123")
      base_url → 리전 (예: "us-central1", 기본값)
    """

    DEFAULT_MODELS = [
        "gemini-2.0-flash-001",
        "gemini-1.5-pro-002",
        "gemini-1.5-flash-002",
    ]
    DEFAULT_REGION = "us-central1"

    def __init__(self, api_key: str = "",
                 model: str = "gemini-2.0-flash-001",
                 base_url: str = ""):
        # api_key → GCP 프로젝트 ID, base_url → 리전
        super().__init__(api_key, model, base_url or self.DEFAULT_REGION)
        self._initialized = False

    def get_provider_name(self) -> str:
        return "Gemini (Vertex AI)"

    def get_available_models(self) -> List[str]:
        return self.DEFAULT_MODELS.copy()

    def validate_config(self) -> Tuple[bool, str]:
        valid, msg = super().validate_config()
        if not valid:
            return valid, msg
        if not self.api_key:
            return False, "GCP 프로젝트 ID가 필요합니다."
        if not HAS_VERTEX_AI:
            return False, (
                "vertexai 패키지가 필요합니다.\n"
                "설치: pip install google-cloud-aiplatform"
            )
        return True, ""

    def supports_streaming(self) -> bool:
        """vertexai 패키지 설치 시 스트리밍 지원"""
        return HAS_VERTEX_AI

    def generate(self, messages: List[Dict[str, str]],
                 system_prompt: str = "") -> str:
        """Vertex AI Gemini API 호출 (비스트리밍)"""
        return self._generate_content(
            messages, system_prompt, stream=False
        )

    def generate_stream(self, messages: List[Dict[str, str]],
                        system_prompt: str = "",
                        on_token: Optional[Callable[[str], None]] = None) -> str:
        """Vertex AI Gemini API 스트리밍 호출"""
        return self._generate_content(
            messages, system_prompt, stream=True, on_token=on_token
        )

    def _generate_content(self, messages: List[Dict[str, str]],
                          system_prompt: str = "",
                          stream: bool = False,
                          on_token: Optional[Callable[[str], None]] = None) -> str:
        """Vertex AI API 공통 호출 로직"""
        if not HAS_VERTEX_AI:
            raise LLMProviderError(
                "vertexai 패키지가 필요합니다.",
                provider=self.get_provider_name()
            )

        try:
            # SDK 초기화 (최초 1회만)
            if not self._initialized:
                vertexai.init(project=self.api_key, location=self.base_url)
                self._initialized = True

            # 시스템 지시사항 설정
            model_kwargs = {"model_name": self.model}
            if system_prompt:
                model_kwargs["system_instruction"] = system_prompt

            model = GenerativeModel(**model_kwargs)
            gen_config = GenerationConfig(max_output_tokens=4096)

            # 메시지 변환
            contents = self._convert_messages(messages)

            if stream:
                return self._stream_content(model, contents, on_token, gen_config)
            else:
                response = model.generate_content(
                    contents, generation_config=gen_config
                )
                # 안전 필터 차단 확인
                if response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason') and \
                       hasattr(candidate.finish_reason, 'name') and \
                       candidate.finish_reason.name == "SAFETY":
                        raise LLMProviderError(
                            "안전 필터에 의해 응답이 차단되었습니다.",
                            provider=self.get_provider_name()
                        )
                try:
                    return response.text or ""
                except ValueError:
                    return ""

        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                f"요청 실패: {str(e)}",
                provider=self.get_provider_name()
            )

    def _stream_content(self, model, contents: List,
                        on_token: Optional[Callable[[str], None]],
                        gen_config=None) -> str:
        """스트리밍 응답 처리"""
        full_text = ""
        try:
            response_stream = model.generate_content(
                contents, stream=True, generation_config=gen_config
            )
            for chunk in response_stream:
                try:
                    text = chunk.text
                    if text:
                        if on_token:
                            on_token(text)
                        full_text += text
                except ValueError:
                    # chunk.text: 텍스트 파트가 없는 경우 (정상)
                    pass
                except Exception as e:
                    logger.warning(f"스트리밍 청크 처리 오류: {e}")
        except Exception as e:
            if not full_text:
                raise LLMProviderError(
                    f"스트리밍 실패: {str(e)}",
                    provider=self.get_provider_name()
                )
        return full_text

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List:
        """메시지를 Vertex AI Content 형식으로 변환

        OpenAI 형식 role 매핑:
          "user"      → "user"
          "assistant" → "model"
        """
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(Content(
                role=role,
                parts=[Part.from_text(msg["content"])]
            ))
        return contents
