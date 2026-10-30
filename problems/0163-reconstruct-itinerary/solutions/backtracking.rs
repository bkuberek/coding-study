use std::collections::HashMap;

const START: &str = "JFK";

struct Search<'a> {
    /// Destinations per airport in increasing order, each with a used flag.
    destinations: HashMap<&'a str, Vec<(&'a str, bool)>>,
    route: Vec<&'a str>,
    ticket_count: usize,
}

impl<'a> Search<'a> {
    /// Tries to complete the route from `airport`; on failure the route is left unchanged.
    fn extend(&mut self, airport: &'a str) -> bool {
        if self.route.len() == self.ticket_count + 1 {
            return true;
        }
        let count = self.destinations.get(airport).map_or(0, Vec::len);
        for i in 0..count {
            let targets = &self.destinations[airport];
            let (target, used) = targets[i];
            if used {
                continue;
            }
            // An identical ticket was just tried from this same position and failed.
            if i > 0 && target == targets[i - 1].0 && !targets[i - 1].1 {
                continue;
            }
            self.set_used(airport, i, true);
            self.route.push(target);
            if self.extend(target) {
                return true;
            }
            self.route.pop();
            self.set_used(airport, i, false);
        }
        false
    }

    fn set_used(&mut self, airport: &str, index: usize, used: bool) {
        if let Some(targets) = self.destinations.get_mut(airport) {
            targets[index].1 = used;
        }
    }
}

pub fn find_itinerary(tickets: Vec<Vec<String>>) -> Vec<String> {
    let mut destinations: HashMap<&str, Vec<(&str, bool)>> = HashMap::new();
    for ticket in &tickets {
        destinations
            .entry(ticket[0].as_str())
            .or_default()
            .push((ticket[1].as_str(), false));
    }
    for targets in destinations.values_mut() {
        targets.sort_unstable();
    }
    let mut search = Search {
        destinations,
        route: vec![START],
        ticket_count: tickets.len(),
    };
    search.extend(START);
    search.route.into_iter().map(String::from).collect()
}
