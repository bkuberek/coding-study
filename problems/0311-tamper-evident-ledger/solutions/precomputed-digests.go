package tamper_evident_ledger

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"regexp"
	"strings"
)

var (
	genesis    = make([]byte, 32)
	leafPrefix = []byte{0x00}
	nodePrefix = []byte{0x01}
	hexDigest  = regexp.MustCompile(`^[0-9a-f]{64}$`)
)

func sha256Of(parts ...[]byte) []byte {
	hash := sha256.New()
	for _, part := range parts {
		hash.Write(part)
	}
	return hash.Sum(nil)
}

// encodeText writes a field as its length in bytes (4 bytes, big-endian) and then its UTF-8 bytes.
func encodeText(value string) []byte {
	encoded := make([]byte, 4, 4+len(value))
	binary.BigEndian.PutUint32(encoded, uint32(len(value)))
	return append(encoded, value...)
}

// canonicalAmount drops trailing fractional zeros and a dangling point, and writes "-0" as "0".
func canonicalAmount(amount string) string {
	if strings.Contains(amount, ".") {
		amount = strings.TrimSuffix(strings.TrimRight(amount, "0"), ".")
	}
	if amount == "-0" {
		return "0"
	}
	return amount
}

func recordDigest(record []string) []byte {
	return sha256Of(
		encodeText(record[0]),
		encodeText(record[1]),
		encodeText(record[2]),
		encodeText(canonicalAmount(record[3])),
	)
}

func leafDigest(digestOfRecord []byte) []byte {
	return sha256Of(leafPrefix, digestOfRecord)
}

func nodeDigest(left, right []byte) []byte {
	return sha256Of(nodePrefix, left, right)
}

func padded(level [][]byte) [][]byte {
	if len(level)%2 == 0 {
		return level
	}
	return append(append([][]byte(nil), level...), level[len(level)-1])
}

// batch computes everything it can be asked once, when it is built.
type batch struct {
	recordDigests [][]byte
	digest        []byte
	tree          [][][]byte
}

func newBatch(records [][]string) *batch {
	digests := make([][]byte, len(records))
	for index, record := range records {
		digests[index] = recordDigest(record)
	}
	return &batch{recordDigests: digests, digest: sha256Of(digests...)}
}

// levels is the Merkle tree from the leaves up; a level of odd length is padded when it is paired.
func (b *batch) levels() [][][]byte {
	if b.tree == nil {
		level := make([][]byte, len(b.recordDigests))
		for index, digest := range b.recordDigests {
			level[index] = leafDigest(digest)
		}
		b.tree = [][][]byte{level}
		for len(level) > 1 {
			pairs := padded(level)
			next := make([][]byte, 0, len(pairs)/2)
			for index := 0; index < len(pairs); index += 2 {
				next = append(next, nodeDigest(pairs[index], pairs[index+1]))
			}
			level = next
			b.tree = append(b.tree, level)
		}
	}
	return b.tree
}

func (b *batch) root() []byte {
	tree := b.levels()
	return tree[len(tree)-1][0]
}

func (b *batch) proof(recordIndex int) [][]string {
	steps := [][]string{}
	tree := b.levels()
	index := recordIndex
	for depth := 0; depth < len(tree)-1; depth++ {
		sibling := index ^ 1
		side := "R"
		if sibling < index {
			side = "L"
		}
		steps = append(steps, []string{side, hex.EncodeToString(padded(tree[depth])[sibling])})
		index /= 2
	}
	return steps
}

type chain struct {
	batchSize int
	pending   [][]string
	batches   []*batch
	digests   [][]byte
}

func (c *chain) add(record []string) {
	c.pending = append(c.pending, append([]string(nil), record...))
	if len(c.pending) == c.batchSize {
		sealed := newBatch(c.pending)
		c.pending = nil
		c.batches = append(c.batches, sealed)
		c.digests = append(c.digests, sha256Of(c.tip(), sealed.digest))
	}
}

func (c *chain) tip() []byte {
	if len(c.digests) == 0 {
		return genesis
	}
	return c.digests[len(c.digests)-1]
}

type Ledger struct {
	batches map[string]*batch
	chains  map[string]*chain
}

func NewLedger() *Ledger {
	return &Ledger{batches: map[string]*batch{}, chains: map[string]*chain{}}
}

// Level 1
func (l *Ledger) AddBatch(name string, records [][]string) {
	l.batches[name] = newBatch(records)
}

func (l *Ledger) BatchDigest(name string) string {
	return hex.EncodeToString(l.batches[name].digest)
}

func (l *Ledger) SameBatch(first, second string) bool {
	return bytes.Equal(l.batches[first].digest, l.batches[second].digest)
}

// Level 2
func (l *Ledger) NewChain(name string, batchSize int) {
	l.chains[name] = &chain{batchSize: batchSize}
}

func (l *Ledger) AddRecord(name string, record []string) {
	l.chains[name].add(record)
}

func (l *Ledger) SealedCount(name string) int {
	return len(l.chains[name].batches)
}

func (l *Ledger) ChainDigest(name string) string {
	return hex.EncodeToString(l.chains[name].tip())
}

func (l *Ledger) SameChain(first, second string) bool {
	return bytes.Equal(l.chains[first].tip(), l.chains[second].tip())
}

// Level 3

// CommonPrefix bisects the length: the prefix digests agree up to some length and never again.
func (l *Ledger) CommonPrefix(first, second string) int {
	left, right := l.chains[first].digests, l.chains[second].digests
	low, high := 0, min(len(left), len(right))
	for low < high {
		middle := (low + high + 1) / 2
		if bytes.Equal(left[middle-1], right[middle-1]) {
			low = middle
		} else {
			high = middle - 1
		}
	}
	return low
}

// Level 4
func (l *Ledger) MerkleRoot(name string, batchIndex int) string {
	return hex.EncodeToString(l.chains[name].batches[batchIndex].root())
}

func (l *Ledger) Proof(name string, batchIndex int, recordIndex int) [][]string {
	return l.chains[name].batches[batchIndex].proof(recordIndex)
}

func (l *Ledger) Verify(root string, record []string, proof [][]string) bool {
	current := leafDigest(recordDigest(record))
	for _, step := range proof {
		if len(step) != 2 || (step[0] != "L" && step[0] != "R") || !hexDigest.MatchString(step[1]) {
			return false
		}
		sibling, err := hex.DecodeString(step[1])
		if err != nil {
			return false
		}
		if step[0] == "L" {
			current = nodeDigest(sibling, current)
		} else {
			current = nodeDigest(current, sibling)
		}
	}
	return hex.EncodeToString(current) == root
}
