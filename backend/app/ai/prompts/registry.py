"""
Prompt registry for file-based prompt templates.

Each entry maps a stable prompt key to:
- the directory under `backend/app/ai/prompts`
- the variables required to render the template safely
"""

from __future__ import annotations

from typing import Final, TypedDict


class PromptMeta(TypedDict):
    dir: str
    required_vars: list[str]


PROMPT_REGISTRY: Final[dict[str, PromptMeta]] = {
    "intake.intent_classifier": {
        "dir": "intake",
        "required_vars": ["user_input"],
    },
    "preprocess.decision": {
        "dir": "preprocess/decision",
        "required_vars": ["user_input", "dataset_profile_json"],
    },
    "preprocess.plan": {
        "dir": "preprocess/plan",
        "required_vars": ["user_input", "source_id", "dataset_profile_json"],
    },
    "visualization.chart_selection": {
        "dir": "visualization",
        "required_vars": [
            "query",
            "numeric_columns",
            "datetime_columns",
            "categorical_columns",
        ],
    },
    "rag.insight_synthesis": {
        "dir": "rag",
        "required_vars": ["question", "context"],
    },
    "answer.general_question": {
        "dir": "answer/general_question",
        "required_vars": ["user_input", "request_context"],
    },
    "answer.data_qa": {
        "dir": "answer/data_qa",
        "required_vars": ["question", "merged_context_json"],
    },
    "report.default": {
        "dir": "report",
        "required_vars": [
            "user_question",
            "metrics_json",
            "insight_summary",
            "visualization_summary",
        ],
    },
    "service.report_create_seed": {
        "dir": "service",
        "required_vars": [],
    },
}
