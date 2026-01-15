# Модуль анализа закупочной документации

## Описание

Модуль `analyzer.py` предназначен для автоматического извлечения требований к документам из закупочной документации с использованием языковых моделей (LLM).

## Ключевые возможности

### 1. Защита от зацикливания для малых моделей

Для моделей размером 4B-7B параметров реализованы специальные механизмы:

- **Жесткие лимиты**: максимум 50 документов в результате
- **Параметры генерации**:
  - `repetition_penalty`: 1.4 (высокий штраф за повторы)
  - `frequency_penalty`: 0.9
  - `presence_penalty`: 0.7
- **Timeout**: автоматическое прерывание через 120 секунд
- **Stop-последовательности**: принудительная остановка при достижении лимита

### 2. Автоматическая дедупликация

```python
# Пример дедупликации
documents = [
    {"name": "Выписка из ЕГРЮЛ"},
    {"name": "выписка из егрюл"},      # Будет удален (регистр)
    {"name": "Выписка  из   ЕГРЮЛ"},   # Будет удален (пробелы)
]

unique = analyzer._deduplicate_documents(documents)
# Результат: 1 уникальный документ
```

Методы дедупликации:
- Точное совпадение (после нормализации)
- Похожие названия (similarity > 0.85)
- Очистка от лишних пробелов
- Приведение к lowercase

### 3. Гибкие форматы вывода

**Текстовый формат** (оптимизирован для малых моделей):
```
=== ИНФОРМАЦИЯ О ЗАКУПКЕ ===
Номер: 39-ЗЦ/2025
Заказчик: АНО «ИРИ»

=== СПИСОК ДОКУМЕНТОВ ===
1 | Выписка из ЕГРЮЛ | Да | Копия | 30 дней | п.3.1
2 | Устав | Да | Копия | Нет | п.3.2
```

**JSON-формат** (для больших моделей):
```json
{
  "procurement_info": {
    "number": "39-ЗЦ/2025",
    "customer": "АНО «ИРИ»"
  },
  "required_documents": [
    {
      "id": "doc_1",
      "name": "Выписка из ЕГРЮЛ",
      "mandatory": true,
      "format": "копия",
      "validity": "30 дней"
    }
  ]
}
```

## Использование

### Базовый пример

```python
from analyzer import DocumentAnalyzer

# Инициализация для малой модели
analyzer = DocumentAnalyzer(model_size="small")

# Анализ документации
doc_text = """
Закупка № 39-ЗЦ/2025
Требования:
- Выписка из ЕГРЮЛ (не ранее 30 дней)
- Устав
- Лицензия
"""

result = analyzer.analyze_documentation(doc_text)

print(f"Найдено документов: {result['total_count']}")
print(f"Время анализа: {result['analysis_time']}s")
```

### С подключением LLM-клиента

```python
from analyzer import DocumentAnalyzer
from your_llm_library import LLMClient

# Инициализация LLM-клиента
llm_client = LLMClient(
    model="ruadapt/Qwen3-4B",
    device="cuda"
)

# Создание анализатора с LLM
analyzer = DocumentAnalyzer(
    llm_client=llm_client,
    model_size="small"
)

# Анализ с реальной моделью
result = analyzer.analyze_documentation(doc_text)
```

### Выбор размера модели

```python
# Для малых моделей (4B-7B)
analyzer_small = DocumentAnalyzer(model_size="small")
# - Текстовый вывод
# - Усиленная защита от повторов
# - Жесткие лимиты

# Для больших моделей (>7B)
analyzer_large = DocumentAnalyzer(model_size="large")
# - JSON-вывод
# - Более мягкие параметры
# - Больше токенов
```

## Структура результата

```python
{
  "procurement_info": {
    "number": "Номер закупки",
    "customer": "Наименование заказчика",
    "procedure_type": "Тип процедуры"
  },
  "required_documents": [
    {
      "id": "doc_1",
      "name": "Название документа",
      "mandatory": true,  # Обязательный/опциональный
      "format": "копия",  # Формат предоставления
      "validity": "30 дней",  # Срок действия
      "source_reference": "п.3.5.2.1"  # Ссылка на источник
    }
  ],
  "total_count": 3,  # Общее количество документов
  "analysis_time": 1.23,  # Время анализа в секундах
  "model_size": "small"  # Размер используемой модели
}
```

## Обработка ошибок

```python
result = analyzer.analyze_documentation(doc_text)

if "error" in result:
    if result["error"] == "timeout":
        print("Превышен лимит времени генерации")
    elif result["error"] == "analysis_failed":
        print(f"Ошибка анализа: {result['message']}")
else:
    # Обработка успешного результата
    print(f"Документов: {result['total_count']}")
```

