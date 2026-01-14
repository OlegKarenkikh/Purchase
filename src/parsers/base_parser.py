#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовый класс для всех парсеров документов
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """
    Результат парсинга документа
    
    Attributes:
        text: Извлеченный текст
        metadata: Метаданные документа
        tables: Извлеченные таблицы
        images: Информация об изображениях
        errors: Список ошибок при парсинге
        warnings: Предупреждения
        parse_time: Время парсинга в секундах
    """
    text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    tables: List[List[List[str]]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    parse_time: float = 0.0
    
    @property
    def is_success(self) -> bool:
        """Проверка успешности парсинга"""
        return len(self.errors) == 0 and len(self.text) > 0
    
    @property
    def word_count(self) -> int:
        """Количество слов в тексте"""
        return len(self.text.split())
    
    @property
    def char_count(self) -> int:
        """Количество символов"""
        return len(self.text)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            "text": self.text,
            "metadata": self.metadata,
            "tables_count": len(self.tables),
            "images_count": len(self.images),
            "errors": self.errors,
            "warnings": self.warnings,
            "parse_time": self.parse_time,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "is_success": self.is_success
        }


class BaseParser(ABC):
    """
    Базовый абстрактный класс для всех парсеров
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация парсера
        
        Args:
            config: Конфигурация парсера
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def parse(self, file_path: Path) -> ParseResult:
        """
        Парсинг документа
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Результат парсинга
        """
        pass
    
    @abstractmethod
    def supports(self, file_path: Path) -> bool:
        """
        Проверка поддержки формата файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            True если формат поддерживается
        """
        pass
    
    def validate_file(self, file_path: Path) -> None:
        """
        Валидация файла перед парсингом
        
        Args:
            file_path: Путь к файлу
            
        Raises:
            FileNotFoundError: Если файл не найден
            ValueError: Если формат не поддерживается
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Путь не указывает на файл: {file_path}")
        
        if not self.supports(file_path):
            raise ValueError(f"Формат файла не поддерживается: {file_path.suffix}")
        
        # Проверка размера файла
        max_size = self.config.get("max_file_size_mb", 50) * 1024 * 1024
        if file_path.stat().st_size > max_size:
            raise ValueError(f"Файл слишком большой: {file_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Извлечение базовых метаданных файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Словарь с метаданными
        """
        stat = file_path.stat()
        return {
            "filename": file_path.name,
            "extension": file_path.suffix,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / 1024 / 1024, 2),
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "parser_class": self.__class__.__name__
        }
