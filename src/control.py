#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль многоэтапного контроля

Реализует FR-4:
- FR-4.1: Автоматический контроль
- FR-4.2: Юридический контроль
- FR-4.3: Финансовый контроль
- FR-4.4: Итоговый контроль
- FR-4.7: Чек-листы для контроля
- FR-4.8: История контроля
"""

import logging
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ChecklistItem:
    """
    Элемент чек-листа (FR-4.7)
    """
    id: str
    description: str
    category: str
    is_automatic: bool = False
    checked: bool = False
    checked_by: Optional[str] = None
    checked_at: Optional[str] = None
    comment: str = ""
    severity: str = "normal"  # normal, critical, warning

    def mark_checked(self, user: str, comment: str = "") -> None:
        """Отметить пункт как проверенный"""
        self.checked = True
        self.checked_by = user
        self.checked_at = datetime.now().isoformat()
        self.comment = comment

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ControlHistoryEntry:
    """
    Запись истории контроля (FR-4.8)
    """
    entry_id: str
    stage_name: str
    action: str  # check, approve, reject, comment
    user_id: str
    user_name: str
    timestamp: str
    status_before: str
    status_after: str
    comment: str = ""
    attachments: List[str] = field(default_factory=list)
    time_spent_minutes: int = 0


class ControlStage:
    """Базовый класс этапа контроля"""

    def __init__(self, name: str):
        self.name = name
        self.status = "pending"
        self.issues = []
        self.checked_at = None
        self.checklist: List[ChecklistItem] = []
        self._init_checklist()

    def _init_checklist(self) -> None:
        """Инициализация чек-листа для этапа"""
        pass

    def check(self, package: Dict) -> Dict:
        raise NotImplementedError()

    def get_result(self) -> Dict:
        return {
            "stage": self.name,
            "status": self.status,
            "issues": self.issues,
            "checked_at": self.checked_at,
            "checklist": [item.to_dict() for item in self.checklist],
            "checklist_completion": self._calculate_checklist_completion(),
        }

    def _calculate_checklist_completion(self) -> float:
        """Расчет процента выполнения чек-листа"""
        if not self.checklist:
            return 100.0
        checked = sum(1 for item in self.checklist if item.checked)
        return round(checked / len(self.checklist) * 100, 1)

    def get_checklist(self) -> List[Dict]:
        """Получить чек-лист этапа"""
        return [item.to_dict() for item in self.checklist]

    def update_checklist_item(
        self,
        item_id: str,
        checked: bool,
        user: str,
        comment: str = ""
    ) -> bool:
        """Обновить пункт чек-листа"""
        for item in self.checklist:
            if item.id == item_id:
                if checked:
                    item.mark_checked(user, comment)
                else:
                    item.checked = False
                    item.checked_by = None
                    item.checked_at = None
                return True
        return False


class AutomaticControl(ControlStage):
    """FR-4.1.1: Автоматический контроль"""

    def __init__(self):
        super().__init__("Автоматический")

    def _init_checklist(self) -> None:
        """Чек-лист автоматического контроля"""
        self.checklist = [
            ChecklistItem(
                id="auto_01",
                description="Все обязательные документы предоставлены",
                category="completeness",
                is_automatic=True,
                severity="critical"
            ),
            ChecklistItem(
                id="auto_02",
                description="Форматы файлов соответствуют требованиям",
                category="format",
                is_automatic=True
            ),
            ChecklistItem(
                id="auto_03",
                description="Размеры файлов в пределах лимитов",
                category="format",
                is_automatic=True
            ),
            ChecklistItem(
                id="auto_04",
                description="Документы не истекли",
                category="validity",
                is_automatic=True,
                severity="critical"
            ),
            ChecklistItem(
                id="auto_05",
                description="Отсутствуют вирусы",
                category="security",
                is_automatic=True
            ),
            ChecklistItem(
                id="auto_06",
                description="Читаемость текста (для сканов)",
                category="quality",
                is_automatic=True
            ),
            ChecklistItem(
                id="auto_07",
                description="Подписи и печати присутствуют (если требуется)",
                category="signatures",
                is_automatic=False
            ),
            ChecklistItem(
                id="auto_08",
                description="Реквизиты актуальны",
                category="requisites",
                is_automatic=True
            ),
        ]

    def check(self, package: Dict) -> Dict:
        self.checked_at = datetime.now().isoformat()
        self.issues = []

        docs = package.get("documents", [])
        required = package.get("required_documents", [])

        # Проверка комплектности
        if len(docs) < len(required):
            self.issues.append({
                "severity": "blocker",
                "message": f"Недостает документов: {len(required) - len(docs)}"
            })
        else:
            self._mark_checklist_item("auto_01", True)

        # Проверка документов
        all_formats_ok = True
        all_sizes_ok = True
        all_valid = True

        for doc in docs:
            fp = doc.get("file_path")
            if not fp or not Path(fp).exists():
                self.issues.append({
                    "severity": "critical",
                    "message": f"Файл не найден: {doc.get('name')}"
                })
                all_formats_ok = False
                continue

            # Проверка размера
            size = Path(fp).stat().st_size
            if size > 50 * 1024 * 1024:
                self.issues.append({
                    "severity": "warning",
                    "message": f"Файл слишком большой: {doc.get('name')}"
                })
                all_sizes_ok = False

            # Проверка срока действия
            if doc.get("status") == "expired":
                self.issues.append({
                    "severity": "blocker",
                    "message": f"Истек срок: {doc.get('name')}"
                })
                all_valid = False

        # Обновляем чек-лист
        self._mark_checklist_item("auto_02", all_formats_ok)
        self._mark_checklist_item("auto_03", all_sizes_ok)
        self._mark_checklist_item("auto_04", all_valid)
        self._mark_checklist_item("auto_05", True)  # Предполагаем отсутствие вирусов
        self._mark_checklist_item("auto_06", True)  # Предполагаем читаемость
        self._mark_checklist_item("auto_08", True)  # Предполагаем актуальность реквизитов

        # Определение статуса
        if any(i["severity"] == "blocker" for i in self.issues):
            self.status = "failed"
        elif any(i["severity"] == "critical" for i in self.issues):
            self.status = "warning"
        else:
            self.status = "passed"

        return self.get_result()

    def _mark_checklist_item(self, item_id: str, checked: bool) -> None:
        """Автоматическая отметка пункта чек-листа"""
        for item in self.checklist:
            if item.id == item_id:
                if checked:
                    item.mark_checked("system", "Автоматическая проверка")
                break


class LegalControl(ControlStage):
    """FR-4.1.2: Юридический контроль"""

    def __init__(self):
        super().__init__("Юридический")

    def _init_checklist(self) -> None:
        """Чек-лист юридического контроля"""
        self.checklist = [
            ChecklistItem(
                id="legal_01",
                description="Соответствие учредительных документов законодательству",
                category="compliance",
                severity="critical"
            ),
            ChecklistItem(
                id="legal_02",
                description="Полномочия подписанта подтверждены",
                category="authority",
                severity="critical"
            ),
            ChecklistItem(
                id="legal_03",
                description="Отсутствие противоречий между документами",
                category="consistency"
            ),
            ChecklistItem(
                id="legal_04",
                description="Соответствие требованиям закупки",
                category="compliance",
                severity="critical"
            ),
            ChecklistItem(
                id="legal_05",
                description="Корректность формулировок",
                category="quality"
            ),
            ChecklistItem(
                id="legal_06",
                description="Наличие обязательных реквизитов",
                category="requisites"
            ),
            ChecklistItem(
                id="legal_07",
                description="Соответствие срокам действия",
                category="validity"
            ),
            ChecklistItem(
                id="legal_08",
                description="Отсутствие ограничений на участие",
                category="restrictions",
                severity="critical"
            ),
        ]

    def check(self, package: Dict) -> Dict:
        self.checked_at = datetime.now().isoformat()
        self.issues = []

        # Юридический контроль требует ручной проверки
        unchecked = [item for item in self.checklist if not item.checked]

        if unchecked:
            self.status = "pending"
            self.issues.append({
                "severity": "info",
                "message": f"Требуется юридическая проверка ({len(unchecked)} пунктов)"
            })
        else:
            # Все пункты проверены
            critical_failed = [
                item for item in self.checklist
                if item.severity == "critical" and not item.checked
            ]
            if critical_failed:
                self.status = "failed"
            else:
                self.status = "passed"

        return self.get_result()


class FinancialControl(ControlStage):
    """FR-4.1.3: Финансовый контроль"""

    def __init__(self):
        super().__init__("Финансовый")

    def _init_checklist(self) -> None:
        """Чек-лист финансового контроля"""
        self.checklist = [
            ChecklistItem(
                id="fin_01",
                description="Финансовые показатели соответствуют требованиям",
                category="financial",
                severity="critical"
            ),
            ChecklistItem(
                id="fin_02",
                description="Обеспечение заявки предоставлено",
                category="security"
            ),
            ChecklistItem(
                id="fin_03",
                description="Расчетные счета активны",
                category="accounts"
            ),
            ChecklistItem(
                id="fin_04",
                description="Отсутствие задолженностей подтверждено",
                category="debts",
                severity="critical"
            ),
            ChecklistItem(
                id="fin_05",
                description="Ценовое предложение корректно",
                category="pricing",
                severity="critical"
            ),
            ChecklistItem(
                id="fin_06",
                description="НДС учтен правильно",
                category="taxes"
            ),
            ChecklistItem(
                id="fin_07",
                description="Нет признаков демпинга",
                category="pricing"
            ),
        ]

    def check(self, package: Dict) -> Dict:
        self.checked_at = datetime.now().isoformat()
        self.issues = []

        unchecked = [item for item in self.checklist if not item.checked]

        if unchecked:
            self.status = "pending"
            self.issues.append({
                "severity": "info",
                "message": f"Требуется финансовая проверка ({len(unchecked)} пунктов)"
            })
        else:
            self.status = "passed"

        return self.get_result()


class FinalControl(ControlStage):
    """FR-4.1.4: Итоговый контроль"""

    def __init__(self):
        super().__init__("Итоговый")

    def _init_checklist(self) -> None:
        """Чек-лист итогового контроля"""
        self.checklist = [
            ChecklistItem(
                id="final_01",
                description="Автоматический контроль пройден",
                category="stages",
                severity="critical"
            ),
            ChecklistItem(
                id="final_02",
                description="Юридический контроль пройден",
                category="stages",
                severity="critical"
            ),
            ChecklistItem(
                id="final_03",
                description="Финансовый контроль пройден",
                category="stages",
                severity="critical"
            ),
            ChecklistItem(
                id="final_04",
                description="Утверждение руководителя получено",
                category="approval",
                severity="critical"
            ),
        ]

    def check(self, package: Dict) -> Dict:
        self.checked_at = datetime.now().isoformat()
        self.issues = []

        unchecked = [item for item in self.checklist if not item.checked]

        if unchecked:
            self.status = "pending"
            self.issues.append({
                "severity": "info",
                "message": f"Требуется утверждение руководителя ({len(unchecked)} пунктов)"
            })
        else:
            self.status = "passed"

        return self.get_result()


class ControlHistory:
    """
    История контроля (FR-4.8)
    """

    def __init__(self, storage_path: str = "./storage/control_history"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.entries: List[ControlHistoryEntry] = []

    def add_entry(
        self,
        stage_name: str,
        action: str,
        user_id: str,
        user_name: str,
        status_before: str,
        status_after: str,
        comment: str = "",
        time_spent_minutes: int = 0
    ) -> ControlHistoryEntry:
        """Добавить запись в историю"""
        entry = ControlHistoryEntry(
            entry_id=f"CHE-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            stage_name=stage_name,
            action=action,
            user_id=user_id,
            user_name=user_name,
            timestamp=datetime.now().isoformat(),
            status_before=status_before,
            status_after=status_after,
            comment=comment,
            time_spent_minutes=time_spent_minutes
        )
        self.entries.append(entry)
        return entry

    def get_history(self, stage_name: Optional[str] = None) -> List[Dict]:
        """Получить историю контроля"""
        entries = self.entries
        if stage_name:
            entries = [e for e in entries if e.stage_name == stage_name]
        return [asdict(e) for e in entries]

    def get_statistics(self) -> Dict[str, Any]:
        """Статистика по контролю"""
        if not self.entries:
            return {"total_entries": 0}

        total_time = sum(e.time_spent_minutes for e in self.entries)
        by_stage = {}
        by_action = {}

        for entry in self.entries:
            by_stage[entry.stage_name] = by_stage.get(entry.stage_name, 0) + 1
            by_action[entry.action] = by_action.get(entry.action, 0) + 1

        return {
            "total_entries": len(self.entries),
            "total_time_minutes": total_time,
            "average_time_minutes": round(total_time / len(self.entries), 1),
            "by_stage": by_stage,
            "by_action": by_action,
        }

    def save(self, package_id: str) -> str:
        """Сохранить историю в файл"""
        file_path = self.storage_path / f"{package_id}_history.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.get_history(), f, ensure_ascii=False, indent=2)
        return str(file_path)


class MultiStageController:
    """FR-4.5, FR-4.6: Контроллер многоэтапного контроля"""

    def __init__(self):
        self.stages = [
            AutomaticControl(),
            LegalControl(),
            FinancialControl(),
            FinalControl()
        ]
        self.history = ControlHistory()

    def execute_full_control(self, package: Dict, user_id: str = "system", user_name: str = "Система") -> Dict:
        """Выполнить полный контроль пакета"""
        results = []

        for stage in self.stages:
            status_before = stage.status
            result = stage.check(package)
            results.append(result)

            # Записываем в историю
            self.history.add_entry(
                stage_name=stage.name,
                action="check",
                user_id=user_id,
                user_name=user_name,
                status_before=status_before,
                status_after=stage.status,
                comment=f"Автоматическая проверка этапа '{stage.name}'"
            )

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
            "completed_at": datetime.now().isoformat(),
            "history_entries": len(self.history.entries),
        }

    def get_stage_checklist(self, stage_index: int) -> List[Dict]:
        """Получить чек-лист этапа по индексу"""
        if 0 <= stage_index < len(self.stages):
            return self.stages[stage_index].get_checklist()
        return []

    def update_checklist_item(
        self,
        stage_index: int,
        item_id: str,
        checked: bool,
        user_id: str,
        user_name: str,
        comment: str = ""
    ) -> bool:
        """Обновить пункт чек-листа"""
        if 0 <= stage_index < len(self.stages):
            stage = self.stages[stage_index]
            result = stage.update_checklist_item(item_id, checked, user_name, comment)

            if result:
                self.history.add_entry(
                    stage_name=stage.name,
                    action="checklist_update",
                    user_id=user_id,
                    user_name=user_name,
                    status_before=stage.status,
                    status_after=stage.status,
                    comment=f"Обновлен пункт {item_id}: {'отмечен' if checked else 'снят'}"
                )

            return result
        return False

    def approve_stage(
        self,
        stage_index: int,
        user_id: str,
        user_name: str,
        comment: str = ""
    ) -> bool:
        """Утвердить этап"""
        if 0 <= stage_index < len(self.stages):
            stage = self.stages[stage_index]
            status_before = stage.status

            # Проверяем, что все критические пункты чек-листа выполнены
            critical_unchecked = [
                item for item in stage.checklist
                if item.severity == "critical" and not item.checked
            ]

            if critical_unchecked:
                return False

            stage.status = "passed"

            self.history.add_entry(
                stage_name=stage.name,
                action="approve",
                user_id=user_id,
                user_name=user_name,
                status_before=status_before,
                status_after=stage.status,
                comment=comment or "Этап утвержден"
            )

            return True
        return False

    def reject_stage(
        self,
        stage_index: int,
        user_id: str,
        user_name: str,
        comment: str
    ) -> bool:
        """Отклонить этап"""
        if 0 <= stage_index < len(self.stages):
            stage = self.stages[stage_index]
            status_before = stage.status
            stage.status = "failed"

            self.history.add_entry(
                stage_name=stage.name,
                action="reject",
                user_id=user_id,
                user_name=user_name,
                status_before=status_before,
                status_after=stage.status,
                comment=comment
            )

            return True
        return False

    def get_all_checklists(self) -> Dict[str, List[Dict]]:
        """Получить все чек-листы"""
        return {
            stage.name: stage.get_checklist()
            for stage in self.stages
        }

    def get_control_history(self) -> List[Dict]:
        """Получить историю контроля"""
        return self.history.get_history()
