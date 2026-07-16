from typing import Dict

from fastapi import FastAPI

app = FastAPI(title="api_paralela")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}
