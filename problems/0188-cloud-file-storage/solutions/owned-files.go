package cloud_file_storage

import (
	"sort"
	"strconv"
	"strings"
)

type file struct {
	name  string
	size  int64
	owner string // empty for a file that belongs to no user
}

type user struct {
	capacity int64
	used     int64
	files    map[string]struct{}
}

func (u *user) fits(size int64) bool {
	return u.used+size <= u.capacity
}

func sortLargestFirst(files []file) {
	sort.Slice(files, func(i, j int) bool {
		if files[i].size != files[j].size {
			return files[i].size > files[j].size
		}
		return files[i].name < files[j].name
	})
}

type CloudStorage struct {
	files   map[string]file
	users   map[string]*user
	backups map[string][]file
}

func NewCloudStorage() *CloudStorage {
	return &CloudStorage{
		files:   make(map[string]file),
		users:   make(map[string]*user),
		backups: make(map[string][]file),
	}
}

// Level 1
func (s *CloudStorage) AddFile(timestamp int64, name string, size int64) bool {
	if _, exists := s.files[name]; exists {
		return false
	}
	s.store(file{name: name, size: size})
	return true
}

// Level 1
func (s *CloudStorage) GetFileSize(timestamp int64, name string) int64 {
	f, ok := s.files[name]
	if !ok {
		return -1
	}
	return f.size
}

// Level 1
func (s *CloudStorage) DeleteFile(timestamp int64, name string) int64 {
	f, ok := s.files[name]
	if !ok {
		return -1
	}
	s.discard(f)
	return f.size
}

// Level 2
func (s *CloudStorage) ListLargest(timestamp int64, prefix string, limit int) []string {
	var matching []file
	for name, f := range s.files {
		if strings.HasPrefix(name, prefix) {
			matching = append(matching, f)
		}
	}
	sortLargestFirst(matching)
	if len(matching) > limit {
		matching = matching[:limit]
	}
	lines := make([]string, len(matching))
	for i, f := range matching {
		lines[i] = f.name + "(" + strconv.FormatInt(f.size, 10) + ")"
	}
	return lines
}

// Level 3
func (s *CloudStorage) AddUser(timestamp int64, userId string, capacity int64) bool {
	if _, exists := s.users[userId]; exists {
		return false
	}
	s.users[userId] = &user{capacity: capacity, files: make(map[string]struct{})}
	return true
}

// Level 3
func (s *CloudStorage) AddFileBy(timestamp int64, userId string, name string, size int64) int64 {
	u, ok := s.users[userId]
	if !ok {
		return -1
	}
	if _, exists := s.files[name]; exists || !u.fits(size) {
		return -1
	}
	s.store(file{name: name, size: size, owner: userId})
	return u.capacity - u.used
}

// Level 3
func (s *CloudStorage) UpdateCapacity(timestamp int64, userId string, capacity int64) int {
	u, ok := s.users[userId]
	if !ok {
		return -1
	}
	u.capacity = capacity
	owned := s.ownedBy(u)
	sortLargestFirst(owned)
	removed := 0
	for _, f := range owned {
		if u.used <= capacity {
			break
		}
		s.discard(f)
		removed++
	}
	return removed
}

// Level 4
func (s *CloudStorage) BackupUser(timestamp int64, userId string) int {
	u, ok := s.users[userId]
	if !ok {
		return -1
	}
	s.backups[userId] = s.ownedBy(u)
	return len(s.backups[userId])
}

// Level 4
func (s *CloudStorage) RestoreUser(timestamp int64, userId string) int {
	u, ok := s.users[userId]
	if !ok {
		return -1
	}
	for _, f := range s.ownedBy(u) {
		s.discard(f)
	}
	saved := append([]file(nil), s.backups[userId]...)
	sort.Slice(saved, func(i, j int) bool { return saved[i].name < saved[j].name })
	restored := 0
	for _, f := range saved {
		if _, exists := s.files[f.name]; !exists && u.fits(f.size) {
			s.store(f)
			restored++
		}
	}
	return restored
}

func (s *CloudStorage) ownedBy(u *user) []file {
	owned := make([]file, 0, len(u.files))
	for name := range u.files {
		owned = append(owned, s.files[name])
	}
	return owned
}

func (s *CloudStorage) store(f file) {
	s.files[f.name] = f
	if f.owner != "" {
		u := s.users[f.owner]
		u.used += f.size
		u.files[f.name] = struct{}{}
	}
}

func (s *CloudStorage) discard(f file) {
	delete(s.files, f.name)
	if f.owner != "" {
		u := s.users[f.owner]
		u.used -= f.size
		delete(u.files, f.name)
	}
}
