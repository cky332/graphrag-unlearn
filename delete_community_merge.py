#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from delete_utils import get_logger

logger = get_logger()

# 配置文件路径
DELETED_FILE = "deleted_clusters_cache.json"
BASE_FILE = os.path.join("cache", "kv_store_community_reports.json")
MERGE_FILE = "kv_store_community_reports3.json"


def main():
    # 读取要删除的社区ID列表
    if not os.path.exists(DELETED_FILE):
        logger.info(f"⚠️ 文件不存在: {DELETED_FILE}")
        return
    with open(DELETED_FILE, encoding='utf-8') as f:
        deleted_ids = set(json.load(f))
    logger.info(f"待删除社区ID: {deleted_ids}")

    # 读取基础社区报告
    if not os.path.exists(BASE_FILE):
        logger.info(f"⚠️ 文件不存在: {BASE_FILE}")
        return
    with open(BASE_FILE, encoding='utf-8') as f:
        base_reports = json.load(f)
    logger.info(f"原始基础报告中社区总数: {len(base_reports)}")

    # 删除指定的社区
    for cid in deleted_ids:
        if cid in base_reports:
            base_reports.pop(cid)
            logger.info(f"已删除社区: {cid}")
        else:
            logger.info(f"社区 {cid} 不在基础报告中，跳过")
    logger.info(f"删除后基础报告中剩余社区数: {len(base_reports)}")

    # 读取要合并的新报告
    if not os.path.exists(MERGE_FILE):
        logger.info(f"⚠️ 文件不存在: {MERGE_FILE}")
        return
    with open(MERGE_FILE, encoding='utf-8') as f:
        new_reports = json.load(f)
    logger.info(f"要合并的新报告中社区总数: {len(new_reports)}")

    # 合并：新报告的键直接写入基础报告 (若有重复则覆盖)
    for cid, data in new_reports.items():
        base_reports[cid] = data
    logger.info(f"合并后基础报告中社区总数: {len(base_reports)}")

    # 将合并结果写回基础文件
    with open(BASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(base_reports, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ 已更新并写回: {BASE_FILE}")


if __name__ == '__main__':
    main()
