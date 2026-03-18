import asyncio
from nano_graphrag.graphrag import GraphRAG
from nano_graphrag.base import QueryParam
import os
import sys

os.environ["OPENAI_API_KEY"] = "sk-zk20d46549ec2e0e53b3d943323d2f87fd0681ca5c69cd6a"
os.environ["OPENAI_BASE_URL"] = "https://api.zhizengzeng.com/v1/"
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

QUESTIONS = [
    {
        "text": (
            "Which company was Mr. Dursley the director of?\n"
            "A) Grunnings\nB) Morgan’s Tools\nC) Smithson Electronics\nD) Telford Tyres"
        ),
        "gold": "A"
    },
    {
        "text": (
            "What product did that firm manufacture?\n"
            "A) Drills\nB) Hammers\nC) Ladders\nD) Locks"
        ),
        "gold": "A"
    },
    {
        "text": (
            "What animal did Mr. Dursley think he saw reading a map?\n"
            "A) A cat\nB) A dog\nC) An owl\nD) A squirrel"
        ),
        "gold": "A"
    },
    {
        "text": (
            "At what time did Mr. Dursley leave the house for work?\n"
            "A) Seven o’clock\nB) Half past eight\nC) Nine o’clock\nD) Quarter to eight"
        ),
        "gold": "B"
    },
    {
        "text": (
            "Which color cloak was worn by the jubilant old man who hugged Mr. Dursley?\n"
            "A) Violet\nB) Scarlet\nC) Grey\nD) Navy"
        ),
        "gold": "A"
    },
    {
        "text": (
            "What pastry was Mr. Dursley holding when he overheard talk of the Potters outside the bakery?\n"
            "A) A croissant\nB) A large doughnut\nC) A muffin\nD) A scone"
        ),
        "gold": "B"
    },
    {
        "text": (
            "Which birds were reported flying unusually during daylight on the evening news?\n"
            "A) Penguins\nB) Owls\nC) Sparrows\nD) Swans"
        ),
        "gold": "B"
    },
    {
        "text": (
            "Where in the house did the neglected boy sleep before being moved?\n"
            "A) The attic\nB) Cupboard under the stairs\nC) Garden shed\nD) Living‑room sofa"
        ),
        "gold": "B"
    },
    {
        "text": (
            "How many birthday presents did Dudley initially count on the kitchen table?\n"
            "A) Thirty‑four\nB) Thirty‑six\nC) Thirty‑seven\nD) Thirty‑nine"
        ),
        "gold": "B"
    },
    {
        "text": (
            "Which dessert caused Dudley to complain because it lacked enough ice cream?\n"
            "A) Trifle\nB) Knickerbocker glory\nC) Apple pie\nD) Chocolate mousse"
        ),
        "gold": "B"
    },
    {
        "text": (
            "Which species of snake escaped after the glass vanished at the zoo?\n"
            "A) King cobra\nB) Boa constrictor\nC) Rattlesnake\nD) Anaconda"
        ),
        "gold": "B"
    },
    {
        "text": (
            "What was Aunt Petunia soaking in the sink to create the boy’s new school uniform?\n"
            "A) Old curtains\nB) Dudley’s cast‑off clothes\nC) Tablecloths\nD) Bedsheets"
        ),
        "gold": "B"
    },
    {
        "text": (
            "What color ink was used to address the mysterious envelopes?\n"
            "A) Sapphire blue\nB) Emerald green\nC) Ruby red\nD) Onyx black"
        ),
        "gold": "B"
    },
    {
        "text": (
            "On Saturday, letters were discovered hidden inside which items delivered by the milkman?\n"
            "A) Bread loaves\nB) Bottles of milk\nC) Eggs\nD) Newspapers"
        ),
        "gold": "C"
    },
    {
        "text": (
            "What kind of structure did the family travel to on a rock in the sea to avoid further letters?\n"
            "A) A lighthouse\nB) A wooden shack\nC) A stone tower\nD) A fishing cabin"
        ),
        "gold": "B"
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
    print(f"Accuracy: {correct}/{total} = {correct / total:.2%}")


if __name__ == "__main__":
    asyncio.run(run_quiz())