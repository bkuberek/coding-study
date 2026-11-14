# Idempotent Converge

## Statement

Build `Converger`, the core of a configuration tool that sets up servers. Instead of a script of commands ("install this, then write that"), you describe the state each server should end up in: this file has this content, this package is installed, this service is running. The tool looks at each server, compares, and changes only what differs. Later levels add a dry run that shows what would change, actions that run only after a change, failures, many servers at once and conditions on facts about each server. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**The words.** A **host** is one server the tool configures. A **resource** is one thing on a host that the tool can check and change: a file, a package or a service. The **desired state** is what you want, written as **tasks**; the **actual state** is what the host has right now. Running a task brings one resource from its actual state to the desired one. If the resource already matches, the task changes nothing and reports `ok`; if it had to change something, it reports `changed`.

**Why describe a state.** A script that appends a line to a file adds a second copy when you run it twice. A task that says "the file has this content" does nothing the second time. That property, where running something again changes nothing more, is called **idempotence**, and it is what lets you run the same configuration every hour, after every failure and on every new server, until all of them **converge** to the desired state. A run that reports `changed` for a task on its second run is a sign of a task that is not idempotent.

Aim to finish in 100 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 50, level 3 by 70 and level 4 by 95, keeping the last minutes for a final run.

## Input

- `Converger()`: creates a tool with no hosts and no tasks.
- A host name, a task name, a handler name and a package name are 1 to 20 characters: lowercase letters, digits and `-`. A fact key follows the same rule.
- A file path and a file's content are 1 to 40 printable ASCII characters (codes 33 to 126, so no space).
- Each level's section describes the methods it adds and their parameters.

## Output

Methods that change the tool return a `bool`. Runs and reports return **rows**: each row is a list of strings, in the order its level specifies. Where something is "sorted", texts are compared by the numeric value of their characters, so `/A` comes before `/a`.

## Level 1: Tasks and runs

A host has files, each with a content, and packages. Every installed package comes with a **service** of the same name, which is `running` or `stopped`. Installing a package gives it a stopped service; removing a package removes its service.

- `addHost(host)`: adds a host with no files and no packages. It returns `true` when the host is new and `false` when it exists.
- `setState(host, kind, target, value)`: sets the starting state of a host, as it was before the tool ever ran. `kind` is `file` (`target` is a path, `value` its content), `package` (`target` is a package name, `value` is `present` or `absent`) or `service` (`target` is the name of an installed package, `value` is `running` or `stopped`). It returns `true`, or `false` without changing anything when the host does not exist.
- `addTask(name, kind, target, value)`: adds a task at the end of the list, with the same kinds and values as `setState`. It returns `true`, or `false` without changing anything when a task of that name exists.
- `run()`: runs every task on every host and returns one row per task and host: `[host, task, status]`.
- `state(host)`: the actual state of the host, one row per resource: `["file", path, content]`, `["package", name, "present"]` for each installed package and `["service", name, state]` for its service, sorted by the first field, then the second. An unknown host gives `[]`.

**What a task does.**

| Kind | `ok` when | Otherwise it |
|------|-----------|--------------|
| `file` | the file exists with exactly this content | writes the content, creating the file |
| `package` | the package is installed (`present`) or not (`absent`), as asked | installs or removes it |
| `service` | the service is in the state asked | starts or stops it |

At this level, a service task always names a package that is installed when the task runs.

**The order.** A run takes the tasks in the order they were added. Each task runs on every host, in the order the hosts were added, before the next task starts. The rows follow that order.

### Example 1

<!-- case: ex1 -->

`web1` already has the file and the package, so those tasks are `ok` there and `changed` on `web2`. The package comes with a stopped service, so `nginx-up` starts it on both hosts. The second run changes nothing: every task reports `ok`. `setState` on `ghost` returns `false`, since there is no such host.

### Example 2

<!-- case: ex2 -->

Removing `telnet` also removes its running service. The second `addTask("conf", ...)` returns `false` and changes nothing, so the file gets `port=2`. On the second run both tasks are `ok`.

