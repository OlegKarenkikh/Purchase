#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль формирования пакетов документов

Реализует требования FR-3 из ТЗ:
- Автоматический подбор документов
- Генерация недостающих документов
- Формирование итогового пакета
"""

import logging
import shutil
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
import zipfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PackageBuilder:
    """Строитель пакетов документов (FR-3.1 - FR-3.7)"""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir or "./output/packages")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def match_documents(self, required: List[Dict], available: List[Dict]) -> Dict:
        """FR-3.1: Сопоставление документов"""
        matched = []
        missing = []
        
        for req_doc in required:
            req_name = req_doc.get("name", "").lower()
            found = None
            
            for avail_doc in available:
                avail_name = avail_doc.get("name", "").lower()
                if req_name in avail_name or avail_name in req_name:
                    if avail_doc.get("status") != "expired":
                        found = avail_doc
                        break
            
            if found:
                matched.append({"required": req_doc, "matched": found})
            else:
                missing.append({"required": req_doc, "mandatory": req_doc.get("mandatory", True)})
        
        return {"matched": matched, "missing": missing}
    
    def calculate_completeness(self, matching: Dict) -> Dict:
        """FR-3.3: Расчет полноты"""
        total = len(matching["matched"]) + len(matching["missing"])
        matched = len(matching["matched"])
        mandatory_missing = sum(1 for m in matching["missing"] if m["mandatory"])
        
        return {
            "total": total,
            "matched": matched,
            "completeness": int((matched / total * 100)) if total > 0 else 0,
            "ready": mandatory_missing == 0
        }
    
    def build_package(self, procurement_id: str, matched: List[Dict]) -> str:
        """FR-3.6, FR-3.7: Формирование пакета"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        pkg_dir = self.output_dir / f"{procurement_id}_{ts}"
        pkg_dir.mkdir(parents=True, exist_ok=True)
        
        for idx, item in enumerate(matched, 1):
            fp = item.get("matched", {}).get("file_path")
            if fp and Path(fp).exists():
                shutil.copy2(fp, pkg_dir / f"{idx:02d}_{Path(fp).name}")
        
        zip_path = self.output_dir / f"{procurement_id}_{ts}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for f in pkg_dir.rglob('*'):
                if f.is_file():
                    zipf.write(f, f.relative_to(pkg_dir))
        
        shutil.rmtree(pkg_dir)
        return str(zip_path)
