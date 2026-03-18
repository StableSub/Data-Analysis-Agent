import unittest

from backend.app.main import app


class ApiRouteSmokeTest(unittest.TestCase):
    def test_critical_routes_are_registered(self):
        registered = {
            (getattr(route, "path", None), tuple(sorted(getattr(route, "methods", set()))))
            for route in app.routes
        }

        expected = {
            ("/datasets/", ("POST",)),
            ("/datasets/", ("GET",)),
            ("/datasets/{dataset_id}", ("GET",)),
            ("/datasets/{source_id}", ("DELETE",)),
            ("/datasets/{source_id}/sample", ("GET",)),
            ("/chats/", ("POST",)),
            ("/chats/stream", ("POST",)),
            ("/chats/{session_id}/runs/{run_id}/resume", ("POST",)),
            ("/chats/{session_id}/runs/{run_id}/pending-approval", ("GET",)),
            ("/chats/{session_id}/history", ("GET",)),
            ("/chats/{session_id}", ("DELETE",)),
            ("/preprocess/apply", ("POST",)),
            ("/vizualization/manual", ("POST",)),
            ("/report/", ("POST",)),
            ("/report/", ("GET",)),
            ("/report/{report_id}", ("GET",)),
            ("/export/csv", ("POST",)),
            ("/rag/query", ("POST",)),
            ("/rag/sources/{source_id}", ("DELETE",)),
        }

        missing = expected - registered
        self.assertFalse(missing, f"missing routes: {sorted(missing)}")


if __name__ == "__main__":
    unittest.main()
