#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер PDF документов с поддержкой OCR
"""

import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

import PyPDF2
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

from .base_parser import BaseParser, ParseResult

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """
    Парсер PDF документов
    
    Поддерживает:
    - Извлечение текста из текстовых PDF
    - OCR для отсканированных PDF
    - Извлечение таблиц
    - Метаданные документа
    """
    
    SUPPORTED_EXTENSIONS = [".pdf"]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.use_ocr = config.get("use_ocr", True) if config else True
        self.ocr_lang = config.get("ocr_lang", "rus+eng") if config else "rus+eng"
        self.extract_tables = config.get("extract_tables", True) if config else True
        self.ocr_threshold = config.get("ocr_threshold", 100) if config else 100  # Минимум символов для текстового PDF
    
    def supports(self, file_path: Path) -> bool:
        """Проверка поддержки формата"""
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
    
    def parse(self, file_path: Path) -> ParseResult:
        """
        Парсинг PDF документа
        
        Args:
            file_path: Путь к PDF файлу
            
        Returns:
            Результат парсинга
        """
        start_time = time.time()
        result = ParseResult()
        
        try:
            self.validate_file(file_path)
            
            # Извлечение базовых метаданных
            result.metadata = self.extract_metadata(file_path)
            
            # Извлечение метаданных PDF
            pdf_metadata = self._extract_pdf_metadata(file_path)
            result.metadata.update(pdf_metadata)
            
            # Попытка извлечь текст стандартными методами
            text = self._extract_text_pypdf(file_path)
            
            # Если текста мало, используем OCR
            if len(text.strip()) < self.ocr_threshold and self.use_ocr:
                self.logger.info(f"Текста мало ({len(text)} символов), применяем OCR")
                ocr_text = self._extract_text_ocr(file_path)
                if len(ocr_text) > len(text):
                    text = ocr_text
                    result.metadata["ocr_used"] = True
            
            result.text = text
            
            # Извлечение таблиц
            if self.extract_tables:
                result.tables = self._extract_tables(file_path)
                result.metadata["tables_count"] = len(result.tables)
            
            # Проверка результата
            if len(result.text.strip()) == 0:
                result.errors.append("Не удалось извлечь текст из документа")
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга PDF: {e}")
            result.errors.append(str(e))
        
        result.parse_time = time.time() - start_time
        return result
    
    def _extract_pdf_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Извлечение метаданных PDF"""
        metadata = {}
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                info = pdf_reader.metadata
                
                if info:
                    metadata["title"] = info.get("/Title", "")
                    metadata["author"] = info.get("/Author", "")
                    metadata["subject"] = info.get("/Subject", "")
                    metadata["creator"] = info.get("/Creator", "")
                    metadata["producer"] = info.get("/Producer", "")
                    metadata["creation_date"] = str(info.get("/CreationDate", ""))
                
                metadata["pages_count"] = len(pdf_reader.pages)
                metadata["is_encrypted"] = pdf_reader.is_encrypted
        
        except Exception as e:
            self.logger.warning(f"Не удалось извлечь метаданные PDF: {e}")
        
        return metadata
    
    def _extract_text_pypdf(self, file_path: Path) -> str:
        """Извлечение текста с помощью PyPDF2"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Страница {page_num} ---\n"
                        text += page_text
        
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения текста PyPDF2: {e}")
        
        return text
    
    def _extract_text_ocr(self, file_path: Path) -> str:
        """
        Извлечение текста с помощью OCR (Tesseract)
        
        Args:
            file_path: Путь к PDF файлу
            
        Returns:
            Извлеченный текст
        """
        text = ""
        try:
            # Конвертация PDF в изображения
            images = convert_from_path(str(file_path), dpi=300)
            
            self.logger.info(f"Конвертировано {len(images)} страниц в изображения")
            
            # OCR для каждой страницы
            for page_num, image in enumerate(images, 1):
                self.logger.info(f"OCR страницы {page_num}/{len(images)}")
                
                # Применение OCR
                page_text = pytesseract.image_to_string(
                    image,
                    lang=self.ocr_lang,
                    config='--psm 1'
                )
                
                if page_text:
                    text += f"\n--- Страница {page_num} (OCR) ---\n"
                    text += page_text
        
        except Exception as e:
            self.logger.error(f"Ошибка OCR: {e}")
            raise
        
        return text
    
    def _extract_tables(self, file_path: Path) -> List[List[List[str]]]:
        """
        Извлечение таблиц из PDF
        
        Args:
            file_path: Путь к PDF файлу
            
        Returns:
            Список таблиц (каждая таблица - список строк, каждая строка - список ячеек)
        """
        tables = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    
                    if page_tables:
                        self.logger.info(f"На странице {page_num} найдено таблиц: {len(page_tables)}")
                        tables.extend(page_tables)
        
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения таблиц: {e}")
        
        return tables
