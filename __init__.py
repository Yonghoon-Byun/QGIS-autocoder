# -*- coding: utf-8 -*-
"""
QGIS AI Auto-Coder Plugin
자연어로 PyQGIS 코드를 생성하고 실행하는 AI 어시스턴트
"""


def classFactory(iface):
    """QGIS Plugin 진입점

    Args:
        iface: QgisInterface 인스턴스

    Returns:
        QgisAiAutoCoder: 플러그인 인스턴스
    """
    from .plugin_main import QgisAiAutoCoder
    return QgisAiAutoCoder(iface)
