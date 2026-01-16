#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API сервер для системы анализа закупочной документации

FastAPI приложение для обработки запросов на анализ документов.
Реализует REST API согласно документации docs/API.md
"""

import os
import logging
import tempfile
import json
from pathlib import Path
from typing import List, Optional, Dict

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from src.analyzer import DocumentAnalyzer
from src.document_registry import DocumentRegistry
from src.package_builder import PackageBuilder
from src.control import MultiStageController
from src.reports import ReportGenerator
from src.template_library import TemplateLibrary
from src.forms_extractor import FormsExtractor
from src.package_manifest import PackageManifest
from src.readiness_report import ReadinessReport

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация приложения
app = FastAPI(
    title="АИС УДЗ API",
    description="API для анализа закупочной документации",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация компонентов
analyzer = DocumentAnalyzer()
registry = DocumentRegistry()
package_builder = PackageBuilder()
controller = MultiStageController()
report_generator = ReportGenerator()

# Опциональные компоненты (требуют конфигурации)
template_library = None
forms_extractor = None
manifest_builder = PackageManifest()
readiness_reporter = ReadinessReport()


# ===================== Pydantic Models =====================

class AnalysisRequest(BaseModel):
    """Запрос на анализ текста"""
    text: str
    provided_documents: Optional[List[str]] = None


class VerificationRequest(BaseModel):
    """Запрос на сверку документов"""
    required_documents: List[Dict]
    provided_documents: List[str]


class DocumentCreate(BaseModel):
    """Создание документа в реестре"""
    name: str
    category: str
    expiry_date: Optional[str] = None
    tags: Optional[List[str]] = None
    file_path: Optional[str] = None


class RequisitesUpdate(BaseModel):
    """Обновление реквизитов"""
    full_name: str
    short_name: Optional[str] = None
    inn: str
    kpp: Optional[str] = None
    ogrn: Optional[str] = None
    address: Optional[str] = None
    bank_details: Optional[Dict] = None


class ChecklistUpdate(BaseModel):
    """Обновление чек-листа"""
    item_id: str
    checked: bool
    user_id: str
    user_name: str
    comment: Optional[str] = ""


class PackageRequest(BaseModel):
    """Запрос на формирование пакета"""
    procurement_id: str
    required_documents: List[Dict]
    source_files: Optional[Dict[str, str]] = None


# ===================== API Endpoints =====================

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "АИС УДЗ API v2.0",
        "status": "running",
        "endpoints": {
            "api_docs": "/api/docs",
            "web_interface": "/web",
            "health": "/health",
        }
    }


@app.get("/health")
async def health_check():
    """Проверка работоспособности"""
    return {
        "status": "healthy",
        "service": "АИС УДЗ",
        "version": "2.0.0",
        "components": {
            "analyzer": "ready",
            "registry": "ready",
            "controller": "ready",
        }
    }


# ===================== Анализ документации =====================

@app.post("/api/v1/analyze")
async def analyze_text(request: AnalysisRequest):
    """
    Анализ текста закупочной документации

    Извлекает требования к документам из текста КД.
    """
    try:
        logger.info(f"Получен запрос на анализ текста (длина: {len(request.text)} символов)")

        result = analyzer.analyze(
            document_text=request.text,
            provided_docs=request.provided_documents
        )

        return result

    except Exception as e:
        logger.error(f"Ошибка анализа: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/analyze/file")
async def analyze_file(file: UploadFile = File(...)):
    """
    Анализ файла закупочной документации

    Поддерживает: PDF, DOCX, TXT
    """
    try:
        logger.info(f"Получен файл: {file.filename}")

        # Сохранение во временный файл
        suffix = Path(file.filename).suffix if file.filename else ".txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Извлечение текста
            text = analyzer.load_document(tmp_path)

            # Анализ
            result = analyzer.analyze(text)

            return result

        finally:
            # Удаление временного файла
            Path(tmp_path).unlink(missing_ok=True)

    except Exception as e:
        logger.error(f"Ошибка анализа файла: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/verify")
async def verify_documents(request: VerificationRequest):
    """
    Сверка предоставленных документов с требованиями
    """
    try:
        logger.info(f"Сверка {len(request.provided_documents)} документов")

        result = analyzer.verify_documents(
            required=request.required_documents,
            provided=request.provided_documents
        )

        return result

    except Exception as e:
        logger.error(f"Ошибка сверки: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== Реестр документов =====================

@app.get("/api/v1/documents")
async def list_documents(
    category: Optional[str] = None,
    status: Optional[str] = None,
    query: Optional[str] = None
):
    """Получить список документов из реестра"""
    documents = registry.search_documents(
        query=query,
        category=category,
        status=status
    )
    return {"documents": documents, "total": len(documents)}


@app.post("/api/v1/documents")
async def create_document(document: DocumentCreate):
    """Добавить документ в реестр"""
    doc_id = registry.add_document(document.dict())
    return {"id": doc_id, "status": "created"}


@app.get("/api/v1/documents/expiring")
async def get_expiring_documents(days: int = 30):
    """Получить документы с истекающим сроком действия"""
    documents = registry.get_expiring_documents(days)
    return {"documents": documents, "total": len(documents)}


@app.put("/api/v1/requisites")
async def update_requisites(requisites: RequisitesUpdate):
    """Обновить реквизиты организации"""
    registry.set_requisites(requisites.dict())
    return {"status": "updated"}


@app.get("/api/v1/requisites")
async def get_requisites():
    """Получить текущие реквизиты"""
    return registry.get_current_requisites()


# ===================== Многоэтапный контроль =====================

@app.post("/api/v1/control/execute")
async def execute_control(package: Dict):
    """Выполнить многоэтапный контроль пакета"""
    result = controller.execute_full_control(package)
    return result


@app.get("/api/v1/control/checklists")
async def get_all_checklists():
    """Получить все чек-листы контроля"""
    return controller.get_all_checklists()


@app.get("/api/v1/control/checklists/{stage_index}")
async def get_stage_checklist(stage_index: int):
    """Получить чек-лист конкретного этапа"""
    checklist = controller.get_stage_checklist(stage_index)
    return {"stage_index": stage_index, "checklist": checklist}


@app.put("/api/v1/control/checklists/{stage_index}")
async def update_checklist(stage_index: int, update: ChecklistUpdate):
    """Обновить пункт чек-листа"""
    success = controller.update_checklist_item(
        stage_index=stage_index,
        item_id=update.item_id,
        checked=update.checked,
        user_id=update.user_id,
        user_name=update.user_name,
        comment=update.comment or ""
    )
    if not success:
        raise HTTPException(status_code=404, detail="Пункт чек-листа не найден")
    return {"status": "updated"}


@app.get("/api/v1/control/history")
async def get_control_history():
    """Получить историю контроля"""
    return controller.get_control_history()


# ===================== Формирование пакетов =====================

@app.post("/api/v1/packages/match")
async def match_documents(
    required: List[Dict],
    available: Optional[List[Dict]] = None
):
    """Сопоставить требуемые документы с имеющимися"""
    if available is None:
        available = registry.search_documents()

    result = package_builder.match_documents(required, available)
    completeness = package_builder.calculate_completeness(result)

    return {
        "matching": result,
        "completeness": completeness
    }


@app.post("/api/v1/packages/build")
async def build_package(request: PackageRequest):
    """Сформировать пакет документов"""
    try:
        # Создаем опись
        manifest = manifest_builder.create_manifest(
            documents=[],
            requirements=request.required_documents,
            procurement_info={"id": request.procurement_id}
        )

        # Формируем пакет
        result = manifest_builder.build_complete_package(
            manifest=manifest,
            source_files=request.source_files or {},
            procurement_id=request.procurement_id
        )

        return result

    except Exception as e:
        logger.error(f"Ошибка формирования пакета: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== Отчеты =====================

@app.post("/api/v1/reports/readiness")
async def generate_readiness_report(
    manifest: Dict,
    requirements: List[Dict]
):
    """Сгенерировать отчет о готовности пакета"""
    report = readiness_reporter.generate_report(manifest, requirements)
    return report


@app.get("/api/v1/reports/analytics")
async def get_analytics():
    """Получить аналитику"""
    return report_generator.generate_analytics_dashboard()


# ===================== Типовые документы =====================

@app.get("/api/v1/templates")
async def list_templates():
    """Получить список типовых документов"""
    if template_library is None:
        return {"templates": [], "message": "Каталог типовых документов не настроен"}

    templates = template_library.get_all_templates()
    return {"templates": templates, "total": len(templates)}


@app.get("/api/v1/templates/search")
async def search_templates(
    query: str,
    document_type: Optional[str] = None
):
    """Поиск типового документа"""
    if template_library is None:
        return {"results": [], "message": "Каталог типовых документов не настроен"}

    results = template_library.search_template(query, document_type)
    return {"results": results}


@app.get("/api/v1/templates/stats")
async def get_templates_stats():
    """Статистика каталога типовых документов"""
    if template_library is None:
        return {"message": "Каталог типовых документов не настроен"}

    return template_library.get_statistics()


# ===================== Статический контент =====================

# Создаем директорию для веб-интерфейса
WEB_DIR = Path(__file__).parent.parent / "web"
WEB_DIR.mkdir(exist_ok=True)


@app.get("/web", response_class=HTMLResponse)
@app.get("/web/", response_class=HTMLResponse)
async def web_interface():
    """Главная страница веб-интерфейса"""
    index_path = WEB_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding='utf-8')
    else:
        return """
        <html>
        <head><title>АИС УДЗ</title></head>
        <body>
            <h1>АИС УДЗ - Веб-интерфейс</h1>
            <p>Веб-интерфейс не найден. Запустите установку.</p>
            <p><a href="/api/docs">API Documentation</a></p>
        </body>
        </html>
        """


# Монтируем статические файлы если они есть
if (WEB_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")


if __name__ == "__main__":
    import uvicorn

    # Конфигурация через переменные окружения для безопасности
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run(app, host=host, port=port)
