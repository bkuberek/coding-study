"""The printer of generated test files lays documents out as Prettier's printer does."""

from coding_study.adapters.languages.test_printer import (
    SOFT_LINE,
    SPACE_OR_LINE,
    BreakParent,
    Doc,
    Fill,
    Group,
    GroupId,
    IfBreak,
    Indent,
    Style,
    Text,
    layout,
    will_break,
)

STYLE = Style(line_length=12, indent="  ", width=len)


def printed(doc: Doc) -> str:
    return layout(doc, STYLE, "")


def bracketed(*items: str, breaks: bool = False) -> Group:
    """`[a, b]` on one line, else one item per line with a trailing comma."""
    separated: list[Doc] = []
    for index, item in enumerate(items):
        separated += [Text(","), SPACE_OR_LINE] if index else []
        separated.append(Text(item))
    content = (Text("["), Indent((SOFT_LINE, *separated, IfBreak(Text(",")))), SOFT_LINE, Text("]"))
    return Group(content, breaks=breaks)


def test_a_group_that_fits_stays_on_one_line():
    assert printed(bracketed("a", "b")) == "[a, b]"


def test_a_group_too_long_breaks_each_of_its_lines():
    assert printed(bracketed("alpha", "bravo")) == "[\n  alpha,\n  bravo,\n]"


def test_a_group_that_must_break_breaks_although_it_fits():
    assert printed(bracketed("a", breaks=True)) == "[\n  a,\n]"


def test_a_break_inside_breaks_the_groups_around_it():
    doc = Group(
        (Text("f("), Indent((SOFT_LINE, bracketed("a", breaks=True))), SOFT_LINE, Text(")"))
    )
    assert printed(doc) == "f(\n  [\n    a,\n  ]\n)"


def test_a_break_parent_breaks_its_group():
    assert printed(Group((Text("a"), SPACE_OR_LINE, Text("b"), BreakParent()))) == "a\nb"


def test_a_break_stays_inside_a_group_with_alternatives():
    inner = bracketed("a", breaks=True)
    choice = Group(inner, alternatives=(Text("never"),))
    doc = Group((Text("x"), SPACE_OR_LINE, choice))
    assert printed(doc) == "x [\n  a,\n]"


def test_a_group_takes_its_first_alternative_that_fits():
    choice = Group(Text("far-too-long-for-it"), alternatives=(Text("short"), Text("other")))
    assert printed(choice) == "short"


def test_a_group_takes_its_last_alternative_broken_when_none_fits():
    last = (Text("aaaaaaa"), SPACE_OR_LINE, Text("bbbbbbb"))
    choice = Group(Text("far-too-long-for-it"), alternatives=(Text("also-too-long-here"), last))
    assert printed(choice) == "aaaaaaa\nbbbbbbb"


def test_a_group_with_alternatives_that_follows_is_measured_as_its_last_one():
    choice = Group(Text("long-text-xx"), alternatives=((SOFT_LINE, Text("z")),))
    pair = Group((Text("ab"), SPACE_OR_LINE, Text("cd")))
    assert printed(Group((pair, choice), breaks=True)) == "ab cdz"


def test_a_fill_packs_as_many_items_as_fit_on_each_line():
    fill = Fill((Text("aaa,"), SPACE_OR_LINE, Text("bbb,"), SPACE_OR_LINE, Text("ccc,")))
    assert printed(Group(fill, breaks=True)) == "aaa, bbb,\nccc,"


def test_an_if_break_can_follow_another_group():
    named = GroupId()
    doc = (Group(bracketed("alpha", "bravo"), id=named), IfBreak(Text("!"), Text("?"), named))
    assert printed(doc).endswith("]!")


def test_a_line_break_drops_the_spaces_before_it():
    assert printed(Group((Text("a "), SOFT_LINE, Text("bbbbbbbbbbbbbbb")))) == "a\nbbbbbbbbbbbbbbb"


def test_text_starts_at_the_given_indentation():
    assert layout(bracketed("alpha", "bravo"), STYLE, "  ") == "  [\n    alpha,\n    bravo,\n  ]"


def test_a_group_that_must_break_will_break():
    assert will_break((Text("x"), bracketed("a", breaks=True)))


def test_a_break_among_alternatives_is_not_seen_from_outside():
    assert not will_break(Group(Text("a"), alternatives=(bracketed("a", breaks=True),)))
