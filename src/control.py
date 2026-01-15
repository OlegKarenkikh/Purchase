#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль многоэтапного контроля

Реализует FR-4:
- Автоматический контроль
- Юридический контроль
- Финансовый контроль
- Итоговый контроль
"""

import logging
from typing import List, Dict
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ControlStage:
    """Базовый класс этапа контроля"""
    
    def __init__(self, name: str):
        self.name = name
        self.status = "pending"
        self.issues = []
        self.checked_at = None
    
    def check(self, package: Dict) -> Dict:
        raise NotImplementedError()
    
    def get_result(self) -> Dict:
        return {
            "stage": self.name,
            "status": self.status,
            "issues": self.issues,
            "checked_at": self.checked_at
        }


class AutomaticControl(ControlStage):
    """FR-4.1.1: Автоматический контроль"""
    
    def __init__(self):
        super().__init__("Автоматический")
    
    def check(self, package: Dict) -> Dict:
        self.checked_at = datetime.now().isoformat()
        self.issues = []
        
        docs = package.get("documents", [])
        required = package.get("required_documents", [])
        
        if len(docs) < len(required):
            self.issues.append({
                "severity": "blocker",
                "message": f"Недостает документов: {len(required) - len(docs)}"
            })
        
        for doc in docs:
            fp = doc.get("file_path")
            if not fp or not Path(fp).exists():
                self.issues.append({
                    "severity": "critical",
                    "message": f"Файл не найден: {doc.get('name')}"
                })
                continue
            
            size = Path(fp).stat().st_size
            if size > 50 * 1024 * 1024:
                self.issues.append({
                    "severity": "warning",
                    "message": f"Файл слишком большой: {doc.get('name')}"
                })
            
            if doc.get("status") == "expired":
                self.issues.append({
                    "severity": "blocker",
                    "message": f"Истек срок: {doc.get('name')}"
                })
        
        if any(i["severity"] == "blocker" for i in self.issues):
            self.status = "failed"
        elif any(i["severity"] == "critical" for i in self.issues):
            self.status = "warning"
        else:
            self.status = "passed"
        
        return self.get_result()


class LegalControl(ControlStage):
    """FR-4.1.2: Юридический контроль"""
    
    def __init__(self):
        super().__init__("Юридический")
    
    def check(self, package: Dict) -> Dict:
        self.checked_at = datetime.now().isoformat()
        self.status = "pending"
        self.issues.append({
            "severity": "info",
            "message": "Требуется юридическая проверка"
        })
        return self.get_result()


class FinancialControl(ControlStage):
    """FR-4.1.3: Финансовый контроль"""
    
    def __init__(self):
        super().__init__("Финансовый")
    
    def check(self, package: Dict) -> Dict:
        self.checked_at = datetime.now().isoformat()
        self.status = "pending"
        self.issues.append({
            "severity": "info",
            "message": "Требуется финансовая проверка"
        })
        return self.get_result()


class FinalControl(ControlStage):
    """FR-4.1.4: Итоговый контроль"""
    
    def __init__(self):
        super().__init__("Итоговый")
    
    def check(self, package: Dict) -> Dict:
        self.checked_at = datetime.now().isoformat()
        self.status = "pending"
        self.issues.append({
            "severity": "info",
            "message": "Требуется утверждение руководителя"
        })
        return self.get_result()


class MultiStageController:
    """FR-4.5, FR-4.6: Контроллер многоэтапного контроля"""
    
    def __init__(self):
        self.stages = [
            AutomaticControl(),
            LegalControl(),
            FinancialControl(),
            FinalControl()
        ]
    
    def execute_full_control(self, package: Dict) -> Dict:
        results = []
        
        for stage in self.stages:
            result = stage.check(package)
            results.append(result)
            
            if stage.status == "failed":
                logger.warning(f"Этап '{stage.name}' не пройден")
                break
        
        overall = "passed"
        if any(r["status"] == "failed" for r in results):
            overall = "failed"
        elif any(r["status"] == "warning" for r in results):
            overall = "warning"
        elif any(r["status"] == "pending" for r in results):
            overall = "pending"
        
        return {
            "overall_status": overall,
            "stages": results,
            "completed_at": datetime.now().isoformat()
        }
