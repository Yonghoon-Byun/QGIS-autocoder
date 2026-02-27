# -*- coding: utf-8 -*-
"""
Context Builder
현재 QGIS 프로젝트의 컨텍스트 정보를 수집
"""

from typing import Dict, List, Any, Optional


class ContextBuilder:
    """QGIS 프로젝트 컨텍스트 빌더"""

    def __init__(self, iface):
        """
        Args:
            iface: QgisInterface 인스턴스
        """
        self.iface = iface

    def build_context(self) -> str:
        """현재 QGIS 프로젝트의 컨텍스트를 문자열로 반환합니다."""
        try:
            from qgis.core import QgsProject, QgsWkbTypes, QgsMapLayerType

            from qgis.core import Qgis

            project = QgsProject.instance()
            context_parts = []

            # QGIS 버전
            context_parts.append(f"QGIS 버전: {Qgis.QGIS_VERSION}")

            # 프로젝트 정보
            project_name = project.baseName() or "새 프로젝트"
            project_path = project.fileName() or "저장되지 않음"
            context_parts.append(f"프로젝트: {project_name}")
            context_parts.append(f"경로: {project_path}")

            # CRS 정보
            crs = project.crs()
            if crs.isValid():
                context_parts.append(f"프로젝트 CRS: {crs.authid()} ({crs.description()})")

            # 레이어 정보
            layers = project.mapLayers().values()
            if layers:
                context_parts.append(f"\n레이어 목록 ({len(list(layers))}개):")
                for layer in project.mapLayers().values():
                    layer_info = self._get_layer_info(layer)
                    context_parts.append(f"  - {layer_info}")
            else:
                context_parts.append("\n레이어: 없음")

            # 현재 맵 범위
            canvas = self.iface.mapCanvas()
            if canvas:
                extent = canvas.extent()
                context_parts.append(
                    f"\n현재 맵 범위: "
                    f"({extent.xMinimum():.2f}, {extent.yMinimum():.2f}) - "
                    f"({extent.xMaximum():.2f}, {extent.yMaximum():.2f})"
                )

            # 활성 레이어
            active_layer = self.iface.activeLayer()
            if active_layer:
                context_parts.append(f"활성 레이어: {active_layer.name()}")

            return "\n".join(context_parts)

        except Exception as e:
            return f"컨텍스트 수집 오류: {str(e)}"

    def _get_layer_info(self, layer) -> str:
        """레이어 정보를 문자열로 반환합니다 (필드 스키마 포함)."""
        try:
            from qgis.core import QgsMapLayerType, QgsWkbTypes, QgsVectorLayer

            name = layer.name()
            layer_type = self._get_layer_type_str(layer)

            info_parts = [f"{name} ({layer_type})"]

            # 벡터 레이어 추가 정보
            if isinstance(layer, QgsVectorLayer):
                geom_type = QgsWkbTypes.displayString(layer.wkbType())
                feature_count = layer.featureCount()
                selected_count = layer.selectedFeatureCount()
                info_parts.append(f"[{geom_type}, {feature_count}개 피처")
                if selected_count > 0:
                    info_parts.append(f", {selected_count}개 선택됨")
                info_parts.append("]")

            # CRS
            crs = layer.crs()
            if crs.isValid():
                info_parts.append(f"CRS: {crs.authid()}")

            base_info = " ".join(info_parts)

            # 필드 스키마 (벡터 레이어만)
            if isinstance(layer, QgsVectorLayer):
                field_info = self._get_field_schema(layer)
                if field_info:
                    return f"{base_info}\n    필드: {field_info}"

            return base_info

        except Exception:
            return layer.name()

    def _get_field_schema(self, layer) -> str:
        """벡터 레이어의 필드 스키마를 문자열로 반환합니다."""
        try:
            from PyQt5.QtCore import QVariant

            type_map = {
                QVariant.Int: "Int",
                QVariant.LongLong: "LongInt",
                QVariant.Double: "Float",
                QVariant.String: "String",
                QVariant.Date: "Date",
                QVariant.DateTime: "DateTime",
                QVariant.Bool: "Bool",
            }

            fields = layer.fields()
            field_parts = []
            for field in fields:
                type_name = type_map.get(field.type(), "Unknown")
                field_parts.append(f"{field.name()}({type_name})")

            return ", ".join(field_parts) if field_parts else ""
        except Exception:
            return ""

    def _get_layer_type_str(self, layer) -> str:
        """레이어 타입을 문자열로 반환합니다."""
        try:
            from qgis.core import QgsMapLayerType

            type_map = {
                QgsMapLayerType.VectorLayer: "벡터",
                QgsMapLayerType.RasterLayer: "래스터",
                QgsMapLayerType.PluginLayer: "플러그인",
                QgsMapLayerType.MeshLayer: "메시",
                QgsMapLayerType.VectorTileLayer: "벡터타일",
                QgsMapLayerType.AnnotationLayer: "주석",
                QgsMapLayerType.PointCloudLayer: "포인트클라우드",
                QgsMapLayerType.GroupLayer: "그룹"
            }
            return type_map.get(layer.type(), "기타")
        except Exception:
            return "알 수 없음"

    def get_layer_names(self) -> List[str]:
        """현재 프로젝트의 모든 레이어 이름 목록을 반환합니다."""
        try:
            from qgis.core import QgsProject
            project = QgsProject.instance()
            return [layer.name() for layer in project.mapLayers().values()]
        except Exception:
            return []

    def get_layer_by_name(self, name: str):
        """이름으로 레이어를 찾아 반환합니다."""
        try:
            from qgis.core import QgsProject
            project = QgsProject.instance()
            layers = project.mapLayersByName(name)
            return layers[0] if layers else None
        except Exception:
            return None

    def get_processing_algorithms(self) -> List[Dict[str, str]]:
        """사용 가능한 Processing 알고리즘 목록을 반환합니다."""
        try:
            from qgis.core import QgsApplication
            from processing.core.Processing import Processing

            algorithms = []
            for alg in QgsApplication.processingRegistry().algorithms():
                algorithms.append({
                    "id": alg.id(),
                    "name": alg.displayName(),
                    "group": alg.group()
                })
            return algorithms
        except Exception:
            return []
