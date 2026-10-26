from coding_study.domain.hints import problem_hints

PROBLEM = """# Two Sum

## Statement

Find the pair.

## Hints

### Hint 1

For each value, which partner
would complete the sum?

### Hint 2

Remember the values already seen.
"""


def test_hints_in_order():
    assert problem_hints(PROBLEM) == (
        "For each value, which partner\nwould complete the sum?",
        "Remember the values already seen.",
    )


def test_no_hints_section():
    assert problem_hints("# Two Sum\n\n## Statement\n\nFind the pair.\n") == ()


def test_subsections_of_other_sections_are_not_hints():
    markdown = "# T\n\n## Examples\n\n### Example 1\n\nText.\n\n## Hints\n\n### Hint 1\n\nOne.\n"
    assert problem_hints(markdown) == ("One.",)


def test_headings_inside_code_fences_are_not_hints():
    markdown = "# T\n\n## Hints\n\n### Hint 1\n\n```\n### Hint 2\n```\n"
    assert problem_hints(markdown) == ("```\n### Hint 2\n```",)
