#!/usr/bin/env python3
"""
Анализатор закупочной документации с поддержкой LLM

Основные возможности:
- Извлечение требований к документам
- Защита от зацикливания для малых моделей (4B-7B)
- Автоматическая дедупликация результатов
- Поддержка разных форматов вывода (JSON/текст)

Автор: Система УДЗ
Версия: 2.0
Дата: 2026-01-15
"""

import json
import re
import signal
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Исключение при превышении времени генерации"""
    pass


class DocumentAnalyzer:
    """
    Анализатор закупочной документации с защитой от зацикливания
    """
    
    # Константы
    MAX_DOCUMENTS = 50  # Максимальное количество документов
    GENERATION_TIMEOUT = 120  # Тайм-аут генерации в секундах
    SIMILARITY_THRESHOLD = 0.85  # Порог сходства для дубликатов
    
    # Параметры генерации для малых моделей
    GENERATION_PARAMS_SMALL = {
        "temperature": 0.7,
        "repetition_penalty": 1.4,  # Высокий штраф за повторы
        "frequency_penalty": 0.9,
        "presence_penalty": 0.7,
        "max_tokens": 4096,
        "top_p": 0.9,
        "stop_sequences": ["=== КОНЕЦ СПИСКА ===", "51 |"]  # Остановка после 50-го
    }
    
    # Параметры для больших моделей
    GENERATION_PARAMS_LARGE = {
        "temperature": 0.5,
        "repetition_penalty": 1.2,
        "max_tokens": 8192,
        "top_p": 0.95,
    }
    
    def __init__(self, llm_client: Any = None, model_size: str = "small"):
        """
        Инициализация анализатора
        
        Args:
            llm_client: Клиент для работы с LLM
            model_size: Размер модели ('small' для 4B-7B, 'large' для >7B)
        """
        self.llm_client = llm_client
        self.model_size = model_size
        self.generation_params = (
            self.GENERATION_PARAMS_SMALL if model_size == "small" 
            else self.GENERATION_PARAMS_LARGE
        )
        logger.info(f"Analyzer initialized with model_size={model_size}")
    
    def _timeout_handler(self, signum, frame):
        """Обработчик timeout'а"""
        raise TimeoutError("LLM generation exceeded timeout limit")
    
    def analyze_documentation(self, doc_text: str, 
                            output_format: str = "text") -> Dict[str, Any]:
        """
        Анализировать закупочную документацию
        
        Args:
            doc_text: Текст документации
            output_format: Формат вывода ('text' или 'json')
        
        Returns:
            Структурированные данные о требуемых документах
        """
        logger.info(f"Starting analysis of {len(doc_text)} characters")
        start_time = time.time()

        if not doc_text.strip():
            return {
                "procurement_info": {},
                "required_documents": [],
                "total_count": 0,
                "analysis_time": 0,
                "model_size": self.model_size,
            }
        
        try:
            # Установка timeout
            signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(self.GENERATION_TIMEOUT)
            
            # Выбор промпта в зависимости от формата
            if output_format == "text" or self.model_size == "small":
                prompt = self._get_text_prompt()
                raw_output = self._generate_with_llm(prompt + "\n\n" + doc_text)
                result = self._parse_text_output(raw_output)
            else:
                prompt = self._get_json_prompt()
                raw_output = self._generate_with_llm(prompt + "\n\n" + doc_text)
                result = self._parse_json_output(raw_output)
            
            # Отмена timeout
            signal.alarm(0)
            
            # Дедупликация
            result["required_documents"] = self._deduplicate_documents(
                result.get("required_documents", [])
            )
            
            # Ограничение количества
            if len(result["required_documents"]) > self.MAX_DOCUMENTS:
                logger.warning(
                    f"Truncating documents from {len(result['required_documents'])} "
                    f"to {self.MAX_DOCUMENTS}"
                )
                result["required_documents"] = result["required_documents"][:self.MAX_DOCUMENTS]
            
            # Добавление метаданных
            result["total_count"] = len(result["required_documents"])
            result["analysis_time"] = round(time.time() - start_time, 2)
            result["model_size"] = self.model_size
            
            logger.info(
                f"Analysis completed: {result['total_count']} documents "
                f"in {result['analysis_time']}s"
            )
            
            return result
            
        except TimeoutError as e:
            signal.alarm(0)
            logger.error(f"Generation timeout: {e}")
            return {
                "error": "timeout",
                "message": str(e),
                "required_documents": []
            }
        except Exception as e:
            signal.alarm(0)
            logger.error(f"Analysis error: {e}", exc_info=True)
            return {
                "error": "analysis_failed",
                "message": str(e),
                "required_documents": []
            }
    
    def _generate_with_llm(self, prompt: str) -> str:
        """
        Генерация с помощью LLM
        
        Args:
            prompt: Промпт для модели
        
        Returns:
            Сгенерированный текст
        """
        if self.llm_client is None:
            # Для тестов - заглушка
            logger.warning("No LLM client provided, returning mock data")
            return self._get_mock_output()
        
        # Реальная генерация с параметрами
        return self.llm_client.generate(
            prompt=prompt,
            **self.generation_params
        )
    
    def _deduplicate_documents(self, documents: List[Dict]) -> List[Dict]:
        """
        Удаление дубликатов по названию
        
        Args:
            documents: Список документов
        
        Returns:
            Уникальные документы
        """
        seen = {}
        unique = []
        
        for doc in documents:
            if not isinstance(doc, dict) or "name" not in doc:
                continue
            
            # Нормализация названия
            name_normalized = doc["name"].lower().strip()
            name_normalized = re.sub(r'\s+', ' ', name_normalized)  # Удаление лишних пробелов

            if not name_normalized:
                continue
            
            # Проверка точного совпадения
            if name_normalized in seen:
                logger.debug(f"Exact duplicate found: {doc['name']}")
                continue
            
            # Проверка на похожие названия
            is_similar = False
            for existing_name in seen.keys():
                similarity = SequenceMatcher(None, name_normalized, existing_name).ratio()
                if similarity > self.SIMILARITY_THRESHOLD:
                    logger.debug(
                        f"Similar duplicate found: '{doc['name']}' ~ '{seen[existing_name]['name']}' "
                        f"(similarity: {similarity:.2f})"
                    )
                    is_similar = True
                    break
            
            if not is_similar:
                seen[name_normalized] = doc
                unique.append(doc)
        
        logger.info(f"Deduplication: {len(documents)} -> {len(unique)} documents")
        return unique
    
    def _get_text_prompt(self) -> str:
        """
        Промпт для текстового вывода (оптимизирован для малых моделей)
        """
        return """# РОЛЬ И КОНТЕКСТ
Ты - система извлечения требуемых документов из закупочной документации.

# КРИТИЧЕСКИЕ ПРАВИЛА (ОБЯЗАТЕЛЬНЫ!)
1. МАКСИМУМ 30 документов в списке
2. ОДИН документ = ОДНА строка
3. ПОСЛЕ 30-й строки - НЕМЕДЛЕННО ОСТАНОВ
4. НЕ ПОВТОРЯЙ документы с одинаковым названием
5. Если видишь дубликат - ПРОПУСТИ его

# ФОРМАТ ВЫВОДА (только текст, БЕЗ JSON)

=== ИНФОРМАЦИЯ О ЗАКУПКЕ ===
Номер: [извлечь]
Заказчик: [извлечь]
Тип процедуры: [извлечь]

=== СПИСОК ДОКУМЕНТОВ (макс. 30) ===

[Каждый документ в формате:]
№ | Название | Обязательный | Формат | Срок действия | Раздел

[Пример:]
1 | Выписка из ЕГРЮЛ | Да | Копия | Не ранее 30 дней | п.3.5.2.1
2 | Устав | Да | Копия | Без ограничений | п.3.5.2.2

# АЛГОРИТМ РАБОТЫ

ШАГ 1: Найди в тексте разделы с требованиями
Ищи фразы: "состав заявки", "требования к заявке", "документы участника", "необходимые документы"

ШАГ 2: Извлекай документы построчно
Для каждого найденного документа:
- Проверь: уже есть в списке?
  - ЕСЛИ ДА → пропусти
  - ЕСЛИ НЕТ → добавь новую строку
- Счетчик достиг 30?
  - ЕСЛИ ДА → ОСТАНОВ, выведи "=== КОНЕЦ СПИСКА ==="
  - ЕСЛИ НЕТ → продолжай

ШАГ 3: Завершение
После обработки всех разделов ИЛИ достижения лимита 30 выведи:
=== КОНЕЦ СПИСКА ===
Всего документов: [число]

# ПРИМЕРЫ ДОКУМЕНТОВ (для понимания типов)

Регистрационные:
- Выписка из ЕГРЮЛ/ЕГРИП
- Устав
- Свидетельство о регистрации

Финансовые:
- Бухгалтерская отчётность
- Справка об отсутствии задолженности (ФНС, ПФР, ФСС)

Специальные:
- Лицензии
- Членство СРО
- Сертификаты

Кадровые и опыт:
- Сведения о специалистах
- Реестр выполненных контрактов

# ВАЖНО
- НЕ изобретай документы
- НЕ добавляй "стандартные" документы, если их нет в тексте
- Если документ упомянут 10 раз - добавь ОДИН раз

# ТЕКСТ ЗАКУПОЧНОЙ ДОКУМЕНТАЦИИ:
"""
    
    def _get_json_prompt(self) -> str:
        """
        Промпт для JSON-вывода (для больших моделей)
        """
        return """# РОЛЬ
Ты - специализированная система анализа закупочной документации.

# ЗАДАЧА
Извлечь полный перечень документов, требуемых для подачи заявки.

# КРИТИЧЕСКИЕ ПРАВИЛА
1. Максимум 50 документов
2. ЗАПРЕЩЕНО добавлять документы с одинаковыми названиями
3. После 50-го остановите генерацию и завершите JSON
4. НЕ добавляйте "стандартные" документы, которых нет в тексте

# ФОРМАТ ВЫВОДА
Верни JSON:
```json
{
  "procurement_info": {
    "number": "...",
    "customer": "...",
    "procedure_type": "..."
  },
  "required_documents": [
    {
      "id": "doc_1",
      "name": "Название документа",
      "mandatory": true,
      "format": "копия",
      "validity": "Срок действия",
      "source_reference": "Раздел"
    }
  ]
}
```

# ТЕКСТ ЗАКУПОЧНОЙ ДОКУМЕНТАЦИИ:
"""
    
    def _parse_text_output(self, text: str) -> Dict[str, Any]:
        """
        Парсинг текстового вывода
        
        Args:
            text: Текстовый вывод LLM
        
        Returns:
            Структурированные данные
        """
        lines = text.split('\n')
        documents = []
        procurement_info = {}
        
        for line in lines:
            line = line.strip()
            
            # Извлечение информации о закупке
            if "Номер:" in line:
                procurement_info["number"] = line.split(":", 1)[1].strip()
            elif "Заказчик:" in line:
                procurement_info["customer"] = line.split(":", 1)[1].strip()
            elif "Тип процедуры:" in line:
                procurement_info["procedure_type"] = line.split(":", 1)[1].strip()
            
            # Парсинг строки с документом
            if "|" in line and not any(x in line for x in ["Название", "==="]):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2:
                    try:
                        doc_num = parts[0].replace("№", "").strip()
                        if doc_num.isdigit():
                            documents.append({
                                "id": f"doc_{len(documents) + 1}",
                                "name": parts[1],
                                "mandatory": "да" in parts[2].lower() if len(parts) > 2 else True,
                                "format": parts[3] if len(parts) > 3 else "Копия",
                                "validity": parts[4] if len(parts) > 4 else None,
                                "source_reference": parts[5] if len(parts) > 5 else "Не указано"
                            })
                    except (IndexError, ValueError) as e:
                        logger.debug(f"Failed to parse line: {line}, error: {e}")
                        continue
            
            # Остановка по маркеру
            if "КОНЕЦ СПИСКА" in line:
                break
        
        return {
            "procurement_info": procurement_info,
            "required_documents": documents
        }
    
    def _parse_json_output(self, text: str) -> Dict[str, Any]:
        """
        Парсинг JSON-вывода
        
        Args:
            text: JSON-строка
        
        Returns:
            Структурированные данные
        """
        try:
            # Попытка прямого парсинга
            return json.loads(text)
        except json.JSONDecodeError:
            # Поиск JSON в тексте
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Обрезка до последнего валидного документа
            last_bracket = text.rfind('"}')
            if last_bracket != -1:
                truncated = text[:last_bracket+2] + ']}'
                try:
                    return json.loads(truncated)
                except json.JSONDecodeError:
                    pass
            
            logger.error("Failed to parse JSON output")
            return {
                "procurement_info": {},
                "required_documents": []
            }
    
    def _get_mock_output(self) -> str:
        """
        Мок-вывод для тестирования
        """
        return """=== ИНФОРМАЦИЯ О ЗАКУПКЕ ===
Номер: 39-ЗЦ/2025
Заказчик: АНО «Институт развития интернета»
Тип процедуры: Запрос цен

=== СПИСОК ДОКУМЕНТОВ (макс. 30) ===

1 | Выписка из ЕГРЮЛ | Да | Копия | Не ранее 30 дней | п.3.5.2.1
2 | Устав | Да | Копия | Без ограничений | п.3.5.2.2
3 | Справка об отсутствии задолженности ФНС | Да | Копия | Не ранее 30 дней | п.3.5.2.3

=== КОНЕЦ СПИСКА ===
Всего документов: 3
"""


if __name__ == "__main__":
    # Пример использования
    analyzer = DocumentAnalyzer(model_size="small")
    
    # Тестовый документ
    test_doc = """
    Закупка № 39-ЗЦ/2025
    Заказчик: АНО «Институт развития интернета»
    
    Требования к заявке:
    - Выписка из ЕГРЮЛ (не ранее 30 дней)
    - Устав
    - Справки об отсутствии задолженности (ФНС, ПФР, ФСС)
    """
    
    result = analyzer.analyze_documentation(test_doc)
    print(json.dumps(result, ensure_ascii=False, indent=2))
