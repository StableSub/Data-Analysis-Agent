from typing import Any, AsyncIterator, Dict, Protocol


class TraceStreamingAgent(Protocol):
    async def astream_with_trace(self, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]: ...


class ApprovalAwareTraceStreamingAgent(TraceStreamingAgent, Protocol):
    def get_pending_approval(self, *, run_id: str) -> Dict[str, Any] | None: ...
