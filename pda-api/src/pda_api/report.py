"""Design-review report: one content model, rendered as HTML and as PDF.

`build_report` collects values the other endpoints already return. `blocks`
turns them into headings, paragraphs and tables, and both renderers print those
blocks as they are, so the two formats cannot disagree and neither computes a
number of its own.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from pda_api.benchmark import Trial
from pda_api.restrictiveness import HIGH, score_design, summarise
from pda_api.schemas import Assessment, CitedTrial, Forecast, Report, Suggestion
from pda_api.similarity import to_schema
from pda_api.suggestions import ChangeError, Context, suggest

TRIAL_URL = "https://clinicaltrials.gov/study/"
NCT_ID = re.compile(r"\bNCT\d{8}\b")
DISCLAIMER = (
    "Demo output. The protocol is synthetic and the benchmark is public ClinicalTrials.gov registry data. "
    "The forecast and the termination risk rest on modelling assumptions and are not a prediction for a real study."
)


@dataclass(frozen=True)
class Heading:
    text: str
    level: int = 2


@dataclass(frozen=True)
class Text:
    text: str


@dataclass(frozen=True)
class Grid:
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    widths: tuple[float, ...] | None = None  # relative column widths


Block = Heading | Text | Grid


def build_report(
    protocol_id: str,
    document: str,
    created_at: datetime,
    context: Context,
    ranked: list[tuple[Trial, float]],
    accept: list[str] | None = None,
) -> Report:
    """Assemble the report. `accept` holds the IDs of the suggestions the author accepted."""
    design = context.design
    scores = score_design(design, context.similar)
    assessment = Assessment(
        protocol_id=protocol_id,
        overall_score=round(sum(score.score for score in scores) / len(scores)) if scores else 0,
        red_flags=sum(1 for score in scores if score.score >= HIGH),
        summary=summarise(context.similar),
        criteria=scores,
        similar_trials=[to_schema(trial, similarity) for trial, similarity in ranked],
    )
    baseline = context.baseline
    suggestions, _ = suggest(context)
    by_id = {suggestion.id: suggestion for suggestion in suggestions}
    wanted = list(dict.fromkeys(accept or []))
    unknown = [identifier for identifier in wanted if identifier not in by_id]
    if unknown:
        raise ChangeError(f"Not a validated suggestion for this protocol: {', '.join(unknown)}")
    accepted = [by_id[identifier] for identifier in wanted]
    scenario = context.scenario([suggestion.change for suggestion in accepted]) if accepted else None
    return Report(
        protocol_id=protocol_id,
        document=document,
        created_at=created_at,
        design=design,
        assessment=assessment,
        baseline=baseline,
        scenario=scenario,
        accepted_changes=accepted,
        cited_trials=_cited(context, assessment, baseline, accepted),
    )


def _cited(
    context: Context, assessment: Assessment, baseline: Forecast, accepted: list[Suggestion]
) -> list[CitedTrial]:
    titles = {trial.nct_id: trial.title for trial in context.benchmark.trials}
    reasons: dict[str, list[str]] = {}

    def cite(nct_id: str, reason: str) -> None:
        if reason not in reasons.setdefault(nct_id, []):
            reasons[nct_id].append(reason)

    for suggestion in accepted:
        for nct_id in suggestion.cited_trial_ids:
            cite(nct_id, f"Change {suggestion.id}")
    for nct_id in baseline.termination_risk.trial_ids:
        cite(nct_id, "Termination risk")
    for score in assessment.criteria:
        for trial in score.driving_trials:
            titles.setdefault(trial.nct_id, trial.title)
            cite(trial.nct_id, f"Score of {score.criterion_id}")
    return [
        CitedTrial(nct_id=nct_id, title=titles.get(nct_id), cited_for=reasons[nct_id]) for nct_id in sorted(reasons)
    ]


def num(value: float | None, digits: int = 1) -> str:
    return "not stated" if value is None else f"{value:,.{digits}f}"


def pct(share: float) -> str:
    return f"{share * 100:.1f}%"


def _forecast_grid(baseline: Forecast, scenario: Forecast | None) -> Grid:
    def row(label: str, read: Callable[[Forecast], str]) -> tuple[str, ...]:
        return (label, read(baseline), read(scenario)) if scenario is not None else (label, read(baseline))

    headers = ("", "Draft", "With accepted changes") if scenario is not None else ("", "Draft")
    return Grid(
        headers=headers,
        rows=(
            row("P50 months to full enrollment", lambda f: num(f.p50_months)),
            row("P90 months to full enrollment", lambda f: num(f.p90_months)),
            row("Sites", lambda f: str(f.sites)),
            row("Site activation ramp (months)", lambda f: num(f.ramp_months)),
            row("Eligibility rate multiplier", lambda f: num(f.rate_multiplier, 2)),
            row("Risk of termination for low accrual", lambda f: pct(f.termination_risk.risk)),
            row("Risk level", lambda f: f.termination_risk.level),
        ),
        widths=(3, 2, 2)[: len(headers)],
    )


def blocks(report: Report) -> list[Block]:
    design, assessment, baseline = report.design, report.assessment, report.baseline
    risk = baseline.termination_risk
    population = design.population
    countries = ", ".join(
        f"{item.country} ({item.sites} sites)" if item.sites else item.country for item in design.planned_countries
    )
    out: list[Block] = [
        Heading(f"Design review: {design.title or report.document}", level=1),
        Text(
            f"Source document: {report.document}. Protocol ID: {report.protocol_id}. "
            f"Uploaded {report.created_at:%Y-%m-%d %H:%M} UTC."
        ),
        Text(DISCLAIMER),
        Heading("1. Extracted design"),
        Grid(
            headers=("Field", "Value"),
            rows=(
                ("Indication", (design.indication or "not found").replace("_", " ")),
                ("Phase", design.phase or "not found"),
                ("Target enrollment", f"{design.target_enrollment:,}" if design.target_enrollment else "not found"),
                ("Sites", str(design.site_count) if design.site_count else "not found"),
                ("Planned countries", countries or "not found"),
                ("Age", f"{num(population.min_age, 0)} to {num(population.max_age, 0)} years"),
                ("Sex", population.sex),
                ("Eligibility criteria", str(len(design.criteria))),
            ),
            widths=(1, 3),
        ),
        Heading("2. Eligibility restrictiveness"),
        Text(
            f"Overall score {assessment.overall_score} of 100 against {assessment.summary.n_similar} similar completed "
            f"or terminated trials. {assessment.red_flags} criteria are red flags (score {HIGH} or more)."
        ),
        Grid(
            headers=("ID", "Criterion", "Score", "Level", "Why", "Driving trials"),
            rows=tuple(
                (
                    score.criterion_id,
                    score.text,
                    str(score.score),
                    score.level,
                    score.rationale,
                    ", ".join(trial.nct_id for trial in score.driving_trials),
                )
                for score in assessment.criteria
            ),
            widths=(0.6, 3.4, 0.8, 1, 3.4, 2),
        ),
        Heading("3. Enrollment forecast and termination risk"),
        Text(
            f"Months to enroll {baseline.target_enrollment:,} patients, from {baseline.simulations:,} simulations with "
            f"seed {baseline.seed}. Per-site accrual is drawn from {baseline.n_rates} benchmark rates "
            f"(median {num(baseline.median_benchmark_rate, 2)} patients per site per month)."
        ),
        _forecast_grid(baseline, report.scenario),
        Text(
            f"Termination risk: {risk.similar_low_accrual} of {risk.n_similar} similar trials were terminated for low "
            f"accrual ({pct(risk.indication_phase_share)} across the indication and phase). The smoothed share, "
            f"{pct(risk.baseline_share)}, is multiplied by {num(risk.adjustment, 2)} for the forecast length against "
            f"the benchmark median duration."
        ),
        Heading("4. Accepted changes"),
    ]
    if not report.accepted_changes:
        out.append(Text("No changes were accepted."))
    for suggestion in report.accepted_changes:
        out += [
            Heading(f"{suggestion.id}. {suggestion.title}", level=3),
            Text(suggestion.rationale),
            Text(
                f"Applied alone it saves {num(suggestion.months_saved)} months at P50. "
                f"Cited benchmark trials ({len(suggestion.cited_trial_ids)}): {', '.join(suggestion.cited_trial_ids)}."
            ),
        ]
    out += [
        Heading("5. Cited trials"),
        Grid(
            headers=("Trial ID", "Title", "Cited for"),
            rows=tuple((trial.nct_id, trial.title or "", ", ".join(trial.cited_for)) for trial in report.cited_trials),
            widths=(1.2, 4, 2),
        ),
    ]
    return out


CSS = """
body{font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:#1c2333;
margin:0 auto;max-width:1040px;padding:24px}
h1{font-size:26px;margin:0 0 8px}h2{font-size:19px;margin:28px 0 8px;border-bottom:2px solid #d9dee8;padding-bottom:4px}
h3{font-size:16px;margin:18px 0 4px}p{margin:6px 0}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}
th,td{border:1px solid #d9dee8;padding:6px 8px;text-align:left;vertical-align:top}th{background:#f2f4f8}
a{color:#b5450f}
@media print{body{max-width:none;padding:0}a{color:inherit;text-decoration:none}}
"""


def _linked(text: str) -> str:
    return NCT_ID.sub(lambda m: f'<a href="{TRIAL_URL}{m.group()}">{m.group()}</a>', escape(text))


def render_html(report: Report) -> str:
    """A self-contained page: inline styles, no scripts, no external assets."""
    body: list[str] = []
    for block in blocks(report):
        if isinstance(block, Heading):
            body.append(f"<h{block.level}>{escape(block.text)}</h{block.level}>")
        elif isinstance(block, Text):
            body.append(f"<p>{_linked(block.text)}</p>")
        else:
            head = "".join(f"<th>{escape(cell)}</th>" for cell in block.headers)
            rows = "".join(
                "<tr>" + "".join(f"<td>{_linked(cell)}</td>" for cell in row) + "</tr>" for row in block.rows
            )
            body.append(f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>')
    title = escape(f"Design review: {report.design.title or report.document}")
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{title}</title><style>{CSS}</style></head>\n<body>\n" + "\n".join(body) + "\n</body></html>\n"
    )


def _latin(text: str) -> str:
    """The built-in PDF fonts cover Windows-1252 only; other characters print as '?'."""
    return escape(text.encode("cp1252", "replace").decode("cp1252"), quote=False)


def render_pdf(report: Report) -> bytes:
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9, leading=12)
    cell = ParagraphStyle("cell", parent=body, fontSize=7.5, leading=9.5)
    head = ParagraphStyle("head", parent=cell, fontName="Helvetica-Bold")
    headings = {1: styles["Title"], 2: styles["Heading2"], 3: styles["Heading3"]}
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"Design review: {report.design.title or report.document}",
        author="Protocol Design Advisor",
    )
    story: list[Flowable] = []
    for block in blocks(report):
        if isinstance(block, Heading):
            story.append(Paragraph(_latin(block.text), headings[block.level]))
        elif isinstance(block, Text):
            story.append(Paragraph(_latin(block.text), body))
        else:
            widths = block.widths or tuple(1.0 for _ in block.headers)
            data = [[Paragraph(_latin(text), head) for text in block.headers]]
            data += [[Paragraph(_latin(text), cell) for text in row] for row in block.rows]
            table = Table(data, colWidths=[doc.width * width / sum(widths) for width in widths], repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c5ccd9")),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f4f8")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            story += [Spacer(1, 4), table, Spacer(1, 6)]
    doc.build(story)
    return buffer.getvalue()
