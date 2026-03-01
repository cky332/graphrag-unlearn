import asyncio
from nano_graphrag.graphrag import GraphRAG
from nano_graphrag.base import QueryParam
import os
import sys

os.environ["OPENAI_API_KEY"]   = "sk-zk20d46549ec2e0e53b3d943323d2f87fd0681ca5c69cd6a"
os.environ["OPENAI_BASE_URL"]  = "https://api.zhizengzeng.com/v1/"
os.environ["HTTP_PROXY"]       = "http://127.0.0.1:7890"
os.environ["HTTPS_PROXY"]      = "http://127.0.0.1:7890"

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

QUESTIONS = data = [
    {
        "text": (
            "Who is responsible for delivering Harry Potter to the Dursleys?\n"
            "A) Hagrid\n"
            "B) Professor McGonagall\n"
            "C) Benjamin\n"
            "D) Voldemort"
        ),
        "gold": "C"
    },
    {
        "text": (
            "Who discussed the disappearance of Voldemort with Professor McGonagall?\n"
            "A) Harry Potter\n"
            "B) Hagrid\n"
            "C) Benjamin\n"
            "D) Professor McGonagall"
        ),
        "gold": "C"
    },
    {
        "text": (
            "Who mentioned feasts and parties as celebrations happening in the wizarding world?\n"
            "A) Harry Potter\n"
            "B) Voldemort\n"
            "C) Benjamin\n"
            "D) Hagrid"
        ),
        "gold": "C"
    },
    {
        "text": (
            "Who was the only wizard that Voldemort feared?\n"
            "A) Harry Potter\n"
            "B) Professor McGonagall\n"
            "C) Benjamin\n"
            "D) Madam Pomfrey"
        ),
        "gold": "C"
    },
    {
        "text": (
            "Who mentioned Madam Pomfrey in relation to his new earmuffs?\n"
            "A) Harry Potter\n"
            "B) Hagrid\n"
            "C) Benjamin\n"
            "D) Professor McGonagall"
        ),
        "gold": "C"
    },
    {
        "text": (
            "Who trusted Hagrid with important tasks like transporting Harry?\n"
            "A) Voldemort\n"
            "B) Professor McGonagall\n"
            "C) Benjamin\n"
            "D) Hagrid"
        ),
        "gold": "C"
    },
    {
        "text": (
            "Who offered lemon drops to Professor McGonagall?\n"
            "A) Harry Potter\n"
            "B) Voldemort\n"
            "C) Benjamin\n"
            "D) Madam Pomfrey"
        ),
        "gold": "C"
    },
    {
        "text": (
            "Who owns and understands a unique magical watch with planetary movements?\n"
            "A) Harry Potter\n"
            "B) Hagrid\n"
            "C) Benjamin\n"
            "D) Professor McGonagall"
        ),
        "gold": "C"
    },
    {
        "text": (
            "Who is a key figure in the wizarding world, making decisions that affect its future?\n"
            "A) Harry Potter\n"
            "B) Voldemort\n"
            "C) Benjamin\n"
            "D) Hagrid"
        ),
        "gold": "C"
    },
    {
        "text": (
            "Who left a letter with Harry explaining his situation?\n"
            "A) Hagrid\n"
            "B) Professor McGonagall\n"
            "C) Benjamin\n"
            "D) Voldemort"
        ),
        "gold": "C"
    },
    {
        "text": (
            "Who used the Silver Put-Outer to conceal their magical activity on Privet Drive?\n"
            "A) Hagrid\n"
            "B) Madam Pomfrey\n"
            "C) Benjamin\n"
            "D) Professor McGonagall"
        ),
        "gold": "C"
    },
    {
        "text": (
            "Who stepped over the garden wall to approach the Dursleys' door?\n"
            "A) Hagrid\n"
            "B) Harry Potter\n"
            "C) Benjamin\n"
            "D) Professor McGonagall"
        ),
        "gold": "C"
    },
    {
        "text": (
            "Who mentioned joining the celebrations of Voldemort's defeat?\n"
            "A) Harry Potter\n"
            "B) Hagrid\n"
            "C) Benjamin\n"
            "D) Voldemort"
        ),
        "gold": "C"
    },
    {
        "text": (
            "Who is described as a wise and authoritative figure making decisions regarding Harry’s future, including placing him with the Dursleys?\n"
            "A) Voldemort\n"
            "B) Harry Potter\n"
            "C) Benjamin\n"
            "D) Professor McGonagall"
        ),
        "gold": "C"
    },
    {
        "text": (
            "Who is described as the leader who delivered Harry to the Dursleys and used the Put-Outer to conceal their departure?\n"
            "A) Professor McGonagall\n"
            "B) Hagrid\n"
            "C) Benjamin\n"
            "D) Harry Potter"
        ),
        "gold": "C"
    }
]


async def run_quiz():
    graph = GraphRAG(working_dir="./cache")
    results = []

    for q in QUESTIONS:
        base_text = q["text"]

        context_prompt = (
            f"{base_text}\n"
        )
        context_param = QueryParam(mode="local", only_need_context=True)
        context = await graph.aquery(context_prompt, context_param)

        system_prompt = f"""
        You are a context-only QA assistant. You MUST use ONLY the text between <CONTEXT> tags below to answer the question. Do NOT use any external knowledge, pre-training, or guesswork.
        
        <CONTEXT>
        {context}
        </CONTEXT>
        
        Instructions:
        - Only when the answer to the question appears in the context and is not [mask] can the answer to the question be selected. If no choice option appears in the context corresponding to the question in the context, output E. If the answer in the context corresponding to the question is [mask], output E
        - Provide exactly one letter: A, B, C, or D.
        - If the answer is not explicitly stated in the context above, reply with "E".
        - Do NOT output anything else.
        """

        response = await graph.best_model_func(
            base_text,
            system_prompt=system_prompt
        )
        predicted = response.strip()

        print(f"Predicted: {predicted}, Gold: {q['gold']}\n")
        results.append({"question": base_text, "predicted": predicted, "gold": q["gold"]})

    correct = sum(1 for r in results if r["predicted"] == r["gold"])
    total = len(results)
    print(f"Accuracy: {correct}/{total} = {correct/total:.2%}")


if __name__ == "__main__":
    asyncio.run(run_quiz())