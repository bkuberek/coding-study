package level_store

import (
	"sort"
	"strings"
)

type LevelStore struct {
	values map[string]string
}

func NewLevelStore() *LevelStore {
	return &LevelStore{values: map[string]string{}}
}

func (s *LevelStore) Put(key string, value string) {
	s.values[key] = value
}

func (s *LevelStore) Get(key string) string {
	return s.values[key]
}

func (s *LevelStore) Remove(key string) bool {
	_, found := s.values[key]
	delete(s.values, key)
	return found
}

func (s *LevelStore) Size() int {
	return len(s.values)
}

func (s *LevelStore) KeysWithPrefix(prefix string) []string {
	keys := []string{}
	for key := range s.values {
		if strings.HasPrefix(key, prefix) {
			keys = append(keys, key)
		}
	}
	sort.Strings(keys)
	return keys
}
