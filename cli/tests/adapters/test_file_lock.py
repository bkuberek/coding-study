import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from coding_study.adapters.file_lock import exclusive_lock

WAIT_SECONDS = 10.0


@pytest.fixture
def lock(tmp_path: Path) -> Path:
    return tmp_path / "locks" / "build.lock"


def test_creates_the_lock_file_and_its_directory(lock):
    with exclusive_lock(lock):
        assert lock.is_file()


def test_a_free_lock_does_not_call_on_wait(lock):
    waits: list[str] = []
    with exclusive_lock(lock, lambda: waits.append("waited")):
        pass
    assert waits == []


def test_a_second_holder_waits_until_the_first_leaves(lock):
    events: list[str] = []
    waiting = threading.Event()

    def second() -> None:
        with exclusive_lock(lock, waiting.set):
            events.append("second")

    with ThreadPoolExecutor(max_workers=1) as pool:
        with exclusive_lock(lock):
            future = pool.submit(second)
            assert waiting.wait(WAIT_SECONDS)
            events.append("first")
        future.result(timeout=WAIT_SECONDS)
    assert events == ["first", "second"]


def test_on_wait_runs_once_however_long_the_wait(lock):
    waits: list[str] = []
    waiting = threading.Event()

    def on_wait() -> None:
        waits.append("waited")
        waiting.set()

    def second() -> None:
        with exclusive_lock(lock, on_wait):
            pass

    with ThreadPoolExecutor(max_workers=1) as pool:
        with exclusive_lock(lock):
            future = pool.submit(second)
            assert waiting.wait(WAIT_SECONDS)
        future.result(timeout=WAIT_SECONDS)
    assert waits == ["waited"]


def test_the_lock_is_released_when_the_block_raises(lock):
    with pytest.raises(ValueError, match="boom"), exclusive_lock(lock):
        raise ValueError("boom")
    with exclusive_lock(lock, lambda: pytest.fail("the lock was still held")):
        pass
