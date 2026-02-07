"""
FastAPI backend with CopilotKit SDK Runtime for agentic data analysis.

This server provides:
- /api/copilotkit endpoint using official CopilotKit SDK
- AI-powered data analysis actions
- Chart generation and data preprocessing tools
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from copilotkit import CopilotKitRemoteEndpoint, Action
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from typing import Any, Dict, List

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Data Analysis Agent API",
    description="Agentic data analysis with CopilotKit",
    version="1.0.0"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# CopilotKit Actions for Generative UI
# =============================================================================

async def show_sample_chart_handler() -> Dict[str, Any]:
    """
    Display a sample chart to demonstrate GenUI capabilities.
    Shows monthly sales data in a bar chart.
    """
    return {
        "chartType": "bar",
        "data": [
            {"month": "Jan", "sales": 4000},
            {"month": "Feb", "sales": 3000},
            {"month": "Mar", "sales": 5000},
            {"month": "Apr", "sales": 4500},
            {"month": "May", "sales": 6000},
            {"month": "Jun", "sales": 5500}
        ],
        "xKey": "month",
        "yKey": "sales",
        "title": "Monthly Sales Report"
    }

async def show_sample_table_handler() -> Dict[str, Any]:
    """
    Display a sample data table to demonstrate GenUI capabilities.
    Shows product inventory data.
    """
    return {
        "columns": ["Product", "Stock", "Price", "Status"],
        "rows": [
            ["Widget A", "150", "$25.00", "Available"],
            ["Widget B", "45", "$35.00", "Low Stock"],
            ["Gadget X", "0", "$50.00", "Out of Stock"],
            ["Gadget Y", "200", "$45.00", "Available"],
            ["Tool Z", "75", "$30.00", "Available"]
        ],
        "title": "Product Inventory"
    }

# =============================================================================
# CopilotKit Runtime Setup
# =============================================================================

# Initialize CopilotKit SDK
sdk = CopilotKitRemoteEndpoint(
    actions=[
        Action(
            name="show_sample_chart",
            handler=show_sample_chart_handler,
            description="Display a sample chart to demonstrate GenUI capabilities.",
        ),
        Action(
            name="show_sample_table",
            handler=show_sample_table_handler,
            description="Display a sample data table to demonstrate GenUI capabilities.",
        ),
    ],
)

# Add CopilotKit endpoint to FastAPI app
add_fastapi_endpoint(app, sdk, "/api/copilotkit")

# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "data-analysis-agent-backend",
        "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
        "llm_model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "copilotkit_sdk": "enabled"
    }

# =============================================================================
# Server Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    print(f"🚀 Starting Data Analysis Agent Backend on {host}:{port}")
    print(f"📊 Health Check: http://{host}:{port}/health")
    print(f"🤖 CopilotKit Endpoint: http://{host}:{port}/api/copilotkit")
    print(f"✨ Using Official CopilotKit SDK")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
