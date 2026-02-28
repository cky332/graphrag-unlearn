import json
import asyncio
from dataclasses import asdict
import os
import sys

from nano_graphrag.graphrag import GraphRAG
from nano_graphrag._op import _pack_single_community_describe, _community_report_json_to_str
from nano_graphrag.prompt import PROMPTS
from delete_utils import get_logger, load_api_config

logger = get_logger()

# 全局存储旧的社区报告数据
OLD_REPORTS: dict = {}
# 全局禁止实体名称（由 delete_community.py 传入）
FORBID_ENTITY: str = ""

# 从环境变量或 .env 文件加载 API 配置
load_api_config()

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def update_single_community_report(rag: GraphRAG, community_id: str):
    """
    仅更新 report_string 和 report_json，不修改其他字段（nodes, edges 等）。
    在 prompt 中强制：
      - 从输入中清洗掉所有与 FORBID_ENTITY 相关的数据
      - 严格禁止输出中出现该实体及任何关联信息
    """
    global FORBID_ENTITY

    community_report_kv = rag.community_reports
    knowledge_graph_inst = rag.chunk_entity_relation_graph
    global_config = asdict(rag)

    # 获取最新 schema 以生成 description
    all_schema = await knowledge_graph_inst.community_schema()
    schema = all_schema.get(community_id)

    # 从全局 OLD_REPORTS 中获取旧值
    old_data = OLD_REPORTS.get(community_id, {})

    # 如果社区没有节点，仅清空报告字段
    if not schema or not schema.get('nodes'):
        new_data = {
            **old_data,
            'report_string': '',
            'report_json': {}
        }
        await community_report_kv.upsert({community_id: new_data})
        logger.info(f"INFO: 社区 {community_id} 节点为空，仅清空报告字段。")
        return

    # 打包社区描述（未做额外过滤）
    describe = await _pack_single_community_describe(
        knowledge_graph_inst,
        schema,
        max_token_size=global_config['best_model_max_token_size'],
        already_reports={},  # 不使用子社区
        global_config=global_config,
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

        prompt_body = PROMPTS['community_report'].format(input_text=describe)
        prompt = "\n\n".join([preamble, prompt_body])
    else:
        prompt = PROMPTS['community_report'].format(input_text=describe)

    # 调用 LLM 生成报告 JSON
    response = await rag.best_model_func(
        prompt,
        **rag.special_community_report_llm_kwargs
    )

    # 解析并合并
    report_json = rag.convert_response_to_json_func(response)
    report_string = _community_report_json_to_str(report_json)

    new_data = {
        **old_data,
        'report_string': report_string,
        'report_json': report_json
    }
    await community_report_kv.upsert({community_id: new_data})
    print(f"INFO: 社区 {community_id} 报告字段已更新。")


async def main(forbid_entity: str = ""):
    """
    forbid_entity：要禁止在报告中出现的实体名称，通常传入 raw_node_id。
    """
    global OLD_REPORTS, FORBID_ENTITY
    FORBID_ENTITY = forbid_entity

    # 加载删除的社区列表
    with open('deleted_clusters_cache.json', 'r', encoding='utf-8') as f:
        deleted_clusters = json.load(f)

    # 初始化 GraphRAG，工作目录设为 'cache'
    rag = GraphRAG(working_dir='cache')

    # 启动 KV 存储上下文
    await rag.community_reports.index_start_callback()
    # 启动图存储上下文（仅读）
    await rag.chunk_entity_relation_graph.index_start_callback()

    # 预加载旧的社区报告 JSON
    reports_path = os.path.join(rag.working_dir, 'kv_store_community_reports.json')
    with open(reports_path, 'r', encoding='utf-8') as f:
        OLD_REPORTS = json.load(f)

    # 遍历并更新每个社区报告
    for community_id in deleted_clusters:
        await update_single_community_report(rag, community_id)

    # 提交 KV 存储事务
    await rag.community_reports.index_done_callback()
    # 提交图存储事务
    await rag.chunk_entity_relation_graph.index_done_callback()


if __name__ == '__main__':
    # 可接受一个可选参数 forbid_entity
    forbid = sys.argv[1] if len(sys.argv) > 1 else ""
    asyncio.run(main(forbid))