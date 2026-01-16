#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модели документов для АИС УДЗ.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentCategory(str, Enum):
    """Категории документов из ТЗ (FR-1.9)."""

    REGISTRATION = "Регистрационные"
    FINANCIAL = "Финансовые"
    PERMITS = "Специальные разрешительные"
    HR = "Кадровые"
    EXPERIENCE = "Опыт и квалификация"
    TECHNICAL = "Техническая документация"
    PRICE = "Ценовое предложение"
    SECURITY = "Обеспечительные"


class DocumentRequirement(BaseModel):
    """Требование к документу из результата анализа (FR-1.10)."""

    id: str
    name: str
    category: DocumentCategory
    mandatory: bool = True
    format: str = "Копия"
    validity_requirements: Optional[str] = None
    source_reference: Optional[str] = None
    implicit: bool = False


class Document(BaseModel):
    """Документ в реестре (FR-2.2)."""

    id: str
    name: str
    category: DocumentCategory
    file_path: Optional[str] = None
    issued_at: Optional[date] = None
    expiry_date: Optional[date] = None
    issuer: Optional[str] = None
    number: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
