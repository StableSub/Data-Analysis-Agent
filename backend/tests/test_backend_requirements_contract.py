from pathlib import Path


REQUIREMENTS_PATH = Path(__file__).resolve().parents[1] / "requirements.txt"


def test_huggingface_runtime_dependencies_are_capped_when_requirements_are_read() -> None:
    # Given: the backend dependency manifest used to build the FastAPI runtime.
    requirements_text = REQUIREMENTS_PATH.read_text(encoding="utf-8")

    # When: the Hugging Face runtime dependency caps are inspected.
    required_lines = {
        "huggingface-hub>=0.34.0,<1.0",
        "tokenizers>=0.22.0,<=0.23.0",
    }

    # Then: the manifest prevents transformer import-time version conflicts.
    assert required_lines.issubset(set(requirements_text.splitlines()))
