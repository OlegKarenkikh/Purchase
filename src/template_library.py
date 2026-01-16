#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль работы с каталогом типовых документов

Реализует требования FR-1.10 из расширенного ТЗ:
- Сканирование каталога типовых документов
- Индексация типовых документов
- Маппинг документов на требования
- Копирование типовых документов
"""

import os
import hashlib
import shutil
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
import re

logger = logging.getLogger(__name__)


class TemplateLibrary:
    """
    Работа с каталогом типовых документов (FR-1.10)

    Обеспечивает:
    - Сканирование и индексацию каталога типовых документов
    - Поиск подходящих типовых документов для требований
    - Копирование типовых документов в структуру заявки
    """

    # Ключевые слова для определения типов документов
    DOCUMENT_KEYWORDS = {
        "form": ["форма", "анкета", "заявка", "приложение"],
        "certificate": ["сертификат", "свидетельство", "аттестат"],
        "license": ["лицензия", "разрешение", "допуск"],
        "extract": ["выписка", "справка", "егрюл", "егрип"],
        "charter": ["устав", "учредительный"],
        "contract": ["договор", "контракт", "соглашение"],
        "declaration": ["декларация", "гарантийное письмо"],
        "financial": ["баланс", "отчетность", "бухгалтерский"],
        "sro": ["сро", "саморегулируемая"],
    }

    # Поддерживаемые расширения файлов
    SUPPORTED_EXTENSIONS = {
        ".pdf", ".docx", ".doc", ".rtf", ".txt",
        ".xlsx", ".xls", ".odt", ".png", ".jpg", ".jpeg"
    }

    def __init__(self, catalog_path: str):
        """
        Инициализация библиотеки типовых документов

        Args:
            catalog_path: Путь к каталогу типовых документов
        """
        self.catalog_path = Path(catalog_path)
        self.index: Dict[str, Dict] = {}  # Поисковый индекс
        self._indexed_at: Optional[str] = None

        if not self.catalog_path.exists():
            logger.warning(f"Каталог типовых документов не найден: {catalog_path}")
            self.catalog_path.mkdir(parents=True, exist_ok=True)

    def scan_catalog(self) -> List[Dict]:
        """
        Рекурсивное сканирование каталога типовых документов

        Returns:
            Список метаданных документов
        """
        documents = []

        logger.info(f"Сканирование каталога: {self.catalog_path}")

        for file_path in self.catalog_path.rglob("*"):
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue

            try:
                doc_metadata = self._extract_document_metadata(file_path)
                documents.append(doc_metadata)
            except Exception as e:
                logger.warning(f"Ошибка обработки файла {file_path}: {e}")

        logger.info(f"Найдено документов: {len(documents)}")
        return documents

    def _extract_document_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Извлечение метаданных документа

        Args:
            file_path: Путь к файлу

        Returns:
            Словарь с метаданными
        """
        stat = file_path.stat()

        # Вычисление хеша файла
        file_hash = self._calculate_file_hash(file_path)

        # Определение типа документа по имени файла
        document_type = self._detect_document_type(file_path.name)

        # Извлечение ключевых слов из имени файла
        keywords = self._extract_keywords(file_path.name)

        return {
            "template_id": f"TPL-{file_hash[:8].upper()}",
            "file_name": file_path.name,
            "file_path": str(file_path.absolute()),
            "relative_path": str(file_path.relative_to(self.catalog_path)),
            "file_hash": f"sha256:{file_hash}",
            "file_size": stat.st_size,
            "extension": file_path.suffix.lower(),
            "document_type": document_type,
            "keywords": keywords,
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "indexed_at": datetime.now().isoformat(),
        }

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Вычисление SHA-256 хеша файла"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _detect_document_type(self, filename: str) -> str:
        """Определение типа документа по имени файла"""
        filename_lower = filename.lower()

        for doc_type, keywords in self.DOCUMENT_KEYWORDS.items():
            if any(kw in filename_lower for kw in keywords):
                return doc_type

        return "other"

    def _extract_keywords(self, filename: str) -> List[str]:
        """Извлечение ключевых слов из имени файла"""
        # Убираем расширение и разбиваем на слова
        name_without_ext = Path(filename).stem
        # Разбиваем по пробелам, подчеркиваниям, дефисам
        words = re.split(r'[\s_\-\.]+', name_without_ext.lower())
        # Фильтруем короткие слова
        return [w for w in words if len(w) > 2]

    def index_documents(self, documents: Optional[List[Dict]] = None) -> None:
        """
        Создание поискового индекса

        Args:
            documents: Список документов для индексации (если None, выполняется сканирование)
        """
        if documents is None:
            documents = self.scan_catalog()

        self.index = {}

        for doc in documents:
            template_id = doc["template_id"]
            self.index[template_id] = doc

            # Индексация по ключевым словам
            for keyword in doc.get("keywords", []):
                key = f"kw:{keyword}"
                if key not in self.index:
                    self.index[key] = []
                if isinstance(self.index[key], list):
                    self.index[key].append(template_id)

            # Индексация по типу документа
            doc_type = doc.get("document_type", "other")
            type_key = f"type:{doc_type}"
            if type_key not in self.index:
                self.index[type_key] = []
            if isinstance(self.index[type_key], list):
                self.index[type_key].append(template_id)

        self._indexed_at = datetime.now().isoformat()
        logger.info(f"Проиндексировано документов: {len(documents)}")

    def search_template(
        self,
        document_name: str,
        document_type: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> List[Dict]:
        """
        Поиск типового документа

        Args:
            document_name: Название искомого документа
            document_type: Тип документа (опционально)
            min_confidence: Минимальный порог уверенности (0-1)

        Returns:
            Список найденных документов с confidence score
        """
        if not self.index:
            self.index_documents()

        results = []
        name_lower = document_name.lower()
        name_keywords = self._extract_keywords(document_name)

        # Получаем все документы из индекса
        all_templates = [
            doc for key, doc in self.index.items()
            if isinstance(doc, dict) and "template_id" in doc
        ]

        for template in all_templates:
            confidence = 0.0

            # Сравнение по имени файла
            template_name = template.get("file_name", "").lower()
            name_similarity = SequenceMatcher(None, name_lower, template_name).ratio()
            confidence = max(confidence, name_similarity * 0.8)

            # Сравнение по ключевым словам
            template_keywords = set(template.get("keywords", []))
            if name_keywords and template_keywords:
                keyword_match = len(set(name_keywords) & template_keywords)
                keyword_score = keyword_match / max(len(name_keywords), 1)
                confidence = max(confidence, keyword_score * 0.7)

            # Бонус за совпадение типа документа
            if document_type and template.get("document_type") == document_type:
                confidence += 0.2

            # Ограничиваем confidence до 1.0
            confidence = min(confidence, 1.0)

            if confidence >= min_confidence:
                results.append({
                    **template,
                    "confidence": round(confidence, 2)
                })

        # Сортировка по confidence
        results.sort(key=lambda x: x["confidence"], reverse=True)

        return results[:10]  # Возвращаем топ-10

    def copy_template(
        self,
        template_id: str,
        target_path: str,
        new_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Копирование типового документа в целевую директорию

        Args:
            template_id: ID типового документа
            target_path: Целевая директория
            new_filename: Новое имя файла (опционально)

        Returns:
            Информация о скопированном файле
        """
        template = self.index.get(template_id)

        if not template or not isinstance(template, dict):
            raise ValueError(f"Типовой документ не найден: {template_id}")

        source_path = Path(template["file_path"])

        if not source_path.exists():
            raise FileNotFoundError(f"Файл не найден: {source_path}")

        target_dir = Path(target_path)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Определяем имя целевого файла
        target_filename = new_filename or source_path.name
        target_file = target_dir / target_filename

        # Копируем файл
        shutil.copy2(source_path, target_file)

        logger.info(f"Типовой документ скопирован: {source_path} -> {target_file}")

        return {
            "template_id": template_id,
            "source_path": str(source_path),
            "target_path": str(target_file),
            "file_hash": template["file_hash"],
            "copied_at": datetime.now().isoformat(),
        }

    def get_all_templates(self) -> List[Dict]:
        """Получение списка всех типовых документов"""
        if not self.index:
            self.index_documents()

        return [
            doc for key, doc in self.index.items()
            if isinstance(doc, dict) and "template_id" in doc
        ]

    def get_template_by_id(self, template_id: str) -> Optional[Dict]:
        """Получение типового документа по ID"""
        return self.index.get(template_id)

    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики каталога"""
        templates = self.get_all_templates()

        by_type = {}
        by_extension = {}
        total_size = 0

        for template in templates:
            doc_type = template.get("document_type", "other")
            by_type[doc_type] = by_type.get(doc_type, 0) + 1

            ext = template.get("extension", "unknown")
            by_extension[ext] = by_extension.get(ext, 0) + 1

            total_size += template.get("file_size", 0)

        return {
            "total_templates": len(templates),
            "by_type": by_type,
            "by_extension": by_extension,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "indexed_at": self._indexed_at,
            "catalog_path": str(self.catalog_path),
        }
