#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль парсеров документов для АИС УДЗ

Поддерживаемые форматы:
- PDF (текстовые и отсканированные)
- DOCX, DOC
- RTF
- TXT
- ZIP-архивы
"""

from .pdf_parser import PDFParser
from .docx_parser import DOCXParser
from .rtf_parser import RTFParser
from .text_parser import TextParser
from .archive_parser import ArchiveParser
from .base_parser import BaseParser, ParseResult

__all__ = [
    "PDFParser",
    "DOCXParser",
    "RTFParser",
    "TextParser",
    "ArchiveParser",
    "BaseParser",
    "ParseResult"
]
