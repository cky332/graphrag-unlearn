import os
import asyncio
import json
import sys
from dataclasses import asdict

from nano_graphrag.graphrag import GraphRAG
from nano_graphrag._storage.gdb_networkx import NetworkXStorage
from nano_graphrag._op import _pack_single_community_describe, _community_report_json_to_str
from nano_graphrag.prompt import PROMPTS
from delete_utils import clean_node_id, get_logger, load_api_config

logger = get_logger()

# 全局禁止实体名称（由 prune_edges_for_node 通过参数传入）
FORBID_ENTITY: str = ""

# 从环境变量或 .env 文件加载 API 配置
load_api_config()

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def update_single_community_report(rag: GraphRAG, community_id: str, old_reports: dict):
    """
    与 delete_community_update_reports.py 中相同的更新逻辑，
    仅更新 report_string 和 report_json，并在 prompt 中强制过滤 FORBID_ENTITY。
    """
    global FORBID_ENTITY

    kv = rag.community_reports
    kg = rag.chunk_entity_relation_graph
    config = asdict(rag)

    # 获取最新 schema
    schema = (await kg.community_schema()).get(community_id)
    old_data = old_reports.get(community_id, {})

    # 社区无节点时，仅清空报告字段
    if not schema or not schema.get('nodes'):
        new_data = {**old_data, 'report_string': '', 'report_json': {}}
        await kv.upsert({community_id: new_data})
        logger.info(f"社区 {community_id} 节点为空，仅清空报告字段。")
        return

    # 生成描述
    desc = await _pack_single_community_describe(
        kg,
        schema,
        max_token_size=config['best_model_max_token_size'],
        already_reports={},
        global_config=config
    )

    # 构建“前置清洗+过滤”指令
    forbid = FORBID_ENTITY
    if forbid:
        preamble = f"""
IMPORTANT: You are given an 'Entities' section and a 'Relationships' section below.
Before generating the report, you MUST perform the following CLEANING steps:
  1. Remove any line in the Entities section where id == "{forbid}".
  2. Remove any line in the Relationships section where source == "{forbid}" OR target == "{forbid}".
After cleaning, you will ONLY use the remaining Entities and Relationships to generate the report.

Then, follow these RULES EXACTLY:
  - Do NOT mention, reference, or imply anything about "{forbid}".
  - Do NOT include any content derived from "{forbid}" (directly or indirectly).
  - If no entities remain after cleaning, output:
      {{ "title": "", "summary": "", "findings": [], "recommendations": [] }}
  - Your output must be ONE SINGLE valid JSON object, and nothing else.

-----Begin Cleansed Input Below-----
""".strip()
        prompt_body = PROMPTS['community_report'].format(input_text=desc)
        prompt = "\n\n".join([preamble, prompt_body])
    else:
        prompt = PROMPTS['community_report'].format(input_text=desc)

    # 调用 LLM
    resp = await rag.best_model_func(
        prompt,
        **rag.special_community_report_llm_kwargs
    )


    # 解析 & 写回
    report_json = rag.convert_response_to_json_func(resp)
    report_str = _community_report_json_to_str(report_json)
    new_data = {**old_data, 'report_string': report_str, 'report_json': report_json}
    await kv.upsert({community_id: new_data})
    logger.info(f"社区 {community_id} 报告字段已更新。")


async def prune_edges_for_node(raw_node_id: str,
                               graphml_file: str = os.path.join('cache', 'graph_chunk_entity_relation.graphml')):
    """
    根据 raw_node_id，剪枝社区中涉及该节点的间接边并更新报告，
    同时设定全局 FORBID_ENTITY，使后续报告中不出现该实体。
    """
    global FORBID_ENTITY
    FORBID_ENTITY = raw_node_id

    target_lower = raw_node_id.lower()

    # 初始化
    rag = GraphRAG(working_dir='cache')
    await rag.chunk_entity_relation_graph.index_start_callback()
    await rag.community_reports.index_start_callback()

    # 读取旧报告
    reports_path = os.path.join(rag.working_dir, 'kv_store_community_reports.json')
    with open(reports_path, 'r', encoding='utf-8') as f:
        old_reports = json.load(f)

    # 匹配节点
    g = rag.chunk_entity_relation_graph._graph
    nodes = [n for n in g.nodes if clean_node_id(n).lower() == target_lower]
    if not nodes:
        logger.warning(f"未找到节点 '{raw_node_id}'")
        await rag.community_reports.index_done_callback()
        await rag.chunk_entity_relation_graph.index_done_callback()
        return
    key = nodes[0]
    logger.info(f"匹配到节点: {key}")

    # 获取社区 schemas
    schemas = await rag.chunk_entity_relation_graph.community_schema()

    # 遍历相连边并删除
    for src, tgt in list(g.edges(key)):
        nbr = tgt if src == key else src
        for cid, schema in schemas.items():
            if nbr in schema.get('nodes', []) and key not in schema.get('nodes', []):
                logger.info(f"社区 {cid} 包含邻居 {nbr} 且不含 {key}，删除边并更新报告")
                # 删除图中边
                if isinstance(rag.chunk_entity_relation_graph, NetworkXStorage):
                    try:
                        g.remove_edge(src, tgt)
                    except Exception as e:
                        logger.warning(f"删除边失败: {e}")
                # 更新 JSON 中的 edges 字段
                old_reports[cid]['edges'] = [
                    e for e in old_reports[cid].get('edges', [])
                    if not (clean_node_id(e[0]).lower() == target_lower or clean_node_id(e[1]).lower() == target_lower)
                ]
                # 用带过滤的更新函数
                await update_single_community_report(rag, cid, old_reports)

    # 持久化 JSON 文件
    with open(reports_path, 'w', encoding='utf-8') as f:
        json.dump(old_reports, f, indent=2, ensure_ascii=False)
    logger.info(f"已将更新后的 edges 写回 {reports_path}")

    # 完成索引持久化
    await rag.community_reports.index_done_callback()
    await rag.chunk_entity_relation_graph.index_done_callback()
    logger.info("间接边剪枝与报告更新完成。")


if __name__ == '__main__':
    node = sys.argv[1] if len(sys.argv) > 1 else ""
    asyncio.run(prune_edges_for_node(node))