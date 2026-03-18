"""核心删除逻辑 - 从 delete all.py 提取，供 API 调用。"""

import os
import time
import xml.etree.ElementTree as ET

from api.config import ServerConfig
from delete_utils import (
    get_logger,
    load_api_config,
    validate_entity_exists,
    create_backup,
    restore_backup,
    cleanup_temp_files,
    DeletionReport,
    DeletionError,
    EntityNotFoundError,
)

logger = get_logger()

# 标记是否已完成初始化（API 配置 + 依赖模块导入）
_initialized = False


def _ensure_initialized():
    """延迟加载：首次调用删除时才加载 API 配置和依赖模块。

    这样服务启动时不需要 OPENAI_API_KEY，只有实际执行删除时才需要。
    """
    global _initialized
    if _initialized:
        return

    # 优先从 CWD 加载 .env（与 delete all.py 行为一致），
    # 找不到则 fallback 到项目根目录
    cwd_env = os.path.abspath(".env")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_env = os.path.join(project_root, ".env")

    if os.path.isfile(cwd_env):
        env_file = cwd_env
    elif os.path.isfile(root_env):
        env_file = root_env
    else:
        env_file = cwd_env  # 让 load_api_config 报出具体路径

    logger.info(f"首次初始化：加载配置文件 {env_file}")
    load_api_config(env_file)

    # 预初始化 tiktoken 编码器（需要从 openaipublic.blob.core.windows.net 下载）
    logger.info("预初始化 tiktoken 编码器...")
    import tiktoken
    try:
        tiktoken.encoding_for_model("gpt-4o")
        logger.info("tiktoken 编码器初始化成功")
    except Exception as e:
        logger.error(
            f"tiktoken 初始化失败: {e}\n"
            "可能原因: 无法访问 openaipublic.blob.core.windows.net\n"
            "解决方案:\n"
            "  1. 在能联网的机器上运行: python -c \"import tiktoken; tiktoken.encoding_for_model('gpt-4o')\"\n"
            "  2. 将 ~/.cache/tiktoken_cache 目录复制到服务器相同位置\n"
            "  3. 或设置环境变量 TIKTOKEN_CACHE_DIR 指向缓存目录"
        )
        raise

    global delete_vdb_entities, extract_entities, update_graphml_descriptions
    global remove_node_and_edges, delete_community_pipeline
    global anonymize_all_chunks, update_reports_for_entity

    logger.info("加载删除流程模块...")
    from delete_vdb_entities import delete_vdb_entities
    from before_search import extract_entities
    from delete_update_description import update_graphml_descriptions
    from delete_node_edge import remove_node_and_edges
    from delete_community import delete_community_pipeline
    from delete_text_chunk import anonymize_all_chunks
    from delete_community_update_reports_last import update_reports_for_entity

    logger.info("所有模块加载完成，初始化成功")
    _initialized = True


