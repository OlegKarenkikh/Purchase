# -*- coding: utf-8 -*-
"""
АИС УДЗ - Автоматизированная система управления документами закупочной деятельности
"""

__version__ = "1.0.0"
__author__ = "Oleg Karenkikh"

from .analyzer import DocumentAnalyzer
from .document_registry import DocumentRegistry
from .package_builder import PackageBuilder
from .control import MultiStageController
from .reports import ReportGenerator

__all__ = [
    "DocumentAnalyzer",
    "DocumentRegistry",
    "PackageBuilder",
    "MultiStageController",
    "ReportGenerator",
]
