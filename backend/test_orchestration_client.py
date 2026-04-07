import unittest

from backend.app.orchestration.client import AgentClient


class _WorkflowStub:
    async def astream(self, input_payload, config, *, stream_mode):
        yield {
            "output": {
                "type": "data_qa",
                "content": "테스트 응답",
            }
        }


class OrchestrationClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_astream_workflow_values_works_as_bound_method(self) -> None:
        client = AgentClient(workflow_runtime_factory=lambda: None)

        snapshots = []
        async for snapshot in client._astream_workflow_values(
            _WorkflowStub(),
            {"user_input": "질문"},
            {"configurable": {"thread_id": "test"}},
        ):
            snapshots.append(snapshot)

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["output"]["content"], "테스트 응답")


if __name__ == "__main__":
    unittest.main()
