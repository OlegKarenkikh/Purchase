#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модели данных для АИС УДЗ
"""

from .document import Document, DocumentRequirement, DocumentCategory
from .analysis import Analysis, AnalysisResult
from .company import Company

__all__ = [
    "Document",
    "Company",
    "ParseResult",
    "AnalysisResult"
]