## Параметры генерации

### Для малых моделей (small)

```python
GENERATION_PARAMS_SMALL = {
    "temperature": 0.7,           # Креативность
    "repetition_penalty": 1.4,    # Штраф за повторы (высокий)
    "frequency_penalty": 0.9,     # Штраф за частые токены
    "presence_penalty": 0.7,      # Штраф за присутствие
    "max_tokens": 4096,           # Максимум токенов
    "top_p": 0.9,                 # Nucleus sampling
    "stop_sequences": [           # Стоп-маркеры
        "=== КОНЕЦ СПИСКА ===",
        "51 |"
    ]
}
```

### Для больших моделей (large)

```python
GENERATION_PARAMS_LARGE = {
    "temperature": 0.5,           # Меньше креативности
    "repetition_penalty": 1.2,    # Мягче штрафы
    "max_tokens": 8192,           # Больше токенов
    "top_p": 0.95
}
```

## Тестирование

### Запуск тестов

```bash
# Все тесты
python tests/test_analyzer.py

# С детальным выводом
python tests/test_analyzer.py -v

# Конкретный тест
python -m unittest tests.test_analyzer.TestDocumentAnalyzer.test_deduplication
```

### Покрываемые сценарии

1. **Базовый анализ** - корректность извлечения документов
2. **Дедупликация**:
   - Точные дубликаты
   - Похожие названия
   - Различия в регистре
   - Лишние пробелы
3. **Ограничения**:
   - Лимит количества документов
   - Timeout генерации
4. **Парсинг**:
   - Текстовый формат
   - JSON формат
   - Некорректные данные
5. **Граничные случаи**:
   - Пустой ввод
   - Очень длинные названия
   - Специальные символы
   - Некорректные записи

## Производительность

| Операция | Малая модель (4B) | Большая модель (13B+) |
|----------|-------------------|------------------------|
| Документ 10 стр | 5-10s | 10-20s |
| Документ 50 стр | 15-30s | 30-60s |
| Дедупликация 100 док | 0.1s | 0.1s |
| Парсинг вывода | 0.01s | 0.01s |

## Логирование

```python
import logging

# Включить подробное логирование
logging.basicConfig(level=logging.DEBUG)

# Логи включают:
# - INFO: старт/завершение анализа, статистика
# - DEBUG: детали дедупликации, парсинга
# - WARNING: превышение лимитов, проблемы
# - ERROR: ошибки генерации, парсинга
```

## Расширение функционала

### Добавление нового типа дедупликации

```python
def _deduplicate_by_custom_rule(self, documents: List[Dict]) -> List[Dict]:
    # Ваша логика
    pass

# В методе analyze_documentation:
result["required_documents"] = self._deduplicate_by_custom_rule(
    result["required_documents"]
)
```

### Добавление нового формата вывода

```python
def _get_xml_prompt(self) -> str:
    return """Выведи результат в XML формате..."""

def _parse_xml_output(self, text: str) -> Dict[str, Any]:
    # Парсинг XML
    pass

# В методе analyze_documentation:
if output_format == "xml":
    prompt = self._get_xml_prompt()
    raw_output = self._generate_with_llm(prompt + doc_text)
    result = self._parse_xml_output(raw_output)
```

## Известные ограничения

1. **Timeout работает только на Linux/Unix** (использует `signal.SIGALRM`)
2. **Малые модели** могут пропустить редкие типы документов
3. **Дедупликация** может объединить разные документы с очень похожими названиями
4. **Парсинг** зависит от качества вывода LLM

## Рекомендации

### Для продакшена

1. Используйте модели ≥7B параметров для лучшей точности
2. Настройте логирование для мониторинга
3. Добавьте кэширование результатов анализа
4. Реализуйте очередь задач для массовой обработки
5. Мониторьте метрики:
   - Время анализа
   - Количество timeout'ов
   - Процент дубликатов

### Для разработки

1. Используйте mock-данные для быстрых тестов
2. Тестируйте на реальных документах разных форматов
3. Проверяйте edge cases (см. тесты)
4. Оптимизируйте промпты под вашу специфику

## Поддержка

Для вопросов и предложений:
- GitHub Issues: [OlegKarenkikh/Purchase](https://github.com/OlegKarenkikh/Purchase)
- Документация: [docs/TZ_EXTENDED.md](docs/TZ_EXTENDED.md)

## Лицензия

MIT License - см. LICENSE файл
