//go:build unix && !linux

package runner

import "syscall"

// dup2 makes newFD a copy of oldFD.
func dup2(oldFD, newFD int) error { return syscall.Dup2(oldFD, newFD) }
