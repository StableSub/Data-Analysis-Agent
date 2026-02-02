import io
import html
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...ai.llm.client import LLMClient
from .models import Report, ReportExport


# ReportService: 생성 → 조회/목록 → 내보내기 흐름을 한곳에 모아 가독성을 높임.
class ReportService:
    def __init__(self, db: Session, storage_dir: Path) -> None:
        self.db = db
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    # --- 생성 ---
    def create_report(
        self,
        *,
        session_id: int,
        analysis_results: List[Dict[str, Any]],
        visualizations: List[Dict[str, Any]],
        insights: List[Any],
        llm_client: LLMClient,
    ) -> Report:
        if not analysis_results and not visualizations and not insights:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NO_RESULTS")

        # 1) 입력 데이터를 payload로 정리
        payload = self._build_payload(
            analysis_results=analysis_results,
            visualizations=visualizations,
            insights=insights,
        )
        # 2) 프롬프트 구성 (question + context)
        question, context, prompt_version = self._build_prompt(payload)

        try:
            # 3) LLM 호출
            summary_text = llm_client.ask(question=question, context=context)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GENERATION_ERROR",
            ) from exc

        # 4) 버전 증가 후 저장
        version = self._next_version(session_id)
        report = Report(
            session_id=session_id,
            version=version,
            summary_text=summary_text,
            payload_json=payload,
            llm_model=getattr(llm_client, "preset", None),
            prompt_version=prompt_version,
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    # --- 조회 ---
    def get_report(self, report_id: str) -> Report:
        report = self.db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="REPORT_NOT_FOUND"
            )
        return report

    # --- 목록 ---
    def list_reports(self, session_id: int) -> List[Report]:
        return (
            self.db.query(Report)
            .filter(Report.session_id == session_id)
            .order_by(Report.version.asc())
            .all()
        )

    # --- 내보내기 ---
    def export_report(self, report_id: str, fmt: str) -> StreamingResponse:
        report = self.get_report(report_id)

        fmt = fmt.lower()
        # 1) 기존 내보내기 파일이 있으면 재사용
        existing = (
            self.db.query(ReportExport)
            .filter(ReportExport.report_id == report_id, ReportExport.format == fmt)
            .order_by(ReportExport.created_at.desc())
            .first()
        )
        if existing and existing.file_path:
            file_path = Path(existing.file_path)
            if file_path.exists():
                return self._stream_file(file_path, fmt)

        try:
            # 2) 새 포맷으로 렌더링
            content, media_type, filename = _render_report(report, fmt)
        except Exception as exc:
            export = ReportExport(
                report_id=report_id,
                format=fmt,
                status="failed",
                error_message=str(exc),
            )
            self.db.add(export)
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="EXPORT_ERROR",
            ) from exc

        # 3) 파일 저장 + DB 기록
        target_dir = self.storage_dir / report_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename
        target_path.write_bytes(content)

        export = ReportExport(
            report_id=report_id,
            format=fmt,
            status="success",
            file_path=str(target_path),
        )
        self.db.add(export)
        self.db.commit()
        return self._stream_bytes(content, fmt, filename)

    def _stream_file(self, file_path: Path, fmt: str) -> StreamingResponse:
        media_type = _media_type(fmt)
        handle = file_path.open("rb")
        headers = {
            "Content-Disposition": f'attachment; filename="{file_path.name}"'
        }
        return StreamingResponse(handle, media_type=media_type, headers=headers)

    def _stream_bytes(self, content: bytes, fmt: str, filename: str) -> StreamingResponse:
        media_type = _media_type(fmt)
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return StreamingResponse(io.BytesIO(content), media_type=media_type, headers=headers)

    # --- 데이터 정리 / 프롬프트 ---
    def _build_payload(
        self,
        *,
        analysis_results: List[Dict[str, Any]],
        visualizations: List[Dict[str, Any]],
        insights: List[Any],
    ) -> Dict[str, Any]:
        summary = self._summarize_analysis_results(analysis_results)
        return {
            "analysis_results": analysis_results,
            "visualizations": visualizations,
            "insights": insights,
            "computed_summary": summary,
            "counts": {
                "analysis_results": len(analysis_results),
                "visualizations": len(visualizations),
                "insights": len(insights),
            },
        }

    def _build_prompt(self, payload: Dict[str, Any]) -> tuple[str, str, str]:
        prompt_version = "v1"
        question = (
            "다음 데이터를 종합하여 간결한 분석 요약 리포트를 작성하라.\n"
            "구성:\n"
            "1) 데이터 요약 (행수, 결측치, 통계값 등)\n"
            "2) 시각화 설명 (차트별 핵심 패턴)\n"
            "3) AI 인사이트 (트렌드/이상치/상관관계)\n"
            "4) 최종 요약문\n"
            "가능한 한 구체적 수치와 근거를 포함하고, 불확실하면 추정이라고 명시하라."
        )
        context = json.dumps(payload, ensure_ascii=False)
        return question, context, prompt_version

    def _summarize_analysis_results(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        tables: List[Dict[str, Any]] = []
        for idx, item in enumerate(analysis_results):
            name = (
                item.get("name")
                or item.get("title")
                or item.get("id")
                or f"result_{idx + 1}"
            )
            data = item.get("data")
            if not isinstance(data, list) or not data or not isinstance(data[0], dict):
                continue

            df = pd.DataFrame(data)
            row_count = int(df.shape[0])
            col_count = int(df.shape[1])
            missing = df.isna().sum().to_dict()
            numeric_cols = df.select_dtypes(include="number")
            numeric_summary = {
                col: {
                    "mean": _safe_float(numeric_cols[col].mean()),
                    "min": _safe_float(numeric_cols[col].min()),
                    "max": _safe_float(numeric_cols[col].max()),
                }
                for col in numeric_cols.columns
            }
            tables.append(
                {
                    "name": name,
                    "row_count": row_count,
                    "col_count": col_count,
                    "missing_counts": missing,
                    "numeric_summary": numeric_summary,
                }
            )
        return {"tables": tables}

    # --- 버전 관리 ---
    def _next_version(self, session_id: int) -> int:
        value = (
            self.db.query(func.max(Report.version))
            .filter(Report.session_id == session_id)
            .scalar()
        )
        return int(value or 0) + 1


# --- 렌더링 헬퍼 (txt/md/pdf) ---
def _render_report(report: Report, fmt: str) -> Tuple[bytes, str, str]:
    fmt = fmt.lower()
    if fmt == "txt":
        content = _render_txt(report)
        filename = _filename(report, "txt")
        return content.encode("utf-8"), "text/plain", filename
    if fmt == "md":
        content = _render_md(report)
        filename = _filename(report, "md")
        return content.encode("utf-8"), "text/markdown", filename
    if fmt == "pdf":
        content = _render_pdf(report)
        filename = _filename(report, "pdf")
        return content, "application/pdf", filename
    raise ValueError(f"Unsupported format: {fmt}")


def _render_txt(report: Report) -> str:
    return report.summary_text or ""


def _render_md(report: Report) -> str:
    created_at = _fmt_dt(report.created_at)
    header = (
        f"# 분석 리포트\n\n"
        f"- Report ID: {report.id}\n"
        f"- Session ID: {report.session_id}\n"
        f"- Version: {report.version}\n"
        f"- Created At: {created_at}\n\n"
        f"---\n\n"
    )
    return header + (report.summary_text or "")


def _render_pdf(report: Report) -> bytes:
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError(
            "PDF export requires 'weasyprint'. Install with: pip install weasyprint"
        ) from exc

    regular_font = _pick_existing_font(
        [
            os.getenv("REPORT_PDF_FONT_REGULAR"),
            "storage/fonts/NotoSansKR-Regular.ttf",
            "/Library/Fonts/NanumGothic.ttf",
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            "/Library/Fonts/AppleGothic.ttf",
        ]
    )
    bold_font = _pick_existing_font(
        [
            os.getenv("REPORT_PDF_FONT_BOLD"),
            "storage/fonts/NotoSansKR-Bold.ttf",
            "/Library/Fonts/NanumGothicBold.ttf",
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            "/Library/Fonts/AppleGothic.ttf",
        ]
    ) or regular_font

    css = _build_pdf_css(regular_font=regular_font, bold_font=bold_font)
    summary_html = html.escape(report.summary_text or "").replace("\n", "<br />")
    payload = report.payload_json if isinstance(report.payload_json, dict) else {}
    overview_html = _build_overview_html(payload)
    table_summary_html = _build_table_summary_html(payload)
    visualization_html = _build_visualization_html(payload)
    insight_html = _build_insight_html(payload)
    html_doc = f"""
<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8" />
    <style>
      {css}
    </style>
  </head>
  <body>
    <div class="report">
      <h1>분석 리포트</h1>
      <div class="meta">
        <div><strong>Report ID:</strong> {html.escape(str(report.id))}</div>
        <div><strong>Session ID:</strong> {html.escape(str(report.session_id))}</div>
        <div><strong>Version:</strong> {html.escape(str(report.version))}</div>
        <div><strong>Created At:</strong> {html.escape(_fmt_dt(report.created_at))}</div>
      </div>
      {overview_html}
      {table_summary_html}
      {visualization_html}
      {insight_html}
      <section>
        <h2>최종 요약</h2>
        <p class="summary">{summary_html}</p>
      </section>
    </div>
  </body>
</html>
"""
    return HTML(string=html_doc, base_url=str(Path.cwd())).write_pdf()


def _build_pdf_css(regular_font: Optional[str], bold_font: Optional[str]) -> str:
    font_family = "sans-serif"
    rules: List[str] = []
    if regular_font:
        regular_uri = Path(regular_font).resolve().as_uri()
        rules.append(
            "@font-face { font-family: 'ReportKorean'; "
            f"src: url('{regular_uri}'); font-weight: 400; }}"
        )
        font_family = "'ReportKorean', sans-serif"
    if bold_font:
        bold_uri = Path(bold_font).resolve().as_uri()
        rules.append(
            "@font-face { font-family: 'ReportKorean'; "
            f"src: url('{bold_uri}'); font-weight: 700; }}"
        )
        font_family = "'ReportKorean', sans-serif"

    rules.append(
        f"""
        @page {{ size: A4; margin: 24mm 18mm; }}
        body {{ font-family: {font_family}; font-size: 11pt; color: #222; line-height: 1.6; }}
        h1 {{ font-size: 20pt; margin: 0 0 6mm; }}
        h2 {{ font-size: 14pt; margin: 8mm 0 3mm; border-left: 3px solid #8aa9ff; padding-left: 3mm; }}
        .meta {{ font-size: 10pt; color: #444; margin-bottom: 6mm; }}
        .meta div {{ margin-bottom: 2mm; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 4mm; margin-bottom: 4mm; }}
        .kpi-card {{ border: 1px solid #ddd; border-radius: 3mm; padding: 3mm; background: #fafbff; }}
        .kpi-label {{ font-size: 9pt; color: #666; margin-bottom: 1mm; }}
        .kpi-value {{ font-size: 14pt; font-weight: 700; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 2mm; }}
        th, td {{ border: 1px solid #ddd; padding: 2.2mm; font-size: 10pt; text-align: left; vertical-align: top; }}
        th {{ background: #f4f6fb; }}
        ul {{ margin: 2mm 0 0 0; padding-left: 5mm; }}
        li {{ margin-bottom: 1.2mm; }}
        .summary {{ white-space: pre-wrap; margin: 0; }}
        """
    )
    return "\n".join(rules)


def _build_overview_html(payload: Dict[str, Any]) -> str:
    counts = payload.get("counts", {}) if isinstance(payload, dict) else {}
    analysis_count = int(counts.get("analysis_results", 0) or 0)
    visualization_count = int(counts.get("visualizations", 0) or 0)
    insight_count = int(counts.get("insights", 0) or 0)
    return f"""
    <section>
      <h2>리포트 개요</h2>
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">분석 결과 수</div>
          <div class="kpi-value">{analysis_count}</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">시각화 수</div>
          <div class="kpi-value">{visualization_count}</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">인사이트 수</div>
          <div class="kpi-value">{insight_count}</div>
        </div>
      </div>
    </section>
    """


def _build_table_summary_html(payload: Dict[str, Any]) -> str:
    computed = payload.get("computed_summary", {}) if isinstance(payload, dict) else {}
    tables = computed.get("tables", []) if isinstance(computed, dict) else []
    if not tables:
        return "<section><h2>데이터 요약</h2><p>요약 가능한 테이블 데이터가 없습니다.</p></section>"

    rows: List[str] = []
    for table in tables:
        name = html.escape(str(table.get("name", "-")))
        row_count = html.escape(str(table.get("row_count", "-")))
        col_count = html.escape(str(table.get("col_count", "-")))
        missing_counts = table.get("missing_counts", {})
        missing_text = ", ".join(
            f"{k}:{v}" for k, v in missing_counts.items()
        ) if isinstance(missing_counts, dict) and missing_counts else "-"
        rows.append(
            "<tr>"
            f"<td>{name}</td>"
            f"<td>{row_count}</td>"
            f"<td>{col_count}</td>"
            f"<td>{html.escape(missing_text)}</td>"
            "</tr>"
        )
    rows_html = "\n".join(rows)
    return f"""
    <section>
      <h2>데이터 요약</h2>
      <table>
        <thead>
          <tr>
            <th>테이블</th>
            <th>행 수</th>
            <th>열 수</th>
            <th>결측치</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </section>
    """


def _build_visualization_html(payload: Dict[str, Any]) -> str:
    visualizations = payload.get("visualizations", []) if isinstance(payload, dict) else []
    if not isinstance(visualizations, list) or not visualizations:
        return "<section><h2>시각화 설명</h2><p>시각화 정보가 없습니다.</p></section>"

    items: List[str] = []
    for item in visualizations:
        if isinstance(item, dict):
            chart_type = html.escape(str(item.get("chart_type", item.get("type", "unknown"))))
            title = html.escape(str(item.get("title", "제목 없음")))
            summary = html.escape(str(item.get("summary", "")))
            text = f"[{chart_type}] {title}"
            if summary:
                text += f" - {summary}"
            items.append(f"<li>{text}</li>")
        else:
            items.append(f"<li>{html.escape(str(item))}</li>")

    return (
        "<section><h2>시각화 설명</h2>"
        f"<ul>{''.join(items)}</ul>"
        "</section>"
    )


def _build_insight_html(payload: Dict[str, Any]) -> str:
    insights = payload.get("insights", []) if isinstance(payload, dict) else []
    if not isinstance(insights, list) or not insights:
        return "<section><h2>AI 인사이트</h2><p>인사이트가 없습니다.</p></section>"

    items = [f"<li>{html.escape(str(item))}</li>" for item in insights]
    return (
        "<section><h2>AI 인사이트</h2>"
        f"<ul>{''.join(items)}</ul>"
        "</section>"
    )


def _pick_existing_font(candidates: List[Optional[str]]) -> Optional[str]:
    for path in candidates:
        if not path:
            continue
        candidate = Path(path)
        if candidate.exists():
            return str(candidate)
    return None


def _filename(report: Report, ext: str) -> str:
    return f"report_{report.id}_v{report.version}.{ext}"


def _fmt_dt(value: datetime | None) -> str:
    if not value:
        return ""
    return value.isoformat()


def _media_type(fmt: str) -> str:
    if fmt == "txt":
        return "text/plain"
    if fmt == "md":
        return "text/markdown"
    if fmt == "pdf":
        return "application/pdf"
    return "application/octet-stream"


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return None
