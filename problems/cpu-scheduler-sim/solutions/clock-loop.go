package cpu_scheduler_sim

import (
	"fmt"
	"sort"
)

type segment struct {
	pid        string
	start, end int
}

// core is one CPU's record of a run: its segments, the last process it ran, its switches and
// the ticks it was busy.
type core struct {
	segments []segment
	last     string
	switches int
	busy     int
}

func (c *core) run(pid string, start, end int) {
	n := len(c.segments)
	if n > 0 && c.segments[n-1].pid == pid && c.segments[n-1].end == start {
		c.segments[n-1].end = end
	} else {
		if c.last != "" && c.last != pid {
			c.switches++
		}
		c.segments = append(c.segments, segment{pid, start, end})
	}
	c.last = pid
	c.busy += end - start
}

// run is the result of the latest run: when each process first ran and finished, and the cores.
type run struct {
	pids       []string
	first      map[string]int
	done       map[string]int
	cores      []*core
	migrations int
	makespan   int
}

func newRun(pids []string, cores int) *run {
	r := &run{
		pids:  append([]string{}, pids...),
		first: map[string]int{},
		done:  map[string]int{},
	}
	for c := 0; c < cores; c++ {
		r.cores = append(r.cores, &core{})
	}
	return r
}

func (r *run) started(pid string, time int) {
	if _, ok := r.first[pid]; !ok {
		r.first[pid] = time
	}
}

func (r *run) timelines() [][]string {
	lines := make([][]string, 0, len(r.cores))
	for _, c := range r.cores {
		line := make([]string, 0, len(c.segments))
		for _, s := range c.segments {
			line = append(line, fmt.Sprintf("%s:%d-%d", s.pid, s.start, s.end))
		}
		lines = append(lines, line)
	}
	return lines
}

func fraction(numerator, denominator int) string {
	a, b := numerator, denominator
	for b != 0 {
		a, b = b, a%b
	}
	return fmt.Sprintf("%d/%d", numerator/a, denominator/a)
}

// CpuScheduler holds a workload of processes and the result of the latest run over it.
//
// First come, first served and shortest job first run each process to completion, so they jump
// from one completion to the next. Round robin, the feedback queue and the cores advance a clock
// one tick at a time and settle each tick in the order the statement fixes: the slice that ends,
// the arrivals, the process that goes back to its queue, a boost, a preemption, a dispatch and
// then a steal. One core records its segments, merging a slice that continues the one before.
// Round robin is the case of one core without stealing.
type CpuScheduler struct {
	pids    []string
	arrival map[string]int
	burst   map[string]int
	latest  *run
}

func NewCpuScheduler() *CpuScheduler {
	return &CpuScheduler{arrival: map[string]int{}, burst: map[string]int{}}
}

// Level 1

func (s *CpuScheduler) AddProcess(pid string, arrival int, burst int) bool {
	if _, ok := s.arrival[pid]; ok {
		return false
	}
	s.pids = append(s.pids, pid)
	s.arrival[pid] = arrival
	s.burst[pid] = burst
	return true
}

func (s *CpuScheduler) RunFcfs() []string {
	r := newRun(s.pids, 1)
	clock := 0
	for _, pid := range s.byArrival() {
		clock = s.runToCompletion(r, pid, max(clock, s.arrival[pid]))
	}
	return s.keep(r, clock)[0]
}

func (s *CpuScheduler) RunSjf() []string {
	r := newRun(s.pids, 1)
	position := map[string]int{}
	for i, pid := range s.pids {
		position[pid] = i
	}
	less := func(a, b string) bool {
		if s.burst[a] != s.burst[b] {
			return s.burst[a] < s.burst[b]
		}
		if s.arrival[a] != s.arrival[b] {
			return s.arrival[a] < s.arrival[b]
		}
		return position[a] < position[b]
	}
	pending := append([]string{}, s.pids...)
	clock := 0
	for len(pending) > 0 {
		pick := -1
		next := -1
		for i, pid := range pending {
			if s.arrival[pid] <= clock && (pick == -1 || less(pid, pending[pick])) {
				pick = i
			}
			if next == -1 || s.arrival[pid] < next {
				next = s.arrival[pid]
			}
		}
		if pick == -1 {
			clock = next
			continue
		}
		pid := pending[pick]
		pending = append(pending[:pick], pending[pick+1:]...)
		clock = s.runToCompletion(r, pid, clock)
	}
	return s.keep(r, clock)[0]
}

