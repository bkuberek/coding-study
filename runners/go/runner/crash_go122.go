//go:build !go1.23

package runner

// keepCrashOutput needs runtime/debug.SetCrashOutput (Go 1.23); before that a fatal error during
// a case is written to the output capture only.
func keepCrashOutput() {}
