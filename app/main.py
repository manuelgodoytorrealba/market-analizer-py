from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db.session import init_db
from app.api.api import router as api_router
from app.api.dashboard import router as dashboard_router

app = FastAPI(title="Market Analyzer")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(api_router)
app.include_router(dashboard_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
