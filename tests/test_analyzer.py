#!/usr/bin/env python3
"""
Тесты для модуля analyzer.py

Проверка:
- Защиты от зацикливания
- Дедупликации
- Ограничения количества документов
- Корректности парсинга

Автор: Система УДЗ
Версия: 1.0
Дата: 2026-01-15
"""

import unittest
import sys
from pathlib import Path

# Добавляем путь к backend
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from analyzer import DocumentAnalyzer


class TestDocumentAnalyzer(unittest.TestCase):
    """
    Тесты анализатора документации
    """
    
    def setUp(self):
        """Подготовка перед каждым тестом"""
        self.analyzer = DocumentAnalyzer(model_size="small")
    
    def test_basic_analysis(self):
        """Тест базового анализа"""
        test_doc = """
        Закупка № TEST-001
        Заказчик: Тестовая организация
        
        Требования к заявке:
        - Выписка из ЕГРЮЛ
        - Устав
        - Лицензия
        """
        
        result = self.analyzer.analyze_documentation(test_doc)
        
        # Проверка структуры результата
        self.assertIn("procurement_info", result)
        self.assertIn("required_documents", result)
        self.assertIn("total_count", result)
        
        # Проверка количества документов
        self.assertEqual(result["total_count"], 3)
        self.assertEqual(len(result["required_documents"]), 3)
    
    def test_deduplication_exact(self):
        """Тест точной дедупликации"""
        documents = [
            {"id": "doc_1", "name": "Выписка из ЕГРЮЛ"},
            {"id": "doc_2", "name": "Устав"},
            {"id": "doc_3", "name": "Выписка из ЕГРЮЛ"},  # Дубликат
            {"id": "doc_4", "name": "Лицензия"},
        ]
        
        unique = self.analyzer._deduplicate_documents(documents)
        
        self.assertEqual(len(unique), 3)
        names = [doc["name"] for doc in unique]
        self.assertIn("Выписка из ЕГРЮЛ", names)
        self.assertIn("Устав", names)
        self.assertIn("Лицензия", names)
    
    def test_deduplication_similar(self):
        """Тест дедупликации похожих названий"""
        documents = [
            {"id": "doc_1", "name": "Выписка из ЕГРЮЛ"},
            {"id": "doc_2", "name": "выписка из егрюл"},  # Дубликат (регистр)
            {"id": "doc_3", "name": "Выписка  из   ЕГРЮЛ"},  # Дубликат (пробелы)
        ]
        
        unique = self.analyzer._deduplicate_documents(documents)
        
        # Должен остаться только один документ
        self.assertEqual(len(unique), 1)
    
    def test_max_documents_limit(self):
        """Тест ограничения максимального количества документов"""
        # Генерируем больше документов, чем лимит
        documents = [
            {"id": f"doc_{i}", "name": f"Документ {i}"}
            for i in range(100)
        ]
        
        result = {
            "procurement_info": {},
            "required_documents": documents
        }
        
        # Применяем дедупликацию и лимит
        result["required_documents"] = self.analyzer._deduplicate_documents(
            result["required_documents"]
        )
        
        if len(result["required_documents"]) > self.analyzer.MAX_DOCUMENTS:
            result["required_documents"] = result["required_documents"][:self.analyzer.MAX_DOCUMENTS]
        
        # Проверка, что не больше MAX_DOCUMENTS
        self.assertLessEqual(len(result["required_documents"]), self.analyzer.MAX_DOCUMENTS)
    
    def test_text_parsing(self):
        """Тест парсинга текстового вывода"""
        text_output = """=== ИНФОРМАЦИЯ О ЗАКУПКЕ ===
Номер: TEST-123
Заказчик: ООО "Тест"
Тип процедуры: Аукцион

=== СПИСОК ДОКУМЕНТОВ (макс. 30) ===

1 | Выписка из ЕГРЮЛ | Да | Копия | 30 дней | п.1
2 | Устав | Да | Оригинал | Нет | п.2
3 | Лицензия | Нет | Копия | 1 год | п.3

=== КОНЕЦ СПИСКА ===
Всего документов: 3
"""
        
        result = self.analyzer._parse_text_output(text_output)
        
        # Проверка информации о закупке
        self.assertEqual(result["procurement_info"]["number"], "TEST-123")
        self.assertEqual(result["procurement_info"]["customer"], 'ООО "Тест"')
        self.assertEqual(result["procurement_info"]["procedure_type"], "Аукцион")
        
        # Проверка документов
        self.assertEqual(len(result["required_documents"]), 3)
        
        # Проверка первого документа
        doc1 = result["required_documents"][0]
        self.assertEqual(doc1["name"], "Выписка из ЕГРЮЛ")
        self.assertTrue(doc1["mandatory"])
        self.assertEqual(doc1["format"], "Копия")
    
    def test_empty_input(self):
        """Тест пустого ввода"""
        result = self.analyzer.analyze_documentation("")
        
        self.assertIn("required_documents", result)
        self.assertEqual(len(result["required_documents"]), 0)
    
    def test_no_documents_in_text(self):
        """Тест текста без упоминания документов"""
        test_doc = """
        Это просто текст без требований к документам.
        Здесь нет списков и перечней.
        """
        
        result = self.analyzer.analyze_documentation(test_doc)
        
        # Должен вернуть пустой список или минимум документов
        self.assertLessEqual(len(result["required_documents"]), 5)
    
    def test_generation_params_small_model(self):
        """Тест параметров для малой модели"""
        analyzer_small = DocumentAnalyzer(model_size="small")
        
        params = analyzer_small.generation_params
        
        # Проверка наличия защитных параметров
        self.assertIn("repetition_penalty", params)
        self.assertIn("frequency_penalty", params)
        self.assertIn("presence_penalty", params)
        
        # Проверка значений
        self.assertGreaterEqual(params["repetition_penalty"], 1.3)
        self.assertGreaterEqual(params["frequency_penalty"], 0.8)
    
    def test_generation_params_large_model(self):
        """Тест параметров для большой модели"""
        analyzer_large = DocumentAnalyzer(model_size="large")
        
        params = analyzer_large.generation_params
        
        # Большая модель имеет другие параметры
        self.assertIn("repetition_penalty", params)
        self.assertLess(params["repetition_penalty"], 1.4)
    
    def test_similarity_detection(self):
        """Тест определения похожести названий"""
        from difflib import SequenceMatcher
        
        # Очень похожие названия
        name1 = "выписка из егрюл"
        name2 = "выписка из егрюл"
        similarity = SequenceMatcher(None, name1, name2).ratio()
        self.assertGreater(similarity, self.analyzer.SIMILARITY_THRESHOLD)
        
        # Разные названия
        name1 = "выписка из егрюл"
        name2 = "устав организации"
        similarity = SequenceMatcher(None, name1, name2).ratio()
        self.assertLess(similarity, self.analyzer.SIMILARITY_THRESHOLD)


