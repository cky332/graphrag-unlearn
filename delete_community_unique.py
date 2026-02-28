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
    # Load existing community IDs
    with open(base_file, encoding="utf-8") as f:
        base_reports = json.load(f)
    old_ids = set(base_reports.keys())

    # Load the new reports that need re‐IDing
    with open(new_file, encoding="utf-8") as f:
        new_reports = json.load(f)

    # Compute numeric offset if IDs are all digits
    numeric_old = [int(i) for i in old_ids if i.isdigit()]
    offset = max(numeric_old) + 1 if numeric_old else 1

    # Build a mapping from old→new ID
    id_map: dict[str, str] = {}
    for old_id in new_reports:
        if old_id.isdigit():
            # shift numeric IDs by offset
            new_id = str(int(old_id) + offset)
        else:
            # for non‐numeric IDs, append suffix until unique
            candidate = old_id
            suffix = 1
            while candidate in old_ids or candidate in id_map.values():
                candidate = f"{old_id}_{suffix}"
                suffix += 1
            new_id = candidate

        id_map[old_id] = new_id

    # Rewrite the new_reports structure under new IDs
    unique_reports: dict[str, dict] = {}
    for old_id, data in new_reports.items():
        new_id = id_map[old_id]

        # Update title if it embeds the numeric ID
        title = data.get("title", "")
        data["title"] = title.replace(old_id, new_id)

        # Remap any sub_communities references
        subs = data.get("sub_communities", [])
        data["sub_communities"] = [id_map.get(sub, sub) for sub in subs]

        # Assign under the new key
        unique_reports[new_id] = data

    # Write the deduplicated version back to the same file
    with open(new_file, "w", encoding="utf-8") as f:
        json.dump(unique_reports, f, ensure_ascii=False, indent=2)

    logger.info(f"Processed {len(new_reports)} communities, updated {new_file}")

if __name__ == "__main__":
    ensure_unique_ids(
        base_file="cache/kv_store_community_reports.json",
        new_file="kv_store_community_reports3.json"
    )
