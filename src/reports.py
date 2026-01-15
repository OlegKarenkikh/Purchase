#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль отчетности и аналитики

Реализует FR-5:
- Формирование отчетов
- Аналитика
- Экспорт в различные форматы
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReportGenerator:
    """FR-5.1 - FR-5.3: Генератор отчетов"""
    
    def __init__(self):
        self.procurements: List[Dict] = []
        self.packages: List[Dict] = []
    
    def add_procurement_data(self, procurement: Dict) -> None:
        self.procurements.append(procurement)
    
    def add_package_data(self, package: Dict) -> None:
        self.packages.append(package)
    
    def generate_procurement_report(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """FR-5.1: Отчет по закупкам"""
        filtered = self._filter_by_date(self.procurements, start_date, end_date)
        
        return {
            "period": {"start": start_date or "N/A", "end": end_date or "N/A"},
            "total_procurements": len(filtered),
            "by_status": self._count_by_field(filtered, "status"),
            "by_legal_basis": self._count_by_field(filtered, "legal_basis"),
            "generated_at": datetime.now().isoformat()
        }
    
    def generate_rejection_report(self) -> Dict:
        """FR-5.1: Отчет по отклоненным заявкам"""
        rejected = [p for p in self.procurements if p.get("status") == "rejected"]
        reasons = {}
        
        for proc in rejected:
            reason = proc.get("rejection_reason", "Неизвестна")
            reasons[reason] = reasons.get(reason, 0) + 1
        
        return {
            "total_rejected": len(rejected),
            "rejection_rate": len(rejected) / len(self.procurements) if self.procurements else 0,
            "reasons": reasons,
            "generated_at": datetime.now().isoformat()
        }
    
    def generate_timing_report(self) -> Dict:
        """FR-5.1: Отчет по срокам"""
        timings = [p["preparation_time_hours"] for p in self.procurements if "preparation_time_hours" in p]
        avg = sum(timings) / len(timings) if timings else 0
        
        return {
            "average_preparation_time_hours": round(avg, 2),
            "min_time_hours": min(timings) if timings else 0,
            "max_time_hours": max(timings) if timings else 0,
            "total_applications": len(timings),
            "generated_at": datetime.now().isoformat()
        }
    
    def generate_missing_documents_report(self) -> Dict:
        """FR-5.1: Отчет по отсутствующим документам"""
        missing_docs = {}
        
        for pkg in self.packages:
            for doc in pkg.get("missing", []):
                name = doc.get("required", {}).get("name", "Неизвестный")
                missing_docs[name] = missing_docs.get(name, 0) + 1
        
        sorted_missing = sorted(missing_docs.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "top_missing_documents": [
                {"document": doc, "count": count}
                for doc, count in sorted_missing
            ],
            "generated_at": datetime.now().isoformat()
        }
    
    def generate_analytics_dashboard(self) -> Dict:
        """FR-5.3: Аналитика"""
        successful = len([p for p in self.procurements if p.get("status") == "won"])
        success_rate = successful / len(self.procurements) if self.procurements else 0
        
        return {
            "total_procurements": len(self.procurements),
            "success_rate": round(success_rate * 100, 1),
            "average_preparation_time": self.generate_timing_report()["average_preparation_time_hours"],
            "generated_at": datetime.now().isoformat()
        }
    
    def export_to_json(self, report: Dict, filename: str) -> None:
        """FR-5.2: Экспорт в JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"Отчет экспортирован: {filename}")
    
    def _filter_by_date(self, items: List[Dict], start: Optional[str], end: Optional[str]) -> List[Dict]:
        if not start and not end:
            return items
        return [
            i for i in items
            if (not start or i.get("created_at", "") >= start) and
               (not end or i.get("created_at", "") <= end)
        ]
    
    def _count_by_field(self, items: List[Dict], field: str) -> Dict[str, int]:
        counts = {}
        for item in items:
            value = item.get(field, "Неизвестно")
            counts[value] = counts.get(value, 0) + 1
        return counts
