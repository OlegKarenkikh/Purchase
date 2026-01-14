#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер текстовых файлов
"""

import time
from pathlib import Path
import logging
import chardet

from .base_parser import BaseParser, ParseResult

logger = logging.getLogger(__name__)


class TextParser(BaseParser):
    """
    Парсер текстовых файлов
    
    Поддерживает:
    - TXT файлы
    - Автоматическое определение кодировки
    """
    
    SUPPORTED_EXTENSIONS = [".txt", ".text", ".log"]
    
    def supports(self, file_path: Path) -> bool:
        """Проверка поддержки формата"""
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
    
    def parse(self, file_path: Path) -> ParseResult:
        """
        Парсинг текстового файла
        
        Args:
            file_path: Путь к текстовому файлу
            
        Returns:
            Результат парсинга
        """
        start_time = time.time()
        result = ParseResult()
        
        try:
            self.validate_file(file_path)
            
            # Базовые метаданные
            result.metadata = self.extract_metadata(file_path)
            
            # Определение кодировки
            encoding = self._detect_encoding(file_path)
            result.metadata["encoding"] = encoding
            
            # Чтение файла
            with open(file_path, 'r', encoding=encoding, errors='replace') as file:
                text = file.read()
            
            result.text = text
            
            # Проверка результата
            if len(result.text.strip()) == 0:
                result.warnings.append("Файл пустой или содержит только пробельные символы")
        
        except Exception as e:
            self.logger.error(f"Ошибка парсинга текстового файла: {e}")
            result.errors.append(str(e))
        
        result.parse_time = time.time() - start_time
        return result
    
    def _detect_encoding(self, file_path: Path) -> str:
        """
        Автоматическое определение кодировки файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Название кодировки
        """
        try:
            with open(file_path, 'rb') as file:
                raw_data = file.read()
            
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            confidence = result['confidence']
            
            self.logger.info(f"Определена кодировка: {encoding} (уверенность: {confidence:.2%})")
            
            return encoding or 'utf-8'
        
        except Exception as e:
            self.logger.warning(f"Не удалось определить кодировку: {e}")
            return 'utf-8'
