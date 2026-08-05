import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.agents.base import BaseAgent
from app.services.llm_client import MODEL_NAME, client

logger = logging.getLogger(__name__)

REPORTS_DIR = Path("reports")

# InsightFlow AI brand palette (DESIGN_LANGUAGE.md) — reused as-is rather
# than re-deriving report colors from scratch.
OCEAN_NAVY = colors.HexColor("#1C3B61")
COASTAL_BLUE = colors.HexColor("#3490DC")
CLOUD_GREY = colors.HexColor("#E2E8F0")
SOFT_SAND = colors.HexColor("#F7F9FC")
SEVERITY_COLORS = {"critical": "#DC2626", "warning": "#CA8A04", "info": "#3490DC"}


def _fallback_summary(
    data_domain: str, quality_report: dict, kpis: list[dict], insights: list[dict]
) -> str:
    parts = [f"This {data_domain or 'generic'} dataset was analyzed automatically."]

    if kpis:
        kpi_str = "; ".join(f"{k['label']}: {k['value']}{k['unit']}" for k in kpis[:3])
        parts.append(f"Key metrics: {kpi_str}.")

    if insights:
        parts.append(f'The most notable finding was "{insights[0]["title"]}".')

    score = quality_report.get("overall_score")
    if score is not None:
        parts.append(f"Overall data quality scored {score}/100.")

    return " ".join(parts)


def _build_prompt(
    data_domain: str, dataset_filename: str, quality_report: dict, kpis: list[dict], insights: list[dict]
) -> str:
    kpi_lines = "\n".join(f"- {k['label']}: {k['value']}{k['unit']}" for k in kpis) or "(none)"
    insight_lines = (
        "\n".join(f"- [{i['severity']}] {i['title']}: {i['description']}" for i in insights)
        or "(none)"
    )
    score = quality_report.get("overall_score", "unknown")

    return f"""You are a senior data analyst writing a 2-4 sentence executive summary \
for a business stakeholder, based on an automated analysis of "{dataset_filename}" \
(a "{data_domain}" dataset).

KPIs:
{kpi_lines}

Insights:
{insight_lines}

Overall data quality score: {score}/100

Write ONLY the summary itself — plain prose, 2-4 sentences, no markdown, no \
bullet points, no preamble like "Here is a summary". Synthesize the overall \
picture: what kind of data this is, the single most important finding, and \
how complete/reliable the data is. Write for a business reader, not a \
technical one."""


class ReportAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "report"

    async def execute(self, state: dict) -> dict:
        data_domain = state.get("data_domain") or "generic"
        dataset_filename = state.get("dataset_filename") or "Untitled dataset"
        quality_report = state.get("quality_report") or {}
        kpis = state.get("kpis") or []
        insights = state.get("insights") or []
        cleaning_actions = state.get("cleaning_actions") or []
        forecast = state.get("forecast") or {}

        summary = await self._get_summary(data_domain, dataset_filename, quality_report, kpis, insights)

        run_id = state.get("run_id") or "unknown-run"
        report_path = self._build_pdf(
            run_id=run_id,
            dataset_filename=dataset_filename,
            data_domain=data_domain,
            summary=summary,
            quality_report=quality_report,
            kpis=kpis,
            insights=insights,
            cleaning_actions=cleaning_actions,
            forecast=forecast,
        )

        state["executive_summary"] = summary
        state["report_path"] = report_path
        return state

    async def _get_summary(
        self, data_domain: str, dataset_filename: str, quality_report: dict, kpis: list[dict], insights: list[dict]
    ) -> str:
        prompt = _build_prompt(data_domain, dataset_filename, quality_report, kpis, insights)
        attempts = 2
        for attempt in range(1, attempts + 1):
            try:
                raw = await asyncio.to_thread(self._call_llm, prompt)
                text = raw.strip()
                if text:
                    return text
            except Exception as exc:
                logger.warning(
                    "report: LLM summary attempt %d/%d failed: %s", attempt, attempts, exc
                )

        logger.warning("report: falling back to template summary after %d attempts", attempts)
        return _fallback_summary(data_domain, quality_report, kpis, insights)

    def _call_llm(self, prompt: str) -> str:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return response.text

    def _build_pdf(
        self,
        run_id: str,
        dataset_filename: str,
        data_domain: str,
        summary: str,
        quality_report: dict,
        kpis: list[dict],
        insights: list[dict],
        cleaning_actions: list[dict],
        forecast: dict,
    ) -> str:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        path = REPORTS_DIR / f"{run_id}.pdf"

        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            topMargin=22 * mm,
            bottomMargin=18 * mm,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
        )
        styles = _report_styles()
        story = []

        story.append(Paragraph(dataset_filename, styles["Title"]))
        story.append(
            Paragraph(
                f"InsightFlow AI analysis report &middot; {data_domain.title()} dataset &middot; "
                f"generated {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
                styles["Subtitle"],
            )
        )
        story.append(Spacer(1, 10 * mm))

        story.append(Paragraph("Executive Summary", styles["Heading"]))
        story.append(Paragraph(summary, styles["Body"]))
        story.append(Spacer(1, 6 * mm))

        if kpis:
            story.append(Paragraph("Key Metrics", styles["Heading"]))
            story.append(_kpi_table(kpis))
            story.append(Spacer(1, 6 * mm))

        story.append(Paragraph("Insights", styles["Heading"]))
        if insights:
            for insight in insights:
                story.append(_insight_paragraph(insight, styles))
        else:
            story.append(Paragraph("No insights were generated for this run.", styles["Body"]))
        story.append(Spacer(1, 6 * mm))

        if cleaning_actions:
            story.append(Paragraph("Data Cleaning", styles["Heading"]))
            for action in cleaning_actions:
                prefix = f"<b>{action['column']}:</b> " if action.get("column") else ""
                story.append(Paragraph(f"&bull; {prefix}{action['detail']}", styles["Body"]))
            story.append(Spacer(1, 6 * mm))

        story.append(Paragraph("Forecast", styles["Heading"]))
        story.extend(_forecast_paragraphs(forecast, styles))

        doc.build(story)
        return str(path)


def _report_styles():
    base = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "ReportTitle", parent=base["Title"], textColor=OCEAN_NAVY, fontSize=20, spaceAfter=2
        ),
        "Subtitle": ParagraphStyle(
            "ReportSubtitle", parent=base["Normal"], textColor=colors.grey, fontSize=9
        ),
        "Heading": ParagraphStyle(
            "ReportHeading",
            parent=base["Heading2"],
            textColor=OCEAN_NAVY,
            fontSize=13,
            spaceBefore=2,
            spaceAfter=4,
            borderColor=COASTAL_BLUE,
            borderWidth=0,
        ),
        "Body": ParagraphStyle(
            "ReportBody", parent=base["Normal"], fontSize=10, leading=14, spaceAfter=3
        ),
    }


def _kpi_table(kpis: list[dict]) -> Table:
    rows = [["Metric", "Value"]]
    for kpi in kpis:
        rows.append([kpi["label"], f"{kpi['value']}{kpi['unit']}"])

    table = Table(rows, colWidths=[100 * mm, 60 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), OCEAN_NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT_SAND]),
                ("GRID", (0, 0), (-1, -1), 0.5, CLOUD_GREY),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _insight_paragraph(insight: dict, styles: dict) -> Paragraph:
    severity = insight.get("severity", "info")
    color = SEVERITY_COLORS.get(severity, SEVERITY_COLORS["info"])
    text = (
        f'<b>{insight["title"]}</b> '
        f'<font color="{color}" size="8">[{severity.upper()}]</font><br/>'
        f'{insight["description"]}'
    )
    return Paragraph(text, styles["Body"])


def _forecast_paragraphs(forecast: dict, styles: dict) -> list[Paragraph]:
    if not forecast or forecast.get("skipped", True):
        reason = (forecast or {}).get("reason") or "No forecast was generated for this run."
        return [Paragraph(reason, styles["Body"])]

    column = str(forecast.get("column", "")).replace("_", " ")
    points = forecast.get("forecast_points") or []
    lines = [f"Projected {column} for the next {len(points)} period(s):"]
    for p in points:
        lines.append(
            f"&bull; {p['period']}: {p['predicted_value']} "
            f"(range {p['lower_bound']}–{p['upper_bound']})"
        )
    lines.append(forecast.get("caveat", ""))

    return [Paragraph(line, styles["Body"]) for line in lines if line]
