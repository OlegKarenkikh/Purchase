#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пример полного рабочего процесса АИС УДЗ

Демонстрирует:
1. Загрузку и парсинг документации
2. Анализ с помощью LLM
3. Формирование пакета документов
4. Многоэтапный контроль
5. Экспорт результата
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent.parent))

from src.utils import DocumentParserFactory, CacheManager, DocumentDeduplicator
from src.analyzer import DocumentAnalyzer


def main():
    """
    Полный workflow обработки закупки
    """
    print("=" * 70)
    print("АВТОМАТИЗИРОВАННАЯ СИСТЕМА УПРАВЛЕНИЯ ДОКУМЕНТАМИ ЗАКУПОК")
    print("=" * 70)
    print()
    
    # Шаг 1: Загрузка документации
    print("📄 ШАГ 1: Загрузка закупочной документации")
    print("-" * 70)
    
    doc_file = Path("example_procurement.pdf")
    
    if not doc_file.exists():
        print(f"⚠️  Файл {doc_file} не найден")
        print("💡 Создайте тестовый файл или используйте существующий")
        return
    
    # Создаем парсер автоматически
    parser = DocumentParserFactory.create_parser(
        doc_file,
        config={
            "use_ocr": True,
            "ocr_lang": "rus+eng",
            "extract_tables": True
        }
    )
    
    print(f"✅ Выбран парсер: {parser.__class__.__name__}")
    
    # Парсим документ
    print(f"⏳ Парсинг документа...")
    parse_result = parser.parse(doc_file)
    
    if not parse_result.is_success:
        print(f"❌ Ошибка парсинга: {parse_result.errors}")
        return
    
    print(f"✅ Парсинг завершен:")
    print(f"   - Извлечено символов: {parse_result.char_count}")
    print(f"   - Извлечено слов: {parse_result.word_count}")
    print(f"   - Найдено таблиц: {len(parse_result.tables)}")
    print(f"   - Время парсинга: {parse_result.parse_time:.2f} сек")
    print()
    
    # Шаг 2: Анализ с помощью LLM
    print("🤖 ШАГ 2: Анализ требований с помощью LLM")
    print("-" * 70)
    
    # Инициализация анализатора
    analyzer = DocumentAnalyzer()
    
    # Проверяем кэш
    cache_manager = CacheManager()
    cache_key = CacheManager.generate_key(parse_result.text)
    
    cached_result = cache_manager.get(cache_key)
    
    if cached_result:
        print("✅ Найден результат в кэше")
        analysis_result = cached_result
    else:
        print("⏳ Анализ документации (может занять до 30 сек)...")
        
        try:
            analysis_result = analyzer.analyze(
                document_text=parse_result.text,
                provided_docs=[]
            )
            
            # Сохраняем в кэш
            cache_manager.set(cache_key, analysis_result)
            
            print("✅ Анализ завершен")
        except Exception as e:
            print(f"❌ Ошибка анализа: {e}")
            return
    
    # Дедупликация найденных документов
    deduplicator = DocumentDeduplicator(similarity_threshold=0.85)
    required_docs = deduplicator.deduplicate(
        analysis_result.get("required_documents", [])
    )
    
    print(f"📋 Результаты анализа:")
    print(f"   - Найдено документов: {len(analysis_result.get('required_documents', []))}")
    print(f"   - После дедупликации: {len(required_docs)}")
    print(f"   - Обязательных: {sum(1 for d in required_docs if d.get('mandatory'))}")
    print(f"   - Опциональных: {sum(1 for d in required_docs if not d.get('mandatory'))}")
    print()
    
    # Выводим топ-5 документов
    print("📄 Топ-5 требуемых документов:")
    for i, doc in enumerate(required_docs[:5], 1):
        mandatory_mark = "🔴" if doc.get("mandatory") else "🟡"
        print(f"   {mandatory_mark} {i}. {doc.get('name')}")
        print(f"      Категория: {doc.get('category')}")
        if doc.get('validity_requirements'):
            print(f"      Срок действия: {doc.get('validity_requirements')}")
    print()
    
    # Шаг 3: Сверка предоставленных документов
    print("✅ ШАГ 3: Сверка предоставленных документов")
    print("-" * 70)
    
    # Пример предоставленных документов
    provided_documents = [
        "Выписка из ЕГРЮЛ от 10.01.2026",
        "Устав организации",
        "Бухгалтерский баланс за 2024 год",
    ]
    
    print("📦 Предоставленные документы:")
    for doc in provided_documents:
        print(f"   ✓ {doc}")
    print()
    
    verification_result = analyzer.verify_documents(
        required=required_docs,
        provided=provided_documents
    )
    
    print(f"📊 Результат сверки:")
    print(f"   - Полнота комплекта: {verification_result['completeness_score']}%")
    print(f"   - Предоставлено: {len(verification_result['provided'])}")
    print(f"   - Критичных недостает: {len(verification_result['missing_critical'])}")
    print(f"   - Опциональных недостает: {len(verification_result['missing_optional'])}")
    print()
    
    if verification_result['missing_critical']:
        print("⚠️  Отсутствуют критичные документы:")
        for doc_id in verification_result['missing_critical']:
            doc = next((d for d in required_docs if d['id'] == doc_id), None)
            if doc:
                print(f"   ❌ {doc['name']}")
        print()
    
    # Шаг 4: Формирование итогового отчета
    print("📊 ШАГ 4: Формирование итогового отчета")
    print("-" * 70)
    
    report = {
        "procurement_info": analysis_result.get("procurement_info", {}),
        "analysis_date": datetime.now().isoformat(),
        "documents_statistics": {
            "total_required": len(required_docs),
            "mandatory": sum(1 for d in required_docs if d.get('mandatory')),
            "optional": sum(1 for d in required_docs if not d.get('mandatory')),
            "provided": len(verification_result['provided']),
            "missing_critical": len(verification_result['missing_critical']),
            "missing_optional": len(verification_result['missing_optional']),
            "completeness_score": verification_result['completeness_score']
        },
        "required_documents": required_docs,
        "verification": verification_result,
        "readiness_status": "READY" if verification_result['completeness_score'] >= 100 else "NOT_READY"
    }
    
    # Сохраняем отчет
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    report_file = output_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Отчет сохранен: {report_file}")
    print()
    
    # Финальный статус
    print("=" * 70)
    if report['readiness_status'] == "READY":
        print("🎉 ЗАЯВКА ГОТОВА К ПОДАЧЕ")
        print(f"   Полнота комплекта: {verification_result['completeness_score']}%")
    else:
        print("⚠️  ЗАЯВКА НЕ ГОТОВА К ПОДАЧЕ")
        print(f"   Полнота комплекта: {verification_result['completeness_score']}%")
        print(f"   Недостает {len(verification_result['missing_critical'])} критичных документов")
    print("=" * 70)


if __name__ == "__main__":
    main()
