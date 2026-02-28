"""
共享工具模块 - 为删除流程提供统一的工具函数、日志、备份/恢复和报告功能。
"""

import os
import re
import html
import json
import shutil
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional


# ============== 配置常量 ==============
CACHE_DIR = "cache"
GRAPHML_PATH = os.path.join(CACHE_DIR, "graph_chunk_entity_relation.graphml")
VDB_PATH = os.path.join(CACHE_DIR, "vdb_entities.json")
KV_STORE_PATH = os.path.join(CACHE_DIR, "kv_store_text_chunks.json")
COMMUNITY_REPORTS_PATH = os.path.join(CACHE_DIR, "kv_store_community_reports.json")

TEMP_FILES = [
    "one_hop_nodes.txt",
    "two_hop_nodes.txt",
    "three_hop_nodes.txt",
    "deleted_clusters_cache.json",
    "cluster_change_flags.json",
    "graph_chunk_entity_relation2.graphml",
    "graph_chunk_entity_relation3.graphml",
    "kv_store_community_reports3.json",
]

BACKUP_FILES = [
    "graph_chunk_entity_relation.graphml",
    "kv_store_community_reports.json",
    "kv_store_text_chunks.json",
    "vdb_entities.json",
]


# ============== 自定义异常 ==============
class DeletionError(Exception):
    """删除流程基础异常。"""
    pass


class EntityNotFoundError(DeletionError):
    """目标实体在图中不存在。"""
    pass


class DataFileError(DeletionError):
    """数据文件缺失或损坏。"""
    pass


# ============== 日志 ==============
def get_logger(name: str = "graphrag-delete") -> logging.Logger:
    """获取统一的日志记录器。"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s][%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


logger = get_logger()


# ============== 工具函数 ==============
def clean_node_id(raw: str) -> str:
    """还原 HTML 实体并去除外层双引号。

    统一实现，替代各模块中的重复定义。
    """
    unesc = html.unescape(raw)
    if unesc.startswith('"') and unesc.endswith('"'):
        return unesc[1:-1]
    return unesc


def anonymize_text(text: str, entity_name: str) -> str:
    """将文本中所有出现的 entity_name（含所有格形式）替换为 [mask]。

    - 不区分大小写
    - 处理所有格形式如 Name's
    - 先反转义 HTML 实体
    """
    text = html.unescape(text)
    pattern = re.compile(
        rf"\b{re.escape(entity_name)}(?:['\u2018\u2019]s)?\b",
        re.IGNORECASE,
    )
    return pattern.sub("[mask]", text)


def load_json(path: str) -> dict:
    """带错误处理的 JSON 文件加载。"""
    if not os.path.isfile(path):
        raise DataFileError(f"文件不存在: {path}")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise DataFileError(f"JSON 解析失败 ({path}): {e}")


def save_json(path: str, data, indent: int = 2) -> None:
    """统一的 JSON 写入。"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


