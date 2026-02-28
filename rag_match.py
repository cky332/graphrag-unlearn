#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import html
import asyncio
import networkx as nx
import sys

from nano_graphrag.base import QueryParam
from nano_graphrag.graphrag import GraphRAG
from nano_graphrag._llm import deepseek_v3_complete
from delete_utils import load_api_config

# 从环境变量或 .env 文件加载 API 配置
load_api_config()

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
async def rag_and_alias_extraction(raw_node_id: str, gr: GraphRAG) -> list[str]:
    """
    对 raw_node_id 执行三种 RAG 查询（local/global/naive），
    合并结果后用 deepseek-v3 提取别名/拼写变体。
    """
    print("=== 开始调用三种 RAG 查询 ===")
    resp_local  = await gr.aquery(raw_node_id, param=QueryParam(mode="local",  top_k=3))
    print(f"[LOCAL  查询结果]  {resp_local}")
    resp_global = await gr.aquery(raw_node_id, param=QueryParam(mode="global", top_k=3))
    print(f"[GLOBAL 查询结果] {resp_global}")
    resp_naive  = await gr.aquery(raw_node_id, param=QueryParam(mode="naive",  top_k=3))
    print(f"[NAIVE 查询结果]  {resp_naive}")

    # 合并所有查询结果为一个纯文本字符串
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

    # 用更严格的英文 Prompt 调用 deepseek-v3，只返回逗号分隔的实体名称列表
    prompt = (
        f"Text:\n{combined_text}\n\n"
        f"Task: Identify all unique proper names, aliases, or spelling variants that refer to “{raw_node_id}”.\n"
        "Requirements:\n"
        "1. Output exactly one line: a comma-separated list of the names.\n"
        "2. Do NOT output any additional commentary, explanation, or punctuation.\n"
        "3. Each name should appear only once, without quotes.\n"
        "4. Case-insensitive matching; preserve original capitalization.\n"
        "5. If no variants are found, output an empty line.\n"
    )
    alias_resp = await deepseek_v3_complete(prompt)

    # 拆分并清洗 alias 列表
    raw_aliases = []
    for line in alias_resp.replace("；", ";").replace("、", ",").splitlines():
        for part in line.split(","):
            a = part.strip().strip('"').strip()
            if a:
                raw_aliases.append(a)

    # 去重（忽略大小写）
    aliases = []
    seen = set()
    for a in raw_aliases:
        key = a.lower()
        if key not in seen:
            seen.add(key)
            aliases.append(a)

    print(f"DeepSeek-v3 提取到的别名/变体: {aliases}")
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

    # 完整的 GraphRAG 初始化，请根据你的环境调整参数
    gr = GraphRAG(
        working_dir="./cache",
        enable_local=True,
        enable_naive_rag=True,
        # 若有 Azure/OpenAI 接入，可在此添加相关配置
    )

    # 执行 RAG + 别名提取
    aliases = await rag_and_alias_extraction(raw_node_id, gr)

    # 读取本地 GraphML
    graphml_path = os.path.join("cache", "graph_chunk_entity_relation.graphml")
    if not os.path.isfile(graphml_path):
        print(f"文件不存在: {graphml_path}")
        return
    graph = nx.read_graphml(graphml_path)

    # 只保留那些确实在图里存在的别名
    valid_entities = [a for a in aliases if graph_has_node(graph, a)]
    print(f"在 GraphML 中存在的别名/实体: {valid_entities}")

if __name__ == "__main__":
    asyncio.run(main())
