#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль дедупликации документов
"""

import re
from typing import List, Dict, Any
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class DocumentDeduplicator:
    """
    Дедупликатор для удаления повторяющихся документов
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Args:
            similarity_threshold: Порог схожести (0-1)
        """
        self.similarity_threshold = similarity_threshold
    
    def deduplicate(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Удаление дубликатов из списка документов
        
        Args:
            documents: Список документов
            
        Returns:
            Уникальные документы
        """
        if not documents:
            return []
        
        unique_docs = []
        seen_names = set()
        
        for doc in documents:
            doc_name = doc.get("name", "")
            
            # Нормализация названия
            normalized_name = self._normalize_document_name(doc_name)
            
            # Проверка точного совпадения
            if normalized_name in seen_names:
                logger.debug(f"Удален точный дубликат: {doc_name}")
                continue
            
            # Проверка схожести с уже добавленными
            is_duplicate = False
            for existing_doc in unique_docs:
                existing_name = self._normalize_document_name(
                    existing_doc.get("name", "")
                )
                
                similarity = self._calculate_similarity(
                    normalized_name, existing_name
                )
                
                if similarity >= self.similarity_threshold:
                    logger.debug(
                        f"Удален похожий дубликат: {doc_name} "
                        f"(схожесть {similarity:.2%})"
                    )
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_docs.append(doc)
                seen_names.add(normalized_name)
        
        removed_count = len(documents) - len(unique_docs)
        if removed_count > 0:
            logger.info(f"Удалено дубликатов: {removed_count}")
        
        return unique_docs
    
    def _normalize_document_name(self, name: str) -> str:
        """
        Нормализация названия документа
        
        Args:
            name: Исходное название
            
        Returns:
            Нормализованное название
        """
        # Приведение к нижнему регистру
        name = name.lower().strip()
        
        # Удаление лишних пробелов
        name = re.sub(r'\s+', ' ', name)
        
        # Удаление спецсимволов
        name = re.sub(r'[^\w\sа-яё]', '', name)
        
        # Удаление стоп-слов
        stop_words = ['копия', 'оригинал', 'заверенная', 'нотариальная']
        words = name.split()
        words = [w for w in words if w not in stop_words]
        
        return ' '.join(words)
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Расчет схожести двух строк
        
        Args:
            str1: Первая строка
            str2: Вторая строка
            
        Returns:
            Коэффициент схожести (0-1)
        """
        return SequenceMatcher(None, str1, str2).ratio()
