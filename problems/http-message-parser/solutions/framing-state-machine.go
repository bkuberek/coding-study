package http_message_parser

import (
	"strconv"
	"strings"
)

const (
	crlf      = "\r\n"
	endOfHead = "\r\n\r\n"
	// A size with more significant digits than this is larger than any limit, so it is never
	// converted into a number: that is how a size such as 10000000000000000 (hex) cannot wrap.
	maxSignificantDigits = 12
	tooManyDigits        = int64(1) << 62
)

// outcome tells a stage's caller why it stopped: it needs more bytes, or the message failed.
type outcome struct {
	needMore bool
	code     string
}

func needMore() *outcome           { return &outcome{needMore: true} }
func failure(code string) *outcome { return &outcome{code: code} }

func isTokenChar(c byte) bool {
	return c >= '0' && c <= '9' || c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' ||
		strings.IndexByte("!#$%&'*+-.^_`|~", c) >= 0
}

func isToken(text string) bool {
	if text == "" {
		return false
	}
	for i := 0; i < len(text); i++ {
		if !isTokenChar(text[i]) {
			return false
		}
	}
	return true
}

func allBytes(text string, ok func(byte) bool) bool {
	for i := 0; i < len(text); i++ {
		if !ok(text[i]) {
			return false
		}
	}
	return true
}

func isDigit(c byte) bool { return c >= '0' && c <= '9' }

func isHex(c byte) bool { return isDigit(c) || c >= 'a' && c <= 'f' || c >= 'A' && c <= 'F' }

func trimOws(text string) string { return strings.Trim(text, " \t") }

// sizeOf is the value of a run of digits, or a huge number when it has too many digits to matter.
func sizeOf(digits string, base int) int64 {
	significant := strings.TrimLeft(digits, "0")
	if significant == "" {
		return 0
	}
	if len(significant) > maxSignificantDigits {
		return tooManyDigits
	}
	value, _ := strconv.ParseInt(significant, base, 64)
	return value
}

func skipEmptyLines(data string, pos int) int {
	for strings.HasPrefix(data[pos:], crlf) {
		pos += 2
	}
	return pos
}

func checkLineEndings(text string) *outcome {
	rest := strings.ReplaceAll(text, crlf, "")
	if strings.ContainsAny(rest, "\r\n") {
		return failure("bad-line-ending")
	}
	return nil
}

func parseRequestLine(line string) ([]string, *outcome) {
	parts := strings.Split(line, " ")
	if len(parts) != 3 {
		return nil, failure("bad-request-line")
	}
	method, target, version := parts[0], parts[1], parts[2]
	validTarget := target != "" && allBytes(target, func(c byte) bool { return c >= '!' && c <= '~' })
	validVersion := len(version) == 8 && strings.HasPrefix(version, "HTTP/") &&
		isDigit(version[5]) && version[6] == '.' && isDigit(version[7])
	if !isToken(method) || !validTarget || !validVersion {
		return nil, failure("bad-request-line")
	}
	return []string{"request", method, target, version}, nil
}

func parseFieldLine(line string) (string, string, *outcome) {
	if strings.HasPrefix(line, " ") || strings.HasPrefix(line, "\t") {
		return "", "", failure("obs-fold")
	}
	colon := strings.IndexByte(line, ':')
	if colon == -1 || !isToken(line[:colon]) {
		return "", "", failure("bad-field")
	}
	value := trimOws(line[colon+1:])
	if !allBytes(value, func(c byte) bool { return c == '\t' || c >= ' ' && c <= '~' }) {
		return "", "", failure("bad-field")
	}
	return strings.ToLower(line[:colon]), value, nil
}

// listElements reads a comma-separated list over every field line, with empty elements dropped.
func listElements(values []string) []string {
	var elements []string
	for _, element := range strings.Split(strings.Join(values, ","), ",") {
		if trimmed := trimOws(element); trimmed != "" {
			elements = append(elements, trimmed)
		}
	}
	return elements
}

