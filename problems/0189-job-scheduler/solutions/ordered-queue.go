package job_scheduler

import (
	"slices"
	"sort"
)

const (
	queued    = "QUEUED"
	running   = "RUNNING"
	done      = "DONE"
	failed    = "FAILED"
	cancelled = "CANCELLED"
)

type job struct {
	id         string
	tenant     string
	priority   int
	sequence   int
	dependsOn  []string
	status     string
	notBefore  int64
	failures   int
	dependents []string
}

// before reports whether a goes ahead of b in the queue: higher priority first, then earlier
// submission.
func before(a, b *job) bool {
	if a.priority != b.priority {
		return a.priority > b.priority
	}
	return a.sequence < b.sequence
}

type rateLimit struct {
	limit  int
	window int64
}

type retryPolicy struct {
	maxRetries  int
	baseDelayMs int64
}

// delayAfter is the wait before the next start; ok is false when no retry is left.
func (p retryPolicy) delayAfter(failures int) (delay int64, ok bool) {
	if failures > p.maxRetries {
		return 0, false
	}
	return p.baseDelayMs << (failures - 1), true
}

type JobScheduler struct {
	jobs     map[string]*job
	queue    []*job             // every QUEUED job, sorted by before
	starts   map[string][]int64 // tenant -> start times, ascending
	limits   map[string]rateLimit
	policies map[string]retryPolicy
}

func NewJobScheduler() *JobScheduler {
	return &JobScheduler{
		jobs:     make(map[string]*job),
		starts:   make(map[string][]int64),
		limits:   make(map[string]rateLimit),
		policies: make(map[string]retryPolicy),
	}
}

// Level 1
func (s *JobScheduler) Submit(timestamp int64, jobId string, tenant string, priority int) bool {
	return s.SubmitAfter(timestamp, jobId, tenant, priority, nil)
}

// Level 1
func (s *JobScheduler) RunNext(timestamp int64) string {
	for _, j := range s.queue {
		if s.canStart(j, timestamp) {
			s.unqueue(j)
			j.status = running
			s.starts[j.tenant] = append(s.starts[j.tenant], timestamp)
			return j.id
		}
	}
	return ""
}

// Level 1
func (s *JobScheduler) Status(timestamp int64, jobId string) string {
	if j, ok := s.jobs[jobId]; ok {
		return j.status
	}
	return ""
}

// Level 1
func (s *JobScheduler) Queued(timestamp int64) int {
	return len(s.queue)
}

// Level 2
func (s *JobScheduler) SetRateLimit(timestamp int64, tenant string, limit int, windowMs int64) {
	s.limits[tenant] = rateLimit{limit, windowMs}
}

// Level 3
func (s *JobScheduler) SetRetryPolicy(timestamp int64, tenant string, maxRetries int, baseDelayMs int64) {
	s.policies[tenant] = retryPolicy{maxRetries, baseDelayMs}
}

// Level 3
func (s *JobScheduler) Complete(timestamp int64, jobId string) bool {
	j, ok := s.jobs[jobId]
	if !ok || j.status != running {
		return false
	}
	j.status = done
	return true
}

// Level 3
func (s *JobScheduler) Fail(timestamp int64, jobId string) int64 {
	j, ok := s.jobs[jobId]
	if !ok || j.status != running {
		return -1
	}
	j.failures++
	delay, retry := s.policies[j.tenant].delayAfter(j.failures)
	if !retry {
		j.status = failed
		s.cancelDependents(j)
		return 0
	}
	j.notBefore = timestamp + delay
	s.enqueue(j)
	return j.notBefore
}

// Level 4
func (s *JobScheduler) SubmitAfter(timestamp int64, jobId string, tenant string, priority int, dependsOn []string) bool {
	if _, exists := s.jobs[jobId]; exists {
		return false
	}
	for _, dependency := range dependsOn {
		found, ok := s.jobs[dependency]
		if !ok || found.status == failed || found.status == cancelled {
			return false
		}
	}
	j := &job{
		id:        jobId,
		tenant:    tenant,
		priority:  priority,
		sequence:  len(s.jobs),
		dependsOn: slices.Clone(dependsOn),
	}
	s.jobs[jobId] = j
	for _, dependency := range dependsOn {
		s.jobs[dependency].dependents = append(s.jobs[dependency].dependents, jobId)
	}
	s.enqueue(j)
	return true
}

// Level 4
func (s *JobScheduler) Cancel(timestamp int64, jobId string) int {
	j, ok := s.jobs[jobId]
	if !ok || j.status != queued {
		return 0
	}
	s.unqueue(j)
	j.status = cancelled
	return 1 + s.cancelDependents(j)
}

func (s *JobScheduler) canStart(j *job, timestamp int64) bool {
	if j.notBefore > timestamp {
		return false
	}
	for _, dependency := range j.dependsOn {
		if s.jobs[dependency].status != done {
			return false
		}
	}
	return s.withinLimit(j.tenant, timestamp)
}

func (s *JobScheduler) withinLimit(tenant string, timestamp int64) bool {
	limit, ok := s.limits[tenant]
	if !ok {
		return true
	}
	starts := s.starts[tenant]
	windowStart := timestamp - limit.window
	inWindow := len(starts) - sort.Search(len(starts), func(i int) bool { return starts[i] > windowStart })
	return inWindow < limit.limit
}

// cancelDependents cancels every queued job that waits, directly or not, on j and returns how many.
func (s *JobScheduler) cancelDependents(j *job) int {
	count := 0
	pending := slices.Clone(j.dependents)
	for len(pending) > 0 {
		dependent := s.jobs[pending[len(pending)-1]]
		pending = pending[:len(pending)-1]
		if dependent.status == queued {
			s.unqueue(dependent)
			dependent.status = cancelled
			count++
			pending = append(pending, dependent.dependents...)
		}
	}
	return count
}

func (s *JobScheduler) enqueue(j *job) {
	j.status = queued
	position := sort.Search(len(s.queue), func(i int) bool { return before(j, s.queue[i]) })
	s.queue = slices.Insert(s.queue, position, j)
}

func (s *JobScheduler) unqueue(j *job) {
	position := sort.Search(len(s.queue), func(i int) bool { return before(j, s.queue[i]) })
	s.queue = slices.Delete(s.queue, position-1, position)
}
