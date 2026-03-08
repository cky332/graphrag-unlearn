"""服务端集中配置 - 所有内部配置从此处读取，不通过 API 参数暴露。"""

import os


class ServerConfig:
    """从环境变量读取服务端配置。"""

    @staticmethod
    def get_cache_dir() -> str:
        return os.environ.get("GRAPHRAG_CACHE_DIR", "cache")

    @staticmethod
    def get_api_key() -> str:
        return os.environ.get("GRAPHRAG_API_KEY", "")

    @staticmethod
    def get_delete_rate_limit() -> str:
        return os.environ.get("GRAPHRAG_DELETE_RATE_LIMIT", "5/minute")

    @staticmethod
    def get_query_rate_limit() -> str:
        return os.environ.get("GRAPHRAG_QUERY_RATE_LIMIT", "30/minute")

    @staticmethod
    def get_cors_origins() -> list[str]:
        origins = os.environ.get("GRAPHRAG_CORS_ORIGINS", "")
        if origins:
            return [o.strip() for o in origins.split(",") if o.strip()]
        return []

    @staticmethod
    def get_task_db_path() -> str:
        return os.environ.get("GRAPHRAG_TASK_DB", "tasks.db")
