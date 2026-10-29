//go:build unix

package runner

import (
	"os"
	"syscall"
	"unicode/utf8"
)

const (
	maxOutputBytes   = 4096
	truncationNotice = "\n[output truncated at 4 KiB]\n"
	// keptBytes is enough to tell whether the character at the limit is complete.
	keptBytes = maxOutputBytes + utf8.UTFMax
	stdoutFD  = 1
	stderrFD  = 2
)

// capture collects what user code prints during one case (docs/specs/runners.md#execution-
// environment). File descriptors 1 and 2 are redirected to one pipe, because the println builtin
// and a fatal error write to fd 2 directly, bypassing os.Stderr. Standard output and standard
// error share the pipe, so the text reads as it would in a terminal.
type capture struct {
	reader, writer *os.File
	saved          [2]int
	kept           []byte
	total          int
	done           chan struct{}
}

// startCapture redirects fds 1 and 2; nil when the redirection is impossible, in which case the
// case runs uncaptured.
func startCapture() *capture {
	reader, writer, err := os.Pipe()
	if err != nil {
		return nil
	}
	c := &capture{reader: reader, writer: writer, done: make(chan struct{})}
	for i, fd := range []int{stdoutFD, stderrFD} {
		saved, err := syscall.Dup(fd)
		if err == nil {
			err = dup2(int(writer.Fd()), fd)
		}
		if err != nil {
			c.restore(i)
			_ = writer.Close()
			_ = reader.Close()
			return nil
		}
		c.saved[i] = saved
	}
	go c.drain()
	return c
}

// drain keeps the first bytes and reads the rest away, so a writer never blocks on a full pipe.
func (c *capture) drain() {
	defer close(c.done)
	buffer := make([]byte, 32*1024)
	for {
		n, err := c.reader.Read(buffer)
		c.total += n
		if room := keptBytes - len(c.kept); room > 0 {
			c.kept = append(c.kept, buffer[:min(n, room)]...)
		}
		if err != nil {
			return
		}
	}
}

// stop restores fds 1 and 2 and returns the captured text, truncated to maxOutputBytes without
// splitting a character.
func (c *capture) stop() string {
	if c == nil {
		return ""
	}
	c.restore(len(c.saved))
	_ = c.writer.Close()
	<-c.done
	_ = c.reader.Close()
	return truncated(c.kept, c.total)
}

func (c *capture) restore(count int) {
	for i, fd := range []int{stdoutFD, stderrFD}[:count] {
		_ = dup2(c.saved[i], fd)
		_ = syscall.Close(c.saved[i])
	}
}

// truncated is the kept text, or its first maxOutputBytes and the notice when more was printed;
// a character split at the limit is dropped.
func truncated(kept []byte, total int) string {
	if total <= maxOutputBytes {
		return string(kept)
	}
	cut := kept[:maxOutputBytes]
	start := len(cut) - 1
	for start > 0 && !utf8.RuneStart(cut[start]) && len(cut)-start < utf8.UTFMax {
		start--
	}
	if !utf8.FullRune(cut[start:]) {
		cut = cut[:start]
	}
	return string(cut) + truncationNotice
}
