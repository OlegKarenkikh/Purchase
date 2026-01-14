#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Фабрика для создания парсеров документов
"""

from pathlib import Path
from typing import Optional
import logging

from ..parsers import (
    BaseParser,
    PDFParser,
    DOCXParser,
    RTFParser,
    TextParser,
    ArchiveParser
)

logger = logging.getLogger(__name__)


class DocumentParserFactory:
    """
    Фабрика для автоматического выбора парсера
    """
    
    _parsers = [
        PDFParser,
        DOCXParser,
        RTFParser,
        TextParser,
        ArchiveParser
    ]
    
    @classmethod
    def create_parser(cls, file_path: Path, config: Optional[dict] = None) -> BaseParser:
        """
        Создание парсера для файла
        
        Args:
            file_path: Путь к файлу
            config: Конфигурация парсера
            
        Returns:
            Экземпляр парсера
            
        Raises:
            ValueError: Если парсер не найден
        """
        for parser_class in cls._parsers:
            parser = parser_class(config)
            if parser.supports(file_path):
                logger.info(f"Выбран парсер: {parser_class.__name__} для {file_path.suffix}")
                return parser
        
        raise ValueError(f"Не найден парсер для формата: {file_path.suffix}")
    
    @classmethod
    def get_supported_formats(cls) -> list:
        """
        Получение списка поддерживаемых форматов
        
        Returns:
            Список расширений файлов
        """
        formats = set()
        for parser_class in cls._parsers:
            parser = parser_class()
            if hasattr(parser, 'SUPPORTED_EXTENSIONS'):
                formats.update(parser.SUPPORTED_EXTENSIONS)
        return sorted(formats)
