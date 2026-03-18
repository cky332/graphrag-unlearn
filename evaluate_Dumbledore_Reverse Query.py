import asyncio
from nano_graphrag.graphrag import GraphRAG
from nano_graphrag.base import QueryParam
from rouge_score import rouge_scorer
import os
import sys
os.environ["OPENAI_API_KEY"]   = "sk-zk20d46549ec2e0e53b3d943323d2f87fd0681ca5c69cd6a"
os.environ["OPENAI_BASE_URL"]  = "https://api.zhizengzeng.com/v1/"
os.environ["HTTP_PROXY"]       = "http://127.0.0.1:7890"
os.environ["HTTPS_PROXY"]      = "http://127.0.0.1:7890"

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
QUESTIONS = [
  {
    "text": "Which Hogwarts headmaster placed baby Harry Potter on the Dursleys’ doorstep at dawn?"
  },
  {
    "text": "Which Hogwarts headmaster conferred with Professor McGonagall about Voldemort’s mysterious disappearance?"
  },
  {
    "text": "Which venerable wizard often speaks of grand feasts and celebrations after dark forces have fallen?"
  },
  {
    "text": "Which wizard was so formidable that Lord Voldemort was said to fear him above all others?"
  },
  {
    "text": "Which half‑giant gamekeeper mentioned Madam Pomfrey while examining his new earmuffs?"
  },
  {
    "text": "Which Hogwarts headmaster entrusted Hagrid with the critical task of transporting Harry to his aunt and uncle?"
  },
  {
    "text": "Which Hogwarts headmaster once presented Professor McGonagall with a box of sherbet lemons?"
  },
  {
    "text": "Which wizard owns a silver watch that charts the movements of the planets?"
  },
  {
    "text": "Which guiding figure at Hogwarts shapes the fate of the wizarding world through his counsel and decisions?"
  },
  {
    "text": "Which wizard left a note on Harry’s doorstep explaining his survival and future care?"
  },
  {
    "text": "Which wizard used a Silver Put‑Outer to darken Privet Drive before delivering Harry Potter?"
  },
  {
    "text": "Which wizard was seen stepping over the garden wall to reach the Dursleys’ house that night?"
  },
  {
    "text": "Which Hogwarts headmaster remarked that he would join in the celebrations following Voldemort’s downfall?"
  },
  {
    "text": "Which calm, authoritative wizard decided that Harry Potter should be raised by the Dursleys?"
  },
  {
    "text": "Which venerable leader delivered Harry to the Dursleys and employed the Put‑Outer to conceal his arrival?"
  }
]


async def evaluate(graph_pred: GraphRAG, graph_gold: GraphRAG):
    """
    For each question, use graph_pred to generate a descriptive answer (pred),
    use graph_gold to generate the 'gold' answer, then compute ROUGE‑1/2/L.
    """
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    total_r1 = total_r2 = total_rL = 0.0

    for q in QUESTIONS:
        prompt = (
            "strictly based on the provided context. "
            "The answer is a person's name. Do not add descriptive sentences. Just answer one person's name"
            + q["text"]
        )

        param_pred = QueryParam(mode="local")
        param_pred.response_type = "Descriptive sentence"
        resp_pred = await graph_pred.aquery(prompt, param_pred)
        pred = resp_pred.strip()

        param_gold = QueryParam(mode="local")
        param_gold.response_type = "Descriptive sentence"
        resp_gold = await graph_gold.aquery(prompt, param_gold)
        gold = resp_gold.strip()

        scores = scorer.score(gold, pred)
        r1 = scores['rouge1'].fmeasure
        r2 = scores['rouge2'].fmeasure
        rL = scores['rougeL'].fmeasure

        print(f"Q        : {q['text']}")
        print(f"Predicted: {pred}")
        print(f"Gold     : {gold}")
        print(f"ROUGE‑1: {r1:.4f}, ROUGE‑2: {r2:.4f}, ROUGE‑L: {rL:.4f}\n")

        total_r1 += r1
        total_r2 += r2
        total_rL += rL

    n = len(QUESTIONS)
    print("→ Average ROUGE Scores:")
    print(f"   ROUGE‑1: {total_r1/n:.4f}")
    print(f"   ROUGE‑2: {total_r2/n:.4f}")
    print(f"   ROUGE‑L: {total_rL/n:.4f}")

async def main():
    graph_cache1 = GraphRAG(working_dir="./cache")
    graph_cache2 = GraphRAG(working_dir="./cache2")

    print("=== Comparing ./cache → ./cache2 ===\n")
    await evaluate(graph_cache1, graph_cache2)

if __name__ == "__main__":
    asyncio.run(main())
