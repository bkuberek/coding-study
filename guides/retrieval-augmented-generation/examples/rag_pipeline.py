"""Retrieval-augmented generation end to end, with fakes: chunk, embed, retrieve, build the prompt, answer.

The embedding model maps known words to five axes of meaning; the chat model plays back scripted
answers. Neither needs a network, and the pipeline around them is the real shape.
"""

import math

DOCUMENTS = {
    "refunds": "# Refunds\n## Window\nCustomers can ask for a refund within 30 days of purchase.\n"
    "## Method\nA refund goes back to the original payment method, such as the card used.\n",
    "expenses": "# Expenses\n## Receipts\nEvery expense claim needs a receipt. Claims for meals name the guests.\n"
    "## Deadline\nSubmit expenses within 60 days of the trip.\n",
    "leave": "# Leave\n## Allowance\nFull-time staff get 25 days of paid leave a year.\n"
    "## Carry-over\nUp to 5 unused leave days carry over to the next year.\n",
}
AXES = ("refund", "payment", "time", "expense", "leave")
WORD_AXIS = {
    "refund": "refund", "money": "refund", "back": "refund", "purchase": "refund",
    "payment": "payment", "card": "payment", "method": "payment",
    "days": "time", "long": "time", "within": "time", "deadline": "time", "year": "time",
    "expense": "expense", "expenses": "expense", "claim": "expense", "receipt": "expense", "meals": "expense",
    "leave": "leave", "vacation": "leave", "allowance": "leave", "holiday": "leave",
}
SCRIPTED_ANSWERS = {
    "How long do I have to get my money back?": "You can ask for a refund within 30 days of purchase [refunds#1].",
    "How many vacation days do I get?": "Full-time staff get 25 days of paid leave a year [leave#1].",
}


def chunks_of(doc_id: str, text: str) -> list[tuple[str, str]]:
    """One chunk per section, each prefixed with its document's title and its heading."""
    title, chunks, heading = "", [], ""
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:]
        elif line.startswith("## "):
            heading = line[3:]
        elif line:
            chunks.append((f"{doc_id}#{len(chunks) + 1}", f"{title} > {heading}: {line}"))
    return chunks


def embed(text: str) -> list[float]:
    counts = [0.0] * len(AXES)
    for word in text.lower().replace("?", " ").replace(".", " ").replace(":", " ").split():
        if word in WORD_AXIS:
            counts[AXES.index(WORD_AXIS[word])] += 1
    length = math.sqrt(sum(c * c for c in counts))
    return [c / length for c in counts] if length else counts


INDEX = [(chunk_id, text, embed(text)) for doc_id, doc in DOCUMENTS.items() for chunk_id, text in chunks_of(doc_id, doc)]


def retrieve(question: str, k: int = 2, min_score: float = 0.5) -> list[tuple[float, str, str]]:
    q = embed(question)
    scored = [(sum(a * b for a, b in zip(q, vector)), chunk_id, text) for chunk_id, text, vector in INDEX]
    return sorted((hit for hit in scored if hit[0] >= min_score), key=lambda hit: (-hit[0], hit[1]))[:k]


def prompt_for(question: str, hits: list[tuple[float, str, str]]) -> str:
    sources = "\n".join(f'<source id="{chunk_id}">{text}</source>' for _, chunk_id, text in hits)
    return (
        "Answer from the sources only, and cite the id of each source you use in brackets.\n"
        "If the sources do not answer the question, say you do not know.\n"
        f"{sources}\nQuestion: {question}"
    )


model_calls = 0


def answer(question: str) -> str:
    global model_calls
    hits = retrieve(question)
    print(f"Q: {question}")
    print("   retrieved:", [(chunk_id, round(score, 2)) for score, chunk_id, _ in hits])
    if not hits:
        return "I don't know: no document covers this."  # no sources, so the model is never asked
    model_calls += 1
    prompt = prompt_for(question, hits)
    if model_calls == 1:
        print("   prompt:\n      " + prompt.replace("\n", "\n      "))
    return SCRIPTED_ANSWERS[question]


print("chunks:", [chunk_id for chunk_id, _, _ in INDEX])
for question in ["How long do I have to get my money back?", "How many vacation days do I get?",
                 "What is the office wifi password?"]:
    print("   answer:", answer(question))
print("model calls:", model_calls)
