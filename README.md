# АИС УДЗ - Автоматизированная система управления документами закупок

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)]()

Интеллектуальная система для автоматизации подготовки, анализа и контроля документации при участии в государственных и коммерческих закупках по 44-ФЗ, 223-ФЗ.

## 🎯 Основные возможности

- **📄 Интеллектуальный парсинг** - извлечение текста из PDF, DOCX, RTF с OCR для сканов
- **🤖 Анализ с помощью LLM** - автоматическое извлечение требований к документам через Claude 3.5
- **🗃️ Реестр документов** - централизованное хранилище с контролем сроков, версионированием реквизитов
- **📦 Формирование пакетов** - автоматический подбор, чек-листы, экспорт в ZIP
- **✅ Многоэтапный контроль** - автоматическая, юридическая, финансовая и итоговая проверка
- **🔍 Дедупликация** - устранение повторяющихся требований с высокой точностью
- **📊 Отчеты и аналитика** - детальная статистика по закупкам и документам

## 📋 Статус реализации ТЗ

| Модуль | Статус | Файл | Описание |
|--------|--------|------|------------|
| **FR-1: Загрузка и анализ** | ✅ | `src/analyzer.py`<br>`src/parsers/` | Парсинг PDF/DOCX/RTF, OCR, LLM анализ, дедупликация |
| **FR-2: Реестр документов** | ✅ | `src/document_registry.py` | Централизованное хранилище, реквизиты, контроль сроков, поиск |
| **FR-3: Формирование пакетов** | ✅ | `src/package_builder.py` | Сопоставление, чек-листы, расчет полноты, экспорт |
| **FR-4: Многоэтапный контроль** | ✅ | `src/control.py` | 4 этапа: автоматический, юридический, финансовый, итоговый |
| **FR-5: Отчетность** | ✅ | `src/reports.py` | Отчеты по закупкам, отклонениям, срокам, аналитика |
| **API интерфейс** | ✅ | `src/api.py` | REST API с FastAPI, Swagger UI |

**🎉 Все 5 основных модулей из технического задания полностью реализованы!**

## 📚 Документация

- **[Техническое задание (Часть 1)](docs/TZ_FULL.md)** - Функциональные требования FR-1 — FR-5
- **[Техническое задание (Часть 2)](docs/TZ_PART2.md)** - Нефункциональные требования, план разработки, критерии приемки
- **[API Документация](docs/API.md)** - REST API эндпоинты, форматы запросов/ответов, примеры
- **[Архитектура системы](docs/ARCHITECTURE.md)** - Компоненты, tech stack, безопасность, масштабирование

## 🚀 Быстрый старт

### Требования

- Python 3.11+
- Docker & Docker Compose
- Tesseract OCR (для распознавания сканов)
- Claude API key (для LLM анализа)

### Установка

```bash
# Клонировать репозиторий
git clone https://github.com/OlegKarenkikh/Purchase.git
cd Purchase

# Создать .env файл
cp .env.example .env
# Добавить ANTHROPIC_API_KEY в .env

# Установить зависимости
pip install -r requirements.txt

# Или запустить через Docker
docker-compose up -d
```

### Использование

#### Пример 1: Базовый анализ документации

```python
from src.analyzer import DocumentAnalyzer
from src.document_registry import DocumentRegistry
from src.package_builder import PackageBuilder
from src.control import MultiStageController
from src.reports import ReportGenerator
from src.utils import DocumentParserFactory

# 1. Парсинг документа
parser = DocumentParserFactory.create_parser(
    "procurement.pdf",
    config={"use_ocr": True, "ocr_lang": "rus+eng"}
)
result = parser.parse("procurement.pdf")

# 2. Анализ через LLM
analyzer = DocumentAnalyzer()
analysis = analyzer.analyze(
    document_text=result.text,
    provided_docs=[]
)

# 3. Работа с реестром
registry = DocumentRegistry()
for doc in my_company_documents:
    registry.add_document(doc)

# 4. Формирование пакета
builder = PackageBuilder()
matching = builder.match_documents(
    required=analysis['required_documents'],
    available=registry.search_documents()
)
package_path = builder.build_package(
    procurement_id="0373200000123000001",
    matched_documents=matching['matched']
)

# 5. Многоэтапный контроль
controller = MultiStageController()
control_result = controller.execute_full_control({
    "documents": matching['matched'],
    "required_documents": analysis['required_documents']
})

print(f"Статус: {control_result['overall_status']}")
print(f"Пакет: {package_path}")
```

## 🏭 Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                             │
│  Web Browser (React/Next.js)  │  Mobile App (Future)        │
└───────────────────┬──────────────────────────────────────────┘
                    │ HTTPS/TLS 1.3
                    ▼
