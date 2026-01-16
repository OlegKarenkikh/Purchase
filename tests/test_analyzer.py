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
import json
import uuid
from unittest.mock import MagicMock
from src.analyzer import DocumentAnalyzer


class TestDocumentAnalyzer(unittest.TestCase):
    """
    Тесты анализатора документации
    """
    
    def setUp(self):
        """Подготовка перед каждым тестом"""
        self.mock_client = MagicMock()

        # Стандартный ответ мока
        self.default_response = {
            "procurement_info": {
                "number": "TEST-001",
                "customer": "Тестовая организация",
                "procedure_type": "Аукцион"
            },
            "required_documents": [
                {"id": "doc_1", "name": "Выписка из ЕГРЮЛ", "mandatory": True},
                {"id": "doc_2", "name": "Устав", "mandatory": True},
                {"id": "doc_3", "name": "Лицензия", "mandatory": False}
            ]
        }
        self.mock_client.chat_completion.return_value = json.dumps(self.default_response)

        self.analyzer = DocumentAnalyzer(llm_client=self.mock_client, model_size="small")
    
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
        
        result = self.analyzer.analyze(test_doc)
        
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
        # Генерируем больше документов, чем лимит.
        # Используем уникальные имена (UUID) чтобы они не считались дубликатами по fuzzy match
        documents = [
            {"id": f"doc_{i}", "name": f"Document {uuid.uuid4()}"}
            for i in range(100)
        ]
        
        # Настраиваем мок, чтобы вернул много документов
        response = self.default_response.copy()
        response["required_documents"] = documents
        self.mock_client.chat_completion.return_value = json.dumps(response)
        
        # Вызываем analyze, который должен применить лимит
        result = self.analyzer.analyze("some text")
        
        # Проверка, что не больше MAX_DOCUMENTS
        self.assertLessEqual(len(result["required_documents"]), self.analyzer.MAX_DOCUMENTS)
        self.assertEqual(len(result["required_documents"]), 50)
    
    def test_empty_input(self):
        """Тест пустого ввода"""
        result = self.analyzer.analyze("")
        
        self.assertIn("required_documents", result)
        self.assertEqual(len(result["required_documents"]), 0)
    
    def test_generation_params_small_model(self):
        """Тест параметров для малой модели"""
        analyzer_small = DocumentAnalyzer(llm_client=self.mock_client, model_size="small")
        
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
        analyzer_large = DocumentAnalyzer(llm_client=self.mock_client, model_size="large")
        
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
        self.mock_client = MagicMock()
        self.analyzer = DocumentAnalyzer(llm_client=self.mock_client, model_size="small")
    
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
