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
            "backend.app.orchestration.client",
            "backend.app.orchestration.dependencies",
            "backend.app.orchestration.workflows.preprocess",
            "backend.app.orchestration.workflows.rag",
            "backend.app.orchestration.workflows.report",
            "backend.app.orchestration.workflows.visualization",
        ]
        for module_name in modules:
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                self.assertIsNotNone(module)

    def test_service_factory_module_is_removed(self) -> None:
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("backend.app.orchestration.service_factory")

    def test_chat_dependencies_import_agent_from_orchestration_dependencies(self) -> None:
        chat_dependencies = importlib.import_module("backend.app.modules.chat.dependencies")
        orchestration_dependencies = importlib.import_module(
            "backend.app.orchestration.dependencies"
        )
        self.assertIs(chat_dependencies.get_agent, orchestration_dependencies.get_agent)

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

    def test_build_orchestration_services_uses_module_builders(self) -> None:
        from backend.app.orchestration.dependencies import build_orchestration_services

        db = object()
        agent = object()
        dataset_repository = object()
        dataset_reader = object()
        preprocess_processor = object()
        preprocess_service = object()
        rag_repository = object()
        rag_service = object()
        report_repository = object()
        report_service = object()
        visualization_service = object()

        with (
            patch(
                "backend.app.orchestration.dependencies.build_data_source_repository",
                return_value=dataset_repository,
            ) as build_dataset_repository,
            patch(
                "backend.app.orchestration.dependencies.build_dataset_reader",
                return_value=dataset_reader,
            ) as build_dataset_reader,
            patch(
                "backend.app.orchestration.dependencies.build_preprocess_processor",
                return_value=preprocess_processor,
            ) as build_preprocess_processor,
            patch(
                "backend.app.orchestration.dependencies.build_preprocess_service",
                return_value=preprocess_service,
            ) as build_preprocess_service,
            patch(
                "backend.app.orchestration.dependencies.build_rag_repository",
                return_value=rag_repository,
            ) as build_rag_repository,
            patch(
                "backend.app.orchestration.dependencies.build_rag_service",
                return_value=rag_service,
            ) as build_rag_service,
            patch(
                "backend.app.orchestration.dependencies.build_report_repository",
                return_value=report_repository,
            ) as build_report_repository,
            patch(
                "backend.app.orchestration.dependencies.build_report_service",
                return_value=report_service,
            ) as build_report_service,
            patch(
                "backend.app.orchestration.dependencies.build_visualization_service",
                return_value=visualization_service,
            ) as build_visualization_service,
        ):
            services = build_orchestration_services(db=db, agent=agent)

        build_dataset_repository.assert_called_once_with(db)
        build_dataset_reader.assert_called_once_with()
        build_preprocess_processor.assert_called_once_with()
        build_preprocess_service.assert_called_once_with(
            repository=dataset_repository,
            reader=dataset_reader,
            processor=preprocess_processor,
        )
        build_rag_repository.assert_called_once_with(db)
        build_rag_service.assert_called_once_with(
            repository=rag_repository,
            dataset_repository=dataset_repository,
            answer_agent=agent,
        )
        build_report_repository.assert_called_once_with(db)
        build_report_service.assert_called_once_with(
            repository=report_repository,
            dataset_repository=dataset_repository,
            reader=dataset_reader,
        )
        build_visualization_service.assert_called_once_with(
            repository=dataset_repository,
            reader=dataset_reader,
        )
        self.assertIs(services.preprocess_service, preprocess_service)
        self.assertIs(services.rag_service, rag_service)
        self.assertIs(services.report_service, report_service)
        self.assertIs(services.visualization_service, visualization_service)

    def test_build_workflow_without_legacy_imports(self) -> None:
        from backend.app.core.db import SessionLocal
        from backend.app.orchestration.client import AgentClient

        client = AgentClient()
        db = SessionLocal()
        try:
            with patch(
                "backend.app.modules.rag.dependencies.get_embedder",
                return_value=_FakeEmbedder(),
            ):
                workflow = client._build_workflow(db=db)
        finally:
            db.close()

        self.assertIsNotNone(workflow)


if __name__ == "__main__":
    unittest.main()
