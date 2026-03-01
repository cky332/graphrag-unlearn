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
    "text": "Who is accountable for conveying the boy wizard to the Dursley household?"
  },
  {
    "text": "Who conferred about the Dark Lord’s vanishing with the Transfiguration mistress?"
  },
  {
    "text": "Who referred to banquets and festivities as celebrations occurring in the magical realm?"
  },
  {
    "text": "Who was the sole mage whom the Dark Lord dreaded?"
  },
  {
    "text": "Which half‑giant gamekeeper referred to the school matron in connection with his new winter ear protectors?"
  },
  {
    "text": "Which headmaster relied on the half‑giant gamekeeper for vital duties such as escorting the boy wizard?"
  },
  {
    "text": "Which wizard presented sherbet lemons to the Transfiguration mistress?"
  },
  {
    "text": "Which wizard possesses and comprehends a silver timepiece that tracks celestial orbits?"
  },
  {
    "text": "Which central figure in the magical society makes decisions shaping its destiny?"
  },
  {
    "text": "Which wizard placed a note beside the infant detailing his circumstances?"
  },
  {
    "text": "Which wizard employed the Silver Put‑Outer to obscure his spellwork on Privet Path?"
  },
  {
    "text": "Which wizard vaulted the hedge barrier to reach the Dursley household’s entrance?"
  },
  {
    "text": "Which headmaster hinted at joining the festivities following the Dark Lord’s downfall?"
  },
  {
    "text": "Which wizard is portrayed as a sage and commanding presence determining the boy’s destiny, such as consigning him to the Dursley household?"
  },
  {
    "text": "Which headmaster is portrayed as the one who escorted the boy wizard to the Dursleys and utilized the silver device to mask their exit?"
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
            "strictly based on the provided context."
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
