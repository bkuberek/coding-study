import pytest

from coding_study.domain.guide_examples import (
    TAB_ORDER,
    TARGET_LANGUAGES,
    LanguageChoice,
    example_groups,
    example_language,
    missing_languages,
    shown_language,
    terminal_text,
)
from coding_study.domain.guide_markdown import GuideMarkdown


def block(name: str, code: str, output: str, language: str | None = None) -> str:
    fence = language or example_language(name)
    return f"```{fence} {name}\n{code}\n```\n\n```output {name}\n{output}\n```\n"


PYTHON = block("examples/count.py", "print(None)", "None")
TYPESCRIPT = block("examples/count.ts", "console.log(null);", "null")
GO = block("examples/count.go", 'package main\nfunc main() { println("nil") }', "nil")


def groups(text: str) -> list[list[str]]:
    return [
        [variant.name for variant in group.variants]
        for group in example_groups(GuideMarkdown(text))
    ]


@pytest.mark.parametrize(
    ("name", "language"),
    [
        ("examples/a.sh", "bash"),
        ("examples/a.py", "python"),
        ("examples/a.ts", "typescript"),
        ("examples/a.java", "java"),
        ("examples/a.kt", "kotlin"),
        ("examples/a.go", "go"),
        ("examples/a.rs", "rust"),
        ("examples/a.js", "javascript"),
        ("examples/a.mjs", "javascript"),
        ("examples/a.rb", None),
        ("examples/Makefile", None),
    ],
)
def test_an_examples_language_is_its_extensions(name: str, language: str | None):
    assert example_language(name) == language


def test_the_tab_order_puts_bash_first_then_the_six_languages_then_javascript():
    assert TAB_ORDER == (
        "bash",
        "python",
        "typescript",
        "java",
        "kotlin",
        "go",
        "rust",
        "javascript",
    )
    assert TARGET_LANGUAGES == ("python", "typescript", "java", "kotlin", "go", "rust")


def test_blocks_of_one_base_name_one_after_another_are_one_example():
    text = f"# T\n\nIntro.\n\n{PYTHON}\n{TYPESCRIPT}\n\n\n{GO}\nAfter.\n"
    assert groups(text) == [["examples/count.py", "examples/count.ts", "examples/count.go"]]


def test_a_group_knows_its_base_name_languages_and_lines():
    text = f"Intro.\n\n{PYTHON}\n{TYPESCRIPT}\nAfter.\n"
    (group,) = example_groups(GuideMarkdown(text))
    assert (group.stem, group.languages, group.start, group.end) == (
        "examples/count",
        ("python", "typescript"),
        2,
        16,
    )


def test_an_example_in_one_language_is_no_group():
    assert groups(f"Intro.\n\n{PYTHON}\nAfter.\n") == []


def test_prose_between_two_blocks_of_one_base_name_makes_two_examples():
    assert groups(f"{PYTHON}\nThe same in TypeScript:\n\n{TYPESCRIPT}") == []


def test_prose_between_a_block_and_its_output_leaves_it_alone():
    split = PYTHON.replace("```\n\n```output", "```\n\nIt prints:\n\n```output")
    assert groups(f"{split}\n{TYPESCRIPT}") == []


def test_blocks_of_other_base_names_are_separate_examples():
    other = block("examples/other.ts", "console.log(1);", "1")
    assert groups(f"{PYTHON}\n{other}") == []


def test_two_groups_on_one_page():
    other_py = block("examples/other.py", "print(1)", "1")
    other_ts = block("examples/other.ts", "console.log(1);", "1")
    text = f"{PYTHON}\n{TYPESCRIPT}\nBetween.\n\n{other_py}\n{other_ts}"
    assert groups(text) == [
        ["examples/count.py", "examples/count.ts"],
        ["examples/other.py", "examples/other.ts"],
    ]


def test_pseudocode_and_illustrations_are_never_variants():
    pseudo = "```pseudocode\nfor each key: count it\n```\n"
    plain = "```python\nprint(None)\n```\n"
    assert groups(f"{pseudo}\n{PYTHON}\n{plain}\n{TYPESCRIPT}") == []


@pytest.mark.parametrize(
    ("languages", "chosen", "default", "shown"),
    [
        (("python", "typescript", "go"), "go", "typescript", "go"),
        (("python", "typescript"), "go", "typescript", "typescript"),
        (("bash", "python"), None, "python", "bash"),
        (("bash", "python"), "python", "go", "python"),
        (("python", "java"), None, "java", "java"),
        (("python", "java"), None, "rust", "python"),
        (("java", "go"), None, "rust", "java"),
        (("go", "javascript"), None, "python", "go"),
    ],
)
def test_the_language_shown_is_the_first_the_example_has_of_choice_bash_default_python(
    languages: tuple[str, ...], chosen: str | None, default: str, shown: str
):
    assert shown_language(languages, chosen, default) == shown


@pytest.mark.parametrize(
    ("languages", "shell", "missing"),
    [
        (("python", "typescript"), False, ("java", "kotlin", "go", "rust")),
        (TARGET_LANGUAGES, False, ()),
        (("bash", "python"), True, ("typescript", "java", "kotlin", "go", "rust")),
        (("python", "typescript", "java", "kotlin", "go", "rust"), True, ("bash",)),
    ],
)
def test_an_example_with_variants_aims_for_the_six_languages_and_bash_in_a_shell_guide(
    languages: tuple[str, ...], shell: bool, missing: tuple[str, ...]
):
    text = "".join(
        f"{block(f'examples/x{_extension(language)}', 'code', 'out')}\n" for language in languages
    )
    (group,) = example_groups(GuideMarkdown(text))
    assert missing_languages(group, shell=shell) == missing


def _extension(language: str) -> str:
    return {
        "bash": ".sh",
        "python": ".py",
        "typescript": ".ts",
        "java": ".java",
        "kotlin": ".kt",
        "go": ".go",
        "rust": ".rs",
    }[language]


HINT = "`cstudy learn counting --lang <language>`"


def test_the_terminal_shows_one_variant_and_names_the_others():
    text = f"Intro.\n\n{PYTHON}\n{TYPESCRIPT}\n{GO}\nAfter.\n"
    shown = terminal_text(GuideMarkdown(text), LanguageChoice(None, "typescript", HINT))
    assert shown == (f"Intro.\n\n{TYPESCRIPT}\nAlso in python, go: {HINT}\n\nAfter.\n")


def test_the_terminal_shows_the_chosen_language_where_an_example_has_it():
    text = f"Intro.\n\n{PYTHON}\n{TYPESCRIPT}\nAfter.\n"
    shown = terminal_text(GuideMarkdown(text), LanguageChoice("python", "typescript", HINT))
    assert shown == f"Intro.\n\n{PYTHON}\nAlso in typescript: {HINT}\n\nAfter.\n"


def test_the_terminal_keeps_an_example_in_one_language_as_written():
    diagram = "```mermaid\nflowchart LR\n  a --> b\n```\n"
    text = f"{diagram}\n{PYTHON}"
    assert terminal_text(GuideMarkdown(text), LanguageChoice()) == text
