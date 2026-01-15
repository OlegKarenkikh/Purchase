# API ДОКУМЕНТАЦИЯ

## Обзор

АИС УДЗ предоставляет RESTful API для интеграции с внешними системами и автоматизации процессов работы с закупочной документацией.

**Base URL:** `https://api.purchase-system.example.com`  
**Версия:** v1  
**Формат:** JSON  
**Аутентификация:** JWT Bearer Token

---

## Аутентификация

### POST /api/v1/auth/login

Получение токена доступа.

**Request:**
```json
{
  "username": "user@example.com",
  "password": "securePassword123"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 900
}
```

### POST /api/v1/auth/refresh

Обновление токена доступа.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## Закупки (Procurements)

### GET /api/v1/procurements

Получить список закупок.

**Query Parameters:**
- `page` (integer, default=1) - номер страницы
- `per_page` (integer, default=20, max=100) - количество на странице
- `status` (string) - фильтр по статусу (draft, analyzed, ready, submitted)
- `search` (string) - поиск по номеру или названию

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "number": "0373200000123000001",
      "legal_basis": "44-ФЗ",
      "procedure_type": "Электронный аукцион",
      "customer": "ГКУ Управление капитального строительства",
      "status": "analyzed",
      "created_at": "2026-01-15T10:00:00Z",
      "updated_at": "2026-01-15T10:30:00Z",
      "completeness_score": 85
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 20,
  "pages": 8
}
```

### POST /api/v1/procurements

Создать новую закупку.

**Request:**
```json
{
  "number": "0373200000123000001",
  "name": "Закупка строительных материалов",
  "description": "Описание закупки"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "number": "0373200000123000001",
  "status": "draft",
  "created_at": "2026-01-15T10:00:00Z"
}
```

### GET /api/v1/procurements/{id}

Получить детали закупки.

**Response 200:**
```json
{
  "id": "uuid",
  "number": "0373200000123000001",
  "legal_basis": "44-ФЗ",
  "procedure_type": "Электронный аукцион",
  "customer": "ГКУ Управление капитального строительства",
  "status": "analyzed",
  "required_documents": [
    {
      "id": "doc_001",
      "name": "Выписка из ЕГРЮЛ",
      "category": "Регистрационные",
      "mandatory": true,
      "format": "Заверенная копия",
      "validity_requirements": "Не старее 30 дней",
      "source_reference": "Раздел III.3.4.1, п. 1",
      "implicit": false
    }
  ],
  "completeness_score": 85,
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-01-15T10:30:00Z"
}
```

### POST /api/v1/procurements/{id}/analyze

Анализ документации закупки.

**Request:**
```json
{
  "document_file": "base64_encoded_file",
  "use_cache": true
}
```

**Response 200:**
```json
{
  "procurement_info": {
    "number": "0373200000123000001",
    "legal_basis": "44-ФЗ",
    "procedure_type": "Электронный аукцион",
    "customer": "ГКУ Управление капитального строительства"
  },
  "required_documents": [
    {
      "id": "doc_001",
      "name": "Выписка из ЕГРЮЛ",
      "category": "Регистрационные",
      "mandatory": true,
      "format": "Заверенная копия",
      "validity_requirements": "Не старее 30 дней",
      "source_reference": "Раздел III.3.4.1, п. 1",
      "implicit": false
    }
  ],
  "document_verification": {
    "provided": [],
    "missing_critical": ["doc_001", "doc_002"],
    "missing_optional": [],
    "issues": [],
    "completeness_score": 0
  },
  "critical_warnings": [
    "Отсутствуют критичные документы"
  ],
  "analysis_time": 25.3
}
```

### POST /api/v1/procurements/{id}/generate-package

Сформировать пакет документов.

**Request:**
```json
{
  "participant_name": "ООО Пример",
  "participant_inn": "7712345678",
  "include_optional": false
}
```

**Response 200:**
```json
{
  "package_id": "uuid",
  "total_documents": 25,
  "generated_documents": 5,
  "existing_documents": 20,
  "download_url": "/api/v1/packages/uuid/download",
  "expires_at": "2026-01-16T10:00:00Z"
}
```

---

## Документы (Documents)

### POST /api/v1/documents/upload

Загрузить документ.

**Request:** multipart/form-data
- `file` - файл документа
- `category` - категория документа
- `name` - название (опционально)

**Response 201:**
```json
{
  "id": "uuid",
  "filename": "document.pdf",
  "size": 1024000,
  "mime_type": "application/pdf",
  "category": "Регистрационные",
  "uploaded_at": "2026-01-15T10:00:00Z",
  "url": "/api/v1/documents/uuid"
}
```

### GET /api/v1/documents/{id}

Получить документ.

**Response 200:**
```json
{
  "id": "uuid",
  "filename": "document.pdf",
  "size": 1024000,
  "mime_type": "application/pdf",
  "category": "Регистрационные",
  "name": "Выписка из ЕГРЮЛ",
  "validity_start": "2026-01-10",
  "validity_end": "2027-01-10",
  "uploaded_at": "2026-01-15T10:00:00Z",
  "download_url": "/api/v1/documents/uuid/download"
}
```

---

## Коды ответов

| Код | Описание |
|-----|----------|
| 200 | OK - Успешный запрос |
| 201 | Created - Ресурс создан |
| 204 | No Content - Успешно, нет содержимого |
| 400 | Bad Request - Неверный запрос |
| 401 | Unauthorized - Требуется аутентификация |
| 403 | Forbidden - Доступ запрещен |
| 404 | Not Found - Ресурс не найден |
| 422 | Unprocessable Entity - Ошибка валидации |
| 429 | Too Many Requests - Превышен лимит запросов |
| 500 | Internal Server Error - Ошибка сервера |
| 503 | Service Unavailable - Сервис недоступен |

## Формат ошибок

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {
        "field": "inn",
        "message": "Invalid INN format"
      }
    ],
    "timestamp": "2026-01-15T10:00:00Z",
    "request_id": "req_abc123"
  }
}
```

---

## Rate Limiting

- Анонимные запросы: 10 req/min
- Аутентифицированные: 100 req/min
- Premium: 1000 req/min

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642252800
```

---

*Версия API: v1*  
*Последнее обновление: 15.01.2026*
