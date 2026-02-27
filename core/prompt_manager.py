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

## 핵심 규칙
1. `iface`와 `QgsProject.instance()`는 이미 전역으로 사용 가능합니다.
2. 마크다운 코드 블록(```python```) 없이 순수 Python 코드만 출력하세요.
3. 필요한 모든 import문을 코드 시작 부분에 포함하세요.
4. 결과를 print()로 출력하여 사용자가 확인할 수 있게 하세요.
5. 에러 처리를 포함하여 안정적인 코드를 작성하세요.
6. 한국어 주석으로 코드를 설명하세요.

## 사용 가능한 변수 및 모듈
- `iface`: QgisInterface - QGIS 인터페이스 (활성 레이어, 뷰 조작 등)
- `QgsProject.instance()`: 현재 QGIS 프로젝트
- qgis.core: QgsProject, QgsVectorLayer, QgsRasterLayer, QgsFeature,
  QgsGeometry, QgsField, QgsFields, QgsPointXY, QgsCoordinateReferenceSystem,
  QgsCoordinateTransform, QgsWkbTypes, QgsSymbol, QgsRendererRange,
  QgsGraduatedSymbolRenderer, QgsCategorizedSymbolRenderer,
  QgsVectorFileWriter, QgsLayerTreeGroup, QgsApplication
- processing: Processing Toolbox 알고리즘 실행

## 레이어 접근 패턴
```python
# 이름으로 레이어 가져오기
layer = QgsProject.instance().mapLayersByName("레이어명")[0]

# 활성 레이어 가져오기
layer = iface.activeLayer()

# 모든 레이어 순회
for layer in QgsProject.instance().mapLayers().values():
    print(layer.name(), layer.type())
```

## 필드 및 피처 접근 패턴
```python
# 필드 스키마 확인 (컨텍스트에서 필드명/타입 참고 후 사용)
for field in layer.fields():
    print(field.name(), field.typeName())

# 피처 순회 및 필드 값 접근
for feature in layer.getFeatures():
    value = feature['field_name']  # 컨텍스트의 필드명 사용
    geom = feature.geometry()
    print(value, geom.asWkt())

# 선택된 피처만 처리
for feature in layer.selectedFeatures():
    print(feature['id'])
```

## Processing 알고리즘 사용
```python
import processing

# 버퍼 생성 예시
result = processing.run("native:buffer", {
    'INPUT': layer,
    'DISTANCE': 100,
    'SEGMENTS': 5,
    'OUTPUT': 'memory:'
})
buffer_layer = result['OUTPUT']
QgsProject.instance().addMapLayer(buffer_layer)

# 사용 가능한 알고리즘 목록 확인
for alg in QgsApplication.processingRegistry().algorithms():
    print(alg.id(), alg.displayName())
```

## 현재 QGIS 프로젝트 컨텍스트
{context}

## 출력 형식
순수 Python 코드만 출력하세요. 설명이나 마크다운 태그 없이 실행 가능한 코드만 작성하세요.
컨텍스트에 있는 필드명과 레이어명을 정확히 사용하세요."""

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
