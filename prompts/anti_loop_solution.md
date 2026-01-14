# Решения проблемы зацикливания для малых LLM

## Проблема
Малые модели (4B параметров) склонны к зацикливанию при генерации структурированного JSON вывода, особенно при создании списков документов. Модель начинает бесконечно повторять один и тот же документ.

## Решение 1: Параметры генерации

```python
generation_params = {
    "temperature": 0.7,  # Добавить рандомность
    "repetition_penalty": 1.3,  # Штраф за повторение токенов (1.0-2.0)
    "frequency_penalty": 0.8,  # Штраф пропорционально частоте
    "presence_penalty": 0.6,  # Штраф за уже встречавшиеся токены
    "max_tokens": 4096,  # Жёсткий лимит
    "top_p": 0.9,  # Nucleus sampling
}
```

## Решение 2: Модифицированный промпт

```markdown
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
```

## Решение 3: Constrained Decoding с JSON Schema

```python
from outlines import models, generate

schema = {
    "type": "object",
    "properties": {
        "required_documents": {
            "type": "array",
            "maxItems": 50,  # Жёсткий лимит
            "uniqueItems": True,  # Предотвращает дубликаты
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                },
                "required": ["id", "name"]
            }
        }
    }
}

model = models.transformers("ruadapt/Qwen3-4B", device="cuda")
generator = generate.json(model, schema)
result = generator(prompt)
```

## Решение 4: Двухэтапная обработка

### Этап 1: Извлечение списка (текст)
```
Извлеки из закупочной документации СПИСОК требуемых документов.
Выведи каждый документ ОДИН РАЗ в формате:
- Наименование документа | Раздел

ПРАВИЛА:
- Каждая строка = один уникальный документ
- НЕ повторяй документы
- Максимум 50 строк
- Останови генерацию после 50-го документа
```

### Этап 2: Структурирование (Python)
```python
def deduplicate_documents(raw_output: str) -> dict:
    """Постобработка с дедупликацией"""
    lines = raw_output.strip().split('\n')
    seen_names = set()
    documents = []
    
    for idx, line in enumerate(lines[:50], 1):
        if '|' not in line:
            continue
        name, source = line.split('|', 1)
        name = name.strip().strip('-').strip()
        
        if name in seen_names:
            continue
        seen_names.add(name)
        
        documents.append({
            "id": f"doc_{idx}",
            "name": name,
            "source_reference": source.strip(),
        })
    
    return {"required_documents": documents}
```

## Решение 5: Экстренная постобработка

```python
import json

def fix_duplicates(json_output: str) -> str:
    """Удаляет дубликаты из уже сгенерированного JSON"""
    try:
        data = json.loads(json_output)
    except json.JSONDecodeError:
        # Обрезаем до последнего валидного документа
        json_output = json_output[:json_output.rfind('"},')+2] + ']}'
        data = json.loads(json_output)
    
    # Дедупликация по name
    seen = {}
    unique_docs = []
    
    for doc in data.get("required_documents", []):
        name = doc.get("name", "")
        if name not in seen:
            seen[name] = True
            unique_docs.append(doc)
    
    data["required_documents"] = unique_docs
    return json.dumps(data, ensure_ascii=False, indent=2)
```

## Рекомендация

Для малых моделей (4B) оптимальный подход — **комбинация решений 1+2+5**:

1. Установите `repetition_penalty=1.3-1.5`
2. Добавьте в промпт явное правило: "Максимум 50 документов. После 50-го завершите JSON и остановитесь"
3. Примените постобработку для удаления дубликатов

Если проблема сохраняется, переключитесь на **двухэтапную обработку** (решение 4) — она надёжнее для малых моделей на структурированных задачах.

---

*Документ создан: 14.01.2026*
*Протестировано на: ruadapt-Qwen3-4B, Qwen2.5-4B-Instruct*
