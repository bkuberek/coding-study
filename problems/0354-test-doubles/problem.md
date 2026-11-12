# Test Doubles

## Statement

Build `Doubles`, a small library of **test doubles**. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is a test double?** Most code depends on other code: a payment service calls a card processor, a report reads the clock, a sign-up sends an email. In a test, the real dependency is often a problem. It may be slow (a network call), unpredictable (the current time, a random number), costly or dangerous (charging a real card), or simply not built yet. A *test double* stands in for the dependency during the test, the way a stunt double stands in for an actor: the code under test calls it exactly as it would call the real thing, and the test decides what happens. The word covers several kinds, and each answers a different need:

| Kind | What it does | Typical question it answers |
|------|--------------|-----------------------------|
| Stub | Gives scripted answers to the calls it gets | "What does my code do when the clock says 9 o'clock, or when the server times out?" |
| Spy | A stub that also records every call, for the test to inspect afterwards | "Did my code send exactly one welcome email, and to whom?" |
| Mock | Is told *before* the run which calls to expect, complains about any other, and checks at the end that the expected ones happened | "Does my code charge the card once, and do nothing else with it?" |
| Fake | A working but simplified implementation, such as an in-memory store or a clock the test moves by hand | "Does the retry fire after 30 seconds?", without waiting 30 seconds |

(A fifth, the *dummy*, is a value passed only because a parameter needs one, and never used. It needs no library.)

**How the tests play the code under test.** A test case is a list of operations, and only data can travel in it, so this problem models a dependency's calls as data. A call is a double's name, a method name and a list of arguments, all strings. The operations of a case play two parts. Most of them are *the test*: they create doubles, script them and ask them questions. The `call` operations (and, at level 4, timers) are *the code under test* calling its dependencies: `call("api", "fetch", ["order7"])` stands for a line such as `api.fetch("order7")` inside the code you are testing, and its result is what that line would receive.

Aim to finish in 90 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 45, level 3 by 65 and level 4 by 85, keeping the last minutes for a final run.

## Input

- `Doubles()`: creates a library with no doubles.
- A **double name** and a **method name** are 1 to 20 letters and digits, starting with a lowercase letter. Each double name belongs to one double, whatever its kind.
- An **argument** is 1 to 20 characters from letters, digits and `_ - . : @ /`. A call has 0 to 4 arguments.
- A **pattern** is a list of strings that describes the arguments of calls. Each entry is an argument, which must be equal, or `*`, which stands for any one argument. A pattern **fits** a call's arguments when both have the same length and every entry fits the argument in its position: `["ana", "*"]` fits `["ana", "20"]` but not `["bo", "20"]` or `["ana"]`, and `[]` fits only a call without arguments.
- An **answer** is 0 to 30 printable ASCII characters (codes 32 to 126) that does not start with `!`.
- Each level's section describes the methods it adds and their parameters.

## Output

A method that changes the library returns a `bool` or a number, a call returns its answer, and a question returns a number, a list of strings or a `bool`. Results that start with `!` are the library's own errors: `"!unknown"` means that no double has the name given.

## Level 1: Stubs

A **stub** gives scripted answers. The test writes **rules**: "when method `m` is called with arguments that fit this pattern, answer this". The code under test then calls the stub and gets those answers, so the test controls what the code under test receives from its dependency. That is the stub's job: steering the code under test down the path you want to test, for example the path where the server times out twice before it answers.

- `addStub(name)`: creates a stub called `name`. It returns `true`, or `false` when a double with that name already exists (and nothing changes).
- `onCall(name, method, args, answers)`: adds a rule to the double `name`: a call to `method` whose arguments fit the pattern `args` is answered from the list `answers` (1 to 5 answers). The first call this rule answers gets `answers[0]`, the next `answers[1]`, and so on; once the list is used up, every later call it answers gets the last answer again. It returns `true`, or `false` when no double has the name.
- `otherwise(name, method, answer)`: sets the answer for calls to `method` that no rule answers. A second `otherwise` for the same method replaces the first. It returns `true`, or `false` when no double has the name.
- `call(name, method, args)`: the code under test calls `method` of the double `name` with the arguments `args`. Of the rules for this method whose pattern fits `args`, the one added most recently answers; with none, the `otherwise` answer for the method; with neither, `""`. A rule that did not answer keeps its place in its list of answers. Calling a name that no double has returns `"!unknown"`.

