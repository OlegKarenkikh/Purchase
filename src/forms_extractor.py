#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль выделения форм из закупочной документации

Реализует требования FR-3.10 из расширенного ТЗ:
- Поиск форм в КД
- Структуризация форм
- Сопоставление с типовыми документами
"""

import re
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


@dataclass
class FormField:
    """Поле формы"""
    name: str
    field_type: str = "text"  # text, number, date, checkbox, select
    mandatory: bool = True
    default_value: Optional[str] = None
    description: Optional[str] = None


@dataclass
class ExtractedForm:
    """Извлеченная форма"""
    form_id: str
    form_name: str
    form_number: Optional[str] = None
    source_section: Optional[str] = None
    raw_text: str = ""
    fields: List[FormField] = field(default_factory=list)
    template_match: Optional[Dict] = None


class FormsExtractor:
    """
    Извлечение форм из закупочной документации (FR-3.10)

    Обеспечивает:
    - Поиск и извлечение форм из текста КД
    - Парсинг структуры формы
    - Сопоставление с типовыми документами
    """

    # Паттерны для поиска форм
    FORM_PATTERNS = [
        r'(?i)форма\s*[№#]?\s*(\d+)',
        r'(?i)приложение\s*[№#]?\s*(\d+)',
        r'(?i)форма\s+заявки',
        r'(?i)анкета\s+участника',
        r'(?i)сведения\s+об?\s+участник[еа]',
        r'(?i)ценовое\s+предложение',
        r'(?i)техническое\s+предложение',
        r'(?i)декларация\s+',
        r'(?i)гарантийное\s+письмо',
    ]

    # Паттерны для определения полей формы
    FIELD_PATTERNS = [
        r'(\d+)\.\s*(.+?)[:]\s*[_\-]{3,}',  # 1. Название: ___
        r'(\d+)\.\s*(.+?)[:]\s*$',  # 1. Название:
        r'([А-Яа-яA-Za-z\s]+)[:]\s*[_\-]{3,}',  # Название: ___
        r'\|\s*([^|]+?)\s*\|',  # | Название |
    ]

    def __init__(self, template_library=None):
        """
        Args:
            template_library: Библиотека типовых документов для сопоставления
        """
        self.template_library = template_library

    def extract_forms(self, kd_text: str) -> List[Dict]:
        """
        Извлечение всех форм из текста закупочной документации

        Args:
            kd_text: Текст закупочной документации

        Returns:
            Список извлеченных форм
        """
        forms = []

        # Разбиваем текст на секции
        sections = self._split_into_sections(kd_text)

        for section_name, section_text in sections:
            # Ищем формы в каждой секции
            found_forms = self._find_forms_in_section(section_text, section_name)
            forms.extend(found_forms)

        # Пытаемся сопоставить с типовыми документами
        if self.template_library:
            for form in forms:
                self._match_with_template(form)

        logger.info(f"Извлечено форм: {len(forms)}")
        return forms

    def _split_into_sections(self, text: str) -> List[tuple]:
        """Разбиение текста на секции"""
        sections = []

        # Паттерн для заголовков разделов
        section_pattern = r'(?:^|\n)\s*((?:\d+\.)+\s*.+?)(?=\n)'

        matches = list(re.finditer(section_pattern, text, re.MULTILINE))

        if not matches:
            return [("", text)]

        for i, match in enumerate(matches):
            section_name = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_text = text[start:end]
            sections.append((section_name, section_text))

        return sections

    def _find_forms_in_section(self, text: str, section_name: str) -> List[Dict]:
        """Поиск форм в секции текста"""
        forms = []

        for pattern in self.FORM_PATTERNS:
            matches = re.finditer(pattern, text)

            for match in matches:
                form_id = f"FORM-{uuid.uuid4().hex[:8].upper()}"

                # Определяем номер формы если есть
                form_number = None
                groups = match.groups()
                if groups:
                    form_number = groups[0]

                # Определяем название формы
                form_name = self._extract_form_name(text, match.start(), match.end())

                # Извлекаем текст формы
                raw_text = self._extract_form_text(text, match.start())

                # Парсим структуру формы
                structure = self.parse_form_structure(raw_text)

                form = {
                    "form_id": form_id,
                    "form_name": form_name,
                    "form_number": form_number,
                    "source_section": section_name or "Не определено",
                    "structure": structure,
                    "raw_text": raw_text[:2000],  # Ограничиваем длину
                    "template_match": None,
                }

                # Проверяем на дубликаты по названию
                if not any(f["form_name"] == form_name for f in forms):
                    forms.append(form)

        return forms

    def _extract_form_name(self, text: str, start: int, end: int) -> str:
        """Извлечение названия формы из контекста"""
        # Берем текст вокруг match
        context_start = max(0, start - 50)
        context_end = min(len(text), end + 200)
        context = text[context_start:context_end]

        # Ищем название в строке с "Форма"
        lines = context.split('\n')
        for line in lines:
            line = line.strip()
            if re.search(r'(?i)форма|приложение|анкета', line):
                # Убираем номер и возвращаем остаток
                name = re.sub(r'(?i)(форма|приложение)\s*[№#]?\s*\d*\s*[-–:]?\s*', '', line)
                if name:
                    return name.strip()[:100]

        return "Форма без названия"

    def _extract_form_text(self, text: str, start: int, max_length: int = 3000) -> str:
        """Извлечение текста формы"""
        # Ищем конец формы (следующий раздел или конец текста)
        end_patterns = [
            r'\n\s*(?:\d+\.)+\s+[А-ЯA-Z]',  # Новый раздел
            r'\n\s*Форма\s*[№#]?\s*\d+',  # Следующая форма
            r'\n\s*Приложение\s*[№#]?\s*\d+',  # Следующее приложение
        ]

        end = min(start + max_length, len(text))

        for pattern in end_patterns:
            match = re.search(pattern, text[start:end])
            if match:
                end = start + match.start()
                break

        return text[start:end].strip()

    def parse_form_structure(self, form_text: str) -> Dict[str, Any]:
        """
        Парсинг структуры формы

        Args:
            form_text: Текст формы

        Returns:
            Словарь со структурой формы
        """
        fields = []

        # Ищем поля формы
        for pattern in self.FIELD_PATTERNS:
            matches = re.finditer(pattern, form_text, re.MULTILINE)

            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    field_name = groups[1].strip() if groups[1] else groups[0].strip()
                elif groups:
                    field_name = groups[0].strip()
                else:
                    continue

                # Фильтруем слишком короткие или длинные названия
                if len(field_name) < 3 or len(field_name) > 100:
                    continue

                # Определяем тип поля
                field_type = self._detect_field_type(field_name)

                # Определяем обязательность
                mandatory = self._is_field_mandatory(field_name, form_text)

                field_data = {
                    "name": field_name,
                    "type": field_type,
                    "mandatory": mandatory,
                }

                # Проверяем на дубликаты
                if not any(f["name"].lower() == field_name.lower() for f in fields):
                    fields.append(field_data)

        # Анализируем таблицы
        tables = self._extract_tables(form_text)

        return {
            "fields": fields[:50],  # Ограничиваем количество полей
            "tables_count": len(tables),
            "has_signature": bool(re.search(r'(?i)подпись|печать|м\.?п\.?', form_text)),
            "has_date": bool(re.search(r'(?i)дата|«\s*»\s*\d{4}', form_text)),
        }

    def _detect_field_type(self, field_name: str) -> str:
        """Определение типа поля по названию"""
        name_lower = field_name.lower()

        if any(kw in name_lower for kw in ["дата", "date", "год"]):
            return "date"
        if any(kw in name_lower for kw in ["инн", "огрн", "кпп", "номер", "сумма", "цена"]):
            return "number"
        if any(kw in name_lower for kw in ["адрес", "email", "телефон"]):
            return "text"
        if any(kw in name_lower for kw in ["да/нет", "согласен", "подтверждаю"]):
            return "checkbox"

        return "text"

    def _is_field_mandatory(self, field_name: str, context: str) -> bool:
        """Определение обязательности поля"""
        # Ищем контекст вокруг поля
        field_pos = context.lower().find(field_name.lower())
        if field_pos == -1:
            return True  # По умолчанию обязательно

        context_around = context[max(0, field_pos - 50):field_pos + len(field_name) + 50]

        # Проверяем на опциональность
        optional_markers = ["при наличии", "опционально", "по желанию", "(не обязательно)"]
        return not any(marker in context_around.lower() for marker in optional_markers)

    def _extract_tables(self, text: str) -> List[Dict]:
        """Извлечение информации о таблицах"""
        tables = []

        # Простой паттерн для определения таблиц
        table_patterns = [
            r'\|[^|]+\|[^|]+\|',  # Markdown-style таблицы
            r'(?:\s{2,}[\w\s]+){3,}',  # Текстовые таблицы с табуляцией
        ]

        for pattern in table_patterns:
            matches = re.findall(pattern, text)
            if matches:
                tables.append({
                    "type": "detected",
                    "rows_count": len(matches),
                })

        return tables

    def _match_with_template(self, form: Dict) -> None:
        """Сопоставление формы с типовым документом"""
        if not self.template_library:
            return

        form_name = form.get("form_name", "")
        form_number = form.get("form_number")

        # Поиск по имени
        results = self.template_library.search_template(
            document_name=form_name,
            document_type="form",
            min_confidence=0.4
        )

        # Если есть номер формы, ищем также по нему
        if form_number and not results:
            results = self.template_library.search_template(
                document_name=f"Форма {form_number}",
                document_type="form",
                min_confidence=0.4
            )

        if results:
            best_match = results[0]
            form["template_match"] = {
                "template_id": best_match.get("template_id"),
                "file_path": best_match.get("file_path"),
                "confidence": best_match.get("confidence"),
            }

    def get_forms_summary(self, forms: List[Dict]) -> Dict[str, Any]:
        """
        Получение сводки по извлеченным формам

        Args:
            forms: Список извлеченных форм

        Returns:
            Сводная информация
        """
        total_fields = sum(
            len(f.get("structure", {}).get("fields", []))
            for f in forms
        )

        with_template = sum(1 for f in forms if f.get("template_match"))

        return {
            "total_forms": len(forms),
            "total_fields": total_fields,
            "forms_with_template": with_template,
            "forms_without_template": len(forms) - with_template,
            "forms_by_section": self._group_by_section(forms),
        }

    def _group_by_section(self, forms: List[Dict]) -> Dict[str, int]:
        """Группировка форм по секциям"""
        by_section = {}
        for form in forms:
            section = form.get("source_section", "Не определено")
            by_section[section] = by_section.get(section, 0) + 1
        return by_section
