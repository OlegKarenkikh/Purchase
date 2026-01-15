#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль реестра документов

Реализует требования FR-2 из ТЗ:
- Централизованное хранилище документов
- Реестр реквизитов
- Отслеживание сроков действия
- Поиск и фильтрация
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentRegistry:
    """
    Реестр документов компании
    
    Требования: FR-2.1 - FR-2.7
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or "./storage/documents")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.documents: List[Dict] = []
        self.requisites: Dict = {}
        
    def add_document(self, document: Dict) -> str:
        """FR-2.2: Добавление документа"""
        doc_id = f"doc_{len(self.documents) + 1:04d}"
        document["id"] = doc_id
        document["added_at"] = datetime.now().isoformat()
        document["status"] = self._calculate_status(document)
        
        self.documents.append(document)
        logger.info(f"Документ {doc_id} добавлен")
        return doc_id
    
    def _calculate_status(self, document: Dict) -> str:
        """FR-2.3: Расчет статуса документа"""
        if "expiry_date" not in document or not document["expiry_date"]:
            return "valid"
        
        try:
            expiry = datetime.fromisoformat(document["expiry_date"])
            now = datetime.now()
            days_left = (expiry - now).days
            
            if days_left < 0:
                return "expired"
            elif days_left <= 7:
                return "expiring_soon_7d"
            elif days_left <= 30:
                return "expiring_soon_30d"
            else:
                return "valid"
        except (ValueError, TypeError):
            return "unknown"
    
    def get_expiring_documents(self, days: int = 30) -> List[Dict]:
        """FR-2.3: Получение истекающих документов"""
        expiring = []
        threshold = datetime.now() + timedelta(days=days)
        
        for doc in self.documents:
            if "expiry_date" in doc and doc["expiry_date"]:
                try:
                    expiry = datetime.fromisoformat(doc["expiry_date"])
                    if datetime.now() < expiry <= threshold:
                        expiring.append(doc)
                except (ValueError, TypeError):
                    continue
        
        return expiring
    
    def search_documents(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict]:
        """FR-2.6, FR-2.7: Поиск и фильтрация"""
        results = self.documents.copy()
        
        if query:
            query_lower = query.lower()
            results = [
                doc for doc in results
                if query_lower in doc.get("name", "").lower()
            ]
        
        if category:
            results = [doc for doc in results if doc.get("category") == category]
        
        if status:
            results = [
                doc for doc in results
                if self._calculate_status(doc) == status
            ]
        
        if tags:
            results = [
                doc for doc in results
                if any(tag in doc.get("tags", []) for tag in tags)
            ]
        
        return results
    
    def set_requisites(self, requisites: Dict) -> None:
        """FR-2.4, FR-2.5: Управление реквизитами"""
        requisites["version"] = requisites.get("version", 1)
        requisites["effective_from"] = datetime.now().isoformat()
        
        if "history" not in self.requisites:
            self.requisites["history"] = []
        
        if "current" in self.requisites:
            old = self.requisites["current"].copy()
            old["effective_to"] = datetime.now().isoformat()
            self.requisites["history"].append(old)
        
        self.requisites["current"] = requisites
        logger.info(f"Реквизиты обновлены (v{requisites['version']})")
    
    def get_current_requisites(self) -> Dict:
        return self.requisites.get("current", {})
