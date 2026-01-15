#!/usr/bin/env python3
"""
Модуль защиты от зацикливания LLM и дедупликации документов.

Решает проблему зацикливания малых моделей (4B параметров)
при генерации структурированного вывода (JSON).
"""

import json
import re
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class DocumentDeduplicator:
    """Класс для удаления дубликатов из результатов анализа."""

    MAX_DOCUMENTS = 50  # Максимальное количество документов

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Args:
            similarity_threshold: Порог схожести для определения дубликатов (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.stats = {
            "total_input": 0,
            "duplicates_removed": 0,
            "total_output": 0,
            "truncated_by_limit": False
        }

    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Нормализация названия документа для сравнения.
        
        Args:
            name: Название документа
            
        Returns:
            Нормализованное название
        """
        if not name:
            return ""
        
        # Приведение к нижнему регистру
        normalized = name.lower().strip()
        
        # Удаление лишних пробелов
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Удаление пунктуации (кроме слэша и дефиса)
        normalized = re.sub(r'[^\w\s\-/]', '', normalized)
        
        # Замена схожих конструкций
        replacements = [
            (r'\bсправка\s+о\s+', 'справка_'),
            (r'\bвыписка\s+из\s+', 'выписка_'),
            (r'\bсведения\s+о\s+', 'сведения_'),
            (r'\bдоговор\s+\u043d\u0440\s+', 'договор_'),
        ]
        
        for pattern, replacement in replacements:
            normalized = re.sub(pattern, replacement, normalized)
        
        return normalized

    @staticmethod
    def calculate_similarity(str1: str, str2: str) -> float:
        """
        Вычисление коэффициента схожести между двумя строками (коэффициент Жаккара).
        
        Args:
            str1, str2: Строки для сравнения
            
        Returns:
            Коэффициент схожести (0-1)
        """
        if not str1 or not str2:
            return 0.0
        
        # Разбиваем на множества слов
        set1 = set(str1.split())
        set2 = set(str2.split())
        
        # Коэффициент Жаккара
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0

    def is_duplicate(self, doc1: Dict, doc2: Dict) -> bool:
        """
        Проверка, являются ли документы дубликатами.
        
        Args:
            doc1, doc2: Документы для сравнения
            
        Returns:
            True, если документы - дубликаты
        """
        name1 = self.normalize_name(doc1.get("name", ""))
        name2 = self.normalize_name(doc2.get("name", ""))
        
        # Точное совпадение
        if name1 == name2:
            return True
        
        # Схожесть по коэффициенту Жаккара
        similarity = self.calculate_similarity(name1, name2)
        return similarity >= self.similarity_threshold

    def deduplicate(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Удаление дубликатов из результата анализа.
        
        Args:
            analysis: Результат анализа с массивом required_documents
            
        Returns:
            Обработанный результат без дубликатов
        """
        documents = analysis.get("required_documents", [])
        self.stats["total_input"] = len(documents)
        
        if not documents:
            return analysis
        
        unique_docs = []
        seen_names: Set[str] = set()
        
        for doc in documents:
            # Проверка лимита
            if len(unique_docs) >= self.MAX_DOCUMENTS:
                self.stats["truncated_by_limit"] = True
                logger.warning(
                    f"Достигнут лимит в {self.MAX_DOCUMENTS} документов. "
                    f"Оставшиеся {len(documents) - len(unique_docs)} документов отброшены."
                )
                break
            
            # Нормализация названия
            name_normalized = self.normalize_name(doc.get("name", ""))
            
            if not name_normalized:
                continue
            
            # Проверка точного дубликата
            if name_normalized in seen_names:
                self.stats["duplicates_removed"] += 1
                logger.debug(f"Удален точный дубликат: {doc.get('name')}")
                continue
            
            # Проверка схожих документов
            is_similar = False
            for unique_doc in unique_docs:
                if self.is_duplicate(doc, unique_doc):
                    is_similar = True
                    self.stats["duplicates_removed"] += 1
                    logger.debug(f"Удален схожий документ: {doc.get('name')}")
                    break
            
            if not is_similar:
                seen_names.add(name_normalized)
                unique_docs.append(doc)
        
        # Перенумерация ID
        for idx, doc in enumerate(unique_docs, 1):
            doc["id"] = f"doc_{idx}"
        
        self.stats["total_output"] = len(unique_docs)
        
        analysis["required_documents"] = unique_docs
        analysis["deduplication_stats"] = self.stats.copy()
        
        logger.info(
            f"Дедупликация завершена: "
            f"{self.stats['total_input']} → {self.stats['total_output']} документов, "
            f"удалено {self.stats['duplicates_removed']} дубликатов"
        )
        
        return analysis


def fix_incomplete_json(json_str: str) -> str:
    """
    Попытка исправить неполный JSON, полученный при зацикливании LLM.
    
    Args:
        json_str: Неполная JSON-строка
        
    Returns:
        Исправленная JSON-строка или пустая строка
    """
    try:
        # Пробуем распарсить как есть
        json.loads(json_str)
        return json_str
    except json.JSONDecodeError:
        pass
    
    # Находим последний валидный объект в массиве
    last_complete_obj = json_str.rfind('"},')
    if last_complete_obj != -1:
        # Обрезаем до последнего завершенного объекта и закрываем структуру
        truncated = json_str[:last_complete_obj + 2]
        
        # Закрываем required_documents
        if '"required_documents"' in truncated:
            truncated += ']'
        
        # Добавляем остальные поля
        truncated += ',"document_verification":{"provided":[],"missing_critical":[],"missing_optional":[],"issues":[]},'
        truncated += '"completeness_score":0,"critical_warnings":[]}'
        
        try:
            json.loads(truncated)
            logger.info("Неполный JSON успешно исправлен")
            return truncated
        except json.JSONDecodeError:
            pass
    
    logger.error("Не удалось исправить неполный JSON")
    return ""


def get_anti_loop_generation_params() -> Dict[str, Any]:
    """
    Получение параметров генерации для защиты от зацикливания.
    
    Returns:
        Словарь параметров для LLM
    """
    return {
        "temperature": 0.7,
        "repetition_penalty": 1.3,  # Штраф за повторение токенов
        "frequency_penalty": 0.8,    # Штраф пропорционально частоте
        "presence_penalty": 0.6,     # Штраф за уже встречавшиеся токены
        "max_tokens": 4096,
        "top_p": 0.9,
        # Стоп-последовательности для остановки при 51-м документе
        "stop_sequences": [
            "=== \u041a\u041e\u041d\u0415\u0426 \u0421\u041f\u0418\u0421\u041a\u0410 ===",
            "51 |",
            '"id": "doc_51"',
        ]
    }


def get_anti_loop_prompt_addition() -> str:
    """
    Получение дополнительной части промпта для защиты от зацикливания.
    
    Returns:
        Строка с дополнительными инструкциями
    """
    return """

# КРИТИЧЕСКОЕ ПРАВИЛО: ПРЕДОТВРАЩЕНИЕ ДУБЛИКАТОВ
- ЗАПРЕЩЕНО добавлять документы с одинаковыми наименованиями
- Если документ уже добавлен в массив, НЕ добавляйте его повторно
- После добавления каждого документа проверьте: нет ли такого же в списке
- Максимум 50 документов в массиве required_documents
- Если достигнут лимит в 50 документов, остановите генерацию и завершите JSON

# АЛГОРИТМ ДОБАВЛЕНИЯ ДОКУМЕНТА
1. Извлеките требование из текста
2. ПРОВЕРЬТЕ: есть ли документ с таким же "name" в уже созданном списке?
3. Если ДА - пропустите, переходите к следующему требованию
4. Если НЕТ - добавьте в массив и присвойте новый id
5. Если добавлено 50 документов - остановитесь и закройте JSON

# ФОРМАТ ОСТАНОВКИ
После последнего документа обязательно закройте массив:
  ],
  "document_verification": {...},
  "completeness_score": 0,
  "critical_warnings": []
}
"""


if __name__ == "__main__":
    # Пример использования
    logging.basicConfig(level=logging.INFO)
    
    # Тестовые данные с дубликатами
    test_analysis = {
        "procurement_info": {"number": "123"},
        "required_documents": [
            {"id": "doc_1", "name": "Выписка из ЕГРЮЛ"},
            {"id": "doc_2", "name": "Устав"},
            {"id": "doc_3", "name": "Выписка из ЕГРЮЛ"},  # Дубликат
            {"id": "doc_4", "name": "Справка об отсутствии задолженности в ФНС"},
            {"id": "doc_5", "name": "Справка о задолженности в фнс"},  # Схожий
        ]
    }
    
    deduplicator = DocumentDeduplicator()
    result = deduplicator.deduplicate(test_analysis)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
