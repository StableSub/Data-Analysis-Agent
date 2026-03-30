from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from .schemas import AnalysisOutputPayload, SandboxExecutionResult


class AnalysisSandbox:
    """Execute generated analysis code in an isolated Python subprocess."""

    def __init__(
        self,
        *,
        python_executable: str | None = None,
        timeout_seconds: int = 15,
    ) -> None:
        self.python_executable = python_executable or sys.executable
        self.timeout_seconds = timeout_seconds

    def execute(
        self,
        *,
        code: str,
        dataset_path: str,
    ) -> SandboxExecutionResult:
        source_code = str(code or "").strip()
        if not source_code:
            return SandboxExecutionResult(
                ok=False,
                error_type="runtime",
                message="analysis code is empty",
            )

        with tempfile.TemporaryDirectory(prefix="analysis_exec_") as temp_dir:
            workdir = Path(temp_dir)
            script_path = workdir / "run_analysis.py"
            script_path.write_text(
                self._build_script(code=source_code, dataset_path=dataset_path),
                encoding="utf-8",
            )

            try:
                completed = subprocess.run(
                    [self.python_executable, str(script_path)],
                    cwd=str(workdir),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                return SandboxExecutionResult(
                    ok=False,
                    error_type="timeout",
                    message="analysis execution timed out",
                    stderr=str(exc.stderr or ""),
                )
            except Exception as exc:  # pragma: no cover - defensive runtime branch
                return SandboxExecutionResult(
                    ok=False,
                    error_type="runtime",
                    message=f"failed to execute analysis code: {exc}",
                )

            stderr_text = str(completed.stderr or "")
            if completed.returncode != 0:
                return SandboxExecutionResult(
                    ok=False,
                    error_type="runtime",
                    message="analysis execution failed",
                    stderr=stderr_text,
                )

            stdout_text = str(completed.stdout or "").strip()
            if not stdout_text:
                return SandboxExecutionResult(
                    ok=False,
                    error_type="invalid_json",
                    message="analysis execution produced empty stdout",
                    stderr=stderr_text,
                )

            try:
                payload = json.loads(stdout_text)
            except json.JSONDecodeError:
                return SandboxExecutionResult(
                    ok=False,
                    error_type="invalid_json",
                    message="analysis execution did not return valid JSON",
                    stderr=stderr_text,
                )

            try:
                output_payload = AnalysisOutputPayload.model_validate(payload)
            except Exception as exc:
                return SandboxExecutionResult(
                    ok=False,
                    error_type="invalid_json",
                    message=f"analysis output schema validation failed: {exc}",
                    stderr=stderr_text,
                )

            return SandboxExecutionResult(
                ok=True,
                stdout_json=output_payload,
                stderr=stderr_text,
            )

    def _build_script(self, *, code: str, dataset_path: str) -> str:
        return (
            "from pathlib import Path\n"
            f"dataset_path = str(Path({dataset_path!r}).resolve())\n\n"
            f"{code}\n"
        )
