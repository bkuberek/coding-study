"""The lines `cstudy test` and `cstudy submit` print under a case
(docs/specs/cli.md#cstudy-submit)."""

from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Expected, OperationSequence
from coding_study.domain.judging import CaseVerdict, RunnableCase
from coding_study.domain.runs import Stalled, WorkerProgress
from coding_study.entrypoints.commands.report_text import case_details

SEQUENCE = OperationSequence(
    ("Log", "@spawn", "@advance", "@join", "@now"),
    ((), ("r1", "receive", 5000), (2000,), ("r1",), ()),
)
CASE = RunnableCase("h4", SEQUENCE, Expected([None, None, None, "", 2000]))
DEADLOCK = "op 3 (@join r1): deadlock at 2000 ms"


def test_a_deadlock_on_the_virtual_clock_shows_the_operations_up_to_it_and_why():
    stalled = Stalled((), 7, op_index=3, reason=DEADLOCK, partial_output=(None, None, None))
    details = list(case_details(CaseVerdict(CASE, CaseStatus.STALLED, stalled), None))
    assert details == [
        (
            "input",
            'ops=["Log", "@spawn", "@advance", "@join"]  '
            'args=[[], ["r1", "receive", 5000], [2000], ["r1"]]',
        ),
        ("reason", DEADLOCK),
    ]


def test_a_stalled_stress_run_names_its_unfinished_workers():
    stalled = Stalled((WorkerProgress(0, 0, True),), 7)
    details = list(case_details(CaseVerdict(CASE, CaseStatus.STALLED, stalled), None))
    assert details == [("reason", "stalled with 1 unfinished workers")]