async def run_deletion(
    entity_name: str,
    no_backup: bool = False,
) -> DeletionReport:
    """执行完整的实体删除流程。

    cache_dir 从 ServerConfig 读取，不再由调用方传入。
    成功时返回 DeletionReport，失败时自动从备份恢复并抛出异常。
    """
    pipeline_start = time.time()
    _ensure_initialized()
    cache_dir = ServerConfig.get_cache_dir()
    vdb_path = os.path.join(cache_dir, "vdb_entities.json")
    graphml_path = os.path.join(cache_dir, "graph_chunk_entity_relation.graphml")
    kv_store_path = os.path.join(cache_dir, "kv_store_text_chunks.json")

    logger.info(f"========== 开始删除实体 '{entity_name}' ==========")
    logger.info(f"cache_dir={cache_dir}, graphml={graphml_path}")

    report = DeletionReport(entity=entity_name)
    backup_dir = None

    try:
        # 验证实体是否存在（非致命 - RAG 提取仍可能找到关联实体）
        logger.info(f"正在验证实体 '{entity_name}' 是否存在...")
        try:
            entity_info = validate_entity_exists(graphml_path, entity_name)
            logger.info(
                f"实体已找到: 连接边数={entity_info['edge_count']}, "
                f"描述={entity_info['description'][:50]}..."
            )
        except EntityNotFoundError:
            logger.warning(
                f"实体 '{entity_name}' 不直接存在于图中，"
                "将通过模糊匹配和 RAG 提取关联实体..."
            )

        # Step 0: 提取关联实体
        step_start = time.time()
        logger.info("Step 0: 提取关联实体（模糊匹配 + RAG）...")
        entities = await extract_entities(entity_name, graphml_path)
        logger.info(f"Step 0 完成，耗时 {time.time() - step_start:.1f}s，"
                     f"共找到 {len(entities)} 个关联实体：{entities}")
        report.related_entities = list(entities)

        if not entities:
            logger.warning("未找到任何关联实体，删除流程终止。")
            report.finalize()
            return report

        # 创建备份
        if not no_backup:
            logger.info("正在创建备份...")
            backup_dir = create_backup(cache_dir, entity_name)
            report.backup_dir = backup_dir
        else:
            logger.warning("已跳过备份（no_backup=True）")

        # 逐个处理关联实体
        for idx, entity in enumerate(entities, 1):
            entity_start = time.time()
            logger.info(f"\n>>> [{idx}/{len(entities)}] 正在处理实体: {entity}")

            # Step 1: 匿名化描述
            step_start = time.time()
            logger.info(f"--- Step 1: 匿名化描述 '{entity}' ---")
            await update_graphml_descriptions(graphml_path, entity, entity_name)
            logger.info(f"--- Step 1 完成，耗时 {time.time() - step_start:.1f}s ---")

            # Step 2: 匿名化文本块
            step_start = time.time()
            logger.info("--- Step 2: 匿名化文本块 ---")
            try:
                results = await anonymize_all_chunks(
                    kv_store_path, entity, entity_name
                )
                report.chunks_anonymized += len(results)
                logger.info(f"--- Step 2 完成，耗时 {time.time() - step_start:.1f}s，"
                             f"匿名化 {len(results)} 个 chunk ---")
            except FileNotFoundError as e:
                logger.warning(f"文本块处理失败: {e}")
                report.errors.append(f"文本块处理失败 ({entity}): {e}")
                continue

            # Step 3: 社区删除流程（条件执行）
            step_start = time.time()
            run_step3 = False
            try:
                tree = ET.parse(graphml_path)
                root = tree.getroot()
                for node in root.findall(".//{*}node"):
                    node_id = node.get("id", "")
                    if node_id.strip('"') == entity:
                        for data in node.findall("{*}data"):
                            if data.get("key") == "d3":
                                run_step3 = True
                                break
                        break
            except Exception as e:
                logger.warning(f"检查社区数据时出错: {e}")

            if run_step3:
                logger.info(f"--- Step 3: 执行社区删除流程 '{entity}' ---")
                await delete_community_pipeline(entity)
                report.communities_updated += 1
                logger.info(f"--- Step 3 完成，耗时 {time.time() - step_start:.1f}s ---")
            else:
                logger.info(f"--- Step 3: 跳过（'{entity}' 无社区数据）---")

            # Step 4: 匿名化社区报告
            step_start = time.time()
            logger.info("--- Step 4: 匿名化社区报告 ---")
            update_reports_for_entity(entity_name)
            logger.info(f"--- Step 4 完成，耗时 {time.time() - step_start:.1f}s ---")

            # Step 5: 移除节点和边
            step_start = time.time()
            logger.info("--- Step 5: 移除节点和边 ---")
            n_nodes, n_edges = remove_node_and_edges(graphml_path, entity)
            report.nodes_removed += n_nodes
            report.edges_removed += n_edges
            logger.info(f"--- Step 5 完成，耗时 {time.time() - step_start:.1f}s，"
                         f"移除 {n_nodes} 节点, {n_edges} 边 ---")

            # Step 6: 从 VDB 中删除
            step_start = time.time()
            logger.info("--- Step 6: 从 VDB 中删除 ---")
            try:
                n_vdb = delete_vdb_entities(entity, vdb_path)
                report.vdb_entries_removed += n_vdb
                logger.info(f"--- Step 6 完成，耗时 {time.time() - step_start:.1f}s，"
                             f"删除 {n_vdb} 条 VDB 记录 ---")
            except DeletionError as e:
                logger.warning(f"VDB 删除失败: {e}")
                report.errors.append(f"VDB 删除失败 ({entity}): {e}")

            logger.info(f">>> 实体 '{entity}' 处理完成，耗时 {time.time() - entity_start:.1f}s")

        report.finalize()
        total_time = time.time() - pipeline_start
        logger.info(f"========== 删除流程完成，总耗时 {total_time:.1f}s ==========")
        logger.info(report.summary())
        return report

    except Exception as e:
        total_time = time.time() - pipeline_start
        logger.error(f"删除流程失败（已运行 {total_time:.1f}s）: {e}")
        import traceback
        logger.error(f"异常详情:\n{traceback.format_exc()}")
        report.errors.append(str(e))
        if backup_dir:
            logger.info(f"正在从备份恢复: {backup_dir}")
            restore_backup(backup_dir, cache_dir)
            logger.info("已从备份恢复，数据未受影响。")
        raise

    finally:
        cleanup_temp_files()
