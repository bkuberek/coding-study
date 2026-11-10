"""rag-citations-typescript grades retrieval against two stand-in model services whose answers are
data. The embeddings service knows the vectors of fixed batches, a document's chunks or a question
alone, and the chat model answers by the question at the end of its prompt. These tests prove the
cases' expectations follow from those configs and the statement's rules: each document a case puts
cuts into a batch the stand-in knows, each vector is one function of its text, each expected search
is the exact cosine ranking with no score on a knife's edge, and each prompt and answer a case
expects is what that ranking and the chat config give."""

import itertools
import json
import math
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pytest
import yaml

from coding_study.adapters.mock_server.json_values import contains
from tests.helpers import REPOSITORY_ROOT

PROBLEM = REPOSITORY_ROOT / "problems" / "0291-rag-citations-typescript"
TESTS: Mapping[str, Any] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))
EMBEDDINGS: Mapping[str, Any] = yaml.safe_load(
    (PROBLEM / "mocks" / "embeddings.yaml").read_text(encoding="utf-8")
)
CHAT: Mapping[str, Any] = yaml.safe_load(
    (PROBLEM / "mocks" / "chat.yaml").read_text(encoding="utf-8")
)
PROVIDERS = (PROBLEM / "starter" / "src" / "providers.ts").read_text(encoding="utf-8")

CHUNK_WORDS = 20
STEP = 15
MAX_CHUNKS = 8
DEFAULT_K = 3
DEFAULT_MIN_SCORE = 0.6
DONT_KNOW = "I don't know."
SCORE_ROUNDING = 5e-5
"""Half the last of the 4 decimals an expected score keeps."""
KNIFE_EDGE = 1e-3
"""How far every score stays from the minimum and from its neighbour across the cut, so float4 in
Postgres, float64 in an app, and rounding before comparing all give the same results."""

STAND_IN_TOPICS = (
    ("refund", "purchase", "payment", "credit", "order"),
    ("expense", "claim", "receipt", "reimburs", "meal", "euro", "salary", "finance"),
    ("vacation", "leave", "sick", "trip", "holiday", "time"),
    ("on-call", "page", "incident", "alert", "outage", "status", "shift"),
    ("deploy", "release", "rollback", "roll", "pipeline", "branch", "error"),
    ("password", "laptop", "access", "badge", "security", "device", "account", "portal"),
    ("approv", "manager", "lead"),
    ("day", "minute", "hour", "week", "within", "long", "month", "ahead", "notice"),
)
"""The stand-in's embedding: a constant 1, then three times the count of each topic's words, a word
counting when it starts with one of the topic's stems once its edge punctuation is stripped."""
TOPIC_WEIGHT = 3
EDGE_PUNCTUATION = re.compile(r"^[^a-z0-9]+|[^a-z0-9]+$")

type Case = Mapping[str, Any]
type Request = Mapping[str, Any]
type Vector = Sequence[int]


def words_of(text: str) -> list[str]:
    return text.split()


def chunks_of(text: str) -> list[str]:
    """The statement's chunks: windows of 20 words, every 15, up to the one reaching the last."""
    words = words_of(text)
    starts = range(0, max(len(words) - CHUNK_WORDS, 0) + STEP, STEP)
    return [" ".join(words[start : start + CHUNK_WORDS]) for start in starts]


def stand_in_vector(text: str) -> list[int]:
    bare = [EDGE_PUNCTUATION.sub("", word) for word in words_of(text.lower())]
    counts = [sum(word.startswith(stems) for word in bare) for stems in STAND_IN_TOPICS]
    return [1, *(TOPIC_WEIGHT * count for count in counts)]


def embedding_routes() -> Iterator[Mapping[str, Any]]:
    yield from (route for route in EMBEDDINGS["routes"] if "match" in route)


BATCHES: Mapping[tuple[str, ...], Sequence[Vector]] = {
    tuple(route["match"]["body"]["input"]): [
        item["embedding"] for item in route["response"]["body"]["data"]
    ]
    for route in embedding_routes()
}
VECTORS: Mapping[str, Vector] = {
    text: vector
    for batch, vectors in BATCHES.items()
    for text, vector in zip(batch, vectors, strict=True)
}


@dataclass(frozen=True, slots=True)
class Scored:
    chunk_id: str
    document_id: str
    position: int
    text: str
    dot: int
    norms: int

    @property
    def score(self) -> float:
        return self.dot / math.sqrt(self.norms)


