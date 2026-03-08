"""SQLite 持久化任务存储，管理异步删除任务的生命周期。"""

import asyncio
import json
import uuid
import aiosqlite
from datetime import datetime
from typing import Optional

from api.models import TaskStatus, TaskResponse


class TaskStore:
    """SQLite 持久化任务存储，包含全局删除锁。

    服务重启后任务状态不丢失。活跃实体集合在启动时从数据库重建。
    """

    def __init__(self, db_path: str = "tasks.db"):
        self._db_path = db_path
        self._deletion_lock = asyncio.Lock()
        self._active_entities: set[str] = set()

    @property
    def deletion_lock(self) -> asyncio.Lock:
        return self._deletion_lock

    async def initialize(self):
        """创建表并从数据库重建活跃实体集合。应在应用启动时调用。"""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    entity_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    result TEXT,
                    error TEXT
                )
            """)
            await db.commit()

            # 将服务重启前未完成的任务标记为失败
            async with db.execute(
                "SELECT task_id, entity_name FROM tasks WHERE status IN (?, ?)",
                (TaskStatus.PENDING.value, TaskStatus.RUNNING.value),
            ) as cursor:
                interrupted = await cursor.fetchall()

            for task_id, entity_name in interrupted:
                await db.execute(
                    "UPDATE tasks SET status = ?, completed_at = ?, error = ? WHERE task_id = ?",
                    (
                        TaskStatus.FAILED.value,
                        datetime.now().isoformat(),
                        "服务重启导致任务中断",
                        task_id,
                    ),
                )
            if interrupted:
                await db.commit()

    async def create_task(self, entity_name: str) -> TaskResponse:
        task_id = uuid.uuid4().hex[:12]
        now = datetime.now()
        task = TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            entity_name=entity_name,
            created_at=now,
        )
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO tasks (task_id, status, entity_name, created_at) VALUES (?, ?, ?, ?)",
                (task_id, TaskStatus.PENDING.value, entity_name, now.isoformat()),
            )
            await db.commit()
        self._active_entities.add(entity_name.lower())
        return task

    async def get_task(self, task_id: str) -> Optional[TaskResponse]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    return None
                return self._row_to_task(row)

    async def list_tasks(self) -> list[TaskResponse]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_task(row) for row in rows]

    def is_entity_active(self, entity_name: str) -> bool:
        return entity_name.lower() in self._active_entities

    async def mark_running(self, task_id: str):
        now = datetime.now()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE tasks SET status = ?, started_at = ? WHERE task_id = ?",
                (TaskStatus.RUNNING.value, now.isoformat(), task_id),
            )
            await db.commit()

    async def mark_completed(self, task_id: str, result: dict):
        now = datetime.now()
        result_json = json.dumps(result, ensure_ascii=False)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE tasks SET status = ?, completed_at = ?, result = ? WHERE task_id = ?",
                (TaskStatus.COMPLETED.value, now.isoformat(), result_json, task_id),
            )
            # 获取 entity_name 以清理 active 集合
            async with db.execute(
                "SELECT entity_name FROM tasks WHERE task_id = ?", (task_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    self._active_entities.discard(row[0].lower())
            await db.commit()

    async def mark_failed(self, task_id: str, error: str):
        now = datetime.now()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE tasks SET status = ?, completed_at = ?, error = ? WHERE task_id = ?",
                (TaskStatus.FAILED.value, now.isoformat(), error, task_id),
            )
            async with db.execute(
                "SELECT entity_name FROM tasks WHERE task_id = ?", (task_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    self._active_entities.discard(row[0].lower())
            await db.commit()

    @staticmethod
    def _row_to_task(row) -> TaskResponse:
        result = None
        if row["result"]:
            try:
                result = json.loads(row["result"])
            except json.JSONDecodeError:
                result = None

        return TaskResponse(
            task_id=row["task_id"],
            status=TaskStatus(row["status"]),
            entity_name=row["entity_name"],
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            result=result,
            error=row["error"],
        )
