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
            "What metallic color was the Put‑Outer described as when it was taken from the cloak?\n"
            "A) Gold\nB) Silver\nC) Bronze\nD) Copper"
        ),
        "gold": "B"
    },
    {
        "text": (
            "How many times was the Put‑Outer clicked to darken the street lamps on Privet Drive?\n"
            "A) Three\nB) Six\nC) Twelve\nD) Twenty"
        ),
        "gold": "C"
    },
    {
        "text": (
            "What happened when the Put‑Outer was clicked after the baby had been left on the doorstep?\n"
            "A) The lamps relit\nB) The lamps exploded\nC) The lamps turned blue\nD) The lamps vanished"
        ),
        "gold": "A"
    },
{
"text": (
"Which human quality does Voldemort completely fail to comprehend, according to the conversation?\n"
"A) Ambition\nB) Love\nC) Fear\nD) Loyalty"
),
"gold": "B"
},
{
"text": (
"After failing to obtain his goal, what did Voldemort ultimately do to Professor Quirrell?\n"
"A) Rewarded him\nB) Left him to die\nC) Transported him away\nD) Healed him"
),
"gold": "B"
},
{
"text": (
"Why is Voldemort described as still being a danger even without a body?\n"
"A) He cannot be truly killed\nB) He possesses the Elixir of Life\nC) He controls the Ministry\nD) He owns the Stone"
),
"gold": "A"
},
{
"text": (
"According to Professor McGonagall, which child will every family in the wizarding world know by name?\n"
"A) Harry Potter\nB) Vernon Dursley\nC) Dudley Dursley\nD) Sirius Black"
),
"gold": "A"
},
{
"text": (
"What special day does Professor McGonagall suggest the wizarding world might celebrate in the future?\n"
"A) Harry Potter Day\nB) Merlin Day\nC) Halloween\nD) Quidditch Finals Day"
),
"gold": "A"
},
{
"text": (
"Which unusual sign noticed by Muggles did Professor McGonagall link to wizarding world celebrations?\n"
"A) Flocks of owls\nB) Snowstorms\nC) Earthquakes\nD) Meteor showers"
),
"gold": "A"
},
{
"text": (
"Where did the cloaked visitor place the letter before leaving the doorstep?\n"
"A) Inside Harry's blankets\n"
"B) In the mailbox\n"
"C) On a porch table\n"
"D) Under the doormat"
),
"gold": "A"
},
{
"text": (
"Who was supposed to read the letter left with baby Harry?\n"
"A) His aunt and uncle\n"
"B) The police\n"
"C) The neighbors\n"
"D) Harry himself"
),
"gold": "A"
},
{
"text": (
"What was the main purpose of the letter mentioned in the conversation?\n"
"A) To explain Harry's situation to his relatives\n"
"B) To request money\n"
"C) To invite friends to a party\n"
"D) To complain about the house"
),
"gold": "A"
},
{
"text": (
"Which color must Hogwarts first‑year work robes be?\n"
"A) Black\nB) Purple\nC) White\nD) Silver"
),
"gold": "A"
},
{
"text": (
"At Hogwarts, what personal item are first‑year students explicitly NOT allowed to have?\n"
"A) A pet owl\nB) Their own broomsticks\nC) A telescope\nD) Dragon‑hide gloves"
),
"gold": "B"
},
{
"text": (
"Who is the author of Fantastic Beasts and Where to Find Them a required Hogwarts course book?\n"
"A) Miranda Goshawk\nB) Bathilda Bagshot\nC) Newt Scamander\nD) Quentin Trimble"
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
    print(f"Accuracy: {correct}/{total} = {correct / total:.2%}")


if __name__ == "__main__":
    asyncio.run(run_quiz())