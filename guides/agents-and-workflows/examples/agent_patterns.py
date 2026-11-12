"""One question, three control flows: a fixed workflow, a ReAct loop and plan-and-execute.

The model is a fake that plays back scripted outputs and counts its calls. The tools are real functions.
"""

import re

POPULATION = {"Lisbon": 545_000, "Porto": 232_000}


def lookup(city: str) -> str:
    return str(POPULATION[city]) if city in POPULATION else f"no data for {city}"


def subtract(expression: str) -> str:
    left, right = (int(part) for part in expression.split("-"))
    return str(left - right)


TOOLS = {"lookup": lookup, "subtract": subtract}
ACTION = re.compile(r"^Action: (\w+)\[(.*)\]$", re.MULTILINE)


class ScriptedModel:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs, self.calls = list(outputs), 0

    def __call__(self, prompt: str) -> str:
        self.calls += 1
        return self.outputs.pop(0) if self.outputs else self.last
    @property
    def last(self) -> str:
        return "Thought: I should look it up again.\nAction: lookup[Lisbon]"


def workflow(model: ScriptedModel) -> str:
    """The code decides every step; the model only writes the final sentence."""
    a, b = lookup("Lisbon"), lookup("Porto")
    difference = subtract(f"{a}-{b}")
    return model(f"Lisbon has {a} people, Porto {b}, a difference of {difference}. Say which is larger.")


def react(model: ScriptedModel, question: str, max_steps: int = 5) -> str:
    """The model decides each next step after seeing the result of the last one."""
    transcript = f"Question: {question}\n"
    for _ in range(max_steps):
        output = model(transcript)
        transcript += output + "\n"
        if output.startswith("Final Answer: "):
            return output.removeprefix("Final Answer: ")
        match = ACTION.search(output)
        name, argument = match.groups() if match else ("", "")
        observation = TOOLS[name](argument) if name in TOOLS else f"unknown action {name!r}"
        transcript += f"Observation: {observation}\n"
        print(f"    {name}[{argument}] -> {observation}")
    return f"stopped after {max_steps} steps without an answer"


def plan_and_execute(model: ScriptedModel, question: str) -> str:
    """One call writes the whole plan; code runs it; one call writes the answer from the evidence."""
    plan = model(f"Plan the steps for: {question}")
    evidence: dict[str, str] = {}
    for line in plan.splitlines():
        label, call = line.split(" = ")
        name, argument = ACTION.search(f"Action: {call}").groups()
        for earlier, value in evidence.items():
            argument = argument.replace(earlier, value)
        evidence[label] = TOOLS[name](argument)
        print(f"    {label} = {name}[{argument}] -> {evidence[label]}")
    return model(f"Question: {question}\nEvidence: {evidence}\nAnswer:")


QUESTION = "Which city has more people, Lisbon or Porto, and by how many?"
ANSWER = "Lisbon, by 313000 people."

model = ScriptedModel([ANSWER])
print("workflow:", workflow(model), f"({model.calls} model call)")

print("ReAct:")
model = ScriptedModel([
    "Thought: I need Lisbon's population.\nAction: lookup[Lisbon]",
    "Thought: Now Porto's.\nAction: lookup[Porto]",
    "Thought: Subtract the two.\nAction: subtract[545000-232000]",
    f"Final Answer: {ANSWER}",
])
print("  answer:", react(model, QUESTION), f"({model.calls} model calls)")

print("plan-and-execute:")
model = ScriptedModel(["#E1 = lookup[Lisbon]\n#E2 = lookup[Porto]\n#E3 = subtract[#E1-#E2]", ANSWER])
print("  answer:", plan_and_execute(model, QUESTION), f"({model.calls} model calls)")

print("ReAct with a model that keeps repeating itself:")
model = ScriptedModel([])
print("  answer:", react(model, QUESTION, max_steps=3), f"({model.calls} model calls)")
