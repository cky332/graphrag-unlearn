#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统计文本文件中出现频率最高的实体（仅保留有意义的实体类型），
基于 spaCy 实体识别，并使用白名单过滤实体类型。
要运行本脚本，请先安装：
    pip install spacy
    python -m spacy download en_core_web_sm
"""

import spacy
from collections import Counter

# 实体类型白名单（只保留这些类型，过滤掉"said""said"等无意义词）
VALID_LABELS = {
    'PERSON',        # 人名
    'ORG',           # 机构
    'GPE',           # 国家/城市/地点
    'NORP',          # 民族/宗教/政治派别
    'FAC',           # 建筑物/设施
    'LOC',           # 地点
    'PRODUCT',       # 产品
    'EVENT',         # 事件
    'WORK_OF_ART',   # 艺术作品
    'LAW',           # 法律
    'LANGUAGE'       # 语言
}

def get_top_n_entities(file_path: str, n: int = 6,
                       model_name: str = "en_core_web_sm"):
    """
    读取指定文件，使用 spaCy 提取实体并过滤类型，统计出现频率最高的 n 个实体。
    :param file_path: 文本文件路径
    :param n: 要返回的实体数量
    :param model_name: spaCy 模型名称
    :return: List of tuples [(entity_text, count), ...]
    """
    # 加载 spaCy 模型
    nlp = spacy.load(model_name, disable=["tagger", "parser", "lemmatizer"])
    nlp.enable_pipe("ner")

    # 读取全文
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # 分析文本
    doc = nlp(text)

    # 筛选并统计实体
    entities = [
        ent.text.strip()
        for ent in doc.ents
        if ent.label_ in VALID_LABELS and len(ent.text.strip()) > 1
    ]
    counter = Counter(entities)
    return counter.most_common(n)


def main():
    input_file = 'harry.txt'
    top_n = 11

    top_entities = get_top_n_entities(input_file, top_n)

    print(f"在文件"{input_file}"中出现频率最高的 {top_n} 个有意义实体：")
    for rank, (ent, count) in enumerate(top_entities, start=1):
        print(f"{rank}. {ent} — {count} 次")


if __name__ == '__main__':
    main()