func (s *CpuScheduler) WaitingTime(pid string) int {
	turnaround := s.TurnaroundTime(pid)
	if turnaround == -1 {
		return -1
	}
	return turnaround - s.burst[pid]
}

func (s *CpuScheduler) TurnaroundTime(pid string) int {
	if s.latest == nil {
		return -1
	}
	done, ok := s.latest.done[pid]
	if !ok {
		return -1
	}
	return done - s.arrival[pid]
}

func (s *CpuScheduler) AverageWaiting() string {
	return s.average(s.WaitingTime)
}

func (s *CpuScheduler) AverageTurnaround() string {
	return s.average(s.TurnaroundTime)
}

// Level 2

func (s *CpuScheduler) RunRoundRobin(quantum int) []string {
	return s.roundRobin(1, quantum, false)[0]
}

func (s *CpuScheduler) ResponseTime(pid string) int {
	if s.latest == nil {
		return -1
	}
	first, ok := s.latest.first[pid]
	if !ok {
		return -1
	}
	return first - s.arrival[pid]
}

func (s *CpuScheduler) AverageResponse() string {
	return s.average(s.ResponseTime)
}

func (s *CpuScheduler) ContextSwitches() int {
	if s.latest == nil {
		return -1
	}
	total := 0
	for _, c := range s.latest.cores {
		total += c.switches
	}
	return total
}

// Level 3

func (s *CpuScheduler) RunMlfq(quanta []int, boostPeriod int) []string {
	r := newRun(s.pids, 1)
	cpu := r.cores[0]
	remaining := map[string]int{}
	for pid, b := range s.burst {
		remaining[pid] = b
	}
	arrivals := s.byArrival()
	queues := make([][]string, len(quanta))
	level := map[string]int{}
	used := map[string]int{}
	running := ""
	left := len(s.pids)
	clock := 0
	for {
		demoted := ""
		if running != "" {
			if remaining[running] == 0 {
				r.done[running] = clock
				running = ""
				left--
			} else if used[running] == quanta[level[running]] {
				level[running] = min(level[running]+1, len(quanta)-1)
				used[running] = 0
				demoted, running = running, ""
			}
		}
		if left == 0 {
			break
		}
		for len(arrivals) > 0 && s.arrival[arrivals[0]] == clock {
			pid := arrivals[0]
			arrivals = arrivals[1:]
			level[pid], used[pid] = 0, 0
			queues[0] = append(queues[0], pid)
		}
		if demoted != "" {
			queues[level[demoted]] = append(queues[level[demoted]], demoted)
		}
		if boostPeriod > 0 && clock > 0 && clock%boostPeriod == 0 {
			var merged []string
			for i := range queues {
				merged = append(merged, queues[i]...)
				queues[i] = nil
			}
			queues[0] = merged
			lifted := append([]string{}, merged...)
			if running != "" {
				lifted = append(lifted, running)
			}
			for _, pid := range lifted {
				level[pid], used[pid] = 0, 0
			}
		}
		if running != "" {
			for i := 0; i < level[running]; i++ {
				if len(queues[i]) > 0 {
					queues[level[running]] = append(queues[level[running]], running)
					running = ""
					break
				}
			}
		}
		if running == "" {
			for i := range queues {
				if len(queues[i]) > 0 {
					running, queues[i] = queues[i][0], queues[i][1:]
					break
				}
			}
		}
		if running != "" {
			r.started(running, clock)
			cpu.run(running, clock, clock+1)
			remaining[running]--
			used[running]++
		}
		clock++
	}
	return s.keep(r, clock)[0]
}

