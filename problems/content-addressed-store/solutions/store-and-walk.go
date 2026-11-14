package content_addressed_store

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"sort"
	"strings"
)

const (
	fixedSize = 64
	window    = 16
	base      = 257
	modulus   = 1_000_000_007
	minChunk  = 32
	maxChunk  = 256
	divisor   = 64
)

var kinds = map[string]bool{"blob": true, "tree": true, "manifest": true}

// errDamaged reports a tree or a manifest that had to be opened and is missing or damaged.
var errDamaged = errors.New("missing or damaged")

type entry struct {
	kind    string
	address string
}

type change struct {
	path string
	op   string
}

func addressOf(data []byte) string {
	digest := sha256.Sum256(data)
	return hex.EncodeToString(digest[:])
}

func lines(data []byte) []string {
	if len(data) == 0 {
		return nil
	}
	return strings.Split(string(data[:len(data)-1]), "\n")
}

func fixedSizes(length int) []int {
	sizes := []int{}
	for start := 0; start < length; start += fixedSize {
		sizes = append(sizes, min(fixedSize, length-start))
	}
	return sizes
}

// cdcSizes cuts where a rolling hash of the last 16 bytes allows, rolled once per byte.
func cdcSizes(data []byte) []int {
	leavingWeight := int64(1)
	for i := 0; i < window-1; i++ {
		leavingWeight = leavingWeight * base % modulus
	}
	sizes := []int{}
	windowHash := int64(0)
	start := 0
	for index, b := range data {
		if index >= window {
			windowHash = (windowHash - int64(data[index-window])*leavingWeight%modulus + modulus) % modulus
		}
		windowHash = (windowHash*base + int64(b)) % modulus
		length := index - start + 1
		if length == maxChunk || (length >= minChunk && windowHash%divisor == 0) {
			sizes = append(sizes, length)
			start = index + 1
		}
	}
	if start < len(data) {
		sizes = append(sizes, len(data)-start)
	}
	return sizes
}

// ContentStore files bytes under the SHA-256 digest of those bytes. Every read hashes what it
// finds again, so a damaged object reads as a missing one. Folders and manifests are objects that
// list other objects by address, and refs name the objects the collector keeps.
type ContentStore struct {
	objects   map[string][]byte
	fileBytes map[string]int
	chunks    map[string]map[string]int
	refs      map[string]entry
}

func NewContentStore() *ContentStore {
	return &ContentStore{
		objects:   map[string][]byte{},
		fileBytes: map[string]int{"fixed": 0, "cdc": 0},
		chunks:    map[string]map[string]int{"fixed": {}, "cdc": {}},
		refs:      map[string]entry{},
	}
}

func (s *ContentStore) write(data []byte) string {
	address := addressOf(data)
	if _, ok := s.read(address); !ok {
		s.objects[address] = data
	}
	return address
}

func (s *ContentStore) read(address string) ([]byte, bool) {
	data, ok := s.objects[address]
	if !ok || addressOf(data) != address {
		return nil, false
	}
	return data, true
}

// Level 1
func (s *ContentStore) Put(data string) string {
	return s.write([]byte(data))
}

func (s *ContentStore) Get(address string) string {
	data, ok := s.read(address)
	if !ok {
		return ""
	}
	return string(data)
}

func (s *ContentStore) Check(address string) string {
	if _, ok := s.objects[address]; !ok {
		return "missing"
	}
	if _, ok := s.read(address); !ok {
		return "damaged"
	}
	return "ok"
}

func (s *ContentStore) Damage(address string, data string) bool {
	if _, ok := s.objects[address]; !ok {
		return false
	}
	s.objects[address] = []byte(data)
	return true
}

func (s *ContentStore) Count() int {
	return len(s.objects)
}

func (s *ContentStore) BytesStored() int {
	total := 0
	for _, data := range s.objects {
		total += len(data)
	}
	return total
}

// Level 2
type file struct {
	names []string
	data  string
}

func (s *ContentStore) Snapshot(files [][]string) string {
	split := make([]file, 0, len(files))
	for _, f := range files {
		split = append(split, file{strings.Split(f[0], "/"), f[1]})
	}
	return s.folder(split)
}

func (s *ContentStore) folder(files []file) string {
	entries := map[string]entry{}
	below := map[string][]file{}
	for _, f := range files {
		if len(f.names) == 1 {
			entries[f.names[0]] = entry{"blob", s.Put(f.data)}
		} else {
			below[f.names[0]] = append(below[f.names[0]], file{f.names[1:], f.data})
		}
	}
	for name, inner := range below {
		entries[name] = entry{"tree", s.folder(inner)}
	}
	names := make([]string, 0, len(entries))
	for name := range entries {
		names = append(names, name)
	}
	sort.Strings(names)
	var text strings.Builder
	for _, name := range names {
		text.WriteString(entries[name].kind + " " + entries[name].address + " " + name + "\n")
	}
	return s.Put(text.String())
}

func (s *ContentStore) openTree(address string) (map[string]entry, error) {
	data, ok := s.read(address)
	if !ok {
		return nil, errDamaged
	}
	entries := map[string]entry{}
	for _, line := range lines(data) {
		entries[line[70:]] = entry{line[:4], line[5:69]}
	}
	return entries, nil
}