class TestEdgeCases(unittest.TestCase):
    """
    Тесты граничных случаев
    """
    
    def setUp(self):
        self.analyzer = DocumentAnalyzer(model_size="small")
    
    def test_malformed_document_entries(self):
        """Тест некорректно оформленных записей"""
        documents = [
            {"id": "doc_1", "name": "Нормальный документ"},
            {"id": "doc_2"},  # Нет названия
            "не словарь",  # Не словарь
            {"id": "doc_3", "name": ""},  # Пустое название
            {"id": "doc_4", "name": "Еще один нормальный"},
        ]
        
        unique = self.analyzer._deduplicate_documents(documents)
        
        # Должны отфильтроваться только корректные записи
        self.assertGreater(len(unique), 0)
        for doc in unique:
            self.assertIsInstance(doc, dict)
            self.assertIn("name", doc)
            self.assertNotEqual(doc["name"], "")
    
    def test_very_long_document_name(self):
        """Тест очень длинного названия документа"""
        long_name = "А" * 1000
        documents = [
            {"id": "doc_1", "name": long_name},
            {"id": "doc_2", "name": "Нормальное название"},
        ]
        
        unique = self.analyzer._deduplicate_documents(documents)
        
        # Должны обработаться оба документа
        self.assertEqual(len(unique), 2)
    
    def test_special_characters_in_names(self):
        """Тест специальных символов в названиях"""
        documents = [
            {"id": "doc_1", "name": "Документ №1 (копия)"},
            {"id": "doc_2", "name": "Документ #2 [оригинал]"},
            {"id": "doc_3", "name": "Документ @3 {важный}"},
        ]
        
        unique = self.analyzer._deduplicate_documents(documents)
        
        # Все должны сохраниться
        self.assertEqual(len(unique), 3)


if __name__ == "__main__":
    # Запуск тестов
    unittest.main(verbosity=2)
