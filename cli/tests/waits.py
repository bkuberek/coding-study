"""One generous wait for everything a test only waits on, such as a real Docker run or a process
that has to notice something on a busy machine. It bounds a wait, so a real hang still fails. A
test whose point is a time budget or an ordering does not use it."""

GENEROUS_WAIT_S = 180.0
POLL_S = 0.02
