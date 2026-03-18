#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from delete_utils import get_logger

logger = get_logger()

def ensure_unique_ids(
    base_file: str,
    new_file: str,
    prefix: str = "cluster"
):
    """
    Load two JSON community‐reports files, then rewrite the community IDs in `new_file`
    so none collide with those in `base_file`. Writes the result back to `new_file`.
    """
    with open(base_file, encoding="utf-8") as f:
        base_reports = json.load(f)
    old_ids = set(base_reports.keys())

    with open(new_file, encoding="utf-8") as f:
        new_reports = json.load(f)

    numeric_old = [int(i) for i in old_ids if i.isdigit()]
    offset = max(numeric_old) + 1 if numeric_old else 1

    id_map: dict[str, str] = {}
    for old_id in new_reports:
        if old_id.isdigit():
            new_id = str(int(old_id) + offset)
        else:
            candidate = old_id
            suffix = 1
            while candidate in old_ids or candidate in id_map.values():
                candidate = f"{old_id}_{suffix}"
                suffix += 1
            new_id = candidate

        id_map[old_id] = new_id

    unique_reports: dict[str, dict] = {}
    for old_id, data in new_reports.items():
        new_id = id_map[old_id]

        title = data.get("title", "")
        data["title"] = title.replace(old_id, new_id)

        subs = data.get("sub_communities", [])
        data["sub_communities"] = [id_map.get(sub, sub) for sub in subs]

        unique_reports[new_id] = data

    with open(new_file, "w", encoding="utf-8") as f:
        json.dump(unique_reports, f, ensure_ascii=False, indent=2)

    logger.info(f"Processed {len(new_reports)} communities, updated {new_file}")

if __name__ == "__main__":
    ensure_unique_ids(
        base_file="cache/kv_store_community_reports.json",
        new_file="kv_store_community_reports3.json"
    )