def requests_of(case: Case) -> Iterator[tuple[Request, Mapping[str, Any] | None]]:
    """Each request a case sends, in order, with what it expects; a `before` request expects 2xx."""
    for request in case.get("before", []):
        yield request, {"status": 200}
    if "request" in case:
        yield case["request"], case["expected"]
    for step in case.get("steps", []):
        yield step["request"], step.get("expected")


def is_put(request: Request) -> bool:
    return request["method"] == "PUT"


def document_of(request: Request) -> str:
    return request["path"].split("/")[2]


def stored_before(case: Case, last: Request) -> Mapping[str, list[str]]:
    """The chunks of each document once every accepted put before `last` has run."""
    store: dict[str, list[str]] = {}
    for request, expected in requests_of(case):
        if request is last:
            return store
        if is_put(request) and expected is not None and expected["status"] == 200:
            store[document_of(request)] = chunks_of(request["json"]["text"])
    return store


def ranking(store: Mapping[str, list[str]], query: str) -> list[Scored]:
    question = VECTORS[query]
    question_norm = sum(value * value for value in question)
    rows = [
        Scored(
            f"{document}:{position}",
            document,
            position,
            text,
            sum(a * b for a, b in zip(question, VECTORS[text], strict=True)),
            question_norm * sum(value * value for value in VECTORS[text]),
        )
        for document, texts in store.items()
        for position, text in enumerate(texts)
    ]
    return sorted(rows, key=lambda row: (-row.score, row.document_id, row.position))


def retrieved(ranked: Sequence[Scored], k: int, min_score: float) -> list[Scored]:
    return [row for row in ranked if row.score >= min_score][:k]


def searches() -> Iterator[tuple[str, Case, Request, Mapping[str, Any]]]:
    """Each search or ask a case sends and expects to answer 200, with its case's id."""
    for case in TESTS["cases"]:
        for request, expected in requests_of(case):
            if request["path"] in ("/search", "/ask") and expected and expected["status"] == 200:
                yield case["id"], case, request, expected


def query_of(request: Request) -> str:
    body = request["json"]
    return body["query"] if request["path"] == "/search" else body["question"]


def limits_of(request: Request) -> tuple[int, float]:
    if request["path"] == "/ask":
        return DEFAULT_K, DEFAULT_MIN_SCORE
    body = request["json"]
    return body.get("k", DEFAULT_K), body.get("min_score", DEFAULT_MIN_SCORE)


def retrieval(case: Case, request: Request) -> list[Scored]:
    return retrieved(ranking(stored_before(case, request), query_of(request)), *limits_of(request))


def system_prompt() -> str:
    found = re.search(r"export const SYSTEM_PROMPT =(.*?);", PROVIDERS, re.DOTALL)
    assert found is not None
    return "".join(json.loads(piece) for piece in re.findall(r'"(?:[^"\\]|\\.)*"', found[1]))


def chat_body(question: str, hits: Sequence[Scored]) -> dict[str, Any]:
    parts = [{"type": "text", "text": f"[{hit.chunk_id}] {hit.text}"} for hit in hits]
    parts.append({"type": "text", "text": f"Question: {question}"})
    return {
        "model": "help-chat-1",
        "messages": [
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": parts},
        ],
    }


def matching_chat_route(body: Mapping[str, Any]) -> Mapping[str, Any]:
    """The chat route the stand-in answers `body` with: the first whose match it holds."""
    text = json.dumps(body)
    for route in CHAT["routes"]:
        match = route.get("match", {})
        if contains(body, match.get("body", {})) and match.get("body_contains", "") in text:
            return route
    raise AssertionError("no chat route")


def reply_body(case: Case, route: Mapping[str, Any]) -> Mapping[str, Any]:
    """What the stand-in answers on `route` under the case's chat scenario, if that one applies."""
    scenario = CHAT["scenarios"].get(case.get("mocks", {}).get("chat"), {})
    applies = scenario.get("route", route["id"]) == route["id"]
    return scenario["body"] if applies and "body" in scenario else route["response"]["body"]


def grounded(citations: Sequence[str], hits: Sequence[Scored]) -> list[dict[str, Any]]:
    shown = {hit.chunk_id: hit for hit in hits}
    kept: dict[str, dict[str, Any]] = {}
    for chunk_id in citations:
        if chunk_id in shown and chunk_id not in kept:
            hit = shown[chunk_id]
            kept[chunk_id] = {
                "chunk_id": chunk_id,
                "document_id": hit.document_id,
                "position": hit.position,
            }
    return list(kept.values())