// Level 4

func (s *CpuScheduler) RunMulticore(cores int, quantum int, steal bool) [][]string {
	return s.roundRobin(cores, quantum, steal)
}

func (s *CpuScheduler) Utilization(core int) string {
	if s.latest == nil || core < 0 || core >= len(s.latest.cores) {
		return ""
	}
	return fraction(s.latest.cores[core].busy, s.latest.makespan)
}

func (s *CpuScheduler) Migrations() int {
	if s.latest == nil {
		return -1
	}
	return s.latest.migrations
}

// The clock loops

func (s *CpuScheduler) roundRobin(cores int, quantum int, steal bool) [][]string {
	r := newRun(s.pids, cores)
	remaining := map[string]int{}
	for pid, b := range s.burst {
		remaining[pid] = b
	}
	arrivals := s.byArrival()
	queues := make([][]string, cores)
	running := make([]string, cores)
	used := make([]int, cores)
	left := len(s.pids)
	clock := 0
	for {
		expired := make([]string, cores)
		for c := 0; c < cores; c++ {
			pid := running[c]
			if pid != "" && remaining[pid] == 0 {
				r.done[pid] = clock
				running[c] = ""
				left--
			} else if pid != "" && used[c] == quantum {
				expired[c], running[c] = pid, ""
			}
		}
		if left == 0 {
			break
		}
		for len(arrivals) > 0 && s.arrival[arrivals[0]] == clock {
			target, lowest := 0, -1
			for c := 0; c < cores; c++ {
				load := len(queues[c])
				if running[c] != "" {
					load++
				}
				if expired[c] != "" {
					load++
				}
				if lowest == -1 || load < lowest {
					target, lowest = c, load
				}
			}
			queues[target] = append(queues[target], arrivals[0])
			arrivals = arrivals[1:]
		}
		for c := 0; c < cores; c++ {
			if expired[c] != "" {
				queues[c] = append(queues[c], expired[c])
			}
			if running[c] == "" && len(queues[c]) > 0 {
				running[c], queues[c] = queues[c][0], queues[c][1:]
				used[c] = 0
			}
		}
		for c := 0; steal && c < cores; c++ {
			if running[c] != "" {
				continue
			}
			victim := 0
			for v := 1; v < cores; v++ {
				if len(queues[v]) > len(queues[victim]) {
					victim = v
				}
			}
			if n := len(queues[victim]); n > 0 {
				running[c], queues[victim] = queues[victim][n-1], queues[victim][:n-1]
				used[c] = 0
				r.migrations++
			}
		}
		for c := 0; c < cores; c++ {
			pid := running[c]
			if pid == "" {
				continue
			}
			r.started(pid, clock)
			r.cores[c].run(pid, clock, clock+1)
			remaining[pid]--
			used[c]++
		}
		clock++
	}
	return s.keep(r, clock)
}

func (s *CpuScheduler) runToCompletion(r *run, pid string, start int) int {
	end := start + s.burst[pid]
	r.started(pid, start)
	r.cores[0].run(pid, start, end)
	r.done[pid] = end
	return end
}

func (s *CpuScheduler) byArrival() []string {
	order := append([]string{}, s.pids...)
	sort.SliceStable(order, func(i, j int) bool { return s.arrival[order[i]] < s.arrival[order[j]] })
	return order
}

func (s *CpuScheduler) keep(r *run, makespan int) [][]string {
	r.makespan = makespan
	s.latest = r
	return r.timelines()
}

func (s *CpuScheduler) average(metric func(string) int) string {
	if s.latest == nil {
		return ""
	}
	total := 0
	for _, pid := range s.latest.pids {
		total += metric(pid)
	}
	return fraction(total, len(s.latest.pids))
}
