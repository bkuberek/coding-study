"""A run's stream as it happens (docs/specs/web-ui.md#server-sent-events): each line reaches a
stream while the child goes on, a silent stream gets keep-alive comments, and every stream of a
run gets the same messages, with a scripted child in place of `cstudy`."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from coding_study.entrypoints.web.runs import Child, Children, ChildStart, ChildTiming
from tests.scripted_runs import CASE_START, QUICK, RUN_END, RUN_START, Script, outs

TIMEOUT_S = 10.0
KEEP_ALIVE_S = 0.05


def run_start(script: Script, workspace: Path) -> ChildStart:
    return ChildStart(
        script.child,
        workspace,
        ("test", "two-sum", "--lang", "python", "--events"),
        "test",
        "test two-sum · python",
        attempt_id=1,
    )


def event_name(frame: str) -> str:
    return next(line for line in frame.splitlines() if line.startswith("event: "))[7:]


async def next_frame(frames: AsyncIterator[str]) -> str:
    return await asyncio.wait_for(anext(frames), TIMEOUT_S)


async def started(tmp_path: Path, timing: ChildTiming = QUICK) -> tuple[Children, Child, Path]:
    """A run that writes `run_start`, then waits for the gate before it ends."""
    script = Script(tmp_path / "script.json")
    gate = script.gate("go")
    script.play(*outs(RUN_START), {"wait_for": str(gate)}, *outs(CASE_START, RUN_END), {"exit": 0})
    children = Children(timing)
    run = await children.start_run(run_start(script, tmp_path))
    return children, run, gate


def test_a_line_reaches_the_stream_while_the_child_runs(tmp_path):
    async def first_frame() -> str:
        children, run, gate = await started(tmp_path)
        frame = await next_frame(run.frames(None))
        gate.touch()
        await children.stop()
        return frame

    assert asyncio.run(first_frame()) == f"id: 0\nevent: run_start\ndata: {RUN_START}\n\n"


def test_a_silent_stream_gets_a_keep_alive_comment(tmp_path):
    async def second_frame() -> str:
        timing = ChildTiming(keep_alive_s=KEEP_ALIVE_S, drain_s=QUICK.drain_s)
        children, run, gate = await started(tmp_path, timing)
        frames = run.frames(None)
        await next_frame(frames)
        frame = await next_frame(frames)
        gate.touch()
        await children.stop()
        return frame

    assert asyncio.run(second_frame()) == ": keep-alive\n\n"


def test_the_lines_after_a_live_stream_started_reach_it(tmp_path):
    async def names() -> list[str]:
        _children, run, gate = await started(tmp_path)
        frames = run.frames(None)
        await next_frame(frames)
        gate.touch()
        return [event_name(frame) async for frame in frames]

    assert asyncio.run(names()) == ["case_start", "run_end", "closed"]


def test_two_streams_of_a_run_get_the_same_messages(tmp_path):
    async def both() -> tuple[list[str], list[str]]:
        _children, run, gate = await started(tmp_path)
        first, second = run.frames(None), run.frames(None)
        await next_frame(first)
        gate.touch()
        return [frame async for frame in first], [frame async for frame in second][1:]

    first, second = asyncio.run(both())
    assert first == second
