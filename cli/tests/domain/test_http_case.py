from coding_study.domain.cases import Case, Expected, FunctionInput
from coding_study.domain.http_case import HttpCaseInput, HttpExpected, HttpRequest
from coding_study.domain.judging import concrete_case


def http_input() -> HttpCaseInput:
    request = HttpRequest("GET", "/availability")
    return HttpCaseInput(
        {"method": "GET", "path": "/availability"},
        request=request,
        expected=HttpExpected(200),
    )


def test_a_path_without_a_query_is_the_whole_target():
    assert HttpRequest("GET", "/availability").target == "/availability"


def test_a_query_follows_the_path():
    request = HttpRequest("GET", "/availability", query={"date": "2027-03-01"})
    assert request.target == "/availability?date=2027-03-01"


def test_a_repeated_query_key_is_sent_once_per_value():
    request = HttpRequest("GET", "/rooms", query={"room": ("oak", "elm")})
    assert request.target == "/rooms?room=oak&room=elm"


def test_a_query_value_is_encoded():
    request = HttpRequest("GET", "/rooms", query={"name": "oak & elm"})
    assert request.target == "/rooms?name=oak+%26+elm"


def test_reports_show_an_http_input_as_a_function_input():
    assert isinstance(http_input(), FunctionInput)


def test_an_http_case_becomes_a_runnable_case_like_any_other():
    expected = Expected({"status": 200})
    case = Case("h1", http_input(), expected, level=1)
    assert concrete_case(case).input == http_input()
