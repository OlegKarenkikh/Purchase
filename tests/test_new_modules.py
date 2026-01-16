#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для новых модулей Фазы 2

Покрывает:
- TemplateLibrary (FR-1.10)
- FormsExtractor (FR-3.10)
- PackageManifest (FR-3.11, FR-3.12)
- ReadinessReport (FR-4.9)
- Control с чек-листами (FR-4.7, FR-4.8)
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from src.template_library import TemplateLibrary
from src.forms_extractor import FormsExtractor
from src.package_manifest import PackageManifest
from src.readiness_report import ReadinessReport
from src.control import MultiStageController, ChecklistItem, ControlHistory


class TestTemplateLibrary(unittest.TestCase):
    """Тесты каталога типовых документов (FR-1.10)"""

    def setUp(self):
        """Создание временного каталога для тестов"""
        self.temp_dir = tempfile.mkdtemp()
        self.library = TemplateLibrary(self.temp_dir)

        # Создаем тестовые файлы
        (Path(self.temp_dir) / "Форма_1_Сведения.docx").write_text("test")
        (Path(self.temp_dir) / "Выписка_ЕГРЮЛ.pdf").write_bytes(b"PDF content")
        (Path(self.temp_dir) / "Устав.pdf").write_bytes(b"Charter")

    def tearDown(self):
        """Удаление временного каталога"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scan_catalog(self):
        """Тест сканирования каталога"""
        documents = self.library.scan_catalog()

        self.assertEqual(len(documents), 3)
        self.assertTrue(all("template_id" in doc for doc in documents))
        self.assertTrue(all("file_hash" in doc for doc in documents))

    def test_index_documents(self):
        """Тест индексации документов"""
        self.library.index_documents()

        self.assertGreater(len(self.library.index), 0)
        self.assertIsNotNone(self.library._indexed_at)

    def test_search_template(self):
        """Тест поиска типового документа"""
        self.library.index_documents()

        results = self.library.search_template("Выписка ЕГРЮЛ")

        self.assertGreater(len(results), 0)
        self.assertIn("confidence", results[0])

    def test_search_template_with_type(self):
        """Тест поиска по типу документа"""
        self.library.index_documents()

        results = self.library.search_template("форма", document_type="form")

        self.assertGreater(len(results), 0)

    def test_detect_document_type(self):
        """Тест определения типа документа"""
        self.assertEqual(
            self.library._detect_document_type("Форма_1_анкета.docx"),
            "form"
        )
        self.assertEqual(
            self.library._detect_document_type("Выписка_ЕГРЮЛ.pdf"),
            "extract"
        )
        self.assertEqual(
            self.library._detect_document_type("random_file.txt"),
            "other"
        )

    def test_get_statistics(self):
        """Тест получения статистики"""
        self.library.index_documents()

        stats = self.library.get_statistics()

        self.assertIn("total_templates", stats)
        self.assertIn("by_type", stats)
        self.assertIn("by_extension", stats)
        self.assertEqual(stats["total_templates"], 3)


class TestFormsExtractor(unittest.TestCase):
    """Тесты извлечения форм (FR-3.10)"""

    def setUp(self):
        self.extractor = FormsExtractor()

    def test_extract_forms_basic(self):
        """Тест базового извлечения форм"""
        kd_text = """
        Раздел 4. Требования к заявке

        4.1. Форма 1 - Сведения об участнике закупки

        Участник должен предоставить следующие сведения:
        1. Полное наименование: _______
        2. ИНН: _______
        3. КПП: _______

        4.2. Форма 2 - Техническое предложение

        Участник должен представить техническое предложение.
        """

        forms = self.extractor.extract_forms(kd_text)

        self.assertGreater(len(forms), 0)
        self.assertTrue(all("form_id" in f for f in forms))
        self.assertTrue(all("form_name" in f for f in forms))

    def test_extract_forms_with_appendix(self):
        """Тест извлечения приложений"""
        kd_text = """
        Приложение 1 - Анкета участника

        Заполните анкету:
        - Название организации: _____
        - Адрес: _____

        Приложение 2 - Ценовое предложение

        Укажите стоимость работ.
        """

        forms = self.extractor.extract_forms(kd_text)

        self.assertGreater(len(forms), 0)

    def test_parse_form_structure(self):
        """Тест парсинга структуры формы"""
        form_text = """
        Форма 1 - Сведения об участнике

        1. Полное наименование: _______
        2. ИНН: _______
        3. Дата регистрации: _______

        Подпись ______________ М.П.
        """

        structure = self.extractor.parse_form_structure(form_text)

        self.assertIn("fields", structure)
        self.assertIn("has_signature", structure)
        self.assertTrue(structure["has_signature"])

    def test_get_forms_summary(self):
        """Тест получения сводки по формам"""
        forms = [
            {"form_id": "F1", "form_name": "Форма 1", "structure": {"fields": [1, 2, 3]}},
            {"form_id": "F2", "form_name": "Форма 2", "structure": {"fields": [1, 2]}, "template_match": {"template_id": "T1"}},
        ]

        summary = self.extractor.get_forms_summary(forms)

        self.assertEqual(summary["total_forms"], 2)
        self.assertEqual(summary["total_fields"], 5)
        self.assertEqual(summary["forms_with_template"], 1)


class TestPackageManifest(unittest.TestCase):
    """Тесты формирования описи и пакета (FR-3.11, FR-3.12)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manifest_builder = PackageManifest(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_manifest(self):
        """Тест создания описи"""
        requirements = [
            {"id": "R1", "name": "Выписка из ЕГРЮЛ", "mandatory": True},
            {"id": "R2", "name": "Устав", "mandatory": True},
            {"id": "R3", "name": "Рекомендательное письмо", "mandatory": False},
        ]
        documents = []

        manifest = self.manifest_builder.create_manifest(documents, requirements)

        self.assertIn("manifest_id", manifest)
        self.assertIn("items", manifest)
        self.assertIn("metrics", manifest)
        self.assertEqual(len(manifest["items"]), 3)

    def test_calculate_metrics(self):
        """Тест расчета метрик"""
        items = [
            {"mandatory": True, "completion_status": "provided"},
            {"mandatory": True, "completion_status": "missing"},
            {"mandatory": False, "completion_status": "provided"},
        ]

        metrics = self.manifest_builder._calculate_metrics(items)

        self.assertEqual(metrics["total_documents"], 3)
        self.assertEqual(metrics["mandatory_documents"], 2)
        self.assertEqual(metrics["provided_documents"], 2)
        self.assertEqual(metrics["completeness_percentage"], 50.0)

    def test_export_manifest_json(self):
        """Тест экспорта описи в JSON"""
        manifest = {
            "manifest_id": "TEST-001",
            "items": [{"name": "Test"}],
            "metrics": {}
        }

        output_path = self.manifest_builder.export_manifest(manifest, "json")

        self.assertTrue(Path(output_path).exists())
        self.assertTrue(output_path.endswith(".json"))

    def test_export_manifest_csv(self):
        """Тест экспорта описи в CSV"""
        manifest = {
            "manifest_id": "TEST-002",
            "items": [
                {"position": 1, "document_name": "Test", "mandatory": True}
            ],
            "metrics": {}
        }

        output_path = self.manifest_builder.export_manifest(manifest, "csv")

        self.assertTrue(Path(output_path).exists())
        self.assertTrue(output_path.endswith(".csv"))

    def test_create_package_structure(self):
        """Тест создания структуры пакета"""
        package_dir = self.manifest_builder.create_package_structure("TEST-003")

        self.assertTrue(package_dir.exists())
        self.assertTrue((package_dir / "Формы").exists())
        self.assertTrue((package_dir / "Документы_из_каталога").exists())


class TestReadinessReport(unittest.TestCase):
    """Тесты отчета о готовности (FR-4.9)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.reporter = ReadinessReport(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_report(self):
        """Тест генерации отчета"""
        manifest = {
            "items": [
                {"mandatory": True, "completion_status": "provided", "document_name": "Doc1"},
                {"mandatory": True, "completion_status": "missing", "document_name": "Doc2"},
            ]
        }
        requirements = [
            {"id": "R1", "name": "Doc1"},
            {"id": "R2", "name": "Doc2"},
        ]

        report = self.reporter.generate_report(manifest, requirements)

        self.assertIn("report_id", report)
        self.assertIn("status", report)
        self.assertIn("metrics", report)
        self.assertIn("problems", report)
        self.assertIn("recommendations", report)

    def test_calculate_readiness(self):
        """Тест расчета метрик готовности"""
        manifest = {
            "items": [
                {"mandatory": True, "completion_status": "provided"},
                {"mandatory": True, "completion_status": "provided"},
                {"mandatory": False, "completion_status": "missing"},
            ]
        }
        requirements = []

        metrics = self.reporter.calculate_readiness(manifest, requirements)

        self.assertEqual(metrics["total_mandatory_docs"], 2)
        self.assertEqual(metrics["provided_mandatory_docs"], 2)
        self.assertEqual(metrics["completeness_percentage"], 100.0)

    def test_identify_problems(self):
        """Тест выявления проблем"""
        manifest = {
            "items": [
                {"mandatory": True, "completion_status": "missing",
                 "document_id": "D1", "document_name": "Отсутствующий документ"},
            ]
        }
        requirements = []

        problems = self.reporter.identify_problems(manifest, requirements)

        self.assertGreater(len(problems), 0)
        self.assertEqual(problems[0]["type"], "missing_mandatory")
        self.assertEqual(problems[0]["priority"], "high")

    def test_generate_recommendations(self):
        """Тест генерации рекомендаций"""
        problems = [
            {"type": "missing_mandatory", "document_name": "Doc1"},
            {"type": "missing_mandatory", "document_name": "Doc2"},
        ]
        metrics = {"completeness_percentage": 30}

        recommendations = self.reporter.generate_recommendations(problems, metrics)

        self.assertGreater(len(recommendations), 0)

    def test_export_report_html(self):
        """Тест экспорта отчета в HTML"""
        report = {
            "report_id": "RPT-TEST",
            "status": "incomplete",
            "status_description": "Тест",
            "metrics": {"completeness_percentage": 50},
            "problems": [],
            "recommendations": [],
            "checklist": [],
        }

        output_path = self.reporter.export_report(report, "html")

        self.assertTrue(Path(output_path).exists())
        content = Path(output_path).read_text()
        self.assertIn("RPT-TEST", content)


class TestControlWithChecklists(unittest.TestCase):
    """Тесты многоэтапного контроля с чек-листами (FR-4.7, FR-4.8)"""

    def setUp(self):
        self.controller = MultiStageController()

    def test_get_all_checklists(self):
        """Тест получения всех чек-листов"""
        checklists = self.controller.get_all_checklists()

        self.assertIn("Автоматический", checklists)
        self.assertIn("Юридический", checklists)
        self.assertIn("Финансовый", checklists)
        self.assertIn("Итоговый", checklists)

        # Проверяем, что чек-листы не пустые
        self.assertGreater(len(checklists["Автоматический"]), 0)
        self.assertGreater(len(checklists["Юридический"]), 0)

    def test_get_stage_checklist(self):
        """Тест получения чек-листа этапа"""
        checklist = self.controller.get_stage_checklist(0)  # Автоматический

        self.assertGreater(len(checklist), 0)
        self.assertIn("id", checklist[0])
        self.assertIn("description", checklist[0])

    def test_update_checklist_item(self):
        """Тест обновления пункта чек-листа"""
        # Обновляем неавтоматический пункт
        success = self.controller.update_checklist_item(
            stage_index=1,  # Юридический
            item_id="legal_01",
            checked=True,
            user_id="test_user",
            user_name="Тестовый пользователь"
        )

        self.assertTrue(success)

        # Проверяем, что запись в истории создана
        history = self.controller.get_control_history()
        self.assertGreater(len(history), 0)

    def test_approve_stage(self):
        """Тест утверждения этапа"""
        # Сначала отмечаем все критические пункты
        stage = self.controller.stages[1]  # Юридический
        for item in stage.checklist:
            if item.severity == "critical":
                item.mark_checked("test_user")

        success = self.controller.approve_stage(
            stage_index=1,
            user_id="approver",
            user_name="Утверждающий"
        )

        self.assertTrue(success)
        self.assertEqual(stage.status, "passed")

    def test_control_history(self):
        """Тест истории контроля"""
        history = ControlHistory()

        entry = history.add_entry(
            stage_name="Автоматический",
            action="check",
            user_id="user1",
            user_name="Пользователь 1",
            status_before="pending",
            status_after="passed",
            comment="Тестовая проверка",
            time_spent_minutes=5
        )

        self.assertIsNotNone(entry.entry_id)

        all_history = history.get_history()
        self.assertEqual(len(all_history), 1)

        stats = history.get_statistics()
        self.assertEqual(stats["total_entries"], 1)
        self.assertEqual(stats["total_time_minutes"], 5)

    def test_checklist_item_creation(self):
        """Тест создания элемента чек-листа"""
        item = ChecklistItem(
            id="test_item",
            description="Тестовый пункт",
            category="test",
            severity="critical"
        )

        self.assertFalse(item.checked)
        self.assertIsNone(item.checked_by)

        item.mark_checked("tester", "Комментарий")

        self.assertTrue(item.checked)
        self.assertEqual(item.checked_by, "tester")
        self.assertEqual(item.comment, "Комментарий")
        self.assertIsNotNone(item.checked_at)


class TestCacheManagerSecurity(unittest.TestCase):
    """Тесты безопасности менеджера кэша"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_uses_sha256(self):
        """Тест использования SHA-256 для хеширования"""
        from src.utils.cache_manager import CacheManager

        cache = CacheManager(self.temp_dir)
        cache_file = cache._get_cache_file("test_key")

        # SHA-256 создает хеш длиной 64 символа
        filename = cache_file.stem
        self.assertEqual(len(filename), 64)

    def test_cache_uses_json(self):
        """Тест использования JSON для сериализации"""
        from src.utils.cache_manager import CacheManager

        cache = CacheManager(self.temp_dir)

        test_data = {"key": "value", "number": 42}
        cache.set("test", test_data)

        # Проверяем, что файл содержит JSON
        cache_file = cache._get_cache_file("test")
        content = cache_file.read_text()

        self.assertIn('"key"', content)
        self.assertIn('"value"', content)

    def test_cache_get_set(self):
        """Тест базовых операций кэша"""
        from src.utils.cache_manager import CacheManager

        cache = CacheManager(self.temp_dir)

        test_data = {"test": "data", "list": [1, 2, 3]}
        cache.set("key1", test_data)

        retrieved = cache.get("key1")
        self.assertEqual(retrieved, test_data)

    def test_cache_returns_none_for_missing(self):
        """Тест возврата None для отсутствующего ключа"""
        from src.utils.cache_manager import CacheManager

        cache = CacheManager(self.temp_dir)

        result = cache.get("nonexistent_key")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