// HttpParser reads a request in three stages: skip empty lines, find the end of the head (the
// first CRLF CRLF), then read the body that the framing fields announce. Each stage either
// finishes, needs more bytes, or fails, and the same code serves the one-shot methods and the
// connection: Feed keeps the unread bytes and runs the stages again each time more arrive, so a
// message is reported by the call that completes it.
type HttpParser struct {
	headLimit, bodyLimit int64
	limited              bool
	buffer               string
	closed               bool
}

func NewHttpParser() *HttpParser {
	return &HttpParser{}
}

func errorRows(problem *outcome) [][]string {
	if problem.needMore {
		return [][]string{{"error", "incomplete"}}
	}
	return [][]string{{"error", problem.code}}
}

// Level 1
func (p *HttpParser) ParseHead(data string) [][]string {
	start := skipEmptyLines(data, 0)
	end, problem := p.endOfHead(data, start)
	if problem != nil {
		return errorRows(problem)
	}
	rows, problem := p.headRows(data[start : end-4])
	if problem != nil {
		return errorRows(problem)
	}
	return rows
}

// Level 2
func (p *HttpParser) ParseMessage(data string) [][]string {
	rows, _, problem := p.message(data, skipEmptyLines(data, 0))
	if problem != nil {
		return errorRows(problem)
	}
	return rows
}

// Level 3
func (p *HttpParser) Feed(data string) [][]string {
	rows := [][]string{}
	if p.closed {
		return rows
	}
	p.buffer += data
	for {
		p.buffer = p.buffer[skipEmptyLines(p.buffer, 0):]
		message, end, problem := p.message(p.buffer, 0)
		if problem != nil && problem.needMore {
			return rows
		}
		if problem != nil {
			p.closed = true
			p.buffer = ""
			return append(rows, []string{"error", problem.code})
		}
		rows = append(rows, message...)
		p.buffer = p.buffer[end:]
	}
}

func (p *HttpParser) Close() [][]string {
	if p.closed {
		return [][]string{}
	}
	p.closed = true
	if p.buffer != "" {
		return [][]string{{"error", "incomplete"}}
	}
	return [][]string{}
}

// Level 4
func (p *HttpParser) SetLimits(maxHeadBytes int, maxBodyBytes int) {
	p.headLimit, p.bodyLimit, p.limited = int64(maxHeadBytes), int64(maxBodyBytes), true
}

// endOfHead is the index just after the head's empty line. With a limit, only the first
// `limit` bytes are searched, so a head that cannot fit fails without waiting.
func (p *HttpParser) endOfHead(data string, start int) (int, *outcome) {
	window := data[start:]
	if p.limited && int64(len(window)) > p.headLimit {
		window = window[:p.headLimit]
	}
	found := strings.Index(window, endOfHead)
	if found == -1 {
		if p.limited && int64(len(data)-start) >= p.headLimit {
			return 0, failure("head-too-large")
		}
		return 0, needMore()
	}
	return start + found + 4, nil
}

func (p *HttpParser) headRows(text string) ([][]string, *outcome) {
	if problem := checkLineEndings(text); problem != nil {
		return nil, problem
	}
	lines := strings.Split(text, crlf)
	request, problem := parseRequestLine(lines[0])
	if problem != nil {
		return nil, problem
	}
	rows := [][]string{request}
	hosts := 0
	for _, line := range lines[1:] {
		name, value, problem := parseFieldLine(line)
		if problem != nil {
			return nil, problem
		}
		if name == "host" {
			hosts++
		}
		rows = append(rows, []string{"field", name, value})
	}
	if hosts > 1 || hosts == 0 && request[3] == "HTTP/1.1" {
		return nil, failure("bad-host")
	}
	return rows, nil
}

