# -*- coding: utf-8 -*-
"""
Prompt Manager
시스템 프롬프트 및 대화 히스토리 관리
"""

from typing import List, Dict


class PromptManager:
    """프롬프트 및 대화 히스토리 관리"""

    SYSTEM_PROMPT_TEMPLATE = """당신은 전문 PyQGIS 코딩 어시스턴트입니다.
사용자의 요청을 QGIS Python Console에서 실행 가능한 완벽한 Python 스크립트로 변환하세요.

## 규칙
1. `iface`와 `QgsProject.instance()`는 이미 사용 가능합니다.
2. 마크다운 코드 블록(```python```) 없이 순수 Python 코드만 출력하세요.
3. 필요한 모든 import문을 코드 시작 부분에 포함하세요.
4. 결과를 print()로 출력하여 사용자가 확인할 수 있게 하세요.
5. 에러 처리를 포함하여 안정적인 코드를 작성하세요.
6. 한국어 주석으로 코드를 설명하세요.

## 사용 가능한 주요 모듈
- qgis.core: QgsProject, QgsVectorLayer, QgsRasterLayer, QgsFeature, QgsGeometry 등
- qgis.utils: iface (QgisInterface)
- processing: run() 함수로 Processing Toolbox 알고리즘 실행

## 현재 QGIS 프로젝트 컨텍스트
{context}

## 출력 형식
순수 Python 코드만 출력하세요. 설명이나 마크다운 태그 없이 실행 가능한 코드만 작성하세요."""

    def __init__(self):
        """프롬프트 매니저 초기화"""
        self.messages: List[Dict[str, str]] = []
        self.context: str = ""

    def set_context(self, context: str):
        """QGIS 컨텍스트를 설정합니다."""
        self.context = context

    def get_system_prompt(self) -> str:
        """시스템 프롬프트를 반환합니다."""
        return self.SYSTEM_PROMPT_TEMPLATE.format(context=self.context)

    def add_user_message(self, content: str):
        """사용자 메시지를 히스토리에 추가합니다."""
        self.messages.append({
            "role": "user",
            "content": content
        })

    def add_assistant_message(self, content: str):
        """어시스턴트 응답을 히스토리에 추가합니다."""
        self.messages.append({
            "role": "assistant",
            "content": content
        })

    def get_messages(self) -> List[Dict[str, str]]:
        """대화 히스토리를 반환합니다."""
        return self.messages.copy()

    def clear_history(self):
        """대화 히스토리를 초기화합니다."""
        self.messages = []

    def get_last_assistant_message(self) -> str:
        """마지막 어시스턴트 응답을 반환합니다."""
        for msg in reversed(self.messages):
            if msg["role"] == "assistant":
                return msg["content"]
        return ""

    def add_error_feedback(self, error_message: str):
        """에러 피드백을 대화에 추가합니다."""
        feedback = f"""이전 코드 실행 중 다음 에러가 발생했습니다:

{error_message}

에러를 수정한 새로운 코드를 작성해주세요."""
        self.add_user_message(feedback)

    def get_conversation_summary(self) -> str:
        """대화 요약을 반환합니다."""
        if not self.messages:
            return "대화 내역 없음"

        summary_parts = []
        for i, msg in enumerate(self.messages, 1):
            role = "사용자" if msg["role"] == "user" else "AI"
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            summary_parts.append(f"{i}. [{role}] {content}")

        return "\n".join(summary_parts)
