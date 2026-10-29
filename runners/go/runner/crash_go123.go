//go:build go1.23 && unix

package runner

import (
	"os"
	"runtime/debug"
	"syscall"
)

// keepCrashOutput sends fatal errors (a stack overflow, a concurrent map write) to the runner's
// real standard error as well, because during a case fd 2 points at the output capture and the
// CLI reports a crash with the last lines of standard error.
func keepCrashOutput() {
	fd, err := syscall.Dup(stderrFD)
	if err != nil {
		return
	}
	_ = debug.SetCrashOutput(os.NewFile(uintptr(fd), "stderr"), debug.CrashOptions{})
}
