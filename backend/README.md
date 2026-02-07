# Backend

Python FastAPI backend for the Data Analysis Agent.

## Setup

1. **Create virtual environment**:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure environment**:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

4. **Run the server**:
```bash
python main.py
# Or with uvicorn directly:
uvicorn main:app --reload --port 8000
```

## Endpoints

- **Health Check**: `GET http://localhost:8000/health`
- **CopilotKit Runtime**: `POST http://localhost:8000/api/copilotkit`

## Architecture

```
backend/
├── main.py              # FastAPI app + CopilotKit endpoint
├── agents/              # AI agent logic
│   └── data_analyzer.py
├── tools/               # AI tools (actions)
│   └── chart_generator.py
└── tests/               # Unit tests
```

## Development

The server runs with auto-reload enabled. Any changes to Python files will automatically restart the server.
