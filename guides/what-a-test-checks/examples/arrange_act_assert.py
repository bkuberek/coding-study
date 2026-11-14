"""Four tests in the arrange-act-assert shape, run against a buggy and a fixed function.

`chunk(items, size)` splits a list into lists of `size` items, the last one possibly shorter.
The same tests run against both versions. Only the buggy one fails, and each failure says what
was expected and what came back.
"""

import io
import unittest


def chunk_buggy(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items) - size + 1, size)]


def chunk_fixed(items: list, size: int) -> list[list]:
    if size < 1:
        raise ValueError("size must be at least 1")
    return [items[i:i + size] for i in range(0, len(items), size)]


chunk = chunk_fixed  # the tests call whatever function this name points to


class ChunkTests(unittest.TestCase):
    def test_even_split(self):
        items = [1, 2, 3, 4]  # arrange
        result = chunk(items, 2)  # act
        self.assertEqual(result, [[1, 2], [3, 4]])  # assert

    def test_last_chunk_is_shorter(self):
        items = [1, 2, 3, 4, 5]
        result = chunk(items, 2)
        self.assertEqual(result, [[1, 2], [3, 4], [5]])

    def test_empty_list(self):
        result = chunk([], 3)
        self.assertEqual(result, [])

    def test_size_zero_is_refused(self):
        with self.assertRaisesRegex(ValueError, "at least 1"):
            chunk([1, 2], 0)


def run_tests_against(version) -> None:
    global chunk
    chunk = version
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ChunkTests)
    result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
    print(f"{version.__name__}: {result.testsRun} run, {len(result.failures)} failed, "
          f"{len(result.errors)} errors")
    for test, traceback in result.failures:
        message = next(line for line in traceback.splitlines() if line.startswith("Assertion"))
        print(f"  {test.id().split('.')[-1]}: {message}")


run_tests_against(chunk_buggy)
run_tests_against(chunk_fixed)
