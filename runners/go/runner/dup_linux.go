package runner

import "syscall"

// dup2 makes newFD a copy of oldFD; linux/arm64 has no dup2 system call, only dup3.
func dup2(oldFD, newFD int) error { return syscall.Dup3(oldFD, newFD, 0) }
