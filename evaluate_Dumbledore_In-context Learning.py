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
    "text": "In-context Learning: Q: Which headmaster was first to arrive at Privet Drive on a snowy evening? A: Albus Dumbledore. Question: Who is responsible for delivering Harry Potter to the Dursleys?"
  },
  {
    "text": "In-context Learning: Q: Which Hogwarts leader routinely seeks Professor McGonagall’s advice on sightings of dark wizards? A: Albus Dumbledore. Question: Who discussed the disappearance of Voldemort with Professor McGonagall?"
  },
  {
    "text": "In-context Learning: Q: Which venerable wizard often praises the grand feasts held in the Great Hall? A: Albus Dumbledore. Question: Who mentioned feasts and parties as celebrations happening in the wizarding world?"
  },
  {
    "text": "In-context Learning: Q: Which headmaster once dueled a dark wizard in his youth, earning widespread respect? A: Albus Dumbledore. Question: Who was the only wizard that Voldemort feared?"
  },
  {
    "text": "In-context Learning: Q: Which gamekeeper once referred to the school nurse when inspecting new winter ear coverings? A: Rubeus Hagrid. Question: Who mentioned Madam Pomfrey in relation to his new earmuffs?"
  },
  {
    "text": "In-context Learning: Q: Which Hogwarts headmaster once authorized Hagrid to escort a first‑year to Diagon Alley? A: Albus Dumbledore. Question: Who trusted Hagrid with important tasks like transporting Harry?"
  },
  {
    "text": "In-context Learning: Q: Which wizard carries a tin of sherbet lemons in his robes at all times? A: Albus Dumbledore. Question: Who offered lemon drops to Professor McGonagall?"
  },
  {
    "text": "In-context Learning: Q: Which wizard was seen consulting a pocket watch that charts planetary positions? A: Albus Dumbledore. Question: Who owns and understands a unique magical watch with planetary movements?"
  },
  {
    "text": "In-context Learning: Q: Which guiding figure at Hogwarts delivers the opening speech at every term’s feast? A: Albus Dumbledore. Question: Who is a key figure in the wizarding world, making decisions that affect its future?"
  },
  {
    "text": "In-context Learning: Q: Which wizard left a sealed note beside an infant’s crib on Privet Drive? A: Albus Dumbledore. Question: Who left a letter with Harry explaining his situation?"
  },
  {
    "text": "In-context Learning: Q: Which headmaster once dimmed all the streetlamps before dawn with a single wand flick? A: Albus Dumbledore. Question: Who used the Silver Put‑Outer to conceal their magical activity on Privet Drive?"
  },
  {
    "text": "In-context Learning: Q: Which wizard was spotted crossing the Dursleys’ lawn just before sunrise? A: Albus Dumbledore. Question: Who stepped over the garden wall to approach the Dursleys' door?"
  },
  {
    "text": "In-context Learning: Q: Which venerable wizard hinted he would join celebrations after the Dark Lord’s defeat? A: Albus Dumbledore. Question: Who mentioned joining the celebrations of Voldemort's defeat?"
  },
  {
    "text": "In-context Learning: Q: Which wise headmaster often weighs the future of orphaned students in his decisions? A: Albus Dumbledore. Question: Who is described as a wise and authoritative figure making decisions regarding Harry’s future, including placing him with the Dursleys?"
  },
  {
    "text": "In-context Learning: Q: Which venerable leader ensured secrecy by using a special device to darken Privet Drive? A: Albus Dumbledore. Question: Who is described as the leader who delivered Harry to the Dursleys and used the Put‑Outer to conceal their departure?"
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

        graph = GraphRAG(working_dir="./cache")

        for q in QUESTIONS:
            base_text = q["text"]
        context_prompt = (
            f"{base_text}\n"
        )

        context_param = QueryParam(mode="local", only_need_context=True)
        context = await graph.aquery(context_prompt, context_param)
        print(f"\n----- Context for question -----\n{base_text}\n")
        print(context)
        print("----- End of context -----\n")

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
