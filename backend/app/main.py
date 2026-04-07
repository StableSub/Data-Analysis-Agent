from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .core.db import Base, engine
from .modules.analysis import router as analysis_api
from .modules.chat import models as chat_models
from .modules.chat import router as chats_api
from .modules.datasets import models as dataset_models
from .modules.datasets import router as datasets_api
from .modules.eda import router as eda_api
from .modules.export import router as export_api
from .modules.guidelines import models as guideline_models
from .modules.guidelines import router as guidelines_api
from .modules.preprocess import router as preprocess_api
from .modules.rag import models as rag_models
from .modules.rag import router as rag_router
from .modules.reports import models as report_models
from .modules.reports import router as reports_api
from .modules.results import models as result_models
from .modules.visualization import router as visualization_api


load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


app.include_router(datasets_api.router)
app.include_router(eda_api.router)
app.include_router(chats_api.router)
app.include_router(analysis_api.router)
app.include_router(visualization_api.router)
app.include_router(rag_router.router)
app.include_router(export_api.router)
app.include_router(guidelines_api.router)
app.include_router(preprocess_api.router)
app.include_router(reports_api.router)