**Why the newest rule wins.** Tests often set up broad rules first ("every `fetch` answers `ok`") and then, for one test, a narrower rule ("`fetch("order7")` times out"). Taking the newest rule lets the later, specific rule override the earlier, general one, whichever is more specific.

**A worked example.** Suppose the code under test is a `greeting()` function that asks a clock for the hour and says "Good morning" before noon. With the real clock, the result depends on when the test runs. With a stub, the test fixes the hour: `addStub("clock")`, `onCall("clock", "hour", [], ["9"])`, and when `greeting()` calls `clock.hour()` it receives `"9"`, every time. A second test scripts `"15"` and checks the afternoon greeting.

### Example 1

<!-- case: ex1 -->

The clock answers `9` to every call of `hour`, the rule's only answer. Nobody scripted `minute`, so its first call gets the empty answer; after `otherwise`, it gets `30`. No double is called `calendar`, so the call is an error, and a second stub called `clock` cannot be made.

### Example 2

<!-- case: ex2 -->

Both rules fit `fetch("order7")`, and the newer one answers: `timeout` twice, then `ok` for good. `fetch("order8")` fits only the older rule with `*`. A call without arguments fits neither pattern, which both have one entry, and gets `""`. There is no double called `cache`, so `onCall` returns `false`.

## Level 2: Spies

A stub controls what goes *into* the code under test. Often you also need to check what comes *out* of it as calls to its dependencies: did the sign-up send the welcome email? A **spy** records every call it gets, so that the test can ask about them afterwards. From this level on, every double is also a spy: every call to a double that exists is recorded, in the order the calls are made across all doubles, whatever answered it.

- `callCount(name, method)`: how many calls to `method` the double `name` has received, or `-1` when no double has the name.
- `matchCount(name, method, args)`: how many of those calls had arguments that fit the pattern `args`, or `-1` when no double has the name.
- `nthCall(name, n)`: the `n`-th call the double `name` received, as a list of strings: the method name followed by the arguments. A positive `n` counts from the first call (`1` is the first), a negative one from the last (`-1` is the most recent). It returns `[]` when there is no such call, when `n` is `0` and when no double has the name. A call always has a method name, so `[]` cannot be a real call.
- `inOrder(steps)`: whether the recorded calls contain, in this order, one call for each step, with any other calls allowed between them. A step is a list `[name, method, pattern...]`: a double name, a method name and then the pattern for the arguments (nothing after the method means a call without arguments). Each step needs a call of its own: two equal steps need two calls.

**Spy or stub?** A spy checks *after* the run, which keeps the test in the usual order: set up, run, check. Ask only what the test is about. A test that checks every call the code makes breaks as soon as the code changes how it does its job, even when the result is still right.

### Example 1

<!-- case: ex3 -->

The mailer recorded three calls. Both `send` calls fit `["*", "welcome"]`, and one fits `["ana@x.io", "*"]`. The first call was `send` to Ana, and the most recent one was `flush` without arguments. There is no fourth call, and no double called `nobody`.

### Example 2

<!-- case: ex4 -->

The calls were `db.begin`, `db.write(k1)`, `log.info(saved)` and `db.commit`, in this order. The first check passes with `log.info` between the steps. The second fails: `commit` came after `info`. The third passes. The last fails, because two steps need two `write` calls and there was only one.

## Level 3: Mocks

A **mock** turns the spy's check around: the test says *before* the run which calls it expects, and the mock checks them as they come. This finds an unwanted call at the moment it happens, and states the expected conversation in one place, at the top of the test.

- `addMock(name, strict)`: creates a mock called `name`. It returns `true`, or `false` when a double with that name already exists. A mock is a double like the others: `onCall`, `otherwise`, the spy questions and `call` work on it.
- `expect(name, method, args, answer, times)`: the mock `name` expects `times` calls (1 to 5) to `method` with arguments that fit the pattern `args`, and answers each of them with `answer`. It returns `true`, or `false` when no double has the name or the double is not a mock.

