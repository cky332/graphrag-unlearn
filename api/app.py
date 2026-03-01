"""FastAPI 应用 - GraphRAG 实体删除 API。"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

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

task_store = TaskStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("GraphRAG Deletion API 启动")
    yield
    logger.info("GraphRAG Deletion API 关闭")


app = FastAPI(
    title="GraphRAG Entity Deletion API",
    description="从 GraphRAG 知识图谱中删除实体及其关联数据的 API",
    version="1.0.0",
    lifespan=lifespan,
)


async def _execute_deletion(
    task_id: str, entity_name: str, cache_dir: str, no_backup: bool
):
    """后台协程：获取删除锁后执行删除流程。"""
    try:
        async with task_store.deletion_lock:
            task_store.mark_running(task_id)
            try:
                report = await run_deletion(
                    entity_name=entity_name,
                    cache_dir=cache_dir,
                    no_backup=no_backup,
                )
                task_store.mark_completed(task_id, report.to_json())
            except Exception as e:
                task_store.mark_failed(task_id, str(e))
    except Exception as e:
        # 获取锁之前或 mark_running 就失败的情况
        task_store.mark_failed(task_id, str(e))


@app.post("/api/v1/entities/delete", response_model=TaskResponse, status_code=202)
async def delete_entity(request: DeleteRequest):
    """提交实体删除任务。

    返回 202 Accepted 和 task_id，通过 GET /api/v1/tasks/{task_id} 查询进度。
    """
    # 先校验实体是否存在于图中
    graphml_path = os.path.join(
        request.cache_dir, "graph_chunk_entity_relation.graphml"
    )
    try:
        validate_entity_exists(graphml_path, request.entity_name)
    except EntityNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"实体 '{request.entity_name}' 在知识图谱中不存在，无法删除。",
        )
    except DataFileError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if task_store.is_entity_active(request.entity_name):
        raise HTTPException(
            status_code=409,
            detail=f"实体 '{request.entity_name}' 已有活跃的删除任务。",
        )

    task = task_store.create_task(request.entity_name)

    asyncio.create_task(
        _execute_deletion(
            task.task_id, request.entity_name, request.cache_dir, request.no_backup
        )
    )

    return task


@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """查询删除任务的状态。"""
    task = task_store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 '{task_id}' 不存在。")
    return task


@app.get("/api/v1/tasks", response_model=list[TaskResponse])
async def list_tasks():
    """列出所有删除任务。"""
    return task_store.list_tasks()


@app.get("/api/v1/entities/{entity_name:path}", response_model=EntityExistsResponse)
async def check_entity(entity_name: str, cache_dir: str = "cache"):
    """检查实体是否存在于知识图谱中。

    实体名含空格时需 URL 编码，例如: /api/v1/entities/MR.%20DURSLEY
    """
    graphml_path = os.path.join(cache_dir, "graph_chunk_entity_relation.graphml")
    try:
        info = validate_entity_exists(graphml_path, entity_name)
        return EntityExistsResponse(entity_name=entity_name, exists=True, info=info)
    except EntityNotFoundError:
        return EntityExistsResponse(entity_name=entity_name, exists=False)
    except DataFileError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/config/check")
async def check_config():
    """检查 API 配置（.env 文件）是否正确加载。

    在提交删除任务前调用此端点，可提前发现配置问题。
    """
    cwd_env = os.path.abspath(".env")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_env = os.path.join(project_root, ".env")
    return {
        "cwd_env_path": cwd_env,
        "cwd_env_exists": os.path.isfile(cwd_env),
        "project_root_env_path": root_env,
        "project_root_env_exists": os.path.isfile(root_env),
        "openai_api_key_set": bool(os.environ.get("OPENAI_API_KEY")),
        "openai_base_url": os.environ.get("OPENAI_BASE_URL", "(未设置)"),
    }


@app.get("/health", response_model=HealthResponse)
async def health_check(cache_dir: str = "cache"):
    """健康检查端点。"""
    graphml_path = os.path.join(cache_dir, "graph_chunk_entity_relation.graphml")
    return HealthResponse(
        status="ok",
        cache_dir_exists=os.path.isdir(cache_dir),
        graphml_exists=os.path.isfile(graphml_path),
    )
