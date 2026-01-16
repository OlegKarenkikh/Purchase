# -*- coding: utf-8 -*-
"""
АИС УДЗ - Автоматизированная система управления документами закупочной деятельности

Версия 2.0.0 включает:
- FR-1: Анализ закупочной документации с LLM
- FR-2: Реестр документов компании
- FR-3: Формирование пакетов документов
- FR-4: Многоэтапный контроль с чек-листами
- FR-5: Отчетность и аналитика
- Веб-интерфейс

Новые модули Фазы 2:
- FR-1.10: Каталог типовых документов (template_library)
- FR-3.10: Выделение форм из КД (forms_extractor)
- FR-3.11-12: Формирование описи и пакетов (package_manifest)
- FR-4.9: Отчет о готовности (readiness_report)
"""

__version__ = "2.0.0"
__author__ = "Oleg Karenkikh"

from .analyzer import DocumentAnalyzer
from .document_registry import DocumentRegistry
from .package_builder import PackageBuilder
from .control import MultiStageController, ControlHistory, ChecklistItem
from .reports import ReportGenerator
from .template_library import TemplateLibrary
from .forms_extractor import FormsExtractor
from .package_manifest import PackageManifest
from .readiness_report import ReadinessReport

__all__ = [
    # Базовые модули (Фаза 1)
    "DocumentAnalyzer",
    "DocumentRegistry",
    "PackageBuilder",
    "MultiStageController",
    "ReportGenerator",
    # Новые модули (Фаза 2)
    "TemplateLibrary",
    "FormsExtractor",
    "PackageManifest",
    "ReadinessReport",
    "ControlHistory",
    "ChecklistItem",
]
