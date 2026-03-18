"""Pydantic 请求/响应模型。"""

import re
from enum import Enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DeleteRequest(BaseModel):
    entity_name: str = Field(
        ..., min_length=1, max_length=200, description="要删除的实体名称"
    )
    no_backup: bool = Field(default=False, description="跳过删除前备份")

    @field_validator("entity_name")
    @classmethod
    def validate_entity_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("实体名称不能为空")
        if not re.match(r"^[\w\s.\-'\"()\u4e00-\u9fff\u3000-\u303f]+$", v, re.UNICODE):
            raise ValueError("实体名称包含无效字符")
        return v


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    entity_name: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class EntityExistsResponse(BaseModel):
    entity_name: str
    exists: bool
    info: Optional[dict] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    service_ready: bool = Field(description="数据文件是否就绪")
