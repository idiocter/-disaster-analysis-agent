"""Renders the final report from job state: Jinja2 -> HTML (always) and PDF
(via WeasyPrint). The Methodology & Limitations section is populated from
`limitations_note`, not left implicit -- see plan.md: the risk model is a
heuristic index and must say so in the report itself, not just in code
comments.
"""

from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_report(
    *,
    job_id: str,
    zone_name: str,
    date_start: str,
    date_end: str,
    narrative_text: str,
    boundary_source: str,
    dataset_note: str,
    gis_results: dict,
    risk_results: list[dict],
    risk_explanations: list[str],
    static_map_path: str | None,
    limitations_note: str,
    out_dir: str,
) -> dict[str, str]:
    env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)
    template = env.get_template("report_template.html.j2")

    html = template.render(
        zone_name=zone_name,
        date_start=date_start,
        date_end=date_end,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        narrative_text=narrative_text,
        boundary_source=boundary_source,
        dataset_note=dataset_note,
        gis_results=gis_results,
        risk_results=risk_results,
        risk_explanations=risk_explanations,
        static_map_path=static_map_path,
        limitations_note=limitations_note,
    )

    out_dir_path = Path(out_dir) / job_id
    out_dir_path.mkdir(parents=True, exist_ok=True)

    html_path = out_dir_path / "report.html"
    html_path.write_text(html)

    pdf_path = out_dir_path / "report.pdf"
    try:
        from weasyprint import HTML

        HTML(string=html, base_url=str(out_dir_path)).write_pdf(str(pdf_path))
    except Exception as exc:  # noqa: BLE001 -- PDF is best-effort; HTML is the guaranteed output
        pdf_path = None
        print(f"warning: PDF generation failed ({exc}); HTML report still written")

    return {"html": str(html_path), "pdf": str(pdf_path) if pdf_path else ""}
