import os
import sys
import asyncio
import html
import time
import networkx as nx

from fuzzing_match import find_matching_nodes
from rag_match import rag_and_alias_extraction
from nano_graphrag.graphrag import GraphRAG
from delete_utils import get_logger

logger = get_logger()

async def extract_entities(raw_node_id: str, graphml_path: str) -> list[str]:
    """
    1. 从 GraphML 做模糊匹配提取节点
    2. 用 GraphRAG + DeepSeek-v3 提取别名
    3. 在 GraphML 中校验 RAG 提取结果的存在性
    4. 合并两部分结果并去重，返回实体列表
    """
    logger.info(f"[实体提取] 开始为 '{raw_node_id}' 提取关联实体，graphml={graphml_path}")

    # 1. 模糊匹配
    t0 = time.time()
    logger.info(f"[实体提取] 执行模糊匹配...")
    fuzz_matches = find_matching_nodes(graphml_path, raw_node_id)
    fuzz_entities = [node_id for node_id, _xml in fuzz_matches]
    logger.info(f"[实体提取] 模糊匹配完成，耗时 {time.time() - t0:.1f}s，"
                 f"找到 {len(fuzz_entities)} 个: {fuzz_entities}")

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("环境变量 OPENAI_API_KEY 未设置，请在 .env 文件或系统环境变量中配置后重试")

    # 2. RAG + LLM 提取别名
    t0 = time.time()
    logger.info(f"[实体提取] 初始化 GraphRAG (working_dir={os.path.dirname(graphml_path)})...")
    rag_entities = []
    gr = GraphRAG(
        working_dir=os.path.dirname(graphml_path),
        enable_local=True,
        enable_naive_rag=True,
    )
    logger.info(f"[实体提取] GraphRAG 初始化完成，开始 RAG 别名提取...")
    try:
        rag_entities = await rag_and_alias_extraction(raw_node_id, gr)
    finally:
        if hasattr(gr, "async_driver"):
            await gr.async_driver.close()
    logger.info(f"[实体提取] RAG 别名提取完成，耗时 {time.time() - t0:.1f}s，"
                 f"找到 {len(rag_entities)} 个: {rag_entities}")

    # 3. 校验 RAG 结果在图中的存在性
    t0 = time.time()
    graph = nx.read_graphml(graphml_path)
    logger.info(f"[实体提取] GraphML 加载完成，共 {graph.number_of_nodes()} 节点, "
                 f"{graph.number_of_edges()} 边")

    def clean_node_id(raw: str) -> str:
        unesc = html.unescape(raw)
        return unesc[1:-1] if unesc.startswith('"') and unesc.endswith('"') else unesc

    def graph_has_node(alias: str) -> bool:
        target = alias.lower()
        for n in graph.nodes():
            if clean_node_id(n).lower() == target:
                return True
        return False

    filtered_rag = [a for a in rag_entities if graph_has_node(a)]
    removed = [a for a in rag_entities if a not in filtered_rag]
    if removed:
        logger.info(f"[实体提取] RAG 结果中有 {len(removed)} 个不存在于图中，已过滤: {removed}")
    logger.info(f"[实体提取] RAG 过滤后保留 {len(filtered_rag)} 个: {filtered_rag}")

    # 4. 合并去重
    merged = []
    seen = set()
    for name in fuzz_entities + filtered_rag:
        key = name.lower()
        if key not in seen:
            seen.add(key)
            merged.append(name)

    logger.info(f"[实体提取] 最终合并结果: {len(merged)} 个实体: {merged}")
    return merged

async def main():
    raw_node_id = "Dumbledore"
    graphml_path = os.path.join("cache", "graph_chunk_entity_relation.graphml")
    merged = await extract_entities(raw_node_id, graphml_path)
    print(f"[合并结果] 共 {len(merged)} 个实体: {merged}")

if __name__ == "__main__":
    asyncio.run(main())