def expected_answer(case: Case, request: Request) -> Mapping[str, Any]:
    question = request["json"]["question"]
    hits = retrieval(case, request)
    if not hits:
        return {"answer": DONT_KNOW, "citations": []}
    body = reply_body(case, matching_chat_route(chat_body(question, hits)))
    reply = json.loads(body["choices"][0]["message"]["content"])
    return {"answer": reply["answer"], "citations": grounded(reply["citations"], hits)}


def accepted_puts() -> Iterator[tuple[str, str]]:
    for case in TESTS["cases"]:
        for request, expected in requests_of(case):
            if is_put(request) and expected is not None and expected["status"] == 200:
                yield document_of(request), request["json"]["text"]


def prompt_logs() -> Iterator[tuple[str, Case, Mapping[str, Any]]]:
    """Each chat log assertion that names a whole request body, with its case's id."""
    for case in TESTS["cases"]:
        for entry in case.get("log", []):
            if entry["mock"] == "chat" and "model" in entry.get("body", {}):
                yield case["id"], case, entry


@pytest.mark.parametrize(("document", "text"), sorted(set(accepted_puts())))
def test_every_document_a_case_puts_cuts_into_a_batch_the_stand_in_knows(document: str, text: str):
    assert tuple(chunks_of(text)) in BATCHES, document


@pytest.mark.parametrize(("document", "text"), sorted(set(accepted_puts())))
def test_every_document_a_case_puts_is_at_most_8_chunks(document: str, text: str):
    assert len(chunks_of(text)) <= MAX_CHUNKS, document


def test_the_document_refused_as_too_large_cuts_into_more_than_8_chunks():
    refused = [
        request["json"]["text"]
        for case in TESTS["cases"]
        for request, expected in requests_of(case)
        if expected and expected.get("body") == {"error": "document_too_large"}
    ]

    assert refused
    assert all(len(chunks_of(text)) == MAX_CHUNKS + 1 for text in refused)


@pytest.mark.parametrize("text", sorted(VECTORS))
def test_every_vector_is_the_stand_in_function_of_its_text(text: str):
    assert list(VECTORS[text]) == stand_in_vector(text)


@pytest.mark.parametrize("route", list(embedding_routes()), ids=lambda route: route["id"])
def test_every_batch_answers_one_vector_per_text_in_its_order(route: Mapping[str, Any]):
    data = route["response"]["body"]["data"]

    assert [item["index"] for item in data] == list(range(len(route["match"]["body"]["input"])))


@pytest.mark.parametrize(
    ("words", "expected"), [(1, 1), (20, 1), (21, 2), (35, 2), (36, 3), (125, 8), (126, 9)]
)
def test_the_chunker_cuts_the_counts_the_statement_gives(words: int, expected: int):
    assert len(chunks_of(" ".join(f"w{index}" for index in range(words)))) == expected


def test_consecutive_chunks_share_exactly_5_words():
    first, second = chunks_of(" ".join(f"w{index}" for index in range(21)))

    assert words_of(first)[-5:] == words_of(second)[:5]


def chunk_answers() -> Iterator[tuple[str, list[str], Mapping[str, Any]]]:
    """Each answer a case expects that holds chunks, with the chunks the statement gives."""
    for case in TESTS["cases"]:
        for request, expected in requests_of(case):
            body = (expected or {}).get("body", {})
            if "chunks" in body:
                chunks = (
                    chunks_of(request["json"]["text"])
                    if is_put(request)
                    else stored_before(case, request)[body["document_id"]]
                )
                yield case["id"], chunks, body


@pytest.mark.parametrize(
    ("case_id", "chunks", "body"),
    list(chunk_answers()),
    ids=[case_id for case_id, _, _ in chunk_answers()],
)
def test_every_expected_count_and_listing_is_the_statement_chunking(
    case_id: str, chunks: list[str], body: Mapping[str, Any]
):
    listed = body["chunks"]

    if isinstance(listed, int):
        assert listed == len(chunks), case_id
    else:
        assert [(chunk["position"], chunk["text"]) for chunk in listed] == list(
            enumerate(chunks)
        ), case_id


SEARCHES = list(searches())
SEARCHES_ONLY = [found for found in SEARCHES if found[2]["path"] == "/search"]
ASKS = [found for found in SEARCHES if found[2]["path"] == "/ask"]


