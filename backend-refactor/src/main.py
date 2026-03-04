"""Main entry point for the application."""

import uvicorn

from app import create_app
from settings import Settings

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=Settings.get().debug)