**A call to a mock** looks for an answer in this order:

1. The expectations for this method, in the order they were set: the first one whose pattern fits and which has received fewer than `times` calls takes the call and answers it.
2. Otherwise, the stub rules and the `otherwise` answer, as at level 1, if one of them applies. Such a call is **allowed**: the test does not care how often it happens, which suits questions the code asks, such as "what is the quota?".
3. Otherwise the call is **unexpected**. A **strict** mock answers `"!unexpected"`, so that the problem shows up at the line that made the call. A **lenient** mock answers `""` and lets the run go on. Either way the mock remembers the unexpected call for the final check.

A stub never finds a call unexpected: with no rule, it answers `""` as at level 1.

- `verify(name)`: the final check of one double, as a list of lines, empty when all is well:
  1. first, one line for each expectation that received fewer calls than `times`, in the order they were set: `missing <name>.<method>(<pattern>) <received>/<times>`;
  2. then one line for each unexpected call, in the order made: `unexpected <name>.<method>(<arguments>)`.

  The pattern and the arguments are written with commas between them and no spaces, so `missing pay.charge(ana,*) 0/1` and `unexpected mail.ping()`. A stub has nothing to report and gives `[]`. A name that no double has gives `["!unknown"]`, so that a check of a misspelled name cannot pass.
- `verifyAll()`: the lines of `verify` for every mock, mocks in the order they were made.

Checking reports and changes nothing: two checks in a row give the same lines.

**Why check at the end, even after a strict mock failed at the call?** The code under test can catch the error and carry on, as code with a broad error handler does. A run can then look fine, and only the final check tells.

**Mock or spy?** Expect the calls that are the *point* of the code under test, its commands to the outside world: charge the card, send the email. Stub, or simply allow, the calls that only fetch information. A test that expects every query fails whenever the code changes the way it gathers what it needs, even though it still does the right thing.

### Example 1

<!-- case: ex5 -->

The strict mock expects one charge for Ana and one receipt. The first charge fits and answers `ok`. The second fits the pattern, but the expectation has had its one call, so it is unexpected, and so is the refund that nobody expected. The check lists the missing receipt first, then the two unexpected calls in the order they came.

### Example 2

<!-- case: ex6 -->

The lenient mock allows `quota`, which a stub rule answers, and expects two sends. `bounce` was not expected: the mock answers `""` and reports it later. After one send, the check shows one of two sends received; after the second, only the bounce remains. A stub reports nothing, a missing name is an error, and `verifyAll` covers the one mock.

## Level 4: A fake clock

A **fake** is a real, working implementation, made simple for tests. A common one is a **fake clock**. Code that waits, retries after a delay or runs a job every minute schedules **timers**: "in 300 milliseconds, call this". With a real clock, a test of a 5-minute timeout takes 5 minutes, and a test that sleeps "just long enough" fails on a busy machine. A fake clock keeps time that moves only when the test says so: the test moves it forward and the timers that come due fire at once, in order. A stub could only say what time it is; the fake keeps the behaviour that matters, timers that fire in the right order at the right moments.

The library now has a clock. Time is a whole number of milliseconds, starts at `0` and changes only through `advance`. A timer, when it fires, makes a call to a double exactly as the code under test would with `call`: stubs answer it, mocks check it and spies record it, and its answer goes nowhere. Every recorded call also remembers the time at which it was made.

