"""
设置相关接口：数据源选择（前端设置页 -> 后端生效）。

- GET  /api/v1/settings/datasource  : 读取当前生效数据源 + 各外部源可用性
- POST /api/v1/settings/datasource  : 设置数据源（即时翻转 USE_EXTERNAL_DATA 并触发重播种）
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core import runtime_settings as rs

router = APIRouter(prefix="/settings", tags=["settings"])


class DataSourceIn(BaseModel):
    source: str


@router.get("/datasource")
async def get_datasource() -> dict:
    return {"source": rs.get_data_source(), "available": rs.get_availability()}


@router.post("/datasource")
async def post_datasource(body: DataSourceIn) -> dict:
    source = rs.set_data_source(body.source)
    return {"source": source, "available": rs.get_availability()}
