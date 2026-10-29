//go:build unix

package runner

import "syscall"

// cpuNS is the CPU time of the whole process, user and system, in nanoseconds. Go has no
// per-goroutine CPU clock, so it includes the garbage collector's workers
// (docs/specs/performance-analysis.md#measurement).
func cpuNS() int64 {
	var usage syscall.Rusage
	if err := syscall.Getrusage(syscall.RUSAGE_SELF, &usage); err != nil {
		return 0
	}
	return usage.Utime.Nano() + usage.Stime.Nano()
}
