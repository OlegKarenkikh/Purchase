#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API сервер для системы анализа закупочной документации

FastAPI приложение для обработки запросов на анализ документов.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import logging
import tempfile
from pathlib import Path
import json

from analyzer import DocumentAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="АИС УДЗ API",
    description="API для анализа закупочной документации",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация анализатора
analyzer = DocumentAnalyzer()


class AnalysisRequest(BaseModel):
    """Запрос на анализ текста"""
    text: str
    provided_documents: Optional[List[str]] = None


class VerificationRequest(BaseModel):
    """Запрос на сверку документов"""
    required_documents: List[Dict]
    provided_documents: List[str]


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "АИС УДЗ API v1.0",
        "endpoints": [
            "/analyze - Анализ закупочной документации",
            "/analyze/file - Анализ файла",
            "/verify - Сверка документов",
            "/health - Статус сервиса"
        ]
    }


@app.get("/health")
async def health_check():
    """Проверка работоспособности"""
    return {"status": "healthy", "service": "АИС УДЗ"}


@app.post("/analyze")
async def analyze_text(request: AnalysisRequest):
    """
    Анализ текста закупочной документации
    
    Args:
        request: Запрос с текстом документации
        
    Returns:
        Результат анализа в формате JSON
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


@app.post("/analyze/file")
async def analyze_file(file: UploadFile = File(...)):
    """
    Анализ файла закупочной документации
    
    Args:
        file: Загруженный файл (PDF, DOCX, TXT)
        
    Returns:
        Результат анализа в формате JSON
    """
    try:
        logger.info(f"Получен файл: {file.filename}")
        
        # Сохранение во временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
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


@app.post("/verify")
async def verify_documents(request: VerificationRequest):
    """
    Сверка предоставленных документов с требованиями
    
    Args:
        request: Запрос с требуемыми и предоставленными документами
        
    Returns:
        Результат сверки
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
