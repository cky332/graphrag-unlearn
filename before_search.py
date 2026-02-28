import os
import sys
import asyncio
import html
import networkx as nx

from fuzzing_match import find_matching_nodes
from rag_match import rag_and_alias_extraction
from nano_graphrag.graphrag import GraphRAG

async def extract_entities(raw_node_id: str, graphml_path: str) -> list[str]:
    """
    1. 从 GraphML 做模糊匹配提取节点
    2. 用 GraphRAG + DeepSeek-v3 提取别名
    3. 在 GraphML 中校验 RAG 提取结果的存在性
    4. 合并两部分结果并去重，返回实体列表
    """
    # 1. fuzz 匹配
    fuzz_matches = find_matching_nodes(graphml_path, raw_node_id)
    fuzz_entities = [node_id for node_id, _xml in fuzz_matches]

    # 2. RAG + DeepSeek-v3（需要 OPENAI_API_KEY，未设置时跳过）
    rag_entities = []
    if not os.environ.get("OPENAI_API_KEY"):
        import logging
        logging.getLogger("graphrag-delete").warning(
            "OPENAI_API_KEY 未设置，跳过 RAG 别名提取，仅使用模糊匹配结果"
        )
    else:
        gr = GraphRAG(
            working_dir=os.path.dirname(graphml_path),
            enable_local=True,
            enable_naive_rag=True,
        )
        try:
            rag_entities = await rag_and_alias_extraction(raw_node_id, gr)
        finally:
            if hasattr(gr, "async_driver"):
                await gr.async_driver.close()

    # 3. 在 GraphML 中校验 RAG 实体存在性
    graph = nx.read_graphml(graphml_path)
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

    # 4. 合并去重
    merged = []
    seen = set()
    for name in fuzz_entities + filtered_rag:
        key = name.lower()
        if key not in seen:
            seen.add(key)
            merged.append(name)

    return merged

async def main():
    raw_node_id = "Dumbledore"
    graphml_path = os.path.join("cache", "graph_chunk_entity_relation.graphml")
    merged = await extract_entities(raw_node_id, graphml_path)
    print(f"[合并结果] 共 {len(merged)} 个实体: {merged}")

if __name__ == "__main__":
    # 保持原来命令行可直接跑的功能
    asyncio.run(main())