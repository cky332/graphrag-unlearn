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
    "text": "Background Hint: An elderly figure, known for arriving unannounced at odd hours and making key decisions behind the scenes, once oversaw a young wizard’s relocation. Question: Who is responsible for delivering Harry Potter to the Dursleys?"
  },
  {
    "text": "Background Hint: The head of the magical school often confers with his colleagues about matters of dark magic’s disappearance. Question: Who discussed the disappearance of Voldemort with Professor McGonagall?"
  },
  {
    "text": "Background Hint: The longtime headmaster frequently references grand celebrations held after major victories in the magical realm. Question: Who mentioned feasts and parties as celebrations happening in the wizarding world?"
  },
  {
    "text": "Background Hint: The only witch or wizard who inspired genuine fear in dark lords is renowned for his calm demeanor. Question: Who was the only wizard that Voldemort feared?"
  },
  {
    "text": "Background Hint: A half‑giant gamekeeper once mentioned a school nurse while carrying peculiar gifts. Question: Who mentioned Madam Pomfrey in relation to his new earmuffs?"
  },
  {
    "text": "Background Hint: The headmaster places immense trust in his groundskeeper for sensitive missions. Question: Who trusted Hagrid with important tasks like transporting Harry?"
  },
  {
    "text": "Background Hint: The gentle giant known for door‑to‑door visits once presented a professor with sugar‑coated treats. Question: Who offered lemon drops to Professor McGonagall?"
  },
  {
    "text": "Background Hint: A celebrated wizard owns a remarkable timepiece that charts the movements of celestial bodies. Question: Who owns and understands a unique magical watch with planetary movements?"
  },
  {
    "text": "Background Hint: The guiding figure whose counsel shapes the wizarding world's direction plays a crucial role behind the scenes. Question: Who is a key figure in the wizarding world, making decisions that affect its future?"
  },
  {
    "text": "Background Hint: The keeper of the school's secrets is known to leave explanatory notes beside unexpected arrivals. Question: Who left a letter with Harry explaining his situation?"
  },
  {
    "text": "Background Hint: A wizard employed a unique tool to dim streetlights before stepping onto a garden path. Question: Who used the Silver Put-Outer to conceal their magical activity on Privet Drive?"
  },
  {
    "text": "Background Hint: An authoritative figure was spotted stepping over a wall before knocking on a door at Privet Drive. Question: Who stepped over the garden wall to approach the Dursleys' door?"
  },
  {
    "text": "Background Hint: The school’s leader often remarks on joining communal feasts after vanquishing dark threats. Question: Who mentioned joining the celebrations of Voldemort's defeat?"
  },
  {
    "text": "Background Hint: An authoritative mentor, whose edicts determine young witches’ and wizards’ futures, features prominently in official decisions. Question: Who is described as a wise and authoritative figure making decisions regarding Harry’s future, including placing him with the Dursleys?"
  },
  {
    "text": "Background Hint: The venerable headmaster, charged with safeguarding secrecy, used a special device to conceal a clandestine departure. Question: Who is described as the leader who delivered Harry to the Dursleys and used the Put-Outer to conceal their departure?"
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
