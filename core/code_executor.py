# -*- coding: utf-8 -*-
"""
Code Executor
LLM이 생성한 PyQGIS 코드를 안전하게 실행
"""

import sys
import re
import traceback
from io import StringIO
from typing import Tuple, Optional


class CodeExecutor:
    """PyQGIS 코드 실행 엔진"""

    def __init__(self, iface):
        """
        Args:
            iface: QgisInterface 인스턴스
        """
        self.iface = iface

    def extract_code(self, llm_response: str) -> str:
        """LLM 응답에서 Python 코드를 추출합니다.

        마크다운 코드 블록이 있으면 제거하고 순수 코드만 반환합니다.
        """
        # 마크다운 코드 블록 제거 (```python ... ``` 또는 ``` ... ```)
        code = llm_response.strip()

        # ```python 또는 ```py로 시작하는 코드 블록
        pattern = r'```(?:python|py)?\s*\n?(.*?)```'
        matches = re.findall(pattern, code, re.DOTALL)
        if matches:
            # 모든 코드 블록을 합침
            code = '\n\n'.join(matches)
        else:
            # 코드 블록이 없으면 그대로 사용 (단, ``` 제거)
            code = code.replace('```python', '').replace('```py', '').replace('```', '')

        return code.strip()

    def validate_code(self, code: str) -> Tuple[bool, str]:
        """코드의 문법적 유효성을 검증합니다.

        Returns:
            tuple: (유효 여부, 에러 메시지)
        """
        try:
            compile(code, '<string>', 'exec')
            return True, ""
        except SyntaxError as e:
            return False, f"문법 오류 (라인 {e.lineno}): {e.msg}"
        except Exception as e:
            return False, f"검증 오류: {str(e)}"

    def execute(self, code: str) -> Tuple[bool, str, str]:
        """코드를 실행하고 결과를 반환합니다.

        Args:
            code: 실행할 Python 코드

        Returns:
            tuple: (성공 여부, stdout 출력, stderr/에러 메시지)
        """
        # 코드 검증
        valid, error_msg = self.validate_code(code)
        if not valid:
            return False, "", error_msg

        # stdout/stderr 캡처 준비
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stdout_capture = StringIO()
        sys.stderr = stderr_capture = StringIO()

        success = False
        error_output = ""

        try:
            # 실행 환경 구성
            exec_globals = self._build_exec_globals()
            exec_locals = {}

            # 코드 실행
            exec(code, exec_globals, exec_locals)
            success = True

        except Exception as e:
            # 에러 정보 수집
            error_output = self._format_exception(e)

        finally:
            # stdout/stderr 복원
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()

        if stderr_output and not error_output:
            error_output = stderr_output

        return success, stdout_output, error_output

    def _build_exec_globals(self) -> dict:
        """코드 실행을 위한 전역 네임스페이스를 구성합니다."""
        exec_globals = {
            '__builtins__': __builtins__,
            'iface': self.iface,
        }

        # QGIS 핵심 모듈 import
        try:
            from qgis.core import (
                QgsProject, QgsVectorLayer, QgsRasterLayer,
                QgsFeature, QgsGeometry, QgsField, QgsFields,
                QgsPointXY, QgsRectangle, QgsCoordinateReferenceSystem,
                QgsCoordinateTransform, QgsExpression, QgsExpressionContext,
                QgsVectorFileWriter, QgsRasterFileWriter,
                QgsProcessingFeedback, QgsApplication,
                QgsWkbTypes, QgsMapLayerType, QgsPalLayerSettings,
                QgsTextFormat, QgsVectorLayerSimpleLabeling,
                QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol,
                QgsSingleSymbolRenderer, QgsCategorizedSymbolRenderer,
                QgsGraduatedSymbolRenderer, QgsRuleBasedRenderer,
                QgsLayerTreeLayer, QgsLayerTreeGroup,
                QgsPrintLayout, QgsLayoutItemMap, QgsLayoutExporter,
                QgsMessageLog, Qgis
            )
            exec_globals.update({
                'QgsProject': QgsProject,
                'QgsVectorLayer': QgsVectorLayer,
                'QgsRasterLayer': QgsRasterLayer,
                'QgsFeature': QgsFeature,
                'QgsGeometry': QgsGeometry,
                'QgsField': QgsField,
                'QgsFields': QgsFields,
                'QgsPointXY': QgsPointXY,
                'QgsRectangle': QgsRectangle,
                'QgsCoordinateReferenceSystem': QgsCoordinateReferenceSystem,
                'QgsCoordinateTransform': QgsCoordinateTransform,
                'QgsExpression': QgsExpression,
                'QgsExpressionContext': QgsExpressionContext,
                'QgsVectorFileWriter': QgsVectorFileWriter,
                'QgsRasterFileWriter': QgsRasterFileWriter,
                'QgsProcessingFeedback': QgsProcessingFeedback,
                'QgsApplication': QgsApplication,
                'QgsWkbTypes': QgsWkbTypes,
                'QgsMapLayerType': QgsMapLayerType,
                'QgsPalLayerSettings': QgsPalLayerSettings,
                'QgsTextFormat': QgsTextFormat,
                'QgsVectorLayerSimpleLabeling': QgsVectorLayerSimpleLabeling,
                'QgsFillSymbol': QgsFillSymbol,
                'QgsLineSymbol': QgsLineSymbol,
                'QgsMarkerSymbol': QgsMarkerSymbol,
                'QgsSingleSymbolRenderer': QgsSingleSymbolRenderer,
                'QgsCategorizedSymbolRenderer': QgsCategorizedSymbolRenderer,
                'QgsGraduatedSymbolRenderer': QgsGraduatedSymbolRenderer,
                'QgsRuleBasedRenderer': QgsRuleBasedRenderer,
                'QgsLayerTreeLayer': QgsLayerTreeLayer,
                'QgsLayerTreeGroup': QgsLayerTreeGroup,
                'QgsPrintLayout': QgsPrintLayout,
                'QgsLayoutItemMap': QgsLayoutItemMap,
                'QgsLayoutExporter': QgsLayoutExporter,
                'QgsMessageLog': QgsMessageLog,
                'Qgis': Qgis
            })
        except ImportError:
            pass

        # qgis.utils
        try:
            from qgis import utils as qgis_utils
            exec_globals['qgis_utils'] = qgis_utils
        except ImportError:
            pass

        # Processing
        try:
            import processing
            exec_globals['processing'] = processing
        except ImportError:
            pass

        # PyQt
        try:
            from PyQt5.QtCore import QVariant
            from PyQt5.QtGui import QColor, QFont
            from PyQt5.QtWidgets import QMessageBox
            exec_globals.update({
                'QVariant': QVariant,
                'QColor': QColor,
                'QFont': QFont,
                'QMessageBox': QMessageBox
            })
        except ImportError:
            pass

        return exec_globals

    def _format_exception(self, e: Exception) -> str:
        """예외를 읽기 쉬운 형식으로 포맷팅합니다."""
        tb_lines = traceback.format_exception(type(e), e, e.__traceback__)

        # exec 관련 내부 라인 필터링
        filtered_lines = []
        skip_next = False
        for line in tb_lines:
            if 'exec(code' in line or 'code_executor.py' in line:
                skip_next = True
                continue
            if skip_next and line.startswith('  '):
                continue
            skip_next = False
            filtered_lines.append(line)

        return ''.join(filtered_lines).strip()

    def get_code_preview(self, code: str, max_lines: int = 20) -> str:
        """코드의 미리보기를 반환합니다."""
        lines = code.split('\n')
        if len(lines) <= max_lines:
            return code

        preview_lines = lines[:max_lines]
        remaining = len(lines) - max_lines
        preview_lines.append(f"\n... ({remaining}줄 더 있음)")
        return '\n'.join(preview_lines)
