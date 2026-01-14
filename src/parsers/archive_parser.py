#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер ZIP-архивов
"""

import time
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any
import logging

from .base_parser import BaseParser, ParseResult
from .pdf_parser import PDFParser
from .docx_parser import DOCXParser
from .rtf_parser import RTFParser
from .text_parser import TextParser

logger = logging.getLogger(__name__)


class ArchiveParser(BaseParser):
    """
    Парсер ZIP-архивов с документами
    
    Поддерживает:
    - Извлечение и парсинг всех документов из архива
    - Рекурсивная обработка вложенных архивов
    """
    
    SUPPORTED_EXTENSIONS = [".zip"]
    
    def __init__(self, config=None):
        super().__init__(config)
        # Инициализация парсеров для разных форматов
        self.parsers = {
            '.pdf': PDFParser(config),
            '.docx': DOCXParser(config),
            '.rtf': RTFParser(config),
            '.txt': TextParser(config)
        }
    
    def supports(self, file_path: Path) -> bool:
        """Проверка поддержки формата"""
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
    
    def parse(self, file_path: Path) -> ParseResult:
        """
        Парсинг ZIP-архива
        
        Args:
            file_path: Путь к ZIP файлу
            
        Returns:
            Объединенный результат парсинга всех документов
        """
        start_time = time.time()
        result = ParseResult()
        
        try:
            self.validate_file(file_path)
            
            # Базовые метаданные
            result.metadata = self.extract_metadata(file_path)
            
            # Создание временной директории
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Извлечение архива
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # Поиск всех файлов
                files = list(temp_path.rglob('*'))
                files = [f for f in files if f.is_file()]
                
                self.logger.info(f"Найдено файлов в архиве: {len(files)}")
                result.metadata["files_in_archive"] = len(files)
                
                # Парсинг каждого файла
                parsed_files = []
                all_text = []
                all_tables = []
                
                for file in files:
                    file_result = self._parse_file(file)
                    
                    if file_result:
                        parsed_files.append({
                            "filename": file.name,
                            "path": str(file.relative_to(temp_path)),
                            "success": file_result.is_success,
                            "word_count": file_result.word_count
                        })
                        
                        if file_result.is_success:
                            all_text.append(f"\n\n=== {file.name} ===\n")
                            all_text.append(file_result.text)
                            all_tables.extend(file_result.tables)
                        else:
                            result.warnings.extend([
                                f"{file.name}: {err}" for err in file_result.errors
                            ])
                
                result.text = "\n".join(all_text)
                result.tables = all_tables
                result.metadata["parsed_files"] = parsed_files
                result.metadata["successfully_parsed"] = sum(
                    1 for f in parsed_files if f["success"]
                )
        
        except Exception as e:
            self.logger.error(f"Ошибка парсинга архива: {e}")
            result.errors.append(str(e))
        
        result.parse_time = time.time() - start_time
        return result
    
    def _parse_file(self, file_path: Path) -> ParseResult:
        """
        Парсинг одного файла из архива
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Результат парсинга или None если формат не поддерживается
        """
        extension = file_path.suffix.lower()
        parser = self.parsers.get(extension)
        
        if parser:
            try:
                return parser.parse(file_path)
            except Exception as e:
                self.logger.warning(f"Ошибка парсинга {file_path.name}: {e}")
                result = ParseResult()
                result.errors.append(str(e))
                return result
        else:
            self.logger.debug(f"Формат {extension} не поддерживается: {file_path.name}")
            return None
