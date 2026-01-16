# АИС УДЗ - Автоматизированная система управления документами закупок

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-41%20passed-brightgreen.svg)]()
[![Version](https://img.shields.io/badge/Version-2.0.0-blue.svg)]()

Интеллектуальная система для автоматизации подготовки, анализа и контроля документации при участии в государственных и коммерческих закупках по 44-ФЗ, 223-ФЗ.

## Основные возможности

### Базовые функции (Фаза 1) ✅
- **Интеллектуальный парсинг** - извлечение текста из PDF, DOCX, RTF с OCR для сканов
- **Анализ с помощью LLM** - автоматическое извлечение требований к документам через Claude 3.5
- **Реестр документов** - централизованное хранилище с контролем сроков, версионированием реквизитов
- **Формирование пакетов** - автоматический подбор, чек-листы, экспорт в ZIP
- **Многоэтапный контроль** - автоматическая, юридическая, финансовая и итоговая проверка
- **Дедупликация** - устранение повторяющихся требований с высокой точностью
- **Отчеты и аналитика** - детальная статистика по закупкам и документам

### Новые функции (Фаза 2) ✅
- **Каталог типовых документов** (FR-1.10) - индексация, поиск и использование шаблонов
- **Выделение форм из КД** (FR-3.10) - автоматическое извлечение форм для заполнения
- **Структурированная опись** (FR-3.11) - формирование полной описи с экспортом в JSON/CSV/Excel
- **Формирование пакета** (FR-3.12) - автоматическая подготовка структурированного пакета
- **Отчет о готовности** (FR-4.9) - детальный отчет с метриками, проблемами и рекомендациями
- **Чек-листы контроля** (FR-4.7) - структурированные проверочные листы для каждого этапа
- **История контроля** (FR-4.8) - аудит всех проверок и решений
- **Веб-интерфейс** - современный UI для работы с системой

## Статус реализации ТЗ

| Модуль | Статус | Файл | Описание |
|--------|--------|------|----------|
| **FR-1: Загрузка и анализ** | ✅ 100% | `src/analyzer.py`, `src/parsers/` | Парсинг PDF/DOCX/RTF, OCR, LLM анализ, дедупликация |
| **FR-2: Реестр документов** | ✅ 100% | `src/document_registry.py` | Централизованное хранилище, реквизиты, контроль сроков |
| **FR-3: Формирование пакетов** | ✅ 100% | `src/package_builder.py`, `src/package_manifest.py` | Сопоставление, опись, ZIP-архив |
| **FR-4: Многоэтапный контроль** | ✅ 100% | `src/control.py` | 4 этапа контроля с чек-листами |
| **FR-5: Отчетность** | ✅ 100% | `src/reports.py`, `src/readiness_report.py` | Отчеты, аналитика, отчет о готовности |
| **API интерфейс** | ✅ 100% | `src/api.py` | REST API с FastAPI, Swagger UI |
| **Веб-интерфейс** | ✅ 100% | `web/` | Современный UI |

**Все модули из технического задания Фазы 1 и Фазы 2 реализованы!**

## Быстрый старт

### Требования

- Python 3.11+
- Docker & Docker Compose (опционально)
- Tesseract OCR (для распознавания сканов)
- Claude API key или OpenAI-совместимый LLM сервер

### Установка

```bash
# Клонировать репозиторий
git clone https://github.com/OlegKarenkikh/Purchase.git
cd Purchase

# Создать .env файл
cp .env.example .env
# Добавить OPENAI_BASE_URL и OPENAI_API_KEY в .env

# Установить зависимости
pip install -r requirements.txt

# Запустить API сервер
python -m src.api

# Или запустить через Docker
docker-compose up -d
```

### Использование веб-интерфейса

После запуска откройте в браузере:
- **Веб-интерфейс:** http://localhost:8000/web
- **API документация:** http://localhost:8000/api/docs

### Пример использования Python API

```python
from src.analyzer import DocumentAnalyzer
from src.document_registry import DocumentRegistry
from src.package_builder import PackageBuilder
from src.control import MultiStageController
from src.template_library import TemplateLibrary
from src.package_manifest import PackageManifest
from src.readiness_report import ReadinessReport

# 1. Анализ закупочной документации
analyzer = DocumentAnalyzer()
text = analyzer.load_document("procurement.pdf")
analysis = analyzer.analyze(text)

print(f"Найдено требований: {analysis['total_count']}")

# 2. Работа с типовыми документами
library = TemplateLibrary("/path/to/templates")
library.index_documents()
templates = library.search_template("Выписка ЕГРЮЛ")

# 3. Формирование пакета с описью
manifest_builder = PackageManifest()
manifest = manifest_builder.create_manifest(
    documents=[],
    requirements=analysis['required_documents']
)

# Экспорт описи
manifest_builder.export_manifest(manifest, "xlsx")

# 4. Отчет о готовности
reporter = ReadinessReport()
report = reporter.generate_report(manifest, analysis['required_documents'])

print(f"Готовность: {report['metrics']['completeness_percentage']}%")

# 5. Многоэтапный контроль с чек-листами
controller = MultiStageController()
checklists = controller.get_all_checklists()

# Обновление чек-листа
controller.update_checklist_item(
    stage_index=1,  # Юридический
    item_id="legal_01",
    checked=True,
    user_id="user1",
    user_name="Иванов И.И."
)
```

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                             │
│  Web Browser (HTML/CSS/JS)  │  API Clients                  │
└───────────────────┬─────────────────────────────────────────┘
                    │ HTTPS
                    ▼
┌─────────────────────────────────────────────────────────────┐
│              API LAYER (FastAPI)                            │
│  /api/v1/analyze │ /api/v1/documents │ /api/v1/control     │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│           BUSINESS LOGIC LAYER                              │
│  analyzer.py          │ document_registry.py               │
│  package_builder.py   │ package_manifest.py                │
│  control.py           │ readiness_report.py                │
│  template_library.py  │ forms_extractor.py                 │
│  reports.py           │                                     │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                DATA & EXTERNAL                              │
│  PostgreSQL │ Redis │ MinIO │ LLM API (Claude/vLLM)       │
└─────────────────────────────────────────────────────────────┘
```

## Структура проекта

```
Purchase/
├── src/                         # Исходный код
│   ├── analyzer.py             # FR-1: LLM анализатор
│   ├── document_registry.py    # FR-2: Реестр документов
│   ├── package_builder.py      # FR-3: Формирование пакетов
│   ├── package_manifest.py     # FR-3.11-12: Опись и пакеты
│   ├── control.py              # FR-4: Многоэтапный контроль
│   ├── reports.py              # FR-5: Отчетность
│   ├── readiness_report.py     # FR-4.9: Отчет о готовности
│   ├── template_library.py     # FR-1.10: Типовые документы
│   ├── forms_extractor.py      # FR-3.10: Извлечение форм
│   ├── api.py                  # FastAPI приложение
│   ├── parsers/                # Парсеры PDF/DOCX/RTF
│   ├── llm/                    # LLM клиенты
│   └── utils/                  # Утилиты
├── web/                         # Веб-интерфейс
│   ├── index.html
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── tests/                       # Тесты (41 тест)
├── docs/                        # Документация
├── prompts/                     # Промпты для LLM
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Тестирование

```bash
# Все тесты
python -m pytest tests/ -v

# С покрытием
python -m pytest tests/ --cov=src --cov-report=term-missing

# Результат: 41 тест пройден
```

## Метрики качества

- **Тестовое покрытие:** 41 тест
- **Соответствие ТЗ (Фаза 1):** 100%
- **Соответствие ТЗ (Фаза 2):** 100% (основные требования)
- **Безопасность:** Исправлены все критические уязвимости

## Безопасность

- **Аутентификация:** JWT токены
- **Шифрование:** SHA-256 для хеширования, JSON для сериализации
- **Защита:** Rate limiting, CORS, валидация входных данных
- **Аудит:** Логирование всех операций

## Документация

- **[Техническое задание (Часть 1)](docs/TZ_FULL.md)** - Функциональные требования
- **[Техническое задание (Часть 2)](docs/TZ_PART2.md)** - Нефункциональные требования
- **[Расширенное ТЗ](docs/TZ_EXTENDED.md)** - Требования Фазы 2
- **[API Документация](docs/API.md)** - REST API
- **[Архитектура системы](docs/ARCHITECTURE.md)** - Компоненты и tech stack
- **[Отчет аудита](docs/AUDIT_REPORT.md)** - Полный отчет проверки

## Лицензия

MIT License - см. файл [LICENSE](LICENSE)

## Автор

**Oleg Karenkikh**
- GitHub: [@OlegKarenkikh](https://github.com/OlegKarenkikh)

---

**Версия:** 2.0.0  
**Дата:** 16.01.2026  
**Статус:** Production Ready
