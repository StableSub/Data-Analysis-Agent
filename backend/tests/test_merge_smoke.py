from __future__ import annotations

import importlib
import unittest
from unittest.mock import patch


class _FakeEmbedder:
    model_name = "fake"
    embedding_dim = 1


class MergeSmokeTests(unittest.TestCase):
    def test_import_main(self) -> None:
        module = importlib.import_module("backend.app.main")
        self.assertIsNotNone(module.app)

    def test_import_orchestration_modules(self) -> None:
        modules = [
            "backend.app.orchestration.builder",
            "backend.app.orchestration.workflows.preprocess",
            "backend.app.orchestration.workflows.rag",
            "backend.app.orchestration.workflows.report",
            "backend.app.orchestration.workflows.visualization",
        ]
        for module_name in modules:
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                self.assertIsNotNone(module)

    def test_agent_client_preserves_request_context(self) -> None:
        from backend.app.orchestration.client import AgentClient

        client = AgentClient()
        state, early_answer = client._build_state(
            session_id="session-1",
            run_id="run-1",
            question="질문",
            context="추가 컨텍스트",
            dataset=None,
            model_id=None,
        )

        self.assertIsNone(early_answer)
        self.assertEqual(state["request_context"], "추가 컨텍스트")

    def test_build_workflow_without_legacy_imports(self) -> None:
        from backend.app.core.db import SessionLocal
        from backend.app.orchestration.client import AgentClient

        client = AgentClient()
        db = SessionLocal()
        try:
            with patch(
                "backend.app.orchestration.service_factory.get_embedder",
                return_value=_FakeEmbedder(),
            ):
                workflow = client._build_workflow(db=db)
        finally:
            db.close()

        self.assertIsNotNone(workflow)


if __name__ == "__main__":
    unittest.main()
