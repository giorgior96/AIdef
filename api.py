from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import polars as pl

from app import load_dataset, query_boats

app = FastAPI(title="Boat Filter API")

df = load_dataset()

class QueryPayload(BaseModel):
    query: str

@app.get("/boats")
@app.post("/boats")
async def boats(q: str = Query(None, alias="query"), payload: QueryPayload | None = None):
    query = q or (payload.query if payload else "")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    _, results, _ = query_boats(df, query)
    if results.is_empty():
        return {"ids": []}

    if "id" not in results.columns:
        results = results.with_row_count("id")

    return {"ids": results["id"].to_list()}