## Level 2: Check mode and diffs

Before you change a production server, you want to see what would happen. A **check run** (often called a dry run) goes through the same tasks and reports what each would change, without changing anything.

- `check()`: does what `run` would do, on copies of the hosts, and returns the same rows, except that each `changed` row carries a **diff**: `[host, task, "changed", before, after]`. An `ok` row stays `[host, task, "ok"]`. The real hosts are left exactly as they were.

**The diff.** For a file, `before` is its old content, or `""` when the file did not exist, and `after` the new content. For a package, `before` and `after` are `present` or `absent`. For a service, they are its state before and the state asked.

**Copies, not the real hosts.** Each task of a check run sees what the earlier tasks of the same check would have done: after a task that would install a package, a task that starts its service sees a stopped service, not a missing one. That is why the check works on copies that it changes as it goes, and throws them away at the end.

### Example 1

<!-- case: ex3 -->

The check reports three changes, each with its diff. The file did not exist, so its `before` is `""`. `nginx-up` sees the package that `nginx` would install, with its stopped service. The host is still empty afterwards. After a real run, a check finds nothing to change.

### Example 2

<!-- case: ex4 -->

`app1` would get a new port, and `app2` would lose its `debug` package. The check leaves `app2` with its package.

## Level 3: Handlers and failures

Some actions should happen only after a change: restart the web server when its configuration file changes, and not otherwise. Such an action is a **handler**.

- A service task or handler can also ask for `restarted`. A restart always reports `changed`, and leaves the service `running`; its diff has the old state as `before` and `restarted` as `after`. A restart is not idempotent, which is exactly why it belongs in a handler.
- `addHandler(name, kind, target, value)`: adds a handler at the end of the list of handlers, with the kinds and values of a task. It returns `true`, or `false` without changing anything when a handler of that name exists. Handler names and task names never collide.
- `notifies(task, handler)`: from now on, when `task` reports `changed` on a host, it **notifies** `handler` on that host. It returns `true` when the link is new, and `false` when it exists or when the task or the handler does not exist.

**Handlers.** After all the tasks have run, the handlers run, in the order they were added; each runs on every host where it was notified, in host order. A handler runs at most once per host and run, however many tasks notified it. A task that reports `ok` or fails notifies nothing. Notifications last for one run only. Handler rows look like task rows, with the handler's name: `[host, handler, status]`, and in a check run a `changed` handler row carries a diff too.

**Failures.** A service task or handler fails when its package is not installed. It reports `[host, name, "failed"]` and changes nothing. A failed host is done for this run: no later task or handler runs on it, and its notified handlers are dropped. The other hosts carry on. A check run fails the same way, on its copies.

### Example 1

<!-- case: ex5 -->

The configuration changes on `web1` only, so only `web1` restarts nginx, after all the tasks. The second `notifies` returns `false`. On the next run nothing changes, so the handler does not run at all.

### Example 2

<!-- case: ex6 -->

`b` has no `app` package, so `app-up` fails there. `b` runs nothing else: no `motd`, and no `reload`, although `conf` notified it. `a` carries on to the end. The file that `conf` wrote on `b` before the failure stays.

## Level 4: Facts, conditions and batches

Hosts differ: some are web servers, some are databases, some have little memory. A **fact** is something the tool learned about a host before the run, such as its role or its memory size. Conditions on facts let one list of tasks serve every kind of host.

- `setFact(host, key, value)`: records a fact about the host. It returns `true` when the host had no fact with that key, and `false` when this replaces one or when the host does not exist (then nothing changes).
- `onlyIf(task, fact, comparison, value)`: adds a condition to the task: the host's fact `fact` compared with `value` by `comparison`, one of `==`, `!=`, `<`, `<=`, `>` and `>=`. The task runs on a host only when all its conditions hold there; otherwise it reports `skipped`, changes nothing and notifies nothing. It returns `true`, or `false` without changing anything when no task has that name (handlers have no conditions).
  - `==` and `!=` compare the fact and `value` as text.
  - `<`, `<=`, `>` and `>=` compare them as whole numbers, written in decimal with an optional leading `-`, so `10` is greater than `9`. Leading zeros are allowed: `007` is the number 7.
  - A condition that cannot be decided fails the task: the host has no such fact, or a numeric comparison meets a fact that is not a whole number.
  - The conditions are checked in the order they were added, and the first one that settles the result decides it: a false one makes the task `skipped`, and one that cannot be decided makes it `failed`. The conditions after it are not looked at.