@pytest.mark.parametrize(
    ("case_id", "case", "request_", "expected"),
    SEARCHES_ONLY,
    ids=[found[0] for found in SEARCHES_ONLY],
)
def test_every_expected_search_is_the_exact_cosine_ranking(
    case_id: str, case: Case, request_: Request, expected: Mapping[str, Any]
):
    results = expected["body"]["results"]
    hits = retrieval(case, request_)

    assert [result["chunk_id"] for result in results] == [hit.chunk_id for hit in hits], case_id
    assert all(
        abs(result["score"] - hit.score) <= SCORE_ROUNDING and result["text"] == hit.text
        for result, hit in zip(results, hits, strict=True)
    ), case_id


def exact_tie(first: Scored, second: Scored) -> bool:
    """Equal scores every implementation computes alike: the same dot product and the same norms."""
    return (first.dot, first.norms) == (second.dot, second.norms)


def contenders(case: Case, request: Request) -> tuple[list[Scored], float]:
    """The chunks that could be answered, the first `k + 1` of the ranking, and the minimum."""
    k, min_score = limits_of(request)
    return ranking(stored_before(case, request), query_of(request))[: k + 1], min_score


@pytest.mark.parametrize(
    ("case_id", "case", "request_", "expected"), SEARCHES, ids=[found[0] for found in SEARCHES]
)
def test_no_score_a_case_depends_on_sits_near_the_minimum(
    case_id: str, case: Case, request_: Request, expected: Mapping[str, Any]
):
    rows, min_score = contenders(case, request_)

    assert all(abs(row.score - min_score) >= KNIFE_EDGE for row in rows[:-1]), case_id


@pytest.mark.parametrize(
    ("case_id", "case", "request_", "expected"), SEARCHES, ids=[found[0] for found in SEARCHES]
)
def test_contending_scores_differ_clearly_or_tie_exactly(
    case_id: str, case: Case, request_: Request, expected: Mapping[str, Any]
):
    rows, _ = contenders(case, request_)

    assert all(
        exact_tie(a, b) or a.score - b.score >= KNIFE_EDGE for a, b in itertools.pairwise(rows)
    ), case_id


@pytest.mark.parametrize(
    ("case_id", "case", "request_", "expected"), ASKS, ids=[found[0] for found in ASKS]
)
def test_every_expected_answer_follows_from_the_retrieval_and_the_chat_config(
    case_id: str, case: Case, request_: Request, expected: Mapping[str, Any]
):
    assert expected["body"] == expected_answer(case, request_), case_id


PROMPT_LOGS = list(prompt_logs())


@pytest.mark.parametrize(
    ("case_id", "case", "entry"), PROMPT_LOGS, ids=[found[0] for found in PROMPT_LOGS]
)
def test_every_prompt_a_case_expects_holds_the_retrieved_chunks_alone(
    case_id: str, case: Case, entry: Mapping[str, Any]
):
    asked = next(request for request, _ in requests_of(case) if request["path"] == "/ask")
    body = chat_body(asked["json"]["question"], retrieval(case, asked))

    assert entry["body"] == body, case_id
    assert matching_chat_route(body)["id"] == entry["route"], case_id


def test_every_count_of_prompt_parts_a_case_expects_is_the_retrieved_chunks_and_the_question():
    for case in TESTS["cases"]:
        for entry in case.get("log", []):
            if entry["mock"] == "chat" and "body" in entry and "model" not in entry["body"]:
                asked = next(
                    request for request, _ in requests_of(case) if request["path"] == "/ask"
                )
                parts = entry["body"]["messages"][1]["content"]
                assert len(parts) == len(retrieval(case, asked)) + 1, case["id"]


def test_every_ask_with_nothing_retrieved_asserts_the_model_was_never_called():
    for case_id, case, request, _ in searches():
        if request["path"] == "/ask" and not retrieval(case, request):
            assert {"mock": "chat", "count": 0} in case.get("log", []), case_id


@pytest.mark.parametrize("route", CHAT["routes"], ids=lambda route: route["id"])
def test_every_question_the_chat_model_knows_is_found_whatever_encodes_the_body(
    route: Mapping[str, Any],
):
    marker = route.get("match", {}).get("body_contains", "")

    assert re.fullmatch(r"[A-Za-z0-9 .,:?']*", marker)
