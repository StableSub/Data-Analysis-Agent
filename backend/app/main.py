from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.db import Base, engine
from .api import datasets as datasets_api
from .api import chats as chats_api
from .api import visualization as visualization_api
from .rag import models as rag_models
from .rag import router as rag_router
from .api import export as export_api
from .api import preprocess as preprocess_api


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
app.include_router(chats_api.router)
app.include_router(visualization_api.router)
app.include_router(rag_router.router)
app.include_router(export_api.router)
app.include_router(preprocess_api.router)
