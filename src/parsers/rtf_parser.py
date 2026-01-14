#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер RTF документов
"""

import time
from pathlib import Path
from typing import Optional
import logging

from striprtf.striprtf import rtf_to_text

from .base_parser import BaseParser, ParseResult

logger = logging.getLogger(__name__)


class RTFParser(BaseParser):
    """
    Парсер RTF документов
    
    Поддерживает:
    - Извлечение текста из RTF
    - Базовые метаданные
    """
    
    SUPPORTED_EXTENSIONS = [".rtf"]
    
    def supports(self, file_path: Path) -> bool:
        """Проверка поддержки формата"""
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
    
    def parse(self, file_path: Path) -> ParseResult:
        """
        Парсинг RTF документа
        
        Args:
            file_path: Путь к RTF файлу
            
        Returns:
            Результат парсинга
        """
        start_time = time.time()
        result = ParseResult()
        
        try:
            self.validate_file(file_path)
            
            # Базовые метаданные
            result.metadata = self.extract_metadata(file_path)
            
            # Чтение RTF файла
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                rtf_content = file.read()
            
            # Конвертация RTF в текст
            text = rtf_to_text(rtf_content)
            result.text = text
            
            # Проверка результата
            if len(result.text.strip()) == 0:
                result.errors.append("Документ не содержит текста")
        
        except Exception as e:
            self.logger.error(f"Ошибка парсинга RTF: {e}")
            result.errors.append(str(e))
        
        result.parse_time = time.time() - start_time
        return result