# ============== API 配置 ==============
def load_api_config(env_file: str = ".env") -> None:
    """从 .env 文件或环境变量加载 API 配置。

    期望变量: OPENAI_API_KEY, OPENAI_BASE_URL, HTTP_PROXY, HTTPS_PROXY
    """
    if os.path.isfile(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

    if "OPENAI_API_KEY" not in os.environ:
        raise RuntimeError("环境变量 OPENAI_API_KEY 未设置，请在 .env 文件或系统环境变量中配置后重试")


# ============== 预验证 ==============
def validate_entity_exists(graphml_path: str, entity_name: str) -> dict:
    """检查实体是否存在于 GraphML 中。

    返回实体的基本信息（连接数、所属社区等），如果不存在则抛出 EntityNotFoundError。
    """
    import xml.etree.ElementTree as ET

    if not os.path.isfile(graphml_path):
        raise DataFileError(f"GraphML 文件不存在: {graphml_path}")

    ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
    tree = ET.parse(graphml_path)
    root = tree.getroot()
    target = entity_name.strip().lower()

    # 查找目标节点
    entity_info = None
    for node in root.findall(".//g:node", ns):
        nid = clean_node_id(node.get("id", ""))
        if nid.lower() == target:
            # 获取描述
            desc_elem = node.find('g:data[@key="d1"]', ns)
            desc = (desc_elem.text or "")[:100] if desc_elem is not None else ""
            # 获取社区
            cluster_elem = node.find('g:data[@key="d3"]', ns)
            clusters = cluster_elem.text if cluster_elem is not None else ""
            entity_info = {
                "id": node.get("id"),
                "description": desc,
                "clusters": clusters,
            }
            break

    if entity_info is None:
        raise EntityNotFoundError(
            f"实体 '{entity_name}' 在图中不存在: {graphml_path}"
        )

    # 统计连接的边数
    edge_count = 0
    for edge in root.findall(".//g:edge", ns):
        src = clean_node_id(edge.get("source", "")).lower()
        tgt = clean_node_id(edge.get("target", "")).lower()
        if src == target or tgt == target:
            edge_count += 1

    entity_info["edge_count"] = edge_count
    return entity_info


# ============== 备份/恢复 ==============
def create_backup(cache_dir: str, entity_name: str) -> str:
    """在删除前备份所有关键文件到 .deletion_backups/ 目录。

    返回备份目录路径。
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(
        cache_dir, ".deletion_backups", f"{entity_name}_{timestamp}"
    )
    os.makedirs(backup_dir, exist_ok=True)

    for fname in BACKUP_FILES:
        src = os.path.join(cache_dir, fname)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(backup_dir, fname))
            logger.info(f"已备份: {fname}")

    logger.info(f"备份完成: {backup_dir}")
    return backup_dir


def restore_backup(backup_dir: str, cache_dir: str) -> None:
    """从备份目录恢复所有文件。"""
    if not os.path.isdir(backup_dir):
        logger.error(f"备份目录不存在: {backup_dir}")
        return

    for fname in os.listdir(backup_dir):
        src = os.path.join(backup_dir, fname)
        dst = os.path.join(cache_dir, fname)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            logger.info(f"已恢复: {fname}")

    logger.info(f"从备份恢复完成: {backup_dir}")


# ============== 临时文件清理 ==============
def cleanup_temp_files() -> None:
    """清理删除流程产生的临时文件。"""
    cleaned = 0
    for f in TEMP_FILES:
        if os.path.exists(f):
            os.remove(f)
            cleaned += 1
    if cleaned:
        logger.info(f"已清理 {cleaned} 个临时文件")


# ============== 删除摘要报告 ==============
@dataclass
class DeletionReport:
    """删除操作的统计报告。"""

    entity: str
    related_entities: list = field(default_factory=list)
    nodes_removed: int = 0
    edges_removed: int = 0
    chunks_anonymized: int = 0
    communities_updated: int = 0
    vdb_entries_removed: int = 0
    backup_dir: Optional[str] = None
    errors: list = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    def finalize(self):
        self.end_time = datetime.now()

    def summary(self) -> str:
        """生成人类可读的删除摘要。"""
        duration = ""
        if self.end_time and self.start_time:
            secs = (self.end_time - self.start_time).total_seconds()
            duration = f"{secs:.1f}s"

        lines = [
            "",
            "=" * 60,
            "删除操作摘要",
            "=" * 60,
            f"目标实体:        {self.entity}",
            f"关联实体数:      {len(self.related_entities)}",
            f"移除节点数:      {self.nodes_removed}",
            f"移除边数:        {self.edges_removed}",
            f"匿名化文本块数:  {self.chunks_anonymized}",
            f"更新社区数:      {self.communities_updated}",
            f"删除VDB条目数:   {self.vdb_entries_removed}",
            f"错误数:          {len(self.errors)}",
        ]
        if duration:
            lines.append(f"耗时:            {duration}")
        if self.backup_dir:
            lines.append(f"备份位置:        {self.backup_dir}")
        if self.errors:
            lines.append("")
            lines.append("错误详情:")
            for err in self.errors:
                lines.append(f"  - {err}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def to_json(self) -> dict:
        """导出为 JSON 格式。"""
        return {
            "entity": self.entity,
            "related_entities": self.related_entities,
            "nodes_removed": self.nodes_removed,
            "edges_removed": self.edges_removed,
            "chunks_anonymized": self.chunks_anonymized,
            "communities_updated": self.communities_updated,
            "vdb_entries_removed": self.vdb_entries_removed,
            "backup_dir": self.backup_dir,
            "errors": self.errors,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }
