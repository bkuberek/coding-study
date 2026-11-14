package reconstruct_itinerary

import "slices"

const start = "JFK"

func findItinerary(tickets [][]string) []string {
	// Destinations per airport in increasing order, with a used flag per ticket.
	destinations := make(map[string][]string)
	for _, ticket := range tickets {
		destinations[ticket[0]] = append(destinations[ticket[0]], ticket[1])
	}
	used := make(map[string][]bool, len(destinations))
	for airport, targets := range destinations {
		slices.Sort(targets)
		used[airport] = make([]bool, len(targets))
	}
	route := []string{start}

	// extend tries to complete the route from airport; on failure it leaves the route unchanged.
	var extend func(airport string) bool
	extend = func(airport string) bool {
		if len(route) == len(tickets)+1 {
			return true
		}
		targets := destinations[airport]
		for i, target := range targets {
			if used[airport][i] {
				continue
			}
			// An identical ticket was just tried from this same position and failed.
			if i > 0 && target == targets[i-1] && !used[airport][i-1] {
				continue
			}
			used[airport][i] = true
			route = append(route, target)
			if extend(target) {
				return true
			}
			route = route[:len(route)-1]
			used[airport][i] = false
		}
		return false
	}

	extend(start)
	return route
}
