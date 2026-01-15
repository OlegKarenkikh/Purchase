# АИС УДЗ - Автоматизированная система управления документами закупок

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)

Интеллектуальная система для автоматизации подготовки, анализа и контроля документации при участии в государственных и коммерческих закупках по 44-ФЗ, 223-ФЗ.

## 🎯 Основные возможности

- **📄 Интеллектуальный парсинг** - извлечение текста из PDF, DOCX, RTF с OCR для сканов
- **🤖 Анализ с помощью LLM** - автоматическое извлечение требований к документам через Claude 3.5
- **✅ Многоэтапный контроль** - автоматическая, юридическая, финансовая и итоговая проверка
- **📦 Формирование пакетов** - автоматический подбор и генерация недостающих документов
- **🔍 Дедупликация** - устранение повторяющихся требований с высокой точностью
- **💾 Централизованное хранилище** - единая база документов компании с контролем сроков
- **📊 Отчеты и аналитика** - детальная статистика по закупкам и документам

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
from src.utils import DocumentParserFactory

# Парсинг документа
parser = DocumentParserFactory.create_parser(
    "procurement.pdf",
    config={"use_ocr": True, "ocr_lang": "rus+eng"}
)
result = parser.parse("procurement.pdf")

# Анализ через LLM
analyzer = DocumentAnalyzer()
analysis = analyzer.analyze(
    document_text=result.text,
    provided_docs=[]
)

print(f"Найдено документов: {len(analysis['required_documents'])}")
print(f"Полнота комплекта: {analysis['document_verification']['completeness_score']}%")
```

#### Пример 2: Полный workflow

```bash
# Запустить полный пример
python examples/example_full_workflow.py
```

Этот пример демонстрирует:
1. Загрузку и парсинг закупочной документации
2. Интеллектуальный анализ требований с помощью LLM
3. Дедупликацию найденных документов
4. Сверку с предоставленными документами
5. Формирование итогового JSON-отчета

**Вывод:**
```
══════════════════════════════════════════════════════════════════════
АВТОМАТИЗИРОВАННАЯ СИСТЕМА УПРАВЛЕНИЯ ДОКУМЕНТАМИ ЗАКУПОК
══════════════════════════════════════════════════════════════════════

📄 ШАГ 1: Загрузка закупочной документации
──────────────────────────────────────────────────────────────────────
✅ Выбран парсер: PDFOCRParser
⏳ Парсинг документа...
✅ Парсинг завершен:
   - Извлечено символов: 45203
   - Извлечено слов: 8431
   - Найдено таблиц: 3
   - Время парсинга: 12.34 сек

🤖 ШАГ 2: Анализ требований с помощью LLM
──────────────────────────────────────────────────────────────────────
⏳ Анализ документации (может занять до 30 сек)...
✅ Анализ завершен

📋 Результаты анализа:
   - Найдено документов: 52
   - После дедупликации: 42
   - Обязательных: 35
   - Опциональных: 7

📄 Топ-5 требуемых документов:
   🔴 1. Выписка из ЕГРЮЛ
      Категория: Регистрационные
      Срок действия: Не старее 30 дней
   🔴 2. Устав организации
      Категория: Регистрационные
   ...

══════════════════════════════════════════════════════════════════════
🎉 ЗАЯВКА ГОТОВА К ПОДАЧЕ
   Полнота комплекта: 100%
══════════════════════════════════════════════════════════════════════
```

#### Пример 3: API

```bash
# Запустить API сервер
uvicorn src.api:app --reload

# Открыть Swagger UI
open http://localhost:8000/docs
```

```python
import requests

# Создать новую закупку
response = requests.post(
    "http://localhost:8000/api/v1/procurements",
    json={"number": "0373200000123000001", "name": "Закупка материалов"}
)
procurement_id = response.json()["id"]

# Анализ документации
response = requests.post(
    f"http://localhost:8000/api/v1/procurements/{procurement_id}/analyze",
    files={"file": open("procurement.pdf", "rb")}
)
analysis = response.json()
print(f"Требуется документов: {len(analysis['required_documents'])}")
```

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                             │
│  Web Browser (React/Next.js)  │  Mobile App (Future)        │
└───────────────────┬─────────────────────────────────────────┘
                    │ HTTPS/TLS 1.3
                    ▼
┌─────────────────────────────────────────────────────────────┐
│              API GATEWAY (Nginx/Kong)                       │
│  Rate Limiting │ Authentication │ Load Balancing           │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│            APPLICATION LAYER                                │
│  FastAPI REST API │ Celery Workers │ WebSocket Server      │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│           BUSINESS LOGIC LAYER                              │
│  Document Parser │ LLM Analyzer │ Package Builder          │
│  Multi-Stage Controller │ Document Registry │ Reports       │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                DATA LAYER                                    │
│  PostgreSQL │ Redis │ MinIO │ Elasticsearch │ RabbitMQ     │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│          EXTERNAL INTEGRATIONS                              │
│  Claude LLM API │ ЕИС API │ DaData API                     │
└─────────────────────────────────────────────────────────────┘
```

Подробнее: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

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
│   ├── parsers/            # Парсеры документов
│   │   ├── pdf_parser.py
│   │   ├── docx_parser.py
│   │   ├── rtf_parser.py
│   │   └── ...
│   ├── utils/              # Утилиты
│   │   ├── deduplicator.py
│   │   ├── cache.py
│   │   └── factory.py
│   ├── analyzer.py         # LLM анализатор
│   └── api.py              # FastAPI приложение
├── examples/               # Примеры использования
│   └── example_full_workflow.py
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

### SLA
- Uptime: 99.5%
- MTTR: < 2 часа

## 🔒 Безопасность

- **Аутентификация**: JWT токены с refresh механизмом
- **Авторизация**: RBAC (5 ролей)
- **Шифрование**: TLS 1.3, bcrypt для паролей, AES-256 для данных
- **Защита от атак**: Rate limiting, CORS, CSRF, XSS, SQL injection
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
**Статус:** Production Ready
