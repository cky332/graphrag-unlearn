import json
import os
import base64
import numpy as np
from delete_utils import get_logger, DataFileError

logger = get_logger()


def delete_vdb_entities(raw_node_name="Dumbledore", file_path=None):
    """
    从指定的 vdb JSON 文件中删除所有 entity_name 中包含 raw_node_name 的实体，
    并将更新后的 data 列表和 matrix 写回原文件。

    参数:
    - raw_node_name: 要匹配删除的实体关键词，不区分大小写
    - file_path: vdb JSON 文件路径，若为 None，则使用默认路径 cache/vdb_entities.json

    返回: 被删除的实体数量
    """
    if file_path is None:
        file_path = os.path.join("cache", "vdb_entities.json")

    # 检查文件
    if not os.path.isfile(file_path):
        raise DataFileError(f"VDB 文件不存在：{file_path}")

    # 读取 JSON
    with open(file_path, "r", encoding="utf-8") as f:
        vdb = json.load(f)

    data_list = vdb.get("data", [])
    embedding_dim = vdb.get("embedding_dim")
    matrix_b64 = vdb.get("matrix")

    if not isinstance(data_list, list) or embedding_dim is None or not isinstance(matrix_b64, str):
        raise DataFileError("VDB JSON 结构与预期不符，请检查 'data', 'embedding_dim', 'matrix' 字段。")

    # 解码并 reshape
    try:
        matrix_bytes = base64.b64decode(matrix_b64)
        mat = np.frombuffer(matrix_bytes, dtype=np.float32)
        mat = mat.reshape(len(data_list), embedding_dim)
    except Exception as e:
        raise DataFileError(f"解码或 reshape matrix 失败：{e}")

    # 筛选：保留不包含关键词的实体
    keep_indices = [
        idx for idx, entry in enumerate(data_list)
        if raw_node_name.lower() not in entry.get("entity_name", "").lower()
    ]
    removed_count = len(data_list) - len(keep_indices)
    if removed_count > 0:
        logger.info(f"已删除 {removed_count} 个包含 '{raw_node_name}' 的 VDB 实体。")
    else:
        logger.info(f"未找到包含 '{raw_node_name}' 的 VDB 实体，跳过删除。")

    # 生成新的 data 列表和矩阵
    new_data_list = [data_list[i] for i in keep_indices]
    new_mat = mat[keep_indices, :]

    # 重新编码 matrix
    try:
        new_bytes = new_mat.astype(np.float32).tobytes()
        new_b64 = base64.b64encode(new_bytes).decode("ascii")
    except Exception as e:
        raise DataFileError(f"重新编码 matrix 失败：{e}")

    # 更新并写回
    vdb["data"] = new_data_list
    vdb["matrix"] = new_b64
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(vdb, f, indent=2, ensure_ascii=False)

    logger.info(f"VDB 更新完成，已写回：{file_path}")
    return removed_count