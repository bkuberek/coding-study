# Learn Python first

## The idea

cstudy problems assume you can already write a small function in the language you practise: take some input, loop over it, decide things with `if`, and return a result. This page is for you if you want to practise in Python and are not there yet. It lists what to learn first and where to learn it for free: Python's official tutorial, and a community list for people new to programming.

**What to learn before your first problem:**

- Numbers, strings and booleans, and variables to hold them.
- `if`, `elif` and `else`; `for` loops over a list and over `range(...)`; `while` loops.
- Functions: `def`, parameters, `return`.
- Lists (indexing, `append`, `len`, slicing), dictionaries, sets and tuples.
- Reading an error: a traceback ends with the line that says what went wrong.

**Where to learn it:**

- [The Python Tutorial](https://docs.python.org/3/tutorial/), on docs.python.org. Chapter 3, *An Informal Introduction to Python*, covers numbers, text and lists; chapter 4, *More Control Flow Tools*, covers `if`, `for`, `range()` and defining functions; chapter 5, *Data Structures*, covers lists, tuples, sets and dictionaries; chapter 8 covers errors and exceptions. Chapter 2 shows how to start the interactive interpreter, where you can try each line as you read.
- The tutorial says it is written for programmers who are new to Python, not for people new to programming. If you have never programmed, start with the tutorials on the Python Wiki's [Beginner's Guide for non-programmers](https://wiki.python.org/python/getting-started/BeginnersGuide/NonProgrammers.html), a community list (the page warns it may be out of date, and a few entries are paid), and come back to the official tutorial after.

You are ready when you can write, without looking anything up, a function that takes a list of numbers and returns how many of them are even.

## A worked example

When you start a problem, cstudy writes a file for you to fill in, a **stub**. This is the stub that `cstudy start two-sum` writes in `python/practice/two_sum.py`:

```python
"""Two Sum.

You get an integer array nums and an integer target. Exactly two
positions in nums hold values that add up to target. Find those two
positions and return them.

Statement: .statements/two-sum.md
Run: cstudy test two-sum
"""


def two_sum(nums: list[int], target: int) -> list[int]:
    raise NotImplementedError
```

Read it line by line. You should recognise every part before you start:

1. The text between the triple quotes `"""` at the top is the file's **docstring**: a short summary of the problem and the two commands you need. It documents the file and does not change what the code does.
2. `def two_sum(...)` defines the function that cstudy's tests call. Keep its name and its parameters as they are.
3. `nums: list[int]` and `target: int` are **type hints**: `nums` is a list of integers and `target` is an integer. `-> list[int]` says the function returns a list of integers. Python itself does not check them; editors and type checkers use them to warn you.
4. `raise NotImplementedError` raises an error on purpose, so that running the tests on the untouched stub fails clearly. You replace this line with your code.

To fill it in you would loop over the positions of `nums`, compare values and return a list of two positions such as `[i, j]`: chapters 3 to 5 of the tutorial. [Your first problem](../your-first-problem/guide.md) walks through starting, testing and finishing this problem.

## Check your toolchain

cstudy needs Python 3.13 and uv, which manages Python and the workspace's Python project. Install them as the [toolchains guide](https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#python-and-uv) shows, then run:

```console
$ cstudy doctor
ok    python 3.13.12
ok    uv 0.12.13
```

Look for the `python` and `uv` rows. `ok` means the tool was found, with its version; `FAIL` means it is missing or too old, and a `fix:` hint follows when there is one. Inside a workspace, `cstudy doctor --fix` then sets up the Python project with `uv sync`.

Rows for other languages may show `FAIL` or `WARN` when you have not installed their toolchains. That does not stop you practising in Python.

## When to use it

- **Read this page** before your first problem in Python, if writing a loop or a function in Python still needs looking up.
- **Skip it** if you can already write a function that loops over a list and returns a result: go straight to [your first problem](../your-first-problem/guide.md).
- **Choose Python** if you have no strong reason to choose another language. It is cstudy's default language (`default_lang = "python"`), and most problems have a Python reference solution; the exceptions are debugging problems built on another language's trap, and project problems written for one other language.

## Common traps

- **Indentation is the syntax.** The tutorial says it plainly: "indentation is Python's way of grouping statements". A line indented one level too far, or not far enough, changes which block it belongs to, or is an error.
- **Type hints are not checked when the code runs.** Returning a tuple where the stub says `list[int]` runs without complaint; the test may still fail, because it compares the result with the expected value.
- **A default value is evaluated once.** The tutorial's warning: "The default value is evaluated only once." A function with a default such as `items=[]` shares that one list across every call that does not pass its own. Use `None` as the default and create the list inside the function.
- **Changing a list you were given.** A function receives a reference to the caller's list, not a copy, so if it sorts or appends to `nums`, the caller sees the change. Make a new list first, with `sorted(nums)` or `nums.copy()`, when you need a changed version.
- **`print` is not `return`.** cstudy's tests check what the function returns. A function that prints the answer and has no `return` returns `None`.

## Complexity

cstudy's problems state the time and space their solutions take, in Big-O notation, and many have a large hidden input that a slow solution does not finish in time. O(n) means the work grows in step with the input's size n, and O(1) that it stays the same whatever the size. Knowing what Python's own operations cost tells you why.

| Operation | Cost | Source of the fact |
|-----------|------|--------------------|
| `nums[i]` | Independent of the list's length | CPython lists are arrays, the design FAQ says |
| `nums.append(x)`, `nums.pop()` | Fast | The tutorial: appends and pops at the end are fast |
| `nums.insert(0, x)`, `nums.pop(0)` | Grows with the list's length | The tutorial: every other element has to be shifted by one; it recommends `collections.deque` for a queue |
| `d[key]` on a dict | Constant time, O(1), when the keys' hashes differ | The design FAQ: dicts are resizable hash tables |
| `a + b` on integers | No overflow, however large | "Integers have unlimited precision" |

A loop inside a loop over the same list of n items does about n² steps. That is fine for ten items and too slow for a hundred thousand, the length of the largest input of several easy problems.

## Expert notes

- **The version cstudy uses.** cstudy runs your Python code with Python 3.13, which `cstudy doctor` finds with `uv python find 3.13`. Features newer than 3.13 are not available in your solutions.
- **Where your code runs.** `cstudy test` runs your file with the workspace's own virtual environment, `python/.venv`, which `cstudy doctor --fix` creates: a Python installation with its own set of packages, as chapter 12 of the tutorial explains.
- **`list[int]` in hints** subscripts the built-in `list` class itself, without importing anything from `typing`; Python has allowed it since 3.9.
- **Debugging.** The workspace's Python project includes `debugpy`, and `cstudy test --debug` waits for your editor's debugger to attach.

## Practice

Start with [your first problem](../your-first-problem/guide.md), which walks through the whole loop on a real problem.

After that, one problem is built on a Python trap from this page:

- `debug-mutable-default-argument`: a function that is right on its first call, and only on its first call. Find out why and fix it.

## Further reading

- [The Python Tutorial](https://docs.python.org/3/tutorial/): the official introduction, for programmers new to Python.
- [Python For Beginners](https://www.python.org/about/gettingstarted/), on python.org, and the Python Wiki's [Beginner's Guide for non-programmers](https://wiki.python.org/python/getting-started/BeginnersGuide/NonProgrammers.html), a community list that may be out of date: where to start if you have never programmed.
- [More Control Flow Tools](https://docs.python.org/3/tutorial/controlflow.html): `if`, `for`, `range()`, functions, and the warning about default values.
- [Data Structures](https://docs.python.org/3/tutorial/datastructures.html): lists, tuples, sets and dictionaries, and why `pop(0)` is slow.
- [Errors and Exceptions](https://docs.python.org/3/tutorial/errors.html): reading a traceback.
- [Built-in exceptions: `NotImplementedError`](https://docs.python.org/3/library/exceptions.html#NotImplementedError): the error the stub raises.
- [`typing`](https://docs.python.org/3/library/typing.html): type hints, which the runtime does not enforce.
- [Design and history FAQ](https://docs.python.org/3/faq/design.html): how lists and dictionaries are implemented in CPython.
- [Built-in types](https://docs.python.org/3/library/stdtypes.html): integers have unlimited precision.
- [Install the language toolchains: Python and uv](https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#python-and-uv): cstudy's install steps.
