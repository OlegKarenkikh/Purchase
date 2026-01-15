#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль анализа закупочной документации

Использует LLM для извлечения требований к документам из закупочной документации.
Поддерживает работу через OpenAI-совместимый API (vLLM).
"""

import os
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
import PyPDF2
import docx

from src.llm.client import OpenAILikeClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentAnalyzer:
    """
    Анализатор закупочной документации с использованием LLM
    """

    def __init__(self, llm_client: Optional[OpenAILikeClient] = None):
        """
        Инициализация анализатора
        
        Args:
            llm_client: Клиент LLM (по умолчанию OpenAILikeClient из окружения)
        """
        self.llm_client = llm_client or OpenAILikeClient()
        
        # Загрузка промпта
        self.system_prompt = self._load_prompt()
        
    def _load_prompt(self) -> str:
        """Загрузка системного промпта"""
        prompt_path = Path(__file__).parent.parent / "prompts" / "system_prompt_v1.md"
        
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            logger.warning(f"Промпт не найден по пути {prompt_path}, используется базовый")
            return "Ты — специализированная система анализа закупочной документации."
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Извлечение текста из PDF"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Ошибка извлечения текста из PDF: {e}")
        return text
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Извлечение текста из DOCX"""
        text = ""
        try:
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            logger.error(f"Ошибка извлечения текста из DOCX: {e}")
        return text
    
    def load_document(self, file_path: str) -> str:
        """
        Загрузка и извлечение текста из документа
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Текст документа
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Файл {file_path} не найден")
        
        if file_path.suffix.lower() == '.pdf':
            return self.extract_text_from_pdf(str(file_path))
        elif file_path.suffix.lower() in ['.docx', '.doc']:
            return self.extract_text_from_docx(str(file_path))
        elif file_path.suffix.lower() == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {file_path.suffix}")
    
    def analyze(self, document_text: str, provided_docs: Optional[List[str]] = None) -> Dict:
        """
        Анализ закупочной документации
        
        Args:
            document_text: Текст закупочной документации
            provided_docs: Список уже предоставленных документов (опционально)
            
        Returns:
            Структурированный результат анализа в формате JSON
        """
        user_message = f"""
Закупочная документация:
{document_text}
"""
        
        if provided_docs:
            user_message += f"\n\nУже предоставленные документы:\n" + "\n".join(f"- {doc}" for doc in provided_docs)
        
        user_message += "\n\nВыполни полный анализ и предоставь результат в указанном JSON формате."
        
        try:
            # Формирование messages в OpenAI-формате
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # Вызов LLM через OpenAI-совместимый клиент
            result_text = self.llm_client.chat_completion(
                messages=messages,
                temperature=0.7,
                top_p=0.9,
                max_tokens=4096,
                presence_penalty=0.6,
                frequency_penalty=0.8,
                response_format={"type": "json_object"}  # Строгий JSON-вывод
            )
            
            # Извлечение JSON из ответа
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = result_text[json_start:json_end]
                result = json.loads(json_text)
            else:
                raise ValueError("JSON не найден в ответе модели")
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка анализа: {e}")
            raise
    
    def verify_documents(self, required: List[Dict], provided: List[str]) -> Dict:
        """
        Сверка предоставленных документов с требованиями
        
        Args:
            required: Список требуемых документов из анализа
            provided: Список предоставленных документов
            
        Returns:
            Результат сверки с отметками о наличии/отсутствии
        """
        verification = {
            "provided": [],
            "missing_critical": [],
            "missing_optional": [],
            "completeness_score": 0
        }
        
        provided_normalized = [doc.lower() for doc in provided]
        total_mandatory = 0
        matched_mandatory = 0
        
        for req_doc in required:
            doc_name = req_doc.get("name", "").lower()
            is_mandatory = req_doc.get("mandatory", True)
            doc_id = req_doc.get("id", "")
            
            if is_mandatory:
                total_mandatory += 1
            
            # Проверка наличия документа
            is_provided = any(doc_name in prov or prov in doc_name for prov in provided_normalized)
            
            if is_provided:
                verification["provided"].append({
                    "doc_id": doc_id,
                    "name": req_doc["name"],
                    "status": "provided"
                })
                if is_mandatory:
                    matched_mandatory += 1
            else:
                if is_mandatory:
                    verification["missing_critical"].append(doc_id)
                else:
                    verification["missing_optional"].append(doc_id)
        
        # Расчет полноты комплекта
        if total_mandatory > 0:
            verification["completeness_score"] = int((matched_mandatory / total_mandatory) * 100)
        else:
            verification["completeness_score"] = 100
        
        return verification


def main():
    """
    Пример использования анализатора
    """
    analyzer = DocumentAnalyzer()
    
    # Загрузка документации
    doc_path = "example_procurement.pdf"
    
    if Path(doc_path).exists():
        text = analyzer.load_document(doc_path)
        result = analyzer.analyze(text)
        
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        logger.warning(f"Файл {doc_path} не найден")


if __name__ == "__main__":
    main()
