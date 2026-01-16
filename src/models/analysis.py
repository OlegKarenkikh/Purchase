#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модели анализа закупочной документации.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .document import DocumentRequirement


class ProcurementInfo(BaseModel):
    number: Optional[str] = None
    legal_basis: Optional[str] = None
    procedure_type: Optional[str] = None
    customer: Optional[str] = None


class DocumentVerification(BaseModel):
    provided: List[str] = Field(default_factory=list)
    missing_critical: List[str] = Field(default_factory=list)
    missing_optional: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    completeness_score: int = 0


class AnalysisResult(BaseModel):
    procurement_info: ProcurementInfo = Field(default_factory=ProcurementInfo)
    required_documents: List[DocumentRequirement] = Field(default_factory=list)
    document_verification: Optional[DocumentVerification] = None
    critical_warnings: List[str] = Field(default_factory=list)
    analysis_time: Optional[float] = None


class Analysis(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    result: AnalysisResult
