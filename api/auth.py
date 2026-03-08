"""API Key 认证 - 通过 X-API-Key 请求头验证身份。"""

import logging

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from api.config import ServerConfig

logger = logging.getLogger("graphrag-delete")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> str:
    """FastAPI 依赖：验证请求携带的 API Key。

    未配置 GRAPHRAG_API_KEY 环境变量时拒绝所有请求（fail-closed）。
    """
    expected = ServerConfig.get_api_key()
    if not expected:
        logger.error("GRAPHRAG_API_KEY 未配置，拒绝所有请求")
        raise HTTPException(
            status_code=503,
            detail="服务未配置认证密钥，请联系管理员。",
        )
    if not api_key or api_key != expected:
        raise HTTPException(
            status_code=403,
            detail="无效的 API Key。",
        )
    return api_key
