"""FastAPI 应用 - GraphRAG 实体删除 API。"""

import os
import re
import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from api.config import ServerConfig
from api.auth import verify_api_key
from api.models import (
    DeleteRequest,
    TaskResponse,
    EntityExistsResponse,
    HealthResponse,
)
from api.task_store import TaskStore
from api.deletion_service import run_deletion
from delete_utils import validate_entity_exists, EntityNotFoundError, DataFileError

logger = logging.getLogger("graphrag-delete")

task_store = TaskStore(db_path=ServerConfig.get_task_db_path())

limiter = Limiter(key_func=get_remote_address)


def _sanitize_error(error: str) -> str:
    """移除错误消息中的内部路径和敏感信息。"""
    sanitized = re.sub(
        r"(?:/[\w./-]+|[\w./\\]+\.(?:graphml|json|py|env|db|txt))",
        "[internal]",
        error,
    )
    return sanitized


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件。"""

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        logger.info(
            "%s %s -> %d (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration * 1000,
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    await task_store.initialize()
    logger.info("GraphRAG Deletion API 启动")
    yield
    logger.info("GraphRAG Deletion API 关闭")


app = FastAPI(
    title="GraphRAG Entity Deletion API",
    description="从 GraphRAG 知识图谱中删除实体及其关联数据的 API",
    version="2.0.0",
    lifespan=lifespan,
)

# 速率限制
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
cors_origins = ServerConfig.get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins else ["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

# 请求日志
app.add_middleware(RequestLoggingMiddleware)


async def _execute_deletion(
    task_id: str, entity_name: str, no_backup: bool
):
    """后台协程：获取删除锁后执行删除流程。"""
    try:
        async with task_store.deletion_lock:
            await task_store.mark_running(task_id)
            try:
                report = await run_deletion(
                    entity_name=entity_name,
                    no_backup=no_backup,
                )
                await task_store.mark_completed(task_id, report.to_api_json())
            except Exception as e:
                await task_store.mark_failed(task_id, _sanitize_error(str(e)))
    except Exception as e:
        # 获取锁之前或 mark_running 就失败的情况
        await task_store.mark_failed(task_id, _sanitize_error(str(e)))


@app.post(
    "/api/v1/entities/delete",
    response_model=TaskResponse,
    status_code=202,
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit(ServerConfig.get_delete_rate_limit())
async def delete_entity(request: Request, body: DeleteRequest):
    """提交实体删除任务。

    返回 202 Accepted 和 task_id，通过 GET /api/v1/tasks/{task_id} 查询进度。
    """
    cache_dir = ServerConfig.get_cache_dir()
    graphml_path = os.path.join(cache_dir, "graph_chunk_entity_relation.graphml")
    try:
        validate_entity_exists(graphml_path, body.entity_name)
    except EntityNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"实体 '{body.entity_name}' 在知识图谱中不存在，无法删除。",
        )
    except DataFileError:
        raise HTTPException(
            status_code=500,
            detail="内部数据文件错误，请联系管理员。",
        )

    if task_store.is_entity_active(body.entity_name):
        raise HTTPException(
            status_code=409,
            detail=f"实体 '{body.entity_name}' 已有活跃的删除任务。",
        )

    task = await task_store.create_task(body.entity_name)

    asyncio.create_task(
        _execute_deletion(task.task_id, body.entity_name, body.no_backup)
    )

    return task


@app.get(
    "/api/v1/tasks/{task_id}",
    response_model=TaskResponse,
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit(ServerConfig.get_query_rate_limit())
async def get_task(request: Request, task_id: str):
    """查询删除任务的状态。"""
    task = await task_store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 '{task_id}' 不存在。")
    return task


@app.get(
    "/api/v1/tasks",
    response_model=list[TaskResponse],
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit(ServerConfig.get_query_rate_limit())
async def list_tasks(request: Request):
    """列出所有删除任务。"""
    return await task_store.list_tasks()


@app.get(
    "/api/v1/entities/{entity_name:path}",
    response_model=EntityExistsResponse,
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit(ServerConfig.get_query_rate_limit())
async def check_entity(request: Request, entity_name: str):
    """检查实体是否存在于知识图谱中。

    实体名含空格时需 URL 编码，例如: /api/v1/entities/MR.%20DURSLEY
    """
    cache_dir = ServerConfig.get_cache_dir()
    graphml_path = os.path.join(cache_dir, "graph_chunk_entity_relation.graphml")
    try:
        info = validate_entity_exists(graphml_path, entity_name)
        return EntityExistsResponse(entity_name=entity_name, exists=True, info=info)
    except EntityNotFoundError:
        return EntityExistsResponse(entity_name=entity_name, exists=False)
    except DataFileError:
        raise HTTPException(
            status_code=500,
            detail="内部数据文件错误，请联系管理员。",
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点（无需认证，供 Docker/K8s 探针使用）。"""
    cache_dir = ServerConfig.get_cache_dir()
    graphml_path = os.path.join(cache_dir, "graph_chunk_entity_relation.graphml")
    service_ready = os.path.isdir(cache_dir) and os.path.isfile(graphml_path)
    return HealthResponse(status="ok", service_ready=service_ready)
