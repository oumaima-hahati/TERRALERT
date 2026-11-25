"""Standalone test application; does not modify Rayane's API."""

from fastapi import FastAPI

from .api import router

app = FastAPI(
    title="TERRALERT GIS Assistant Prototype",
    version="0.1.0",
)

app.include_router(router)
