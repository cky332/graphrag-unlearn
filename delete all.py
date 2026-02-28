
import os
import argparse
import asyncio
import sys
import xml.etree.ElementTree as ET

from delete_utils import (
    get_logger,
    validate_entity_exists,
    create_backup,
    restore_backup,
    cleanup_temp_files,
    DeletionReport,
    DeletionError,
    EntityNotFoundError,
)
from delete_vdb_entities import delete_vdb_entities
from before_search import extract_entities
from delete_update_description import update_graphml_descriptions
from delete_node_edge import remove_node_and_edges
from delete_community import delete_community_pipeline
from delete_text_chunk import anonymize_all_chunks
from delete_community_update_reports_last import update_reports_for_entity

logger = get_logger()


def parse_args():
    parser = argparse.ArgumentParser(
        description="从 GraphRAG 知识图谱中删除指定实体及其关联数据"
    )
    parser.add_argument("entity", help="要删除的实体名称")
    parser.add_argument(
        "--cache-dir", default="cache", help="缓存目录路径 (默认: cache)"
    )
    parser.add_argument(
        "--no-backup", action="store_true", help="跳过删除前备份（不推荐）"
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="跳过交互确认提示"
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    raw_node_id_default = args.entity
    cache_dir = args.cache_dir

    vdb_path = os.path.join(cache_dir, "vdb_entities.json")
    graphml_path = os.path.join(cache_dir, "graph_chunk_entity_relation.graphml")
    kv_store_path = os.path.join(cache_dir, "kv_store_text_chunks.json")

    report = DeletionReport(entity=raw_node_id_default)
    backup_dir = None

    try:
        # ======== 预验证 ========
        logger.info(f"正在验证实体 ‘{raw_node_id_default}’ 是否存在...")
        try:
            entity_info = validate_entity_exists(graphml_path, raw_node_id_default)
            logger.info(
                f"实体已找到: 连接边数={entity_info[‘edge_count’]}, "
                f"描述={entity_info[‘description’][:50]}..."
            )
        except EntityNotFoundError:
            logger.warning(
                f"实体 ‘{raw_node_id_default}’ 不直接存在于图中，"
                "将通过模糊匹配和 RAG 提取关联实体..."
            )

        # ======== 提取关联实体 ========
        logger.info("Step 0: 提取关联实体...")
        entities = await extract_entities(raw_node_id_default, graphml_path)
        logger.info(f"共找到 {len(entities)} 个关联实体：{entities}")
        report.related_entities = list(entities)

        if not entities:
            logger.warning("未找到任何关联实体，删除流程终止。")
            return

        # ======== 交互确认 ========
        if not args.yes:
            print(f"\n{‘=’*60}")
            print("删除预览")
            print(f"{‘=’*60}")
            print(f"目标实体: {raw_node_id_default}")
            print(f"将处理的关联实体 ({len(entities)} 个):")
            for e in entities:
                print(f"  - {e}")
            print(f"{‘=’*60}")
            confirm = input("确认执行删除操作？(y/N): ").strip().lower()
            if confirm != "y":
                logger.info("用户取消了删除操作。")
                return

        # ======== 备份 ========
        if not args.no_backup:
            logger.info("正在创建备份...")
            backup_dir = create_backup(cache_dir, raw_node_id_default)
            report.backup_dir = backup_dir
        else:
            logger.warning("已跳过备份（--no-backup）")

        # ======== 执行删除流程 ========
        for entity in entities:
            logger.info(f"\n>>> 正在处理实体: {entity}")

            # Step 1: 更新 GraphML 描述
            logger.info(f"--- Step 1: 匿名化描述 ‘{entity}’ ---")
            await update_graphml_descriptions(graphml_path, entity, raw_node_id_default)

            # Step 2: 匿名化文本块
            logger.info(f"--- Step 2: 匿名化文本块 ---")
            try:
                results = await anonymize_all_chunks(
                    kv_store_path, entity, raw_node_id_default
                )
                report.chunks_anonymized += len(results)
                for cid, data in results.items():
                    logger.info(f"Chunk {cid} 已匿名化")
            except FileNotFoundError as e:
                logger.warning(f"文本块处理失败: {e}")
                report.errors.append(f"文本块处理失败 ({entity}): {e}")
                continue

            # Step 3: 社区删除流程（仅当节点有社区数据时）
            run_step3 = False
            try:
                tree = ET.parse(graphml_path)
                root = tree.getroot()
                for node in root.findall(".//{*}node"):
                    node_id = node.get("id", "")
                    if node_id.strip(‘"’) == entity:
                        for data in node.findall("{*}data"):
                            if data.get("key") == "d3":
                                run_step3 = True
                                break
                        break
            except Exception as e:
                logger.warning(f"检查社区数据时出错: {e}")

            if run_step3:
                logger.info(f"--- Step 3: 执行社区删除流程 ‘{entity}’ ---")
                await delete_community_pipeline(entity)
                report.communities_updated += 1
            else:
                logger.info(f"--- Step 3: 跳过（’{entity}’ 无社区数据）---")

            # Step 4: 匿名化社区报告
            logger.info(f"--- Step 4: 匿名化社区报告 ---")
            update_reports_for_entity(raw_node_id_default)

            # Step 5: 移除节点和边
            logger.info(f"--- Step 5: 移除节点和边 ---")
            n_nodes, n_edges = remove_node_and_edges(graphml_path, entity)
            report.nodes_removed += n_nodes
            report.edges_removed += n_edges

            # Step 6: 从 VDB 中删除
            logger.info(f"--- Step 6: 从 VDB 中删除 ---")
            try:
                n_vdb = delete_vdb_entities(entity, vdb_path)
                report.vdb_entries_removed += n_vdb
            except DeletionError as e:
                logger.warning(f"VDB 删除失败: {e}")
                report.errors.append(f"VDB 删除失败 ({entity}): {e}")

        # ======== 输出摘要报告 ========
        report.finalize()
        logger.info(report.summary())

    except Exception as e:
        logger.error(f"删除流程失败: {e}")
        report.errors.append(str(e))
        if backup_dir:
            logger.info(f"正在从备份恢复: {backup_dir}")
            restore_backup(backup_dir, cache_dir)
            logger.info("已从备份恢复，数据未受影响。")
        raise

    finally:
        # ======== 清理临时文件 ========
        cleanup_temp_files()


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())