func (s *ContentStore) ReadPath(root string, path string) string {
	current := entry{"tree", root}
	for _, name := range strings.Split(path, "/") {
		if current.kind != "tree" {
			return ""
		}
		entries, err := s.openTree(current.address)
		if err != nil {
			return ""
		}
		found, ok := entries[name]
		if !ok {
			return ""
		}
		current = found
	}
	if current.kind != "blob" {
		return ""
	}
	return s.Get(current.address)
}

func (s *ContentStore) Diff(oldRoot string, newRoot string) []string {
	var changes []change
	if err := s.compare("", oldRoot, newRoot, &changes); err != nil {
		return []string{}
	}
	sort.Slice(changes, func(i, j int) bool { return changes[i].path < changes[j].path })
	result := make([]string, 0, len(changes))
	for _, c := range changes {
		result = append(result, c.op+" "+c.path)
	}
	return result
}

func (s *ContentStore) compare(prefix, oldTree, newTree string, changes *[]change) error {
	if oldTree == newTree {
		return nil
	}
	before, err := s.openTree(oldTree)
	if err != nil {
		return err
	}
	after, err := s.openTree(newTree)
	if err != nil {
		return err
	}
	names := map[string]bool{}
	for name := range before {
		names[name] = true
	}
	for name := range after {
		names[name] = true
	}
	for name := range names {
		path := prefix + name
		was, inOld := before[name]
		now, inNew := after[name]
		switch {
		case inOld && inNew && was == now:
			continue
		case inOld && inNew && was.kind == now.kind && was.kind == "blob":
			*changes = append(*changes, change{path, "M"})
		case inOld && inNew && was.kind == now.kind:
			if err := s.compare(path+"/", was.address, now.address, changes); err != nil {
				return err
			}
		default:
			if inOld {
				if err := s.listFiles("D", path, was, changes); err != nil {
					return err
				}
			}
			if inNew {
				if err := s.listFiles("A", path, now, changes); err != nil {
					return err
				}
			}
		}
	}
	return nil
}

func (s *ContentStore) listFiles(op, path string, e entry, changes *[]change) error {
	if e.kind == "blob" {
		*changes = append(*changes, change{path, op})
		return nil
	}
	entries, err := s.openTree(e.address)
	if err != nil {
		return err
	}
	for name, inner := range entries {
		if err := s.listFiles(op, path+"/"+name, inner, changes); err != nil {
			return err
		}
	}
	return nil
}

// Level 3
func (s *ContentStore) ChunkSizes(data string, method string) []int {
	if method == "fixed" {
		return fixedSizes(len(data))
	}
	return cdcSizes([]byte(data))
}

func (s *ContentStore) PutFile(data string, method string) string {
	raw := []byte(data)
	seen := s.chunks[method]
	var manifest strings.Builder
	start := 0
	for _, size := range s.ChunkSizes(data, method) {
		chunk := make([]byte, size)
		copy(chunk, raw[start:start+size])
		address := s.write(chunk)
		seen[address] = size
		manifest.WriteString(address + "\n")
		start += size
	}
	s.fileBytes[method] += len(raw)
	return s.Put(manifest.String())
}

func (s *ContentStore) ReadFile(manifest string) string {
	listing, ok := s.read(manifest)
	if !ok {
		return ""
	}
	var parts strings.Builder
	for _, address := range lines(listing) {
		chunk, ok := s.read(address)
		if !ok {
			return ""
		}
		parts.Write(chunk)
	}
	return parts.String()
}

func (s *ContentStore) DedupRatio(method string) float64 {
	stored := 0
	for _, size := range s.chunks[method] {
		stored += size
	}
	if stored == 0 {
		return 0
	}
	return float64(s.fileBytes[method]) / float64(stored)
}

// Level 4
func (s *ContentStore) SetRef(name string, kind string, address string) bool {
	if _, ok := s.objects[address]; !ok || !kinds[kind] {
		return false
	}
	s.refs[name] = entry{kind, address}
	return true
}

func (s *ContentStore) GetRef(name string) string {
	return s.refs[name].address
}

func (s *ContentStore) DeleteRef(name string) bool {
	if _, ok := s.refs[name]; !ok {
		return false
	}
	delete(s.refs, name)
	return true
}

func (s *ContentStore) CollectGarbage() int {
	live, err := s.mark()
	if err != nil {
		return -1
	}
	freed := 0
	for address, data := range s.objects {
		if !live[address] {
			freed += len(data)
			delete(s.objects, address)
		}
	}
	return freed
}

func (s *ContentStore) mark() (map[string]bool, error) {
	live := map[string]bool{}
	visited := map[entry]bool{}
	pending := make([]entry, 0, len(s.refs))
	for _, ref := range s.refs {
		pending = append(pending, ref)
	}
	for len(pending) > 0 {
		e := pending[len(pending)-1]
		pending = pending[:len(pending)-1]
		if visited[e] {
			continue
		}
		visited[e] = true
		live[e.address] = true
		switch e.kind {
		case "tree":
			entries, err := s.openTree(e.address)
			if err != nil {
				return nil, err
			}
			for _, inner := range entries {
				pending = append(pending, inner)
			}
		case "manifest":
			listing, ok := s.read(e.address)
			if !ok {
				return nil, errDamaged
			}
			for _, address := range lines(listing) {
				pending = append(pending, entry{"blob", address})
			}
		}
	}
	return live, nil
}
