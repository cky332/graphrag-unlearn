#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import html
import asyncio
import time
import networkx as nx
import sys

from nano_graphrag.base import QueryParam
from nano_graphrag.graphrag import GraphRAG
from nano_graphrag._llm import deepseek_v3_complete
from delete_utils import load_api_config, get_logger

logger = get_logger()

load_api_config()

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
async def rag_and_alias_extraction(raw_node_id: str, gr: GraphRAG) -> list[str]:
    """
    对 raw_node_id 执行三种 RAG 查询（local/global/naive），
    合并结果后用 deepseek-v3 提取别名/拼写变体。
    """
    logger.info(f"[RAG] 开始三种 RAG 查询: '{raw_node_id}'")

    t0 = time.time()
    logger.info("[RAG] 执行 LOCAL 查询...")
    resp_local  = await gr.aquery(raw_node_id, param=QueryParam(mode="local",  top_k=3))
    logger.info(f"[RAG] LOCAL 查询完成，耗时 {time.time() - t0:.1f}s，结果长度={len(str(resp_local))}")

    t0 = time.time()
    logger.info("[RAG] 执行 GLOBAL 查询...")
    resp_global = await gr.aquery(raw_node_id, param=QueryParam(mode="global", top_k=3))
    logger.info(f"[RAG] GLOBAL 查询完成，耗时 {time.time() - t0:.1f}s，结果长度={len(str(resp_global))}")

    t0 = time.time()
    logger.info("[RAG] 执行 NAIVE 查询...")
    resp_naive  = await gr.aquery(raw_node_id, param=QueryParam(mode="naive",  top_k=3))
    logger.info(f"[RAG] NAIVE 查询完成，耗时 {time.time() - t0:.1f}s，结果长度={len(str(resp_naive))}")

    combined_text = ""
    for resp in (resp_local, resp_global, resp_naive):
        if isinstance(resp, str):
            combined_text += resp + " "
        elif isinstance(resp, list):
            for item in resp:
                if isinstance(item, dict) and "text" in item:
                    combined_text += item["text"] + " "
                elif isinstance(item, str):
                    combined_text += item + " "
        else:
            combined_text += str(resp) + " "
    combined_text = combined_text.strip()
    logger.info(f"[RAG] 三种查询结果合并完成，combined_text 长度={len(combined_text)} 字符")

    prompt = (
        f"Text:\n{combined_text}\n\n"
        f'Task: Identify all unique proper names, aliases, or spelling variants that refer to "{raw_node_id}".\n'
        "Requirements:\n"
        "1. Output exactly one line: a comma-separated list of the names.\n"
        "2. Do NOT output any additional commentary, explanation, or punctuation.\n"
        "3. Each name should appear only once, without quotes.\n"
        "4. Case-insensitive matching; preserve original capitalization.\n"
        "5. If no variants are found, output an empty line.\n"
    )
    t0 = time.time()
    logger.info("[RAG] 调用 DeepSeek-v3 提取别名...")
    alias_resp = await deepseek_v3_complete(prompt)
    logger.info(f"[RAG] DeepSeek-v3 调用完成，耗时 {time.time() - t0:.1f}s，原始响应: {alias_resp[:200]}")

    raw_aliases = []
    for line in alias_resp.replace("；", ";").replace("、", ",").splitlines():
        for part in line.split(","):
            a = part.strip().strip('"').strip()
            if a:
                raw_aliases.append(a)

    aliases = []
    seen = set()
    for a in raw_aliases:
        key = a.lower()
        if key not in seen:
            seen.add(key)
            aliases.append(a)

    logger.info(f"[RAG] DeepSeek-v3 提取到 {len(aliases)} 个别名/变体: {aliases}")
    return aliases

def clean_node_id(raw: str) -> str:
    """把 GraphML 中的节点 ID （含 &quot; 和外层双引号）还原并去掉外层引号。"""
    unesc = html.unescape(raw)
    return unesc[1:-1] if unesc.startswith('"') and unesc.endswith('"') else unesc

def graph_has_node(graph: nx.Graph, alias: str) -> bool:
    """忽略大小写检查 alias 是否正好匹配 graph 中某个节点 ID。"""
    for n in graph.nodes():
        if clean_node_id(n).lower() == alias.lower():
            return True
    return False

async def main():
    raw_node_id = "Dumbledore"

    gr = GraphRAG(
        working_dir="./cache",
        enable_local=True,
        enable_naive_rag=True,
    )

    aliases = await rag_and_alias_extraction(raw_node_id, gr)

    graphml_path = os.path.join("cache", "graph_chunk_entity_relation.graphml")
    if not os.path.isfile(graphml_path):
        print(f"文件不存在: {graphml_path}")
        return
    graph = nx.read_graphml(graphml_path)

    valid_entities = [a for a in aliases if graph_has_node(graph, a)]
    print(f"在 GraphML 中存在的别名/实体: {valid_entities}")

if __name__ == "__main__":
    asyncio.run(main())
