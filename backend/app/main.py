from fastapi import FastAPI

from .core.db import Base, engine
from .api import datasets as datasets_api
from .api import chats as chats_api
from .api import visualization as visualization_api
from .rag import models as rag_models
from .rag import router as rag_router
from .api import export as export_api

app = FastAPI()


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)



app.include_router(datasets_api.router)
app.include_router(chats_api.router)
app.include_router(visualization_api.router)
app.include_router(rag_router.router)
app.include_router(export_api.router)
