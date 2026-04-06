from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .schemas import AnalysisOutputPayload, SandboxExecutionResult

_FORBIDDEN_CALLS = {
    "open",
    "exec",
    "eval",
    "compile",
    "__import__",
    "input",
    "globals",
    "locals",
    "vars",
    "getattr",
    "setattr",
    "delattr",
}
_FORBIDDEN_MODULES = {
    "os",
    "sys",
    "subprocess",
    "socket",
    "pathlib",
    "shutil",
    "requests",
}


def validate_analysis_source_code(code: str, *, require_print: bool) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ValueError(f"generated code is not valid python: {exc}") from exc

    has_print = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise ValueError("generated code cannot import modules")
        if isinstance(node, ast.Call):
            call_name = _extract_name(node.func)
            if call_name in _FORBIDDEN_CALLS:
                raise ValueError(f"generated code cannot call {call_name}")
            if call_name == "print":
                has_print = True
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_MODULES:
            raise ValueError(f"generated code cannot access {node.id}")
        if isinstance(node, ast.Attribute):
            root_name = _extract_root_name(node)
            if root_name in _FORBIDDEN_MODULES:
                raise ValueError(f"generated code cannot access {root_name}")

    if require_print and not has_print:
        raise ValueError("generated code must print a single JSON payload")


def _extract_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _extract_root_name(node: ast.Attribute) -> str | None:
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        current = current.value
    if isinstance(current, ast.Name):
        return current.id
    return None


class AnalysisSandbox:
    """Execute generated analysis code in an isolated Python subprocess."""

    def __init__(
        self,
        *,
        python_executable: str | None = None,
        timeout_seconds: int = 15,
        max_stdout_bytes: int = 256_000,
        max_stderr_bytes: int = 256_000,
    ) -> None:
        self.python_executable = python_executable or sys.executable
        self.timeout_seconds = timeout_seconds
        self.max_stdout_bytes = max_stdout_bytes
        self.max_stderr_bytes = max_stderr_bytes

    # 코드 파일을 만들어서 실행하고 결과를 받아 표준 구조로 반환한다.
    def execute(
        self,
        *,
        code: str,
        dataset_path: str,
    ) -> SandboxExecutionResult:
        # 코드가 비어있는지 검사
        source_code = str(code or "").strip()
        if not source_code:
            return SandboxExecutionResult(
                ok=False,
                error_type="runtime",
                message="analysis code is empty",
            )

        validation_error = self._validate_source_code(source_code)
        if validation_error is not None:
            return SandboxExecutionResult(
                ok=False,
                error_type="runtime",
                message=validation_error,
            )

        # 실행용 임시 폴더를 만들고 그 안에 run_analysis.py를 생성한다.
        with tempfile.TemporaryDirectory(prefix="analysis_exec_") as temp_dir:
            workdir = Path(temp_dir)
            script_path = workdir / "run_analysis.py"
            script_path.write_text(
                self._build_script(code=source_code, dataset_path=dataset_path),
                encoding="utf-8",
            )

            try:
                # subprocess 실행
                completed = subprocess.run(
                    [self.python_executable, "-I", str(script_path)],
                    cwd=str(workdir),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    env=self._build_subprocess_env(),
                )
            # timeout 처리
            except subprocess.TimeoutExpired as exc:
                return SandboxExecutionResult(
                    ok=False,
                    error_type="timeout",
                    message="analysis execution timed out",
                    stderr=str(exc.stderr or ""),
                )
            # 기타 실행 예외 처리
            except Exception as exc:
                return SandboxExecutionResult(
                    ok=False,
                    error_type="runtime",
                    message=f"failed to execute analysis code: {exc}",
                )
            # 프로세스 종료 코드 검사
            stderr_text = str(completed.stderr or "")
            if completed.returncode != 0:
                return SandboxExecutionResult(
                    ok=False,
                    error_type="runtime",
                    message="analysis execution failed",
                    stderr=stderr_text,
                )
            stdout_size = len((completed.stdout or "").encode("utf-8"))
            stderr_size = len(stderr_text.encode("utf-8"))
            if stdout_size > self.max_stdout_bytes or stderr_size > self.max_stderr_bytes:
                return SandboxExecutionResult(
                    ok=False,
                    error_type="runtime",
                    message="analysis execution output exceeded size limit",
                    stderr=stderr_text[:4000],
                )
            # stdout 비었는지 검사
            stdout_text = str(completed.stdout or "").strip()
            if not stdout_text:
                return SandboxExecutionResult(
                    ok=False,
                    error_type="invalid_json",
                    message="analysis execution produced empty stdout",
                    stderr=stderr_text,
                )
            # stdout 문자열을 JSON으로 파싱한다.
            try:
                payload = json.loads(stdout_text)
            except json.JSONDecodeError:
                return SandboxExecutionResult(
                    ok=False,
                    error_type="invalid_json",
                    message="analysis execution did not return valid JSON",
                    stderr=stderr_text,
                )
            # 출력 스키마를 검증한다.
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
            "import json\n"
            "import pandas as pd\n"
            f"dataset_path = str(Path({dataset_path!r}).resolve())\n"
            "df = pd.read_csv(dataset_path)\n\n"
            f"{code}\n"
        )

    def _build_subprocess_env(self) -> dict[str, str]:
        env = {
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUNBUFFERED": "1",
        }
        path_value = os.environ.get("PATH")
        if path_value:
            env["PATH"] = path_value
        return env

    def _validate_source_code(self, code: str) -> str | None:
        try:
            validate_analysis_source_code(code, require_print=False)
        except ValueError as exc:
            return str(exc)
        return None
