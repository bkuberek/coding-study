import sys

from cs_runner.capture import MAX_OUTPUT_BYTES, TRUNCATION_NOTICE, capture_output


def test_captures_printed_lines():
    with capture_output() as output:
        print("hello")
    assert output.text() == "hello\n"


def test_captures_standard_error_in_the_same_stream():
    with capture_output() as output:
        print("out")
        print("err", file=sys.stderr)
    assert output.text() == "out\nerr\n"


def test_output_at_the_limit_is_kept_whole():
    with capture_output() as output:
        print("x" * (MAX_OUTPUT_BYTES - 1))
    assert len(output.text()) == MAX_OUTPUT_BYTES


def test_output_over_the_limit_is_truncated_with_a_notice():
    with capture_output() as output:
        print("x" * MAX_OUTPUT_BYTES)
    assert output.text() == "x" * MAX_OUTPUT_BYTES + TRUNCATION_NOTICE


def test_truncation_never_splits_a_character():
    with capture_output() as output:
        print("€" * MAX_OUTPUT_BYTES)
    kept = output.text().removesuffix(TRUNCATION_NOTICE)
    assert kept == "€" * (MAX_OUTPUT_BYTES // len("€".encode()))


def test_restores_standard_output_afterwards():
    original = sys.stdout
    with capture_output():
        pass
    assert sys.stdout is original


def test_truncation_notice_is_the_one_every_runner_appends():
    assert TRUNCATION_NOTICE == "\n[output truncated at 4 KiB]\n"
