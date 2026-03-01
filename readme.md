# GraphRAG Unlearn

基于 [nano-graphrag](https://github.com/gusye1234/nano-graphrag) 的知识图谱实体删除工具。从 GraphRAG 的知识图谱中删除指定实体及其关联信息，并通过多种攻击策略评估删除效果。

## 环境配置

```shell
pip install -e .
```

## 使用方法

### 删除实体

```shell
python "delete all.py" <实体名>
```

删除流程：
1. 实体识别（模糊匹配 + RAG 别名提取）
2. 图谱描述匿名化（1-hop / 2-hop / 3-hop 邻居）
3. 文本块中的实体名替换为 `[mask]`
4. 社区报告更新
5. 节点和边移除
6. VDB 条目删除

删除前会自动备份到 `cache/.deletion_backups/`。


## 项目结构

```
├── delete all.py                 # 删除主入口
├── delete_utils.py               # 公共工具函数
├── delete_update_description*.py # 图谱描述匿名化
├── delete_text_chunk.py          # 文本块匿名化
├── delete_node_edge.py           # 节点/边移除
├── delete_vdb_entities.py        # VDB 条目删除
├── delete_community*.py          # 社区检测与报告更新
├── before_search.py              # 实体识别（fuzz + RAG）
├── fuzzing_match.py              # 模糊匹配
├── rag_match.py                  # RAG 别名提取
├── evaluate_*.py                 # 评估脚本
├── find_graphml_description_number.py  # 残留检查
├── find_entity_graphml.py        # 实体提取检查
├── nano_graphrag/                # GraphRAG 核心（基于 nano-graphrag）
└── cache/                        # 数据缓存目录
```
