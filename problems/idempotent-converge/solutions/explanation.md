# Idempotent Converge: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| state-copies | optimal | O(N (T + H + C) + S) per run or check, for N hosts, T tasks, H handlers, C conditions and S resources copied | O(S + N H) | default answer; one loop serves runs and checks, with batches around it |

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Tasks and runs | per host, a map from path to content and a map from package to the state of its service; an ordered map of tasks |
| 2 | Check mode | nothing new: a check runs the same loop on deep copies of the hosts and keeps the diffs |
| 3 | Handlers and failures | an ordered map of handlers and the links from tasks to handlers; a run keeps, per host, the notified handlers and whether it failed |
| 4 | Facts, conditions, batches | facts per host, conditions per task, a batch size, and the counts of the latest run |

The choice that keeps level 2 cheap is to make "run one task on one host" a function that returns the status and the value it saw before the change. A run discards the value; a check keeps it as the diff. Since a check works on copies that it changes as it goes, it is the same loop with a different set of hosts, and every later rule (handlers, failures, conditions, batches) applies to checks for free.

## Approach: state-copies (Compare before changing, on deep copies for a check)

### Intuition

Every task reads the current value of one resource, compares it with the value asked for, and writes only when they differ. That comparison is what makes a run idempotent: the second time, every read matches and nothing is written. The run itself is two nested loops, tasks outside and hosts inside, so the rows come out task by task. A dry run must predict, not just compare against the starting state, because a task can depend on what an earlier task does; running the real loop on throwaway copies predicts exactly what the run would do.

### Algorithm

1. Level 1: a host holds `files` (path to content) and `packages` (name to `running` or `stopped`). A task reads the current value: the content or `""` for a file, `present` or `absent` for a package, and the service state for a service. If it equals the value asked, the status is `ok`; otherwise the task writes it (installing gives a stopped service, removing deletes the entry) and the status is `changed`. A run loops over the tasks in order and, inside, over the hosts in order.
2. Level 2: a check deep-copies every host, runs the same loop on the copies, and adds `[before, after]` to each `changed` row. The copies are dropped at the end.
3. Level 3: a service whose package is missing makes the task fail, which adds the host to a failed set; the loop skips failed hosts. A `changed` task adds its linked handlers to the host's notified set. After the task loop, each handler, in the order handlers were added, runs on every host whose set contains it and that has not failed. A restart always writes and always reports `changed`.
4. Level 4: before a task runs, its conditions are checked in order: a missing fact or a number that does not parse fails the task, a false condition skips it. The hosts are cut into slices of the batch size, and the task loop and the handler loop run per slice, with fresh notified and failed sets. If every host of a slice failed, the run stops. A real run fills a table of counts per host and stores it as the summary at the end.

### Correctness

Idempotence: a task writes only when the current value differs from the one asked, and after it writes, the current value is the one asked. So when every task has reported `ok` or `changed` once, a second run with the same tasks reads the asked values and reports `ok`, unless two tasks ask for different values of one resource, or a task asks for a restart, which is never `ok` by definition.

Check mode: a check runs the same function, in the same order, on hosts that start equal to the real ones, so each task of the check sees exactly the state it would see in the run, and reports the status the run would report. The real hosts are never passed to it, so they cannot change.

Handlers: a set holds a handler at most once, so a handler runs at most once per host and run, and walking the handlers in their own order makes the order independent of the order of notifications. A host enters the failed set the moment a task or handler fails there, and every later step checks the set, so nothing runs on it afterwards.

Batches: the loop over a slice is the level 3 run restricted to that slice, so each batch finishes its handlers before the next starts, and the rows come out batch by batch.

### Complexity

- Time: O(N (T + H + C) + S) per run or check, for N hosts, T tasks, H handlers, C conditions and S resources copied — each host meets each task, each of its conditions and each handler at most once, with hash-map reads and writes; a check also copies every resource of every host once.
- Space: O(S + N H) — the hosts' resources (twice during a check), and the notified sets, at most H handlers per host.

### Trade-offs

- Copying whole hosts for a check is simple and exact. A tool with large hosts would keep an overlay of pending writes per host instead, reading through it before the real state.
- Lockstep (task by task over all hosts) keeps every host at the same step, which makes failures easy to read. Running each host as fast as it can finishes sooner, but a broken task then fails on many hosts before anyone notices.
- Dropping the handlers of a failed host avoids restarting a half-configured service, but it can leave a changed file whose restart never happens; the next run will not notify again, because the file is already right.
- Batches limit how many hosts a bad change can reach, at the cost of a longer run.

### Pitfalls and edge cases

- Tasks in the order they were added and hosts in the order they were added, task by task (hidden case `h1`).
- A removed package takes its service with it (`h2`, `h10b`), and a package installed again comes with a stopped service (`h2`).
- A task name added twice keeps the first task, and `setState` on an unknown host adds nothing (`h3`). `state` sorts by character code (`h3`).
- A check must see what earlier tasks would have done, and must leave the hosts alone (`h5`). Only `changed` rows carry a diff, and a missing file shows `""` (`h6`).
- A handler runs once, in the order handlers were added, and only after a change (`h7`); it can fail too (`h8`), and a check runs handlers on its copies (`h9`). A restart is never `ok` (`h10`).
- Numbers compare as numbers, every condition must hold, a skipped task notifies nothing, and a missing or non-numeric fact fails the task (`h11`).
- Handlers run at the end of each batch, a partly failed batch does not stop the run, and a fully failed one does (`h12`, `h15`).
- The summary counts handlers, keeps `changed` out of `ok`, describes only the latest run and lists every host (`h13`).

### Language notes

- Python copies hosts with `copy.deepcopy`, TypeScript and Kotlin build new maps from the old ones, Java uses copy constructors of `HashMap` and `LinkedHashMap`, Go copies its maps in a loop, and Rust derives `Clone` on the host struct.
- Tasks and handlers are kept in insertion order: Python and TypeScript maps remember it, Java and Kotlin use `LinkedHashMap`, and Go and Rust keep a slice or `Vec` that is searched by name, which is cheap for a few dozen entries. Go and Rust also keep the host names in a list, since their maps have no order.
- Every language first checks a number against `-?[0-9]+`, because the built-in parsers accept more than the statement allows: a leading `+` everywhere, `_` in Python's `int`, and exponents and hexadecimal in TypeScript's `Number`. Only then is it parsed, with `int` in Python, `Number` in TypeScript, `Long.parseLong` in Java, `toLong` in Kotlin, `strconv.ParseInt` in Go and `str::parse::<i64>` in Rust; at most 15 digits fit all of them exactly.

## Further reading

- [Handlers: running operations on change, Ansible documentation](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_handlers.html): handlers run only when notified, once however often they are notified, in the order they are defined, after the tasks.
- [Validating tasks: check mode and diff mode, Ansible documentation](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_checkmode.html): a simulation that changes nothing, and before-and-after comparisons.
- [Error handling in playbooks, Ansible documentation](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_error_handling.html): a failed task stops its host while others continue, and notified handlers do not run on a host that fails unless forced.
- [Controlling playbook execution: strategies and more, Ansible documentation](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_strategies.html): running the whole play on one batch of hosts before the next.
- [Controllers, Kubernetes documentation](https://kubernetes.io/docs/concepts/architecture/controller/): a control loop that keeps moving the current state toward the desired state.