┌─────────────────────────────────────────────────────────────┐
│              API GATEWAY (Nginx/Kong)                       │
│  Rate Limiting │ Authentication │ Load Balancing           │
└───────────────────┬──────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│            APPLICATION LAYER                                │
│  FastAPI REST API │ Celery Workers │ WebSocket Server      │
└───────────────────┬──────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│           BUSINESS LOGIC LAYER                              │
│  FR-1: analyzer.py + parsers/     (LLM анализ)           │
│  FR-2: document_registry.py       (Реестр)              │
│  FR-3: package_builder.py         (Пакеты)              │
│  FR-4: control.py                 (Контроль)             │
│  FR-5: reports.py                 (Отчеты)              │
└───────────────────┬──────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                DATA LAYER                                    │
│  PostgreSQL │ Redis │ MinIO │ Elasticsearch │ RabbitMQ     │
└───────────────────┬──────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│          EXTERNAL INTEGRATIONS                              │
│  Claude LLM API │ ЕИС API │ DaData API                     │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Технологический стек

### Backend
- **Python 3.11+** - основной язык
- **FastAPI** - современный асинхронный веб-фреймворк
- **SQLAlchemy 2.0** - ORM для работы с БД
- **Celery** - распределенная очередь задач
- **Pydantic** - валидация данных

### ML/AI
- **Claude 3.5 Sonnet** - анализ документации через API
- **Tesseract OCR** - распознавание текста со сканов
- **PyPDF2** - парсинг PDF документов
- **python-docx** - работа с DOCX

### Хранилище данных
- **PostgreSQL 14+** - основная БД
- **Redis 7.0+** - кэш и очереди
- **MinIO** - объектное хранилище файлов (S3-compatible)
- **Elasticsearch 8.0+** - полнотекстовый поиск (опционально)

### DevOps
- **Docker** - контейнеризация
- **GitHub Actions** - CI/CD
- **Nginx** - reverse proxy
- **Prometheus + Grafana** - мониторинг

## 📁 Структура проекта

```
Purchase/
├── docs/                    # Документация
│   ├── TZ_FULL.md          # ТЗ часть 1 (функциональные требования)
│   ├── TZ_PART2.md         # ТЗ часть 2 (NFR, план, приемка)
│   ├── API.md              # REST API документация
│   └── ARCHITECTURE.md     # Архитектура системы
├── src/                     # Исходный код
│   ├── analyzer.py         # FR-1: LLM анализатор
│   ├── document_registry.py # FR-2: Реестр документов
│   ├── package_builder.py  # FR-3: Формирование пакетов
│   ├── control.py          # FR-4: Многоэтапный контроль
│   ├── reports.py          # FR-5: Отчетность
│   ├── api.py              # FastAPI приложение
│   ├── parsers/            # Парсеры PDF/DOCX/RTF
│   ├── utils/              # Утилиты
│   ├── llm/                # LLM клиент
│   └── models/             # Модели данных
├── examples/               # Примеры использования
├── prompts/                # Промпты для LLM
├── tests/                  # Тесты
├── docker-compose.yml      # Docker конфигурация
├── requirements.txt        # Python зависимости
└── README.md              # Этот файл
```

## 🧪 Тестирование

```bash
# Unit тесты
pytest tests/unit/

# Integration тесты
pytest tests/integration/

# Все тесты с coverage
pytest --cov=src tests/

# E2E тесты
pytest tests/e2e/
```

## 📈 Метрики и мониторинг

### Производительность
- Анализ документации: < 30 сек (до 50 страниц)
- OCR одной страницы: < 3 сек
- Формирование пакета: < 10 сек
- API response time: p95 < 200ms

### Качество
- Code coverage: ≥ 80%
- Точность OCR: ≥ 95%
- Точность извлечения требований: ≥ 90%

## 🔒 Безопасность

- **Аутентификация**: JWT токены с refresh механизмом
- **Авторизация**: RBAC (5 ролей)
- **Шифрование**: TLS 1.3, bcrypt для паролей, AES-256 для данных
- **Защита**: Rate limiting, CORS, CSRF, XSS, SQL injection
- **Аудит**: Логирование всех действий (3 года хранения)

## 🤝 Вклад в проект

1. Fork репозитория
2. Создать feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменений (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Открыть Pull Request

## 📝 Лицензия

MIT License - см. файл [LICENSE](LICENSE)

## 👨‍💻 Автор

**Oleg Karenkikh**
- GitHub: [@OlegKarenkikh](https://github.com/OlegKarenkikh)
- Email: oleg@karenkikh.ru

## 🙏 Благодарности

- [Anthropic](https://www.anthropic.com/) - за Claude API
- [FastAPI](https://fastapi.tiangolo.com/) - за отличный фреймворк
- Сообщество разработчиков open-source

---

**Версия:** 1.0  
**Дата:** 15.01.2026  
**Статус:** Production Ready 🎉
