# GraphRAG Entity Deletion

基于 [nano-graphrag](https://github.com/gusye1234/nano-graphrag) 的知识图谱实体删除工具。从 GraphRAG 的知识图谱中删除指定实体及其关联信息，并通过多种攻击策略评估删除效果。

## 环境配置

```shell
pip install -e .
```

在 `.env` 文件中配置 API：

```
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.zhizengzeng.com/v1/
```

## 使用方法

### 删除实体

```shell
python "delete all.py" <实体名>
```

示例：

```shell
python "delete all.py" Benjamin
```

删除流程：
1. 实体识别（模糊匹配 + RAG 别名提取）
2. 图谱描述匿名化（1-hop / 2-hop / 3-hop 邻居）
3. 文本块中的实体名替换为 `[mask]`
4. 社区报告更新
5. 节点和边移除
6. VDB 条目删除

删除前会自动备份到 `cache/.deletion_backups/`。

### 验证删除效果

**离线验证（不需要 API）：**

```shell
python find_graphml_description_number.py
python find_entity_graphml.py
```

**评估脚本（需要 API）：**

| 脚本 | 说明 |
|------|------|
| `evaluate_Dumbledore_no_attack.py` | 无攻击基线 |
| `evaluate_dumblore_Multiple Choice.py` | 多选题评估 |
| `evaluate_Dumbledore_Affirmative Suffix.py` | 肯定后缀攻击 |
| `evaluate_Dumbledore_Background Hint.py` | 背景提示攻击 |
| `evaluate_Dumbledore_In-context Learning.py` | 上下文学习攻击 |
| `evaluate_Dumbledore_Prefix Injection.py` | 前缀注入攻击 |
| `evaluate_Dumbledore_Reverse Query.py` | 反向查询攻击 |
| `evaluate_Dumbledore_Role Playing.py` | 角色扮演攻击 |
| `evaluate_Dumbledore_Synonym Manipulation.py` | 同义词替换攻击 |
| `evaluate_Dumbledore_neighbor.py` | 邻居实体评估 |
| `evaluate_Dumbledore_unrelated.py` | 无关实体评估 |

评估指标：ROUGE-1/2/L（越低说明删除越彻底）和多选准确率。

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

## 致谢

基于 [nano-graphrag](https://github.com/gusye1234/nano-graphrag) 开发。
