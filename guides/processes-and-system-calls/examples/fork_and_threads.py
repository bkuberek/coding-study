"""A child process gets a copy of its parent's memory; the threads of one process share it.

The parent sets a counter and forks. The child adds 1 to its copy, prints it and exits with
status 7. The parent waits for the child, reads that status, and finds its own counter unchanged.
Then two threads of the parent each append to one list, and both appends are there.
It needs os.fork, which POSIX systems have.
"""

import os
import sys
import threading

counter = 10
sys.stdout.flush()  # empty the output buffer first, or the child would inherit a copy of it

pid = os.fork()
if pid == 0:  # fork returned 0: this is the child
    counter += 1
    print(f"child:   counter = {counter}")
    sys.stdout.flush()
    os._exit(7)  # end the child now, with exit status 7

# fork returned the child's process id: this is the parent
_, status = os.waitpid(pid, 0)  # block until the child ends, and collect its status
print(f"parent:  the child exited with status {os.waitstatus_to_exitcode(status)}")
print(f"parent:  counter = {counter}")

shared: list[str] = []


def work(name: str) -> None:
    shared.append(name)


threads = [threading.Thread(target=work, args=(name,)) for name in ("t1", "t2")]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join()  # wait for the thread to finish
print(f"threads: shared = {sorted(shared)}")