func (p *HttpParser) message(data string, start int) ([][]string, int, *outcome) {
	headEnd, problem := p.endOfHead(data, start)
	if problem != nil {
		return nil, 0, problem
	}
	rows, problem := p.headRows(data[start : headEnd-4])
	if problem != nil {
		return nil, 0, problem
	}
	var codings, lengths []string
	for _, row := range rows[1:] {
		switch row[1] {
		case "transfer-encoding":
			codings = append(codings, row[2])
		case "content-length":
			lengths = append(lengths, row[2])
		}
	}
	if len(codings) > 0 && len(lengths) > 0 {
		return nil, 0, failure("ambiguous-length")
	}
	if len(codings) > 0 {
		list := listElements(codings)
		if len(list) != 1 || !strings.EqualFold(list[0], "chunked") {
			return nil, 0, failure("unsupported-transfer-coding")
		}
		return p.chunked(data, headEnd, rows)
	}
	var length int64
	if len(lengths) > 0 {
		if length, problem = p.contentLength(lengths); problem != nil {
			return nil, 0, problem
		}
	}
	if int64(len(data)-headEnd) < length {
		return nil, 0, needMore()
	}
	end := headEnd + int(length)
	return append(rows, []string{"body", data[headEnd:end]}), end, nil
}

func (p *HttpParser) contentLength(lines []string) (int64, *outcome) {
	elements := listElements(lines)
	if len(elements) == 0 {
		return 0, failure("bad-content-length")
	}
	for _, element := range elements {
		if !allBytes(element, isDigit) {
			return 0, failure("bad-content-length")
		}
	}
	first := strings.TrimLeft(elements[0], "0")
	for _, element := range elements[1:] {
		if strings.TrimLeft(element, "0") != first {
			return 0, failure("conflicting-content-length")
		}
	}
	length := sizeOf(elements[0], 10)
	if p.tooLarge(length, 0) {
		return 0, failure("body-too-large")
	}
	return length, nil
}

func (p *HttpParser) tooLarge(size, used int64) bool {
	return p.limited && used+size > p.bodyLimit
}

func (p *HttpParser) chunked(data string, pos int, rows [][]string) ([][]string, int, *outcome) {
	var content strings.Builder
	var total int64
	for {
		lineEnd := strings.Index(data[pos:], crlf)
		if lineEnd == -1 {
			return nil, 0, needMore()
		}
		size, problem := chunkSize(data[pos : pos+lineEnd])
		if problem != nil {
			return nil, 0, problem
		}
		if p.tooLarge(size, total) {
			return nil, 0, failure("body-too-large")
		}
		pos += lineEnd + 2
		if size == 0 {
			break
		}
		if int64(len(data)-pos) < size+2 {
			return nil, 0, needMore()
		}
		end := pos + int(size)
		if data[end:end+2] != crlf {
			return nil, 0, failure("bad-chunk")
		}
		content.WriteString(data[pos:end])
		total += size
		pos = end + 2
	}
	rows = append(rows, []string{"body", content.String()})
	if strings.HasPrefix(data[pos:], crlf) {
		return rows, pos + 2, nil
	}
	found := strings.Index(data[pos:], endOfHead)
	if found == -1 {
		return nil, 0, needMore()
	}
	text := data[pos : pos+found]
	if problem := checkLineEndings(text); problem != nil {
		return nil, 0, problem
	}
	for _, line := range strings.Split(text, crlf) {
		name, value, problem := parseFieldLine(line)
		if problem != nil {
			return nil, 0, problem
		}
		rows = append(rows, []string{"trailer", name, value})
	}
	return rows, pos + found + 4, nil
}

func chunkSize(line string) (int64, *outcome) {
	if strings.ContainsAny(line, "\r\n") {
		return 0, failure("bad-chunk-size")
	}
	digits := line
	if semicolon := strings.IndexByte(line, ';'); semicolon != -1 {
		digits = strings.TrimRight(line[:semicolon], " \t")
	}
	if digits == "" || !allBytes(digits, isHex) {
		return 0, failure("bad-chunk-size")
	}
	return sizeOf(digits, 16), nil
}
