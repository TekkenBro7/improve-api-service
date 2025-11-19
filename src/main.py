import uvicorn
from fastapi import FastAPI

from src.api.router import api_router
from src.core.config import base_config

app = FastAPI(
    title="Improved API Service",
    description="API service for manage users and transactions",
    version="0.0.1",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=base_config.HOST,
        port=base_config.PORT,
        reload=base_config.RELOAD,
    )