- `now()`: the current time.
- `schedule(delay, name, method, args)`: the code under test sets a **one-shot timer** that calls `method` of the double `name` with `args` at time `now() + delay` (`delay` from `0`). It returns the timer's **id**: timers are numbered `1`, `2`, `3` and so on in the order they are made, by `schedule` and `every` together. It returns `-1`, and makes no timer, when no double has the name.
- `every(interval, name, method, args)`: the same, for a **repeating timer**: it fires at `now() + interval`, then every `interval` after each firing (`interval` from `1`), until it is cancelled.
- `cancel(timerId)`: stops a timer that is still waiting to fire: a one-shot timer that has not fired, or a repeating timer. It returns `true` when it stopped one, and `false` for a timer that has already fired once and for all, one that is already cancelled, and an id that was never given.
- `advance(ms)`: the test moves the clock forward by `ms` (from `0`). Every timer due at or before the new time fires, in time order; while a timer fires, `now()` reads the time it was due. A repeating timer that fires is put back in line for its next time, and fires again within the same `advance` if that time comes before the end. At the end, the clock reads the old time plus `ms`, whether timers fired or not. It returns the firings in order, each as `<id>@<time>`, such as `"2@300"`.
- `pending()`: the timers still waiting, each as `<id>@<due time>`, in the order they would fire.
- `callTimes(name, method)`: the time of each recorded call to `method` of the double `name`, in order; `[]` when there are none and when no double has the name. A call made with `call` happens at the current time.

**Ties.** Timers due at the same time fire in the order they were put in line. A new timer is put in line when it is scheduled. A repeating timer is put in line again each time it fires, behind every timer already waiting. So a timer scheduled at time `0` for time `20` fires at `20` before a repeating timer that, firing at `10`, was put back in line for `20`.

**A delay of 0** does not fire at once: the timer waits for the next `advance`, even `advance(0)`. Code that expects such a timer to have run as soon as it was scheduled has a bug, and a fake clock shows it.

### Example 1

<!-- case: ex7 -->

Three retries are scheduled for 100, 300 and 700 ms. Moving to 150 fires the first. The third is cancelled, so moving on by 1000 fires only the second, and the clock reads 1150. The stub saw `fetch` at 100 and 300. Nothing is waiting now, and a timer cannot be cancelled twice.

### Example 2

<!-- case: ex8 -->

The timer for `c` has a delay of 0 and fires at the first `advance`, even one of 0 ms. `a` and `b` are both due at 5 and fire in the order they were scheduled. The blinking timer, made at time 5, fires at 15, 25 and 35 within one `advance` of 30, and waits for 45 until it is cancelled. The first call the stub got was `draw(c)`.

## Constraints

- At most 500 operations per test, at most 50 doubles, and at most 200 rules and expectations in all.
- Times, delays and intervals are integers from `0` to `10^13`, and the clock never passes `10^14`.
- One `advance` fires at most 1,000 timers.

## Follow-ups

- Real mock libraries also expect calls *in order*, across several mocks. How would you add an expectation that may only be met after another one?
- A *partial mock* or *spy on a real object* forwards the calls it does not script to a real implementation. What would it take to wrap a real object here, and what does that do to the test's independence?
- A fake clock that the code under test reads through a global function is easy to forget to install. What are the trade-offs between passing the clock in as a parameter and replacing a global?
- Here the code under test is data, so a timer cannot schedule another timer. With real callbacks it can. How would you stop a callback that schedules itself with delay 0 from making `advance` run forever?

## Hints

### Hint 1

Start with a dictionary from double name to an object that holds that double's state. For the stub, that state is the rules for each method, kept in the order they were added, and the `otherwise` answers. A call looks at the rules of its method from the newest to the oldest and takes the first whose pattern fits.

### Hint 2

Give each rule a counter of the calls it has answered. The answer for a call is the entry at the counter's position, or the last entry when the counter has run past the end. Only the rule that answers moves its counter.

### Hint 3

For level 2, keep one list of every call made, across all doubles, in order. For each double, keep the positions of its calls in that list, so that its questions read only its own calls. A negative `n` in `nthCall` counts back from the end of the double's list.

### Hint 4

`inOrder` can be answered in one pass over the global list: keep the index of the step you are waiting for, and move to the next step as soon as a call fits it. Taking the first call that fits is never wrong, because a later call could only leave fewer calls for the steps after it.

### Hint 5

A mock is a double with two more lists: its expectations, each with a counter, and its unexpected calls. A call tries the expectations first, then the stub rules, then the `otherwise` answer, and only then counts as unexpected. The strict flag changes only the answer of an unexpected call.

### Hint 6

For level 4, keep the waiting timers in a priority queue ordered by due time and then by a sequence number, which goes up by one every time a timer is put in line, including when a repeating timer is put back after it fires. To cancel, mark the timer as stopped and skip it when it reaches the front.