- `setBatchSize(size)`: from now on, runs and checks take the hosts in **batches** of `size` (at least 1), in host order. A batch runs every task and then every handler on its hosts before the next batch starts. It returns `true` when this changes the batch size and `false` when it was already `size`. Before any call, all hosts form one batch, and there is no batch size yet, so the first call returns `true` even when `size` equals the number of hosts.
- If every host of a batch has failed by the end of that batch, the run stops: later batches do not start. Rolling a change out batch by batch, and stopping when a whole batch breaks, limits the damage of a bad change.
- `summary()`: one row per host, in host order: `[host, ok, changed, failed, skipped]`, where each is the number of tasks and handlers that ended that way on the host in the latest `run`, written as a decimal number. `changed` is not counted in `ok`. A check run does not change the summary, and a host that the latest run never reached, or that was added since, has four zeros.

### Example 1

<!-- case: ex7 -->

`nginx` runs only where the role is `web`, and `swap` only where memory is below 1024 megabytes, so each host skips one task. The summary counts two changes and one skip for each host. On the second run the same tasks are skipped, and the others report `ok`.

### Example 2

<!-- case: ex8 -->

With batches of two, `web1` and `web2` finish both tasks first. In the second batch neither `web3` nor `web4` has the `app` package, so both fail and the whole batch has failed: `web5` and `web6` never start, and their summary rows are all zeros.

## Constraints

- At most 50 hosts, 50 tasks, 20 handlers, 20 facts per host, 20 conditions per task and 500 calls per test.
- `setState` never sets the service of a package that is not installed.
- A fact or value that is a whole number has at most 15 digits.

## Follow-ups

- A real tool runs a task on several hosts at the same time. Which rows would come out in a different order, and which would not change at all?
- Handlers here are lost when a host fails. Some tools let you force the handlers of a failed host to run anyway. When is that the safer choice?
- How would you turn a command that always runs, such as a database migration, into an idempotent task? What would it have to check first?
- Facts here are fixed for the run. What breaks if a task changes something that a later task's condition depends on?

## Hints

### Hint 1

Give each host two dictionaries: one from path to content, and one from package name to the state of its service. A package is installed exactly when it is a key of the second dictionary, so installing sets it to `stopped` and removing deletes the key. Every task then reads the current value, compares it with the one asked, and writes only when they differ.

### Hint 2

The outer loop of a run goes over the tasks and the inner loop over the hosts. Return the status from a small function that takes a host and a task, so that the run itself only collects rows.

### Hint 3

For a check run, copy every host first, deeply, so that no dictionary is shared with the real host, then run the same loop on the copies. The function that runs a task can return the value it saw before the change along with the status, which gives you the diff for free.

### Hint 4

Keep, per host, the set of handlers notified during the run, and the set of hosts that have failed. After the task loop, walk the handlers in the order they were added and run each on the hosts whose set contains it and that have not failed. A set gives "at most once" without any counting.

### Hint 5

Evaluate a task's conditions before the task itself. Look the fact up first: if it is missing, the task fails. For a numeric comparison, parse both sides; if a side does not parse, the task fails. Walk the conditions in the order they were added and stop at the first one that is false (the task is skipped) or that cannot be decided (the task fails).

### Hint 6

Batches are the run loop wrapped in one more loop, over slices of the host list. Everything you kept per run (notified handlers, failed hosts) now belongs to one batch. After a batch, if the number of failed hosts equals the size of the batch, stop. Keep the counts for the summary in a dictionary per host that the run fills in, and replace the stored one only at the end of a real run.
