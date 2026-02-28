
import asyncio
import traceback
import sys

from delete_community_direct_node_edge import main as direct_main
from delete_community_update_reports import main as update_main
from delete_community_indirect import prune_edges_for_node
from delete_community_evaluate import main as evaluate_main
from delete_generate_graphml import main as generate_graphml_main
from delete_community_leiden import main as leiden_main
from delete_community_unique import ensure_unique_ids
from delete_community_merge import main as merge_main
from delete_community_update_ndoe_cluster import main as update_node_cluster_main
from delete_utils import get_logger

logger = get_logger()

# 配置常量
CLUSTER_CHANGE_FLAGS = "cluster_change_flags.json"
BASE_REPORTS_FILE     = "cache/kv_store_community_reports.json"
NEW_REPORTS_FILE      = "cache/kv_store_community_reports3.json"

async def delete_community_pipeline(raw_node_id: str):
    """
    针对单个 raw_node_id，按流程执行：
      1) 同步删除节点及边
      2) 异步更新报告（禁止出现 raw_node_id）
      3) 异步剪枝间接边并更新报告
      4) 同步评估变化
      5) 检查是否有变化标志，如无则跳过
      6) 生成子图
      7) Leiden 聚类与报告
      8) 确保社区 ID 唯一
      9) 合并更新后的社区报告
     10) 更新 GraphML 节点-社区映射
    """
    logger.info(f"[DC] 1) 删除节点/边: {raw_node_id}")
    direct_main(raw_node_id)

    logger.info(f"[DC] 2) 异步更新报告 (禁止实体: {raw_node_id})")
    await update_main(raw_node_id)

    logger.info(f"[DC] 3) 异步剪枝间接边: {raw_node_id}")
    await prune_edges_for_node(raw_node_id)

    logger.info(f"[DC] 4) 同步评估社区结构变化")
    changed = evaluate_main()

    if not changed:
        logger.info("[DC] 未检测到变化，跳过后续步骤")
        return

    logger.info("[DC] 6) 生成子图")
    generate_graphml_main()

    logger.info("[DC] 7) Leiden 聚类与报告")
    try:
        await leiden_main()
    except Exception as e:
        logger.warning(f"[DC] Leiden 失败，跳过后续: {e}")
        traceback.print_exc()
        return

    logger.info("[DC] 8) 确保社区 ID 唯一")
    ensure_unique_ids(
        base_file=BASE_REPORTS_FILE,
        new_file=NEW_REPORTS_FILE,
    )

    logger.info("[DC] 9) 合并更新后的社区报告")
    merge_main()

    logger.info("[DC] 10) 更新 GraphML 节点-社区映射")
    try:
        update_node_cluster_main()
    except Exception as e:
        logger.warning(f"[DC] 更新映射失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.error("用法: python delete_community.py <raw_node_id>")
        sys.exit(1)

    node_id = sys.argv[1]
    asyncio.run(delete_community_pipeline(node_id))