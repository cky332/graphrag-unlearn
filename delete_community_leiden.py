import os
import asyncio
import traceback
import json
from dataclasses import asdict
import sys

from nano_graphrag.graphrag import GraphRAG
from nano_graphrag._storage import NetworkXStorage
from nano_graphrag._op import generate_community_report
from delete_utils import get_logger, load_api_config

logger = get_logger()

load_api_config()

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def generate_communities():
    rag = GraphRAG(working_dir=".")
    rag.chunk_entity_relation_graph = NetworkXStorage(
        namespace="chunk_entity_relation3",
        global_config=asdict(rag),
    )
    logger.info(f"[DEBUG] 使用图文件: graph_chunk_entity_relation3.graphml 边数 {rag.chunk_entity_relation_graph._graph.number_of_edges()}")

    try:
        logger.info("[DEBUG] 开始聚类……")
        await rag.chunk_entity_relation_graph.clustering(rag.graph_cluster_algorithm)
        logger.info("[DEBUG] 聚类完成")
    except Exception as e:
        if type(e).__name__ == "EmptyNetworkError":
            logger.info("⚠️ 空网络，跳过聚类")
        else:
            logger.info("❌ 聚类失败：", e)
            traceback.print_exc()
            return

    logger.info("[DEBUG] 开始生成社区报告……")
    await generate_community_report(
        rag.community_reports,
        rag.chunk_entity_relation_graph,
        asdict(rag),
    )
    logger.info("[DEBUG] 社区报告生成完成")

    out_file = "kv_store_community_reports3.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(rag.community_reports._data, f, indent=2, ensure_ascii=False)
    logger.info(f"✅ 已生成 {out_file}")

async def main():
    try:
        await generate_communities()
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())