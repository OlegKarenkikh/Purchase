#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль отчета о готовности пакета документов

Реализует требования FR-4.9 из расширенного ТЗ:
- Формирование отчета о состоянии готовности заявки
- Расчет метрик готовности
- Выявление проблем
- Генерация рекомендаций
"""

import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ReadinessReport:
    """
    Отчет о готовности пакета документов (FR-4.9)

    Обеспечивает:
    - Расчет метрик готовности
    - Выявление проблем с документами
    - Генерацию рекомендаций
    - Экспорт отчета в различные форматы
    """

    # Статусы готовности пакета
    STATUS_READY = "ready"
    STATUS_INCOMPLETE = "incomplete"
    STATUS_WITH_RISKS = "with_risks"
    STATUS_NOT_STARTED = "not_started"

    # Типы проблем
    PROBLEM_MISSING_MANDATORY = "missing_mandatory"
    PROBLEM_MISSING_OPTIONAL = "missing_optional"
    PROBLEM_NO_TEMPLATE = "no_template"
    PROBLEM_EXPIRING_SOON = "expiring_soon"
    PROBLEM_FORMAT_MISMATCH = "format_mismatch"
    PROBLEM_OUTDATED = "outdated"

    def __init__(self, output_dir: str = "./output/reports"):
        """
        Args:
            output_dir: Директория для сохранения отчетов
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        manifest: Dict,
        requirements: List[Dict],
        procurement_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Генерация полного отчета о готовности

        Args:
            manifest: Опись документов
            requirements: Список требований из анализа КД
            procurement_info: Информация о закупке

        Returns:
            Структурированный отчет о готовности
        """
        report_id = f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        package_id = manifest.get("manifest_id", "UNKNOWN")

        # Расчет метрик
        metrics = self.calculate_readiness(manifest, requirements)

        # Выявление проблем
        problems = self.identify_problems(manifest, requirements)

        # Генерация рекомендаций
        recommendations = self.generate_recommendations(problems, metrics)

        # Определение общего статуса
        status = self._determine_status(metrics, problems)

        report = {
            "report_id": report_id,
            "package_id": package_id,
            "procurement_info": procurement_info or {},
            "generated_at": datetime.now().isoformat(),
            "status": status,
            "status_description": self._get_status_description(status),
            "metrics": metrics,
            "problems": problems,
            "problems_summary": self._summarize_problems(problems),
            "recommendations": recommendations,
            "checklist": self._generate_checklist(manifest, problems),
        }

        logger.info(f"Отчет о готовности создан: {report_id}, статус: {status}")
        return report

    def calculate_readiness(
        self,
        manifest: Dict,
        requirements: List[Dict]
    ) -> Dict[str, Any]:
        """
        Расчет метрик готовности пакета

        Args:
            manifest: Опись документов
            requirements: Список требований

        Returns:
            Словарь с метриками
        """
        items = manifest.get("items", [])

        # Подсчет по категориям
        total_requirements = len(requirements)
        mandatory_docs = [i for i in items if i.get("mandatory")]
        optional_docs = [i for i in items if not i.get("mandatory")]

        provided_statuses = {"provided", "from_template"}
        provided_mandatory = [
            i for i in mandatory_docs
            if i.get("completion_status") in provided_statuses
        ]
        provided_optional = [
            i for i in optional_docs
            if i.get("completion_status") in provided_statuses
        ]

        # Расчет процентов
        total_mandatory = len(mandatory_docs)
        completeness = (
            len(provided_mandatory) / total_mandatory * 100
            if total_mandatory > 0 else 100
        )

        return {
            "total_requirements": total_requirements,
            "requirements_covered": len(provided_mandatory) + len(provided_optional),
            "total_mandatory_docs": total_mandatory,
            "provided_mandatory_docs": len(provided_mandatory),
            "completeness_percentage": round(completeness, 1),
            "total_optional_docs": len(optional_docs),
            "provided_optional_docs": len(provided_optional),
            "documents_from_templates": sum(
                1 for i in items if i.get("source_type") == "template_library"
            ),
            "documents_user_provided": sum(
                1 for i in items if i.get("source_type") == "user_provided"
            ),
        }

    def identify_problems(
        self,
        manifest: Dict,
        requirements: List[Dict]
    ) -> List[Dict]:
        """
        Выявление проблем с документами

        Args:
            manifest: Опись документов
            requirements: Список требований

        Returns:
            Список выявленных проблем
        """
        problems = []
        items = manifest.get("items", [])

        for item in items:
            doc_name = item.get("document_name", "")
            doc_id = item.get("document_id", "")
            status = item.get("completion_status", "")
            mandatory = item.get("mandatory", True)

            # Проблема: отсутствует обязательный документ
            if status == "missing" and mandatory:
                problems.append({
                    "type": self.PROBLEM_MISSING_MANDATORY,
                    "document_id": doc_id,
                    "document_name": doc_name,
                    "linked_requirements": item.get("linked_requirements", []),
                    "priority": "high",
                    "description": f"Обязательный документ отсутствует: {doc_name}",
                    "action_required": "Необходимо предоставить документ",
                })

            # Проблема: отсутствует опциональный документ
            elif status == "missing" and not mandatory:
                problems.append({
                    "type": self.PROBLEM_MISSING_OPTIONAL,
                    "document_id": doc_id,
                    "document_name": doc_name,
                    "priority": "low",
                    "description": f"Опциональный документ отсутствует: {doc_name}",
                    "action_required": "Рекомендуется предоставить для повышения шансов",
                })

            # Проблема: не найден типовой документ
            if status == "not_prepared" and not item.get("template_match"):
                problems.append({
                    "type": self.PROBLEM_NO_TEMPLATE,
                    "document_id": doc_id,
                    "document_name": doc_name,
                    "priority": "medium" if mandatory else "low",
                    "description": f"Типовой шаблон не найден: {doc_name}",
                    "action_required": "Подготовить документ вручную или добавить шаблон",
                })

        # Проверка на истекающие документы
        for item in items:
            validity = item.get("validity_requirements", "")
            if "дней" in validity.lower() or "30" in validity:
                problems.append({
                    "type": self.PROBLEM_EXPIRING_SOON,
                    "document_id": item.get("document_id"),
                    "document_name": item.get("document_name"),
                    "priority": "medium",
                    "description": f"Документ имеет ограниченный срок действия: {validity}",
                    "action_required": "Проверить актуальность перед подачей",
                })

        return problems

    def generate_recommendations(
        self,
        problems: List[Dict],
        metrics: Dict
    ) -> List[str]:
        """
        Генерация рекомендаций на основе проблем

        Args:
            problems: Список проблем
            metrics: Метрики готовности

        Returns:
            Список рекомендаций
        """
        recommendations = []

        # Рекомендации по обязательным документам
        missing_mandatory = [
            p for p in problems if p.get("type") == self.PROBLEM_MISSING_MANDATORY
        ]
        if missing_mandatory:
            docs = [p.get("document_name", "") for p in missing_mandatory[:5]]
            recommendations.append(
                f"СРОЧНО: подготовить обязательные документы ({len(missing_mandatory)} шт.): "
                + ", ".join(docs)
            )

        # Рекомендации по шаблонам
        no_template = [p for p in problems if p.get("type") == self.PROBLEM_NO_TEMPLATE]
        if no_template:
            recommendations.append(
                f"Добавить типовые шаблоны для {len(no_template)} документов "
                "для ускорения подготовки будущих заявок"
            )

        # Рекомендации по срокам
        expiring = [p for p in problems if p.get("type") == self.PROBLEM_EXPIRING_SOON]
        if expiring:
            recommendations.append(
                f"Проверить актуальность {len(expiring)} документов "
                "с ограниченным сроком действия"
            )

        # Рекомендации по полноте
        completeness = metrics.get("completeness_percentage", 0)
        if completeness < 50:
            recommendations.append(
                "Готовность пакета низкая. Рекомендуется "
                "сосредоточиться на обязательных документах"
            )
        elif completeness < 80:
            recommendations.append(
                "Пакет почти готов. Проверьте оставшиеся документы"
            )
        elif completeness >= 100 and not problems:
            recommendations.append(
                "Пакет полностью готов к подаче. "
                "Рекомендуется финальная проверка перед отправкой"
            )

        # Общие рекомендации
        if metrics.get("documents_from_templates", 0) == 0:
            recommendations.append(
                "Рассмотрите использование каталога типовых документов "
                "для ускорения подготовки заявок"
            )

        return recommendations

    def _determine_status(self, metrics: Dict, problems: List[Dict]) -> str:
        """Определение общего статуса готовности"""
        completeness = metrics.get("completeness_percentage", 0)
        mandatory_missing = sum(
            1 for p in problems if p.get("type") == self.PROBLEM_MISSING_MANDATORY
        )

        if completeness == 0:
            return self.STATUS_NOT_STARTED
        elif mandatory_missing > 0:
            return self.STATUS_INCOMPLETE
        elif problems:
            return self.STATUS_WITH_RISKS
        else:
            return self.STATUS_READY

    def _get_status_description(self, status: str) -> str:
        """Получение описания статуса"""
        descriptions = {
            self.STATUS_READY: "Пакет полностью соответствует всем выявленным требованиям",
            self.STATUS_INCOMPLETE: "Есть отсутствующие обязательные документы",
            self.STATUS_WITH_RISKS: "Формально закрыто, но есть потенциальные риски",
            self.STATUS_NOT_STARTED: "Подготовка документов не начата",
        }
        return descriptions.get(status, "Статус не определен")

    def _summarize_problems(self, problems: List[Dict]) -> Dict[str, int]:
        """Сводка по проблемам"""
        summary = {}
        for problem in problems:
            problem_type = problem.get("type", "unknown")
            summary[problem_type] = summary.get(problem_type, 0) + 1
        return summary

    def _generate_checklist(
        self,
        manifest: Dict,
        problems: List[Dict]
    ) -> List[Dict]:
        """Генерация чек-листа для проверки"""
        checklist = []

        # Базовые проверки
        items = manifest.get("items", [])
        total = len(items)
        provided = sum(
            1 for i in items
            if i.get("completion_status") in ("provided", "from_template")
        )

        checklist.append({
            "item": "Все документы предоставлены",
            "checked": provided == total,
            "status": f"{provided}/{total}",
        })

        # Проверка обязательных документов
        mandatory = [i for i in items if i.get("mandatory")]
        mandatory_provided = sum(
            1 for i in mandatory
            if i.get("completion_status") in ("provided", "from_template")
        )

        checklist.append({
            "item": "Все обязательные документы предоставлены",
            "checked": mandatory_provided == len(mandatory),
            "status": f"{mandatory_provided}/{len(mandatory)}",
        })

        # Проверка отсутствия критических проблем
        high_priority = sum(1 for p in problems if p.get("priority") == "high")
        checklist.append({
            "item": "Нет критических проблем",
            "checked": high_priority == 0,
            "status": f"Критических проблем: {high_priority}",
        })

        return checklist

    def export_report(
        self,
        report: Dict,
        output_format: str = "json",
        output_path: Optional[str] = None
    ) -> str:
        """
        Экспорт отчета в указанном формате

        Args:
            report: Отчет о готовности
            output_format: Формат (json, html, pdf)
            output_path: Путь для сохранения

        Returns:
            Путь к созданному файлу
        """
        report_id = report.get("report_id", "report")

        if output_path:
            output_file = Path(output_path)
        else:
            output_file = self.output_dir / f"{report_id}.{output_format}"

        if output_format == "json":
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        elif output_format == "html":
            html_content = self._render_html_report(report)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
        else:
            raise ValueError(f"Неподдерживаемый формат: {output_format}")

        logger.info(f"Отчет экспортирован: {output_file}")
        return str(output_file)

    def _render_html_report(self, report: Dict) -> str:
        """Рендеринг HTML отчета"""
        status = report.get("status", "unknown")
        status_colors = {
            self.STATUS_READY: "#28a745",
            self.STATUS_INCOMPLETE: "#dc3545",
            self.STATUS_WITH_RISKS: "#ffc107",
            self.STATUS_NOT_STARTED: "#6c757d",
        }
        status_color = status_colors.get(status, "#6c757d")

        metrics = report.get("metrics", {})
        problems = report.get("problems", [])
        recommendations = report.get("recommendations", [])
        checklist = report.get("checklist", [])

        html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет о готовности пакета - {report.get('report_id', '')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .status {{ display: inline-block; padding: 10px 20px; border-radius: 4px; color: white; font-weight: bold; background: {status_color}; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .metric {{ background: #e9ecef; padding: 15px; border-radius: 8px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #495057; }}
        .metric-label {{ font-size: 12px; color: #6c757d; }}
        .section {{ margin: 20px 0; }}
        .section h2 {{ border-bottom: 2px solid #dee2e6; padding-bottom: 10px; }}
        .problem {{ padding: 10px; margin: 5px 0; border-left: 4px solid; background: #f8f9fa; }}
        .problem.high {{ border-color: #dc3545; }}
        .problem.medium {{ border-color: #ffc107; }}
        .problem.low {{ border-color: #28a745; }}
        .recommendation {{ padding: 10px; margin: 5px 0; background: #e7f3ff; border-radius: 4px; }}
        .checklist {{ list-style: none; padding: 0; }}
        .checklist li {{ padding: 10px; margin: 5px 0; background: #f8f9fa; border-radius: 4px; }}
        .checklist .checked {{ color: #28a745; }}
        .checklist .unchecked {{ color: #dc3545; }}
        .progress-bar {{ height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; }}
        .progress-fill {{ height: 100%; background: {status_color}; transition: width 0.3s; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Отчет о готовности пакета документов</h1>
        <p><strong>ID отчета:</strong> {report.get('report_id', 'N/A')}</p>
        <p><strong>Дата:</strong> {report.get('generated_at', 'N/A')}</p>
        <div class="status">{report.get('status_description', 'Не определено')}</div>
    </div>

    <div class="section">
        <h2>Метрики готовности</h2>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {metrics.get('completeness_percentage', 0)}%"></div>
        </div>
        <p style="text-align: center; margin-top: 10px;">
            <strong>{metrics.get('completeness_percentage', 0)}%</strong> готовность
        </p>
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{metrics.get('total_mandatory_docs', 0)}</div>
                <div class="metric-label">Обязательных документов</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics.get('provided_mandatory_docs', 0)}</div>
                <div class="metric-label">Предоставлено</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics.get('total_optional_docs', 0)}</div>
                <div class="metric-label">Опциональных</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics.get('documents_from_templates', 0)}</div>
                <div class="metric-label">Из типовых</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Выявленные проблемы ({len(problems)})</h2>
        {''.join(f'<div class="problem {p.get("priority", "low")}"><strong>{p.get("document_name", "")}</strong><br>{p.get("description", "")}</div>' for p in problems) if problems else '<p>Проблем не обнаружено</p>'}
    </div>

    <div class="section">
        <h2>Рекомендации</h2>
        {''.join(f'<div class="recommendation">{r}</div>' for r in recommendations) if recommendations else '<p>Нет рекомендаций</p>'}
    </div>

    <div class="section">
        <h2>Чек-лист</h2>
        <ul class="checklist">
            {''.join(f'<li><span class="{"checked" if c.get("checked") else "unchecked"}">{"✓" if c.get("checked") else "✗"}</span> {c.get("item", "")} ({c.get("status", "")})</li>' for c in checklist)}
        </ul>
    </div>
</body>
</html>
"""
        return html
