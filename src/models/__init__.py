#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модели данных для АИС УДЗ
"""

from .analysis import Analysis, AnalysisResult
from .company import Company
from .document import Document, DocumentCategory, DocumentRequirement

__all__ = [
    "Analysis",
    "AnalysisResult",
    "Company",
    "Document",
    "DocumentCategory",
    "DocumentRequirement",
]
