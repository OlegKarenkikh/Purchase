#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модель реквизитов компании (FR-2.4, FR-2.5).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CompanyRequisites(BaseModel):
    full_name: str
    short_name: Optional[str] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    ogrn: Optional[str] = None
    legal_address: Optional[str] = None
    actual_address: Optional[str] = None
    bank_details: Optional[str] = None
    contacts: Optional[str] = None
    director: Optional[str] = None


class Company(BaseModel):
    id: str
    requisites: CompanyRequisites
    version: int = 1
    effective_from: date = Field(default_factory=date.today)
    effective_to: Optional[date] = None
    history: List[CompanyRequisites] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
