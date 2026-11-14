use std::collections::HashMap;

struct Slo {
    good: String,
    total: String,
    met: i64,
    out_of: i64,
    window: i64,
}

impl Slo {
    fn spare(&self) -> i64 {
        self.out_of - self.met
    }
}

struct Alert {
    severity: String,
    long_window: i64,
    short_window: i64,
    above: i64,
    below: i64,
}

/// Every counter keeps its samples in time order. The increase over a window walks the samples
/// inside it and adds each step, counting a drop as a restart from zero. A histogram is one such
/// counter per bucket. SLOs, burn rates and alerts are ratios of increases, kept as exact
/// fractions and compared by cross-multiplying.
pub struct SloMonitor {
    times: HashMap<String, Vec<i64>>,
    values: HashMap<String, Vec<i64>>,
    bounds: HashMap<String, Vec<i64>>,
    slos: HashMap<String, Slo>,
    alerts: HashMap<String, Vec<Alert>>,
}

fn gcd(a: i64, b: i64) -> i64 {
    if b == 0 {
        a.abs()
    } else {
        gcd(b, a % b)
    }
}

/// `p/q` in lowest terms with q > 0, or `p` for a whole number.
fn fraction(numerator: i64, denominator: i64) -> String {
    let (numerator, denominator) = if denominator < 0 {
        (-numerator, -denominator)
    } else {
        (numerator, denominator)
    };
    let common = gcd(numerator, denominator);
    let (top, bottom) = (numerator / common, denominator / common);
    if bottom == 1 {
        top.to_string()
    } else {
        format!("{}/{}", top, bottom)
    }
}

fn parse_fraction(text: &str) -> (i64, i64) {
    match text.split_once('/') {
        Some((top, bottom)) => (top.parse().unwrap(), bottom.parse().unwrap()),
        None => (text.parse().unwrap(), 1),
    }
}

impl SloMonitor {
    pub fn new() -> Self {
        SloMonitor {
            times: HashMap::new(),
            values: HashMap::new(),
            bounds: HashMap::new(),
            slos: HashMap::new(),
            alerts: HashMap::new(),
        }
    }

    // Level 1
    pub fn scrape(&mut self, series: String, timestamp: i64, value: i64) -> String {
        let seen = self.times.entry(series.clone()).or_default();
        if seen.last().map_or(false, |&last| timestamp <= last) {
            return "out-of-order".to_string();
        }
        seen.push(timestamp);
        self.values.entry(series).or_default().push(value);
        "ok".to_string()
    }

    pub fn scrape_series(
        &mut self,
        series: String,
        start: i64,
        step: i64,
        values: Vec<i64>,
    ) -> i32 {
        let mut stored = 0;
        for (i, value) in values.into_iter().enumerate() {
            if self.scrape(series.clone(), start + i as i64 * step, value) == "ok" {
                stored += 1;
            }
        }
        stored
    }

    pub fn increase(&mut self, series: String, start: i64, end: i64) -> i64 {
        self.increase_of(&series, start, end)
    }

    pub fn rate(&mut self, series: String, start: i64, end: i64) -> String {
        let (times, _) = self.window(&series, start, end);
        if times.len() < 2 {
            return String::new();
        }
        let span = times[times.len() - 1] - times[0];
        fraction(self.increase_of(&series, start, end), span)
    }

    pub fn resets(&mut self, series: String, start: i64, end: i64) -> i32 {
        let (_, values) = self.window(&series, start, end);
        values.windows(2).filter(|pair| pair[1] < pair[0]).count() as i32
    }

    // Level 2
    pub fn scrape_histogram(
        &mut self,
        name: String,
        timestamp: i64,
        bounds: Vec<i64>,
        counts: Vec<i64>,
    ) -> String {
        let total = format!("{}:le=inf", name);
        if let Some(&last) = self.times.get(&total).and_then(|seen| seen.last()) {
            if timestamp <= last {
                return "out-of-order".to_string();
            }
        }
        for (bound, &count) in bounds.iter().zip(counts.iter()) {
            self.scrape(format!("{}:le={}", name, bound), timestamp, count);
        }
        self.scrape(total, timestamp, counts[bounds.len()]);
        self.bounds.insert(name, bounds);
        "ok".to_string()
    }

    pub fn fraction_within(
        &mut self,
        name: String,
        threshold: i64,
        start: i64,
        end: i64,
    ) -> String {
        let counts = match self.buckets(&name, start, end) {
            Some(counts) => counts,
            None => return String::new(),
        };
        match self.bounds[&name]
            .iter()
            .position(|&bound| bound == threshold)
        {
            Some(index) => fraction(counts[index], counts[counts.len() - 1]),
            None => String::new(),
        }
    }

    pub fn quantile(&mut self, name: String, q: String, start: i64, end: i64) -> String {
        let counts = match self.buckets(&name, start, end) {
            Some(counts) => counts,
            None => return String::new(),
        };
        let (top, bottom) = parse_fraction(&q);
        let limits = &self.bounds[&name];
        let total = counts[counts.len() - 1];
        // The rank is q * total; the first bucket whose count reaches it holds the quantile.
        let index = counts
            .iter()
            .position(|&count| count * bottom >= top * total)
            .unwrap();
        if index == limits.len() {
            return limits[limits.len() - 1].to_string();
        }
        let (lower, before) = if index > 0 {
            (limits[index - 1], counts[index - 1])
        } else {
            (0, 0)
        };
        let inside = counts[index] - before;
        let numerator =
            lower * bottom * inside + (limits[index] - lower) * (top * total - bottom * before);
        fraction(numerator, bottom * inside)
    }

    // Level 3
    pub fn define_slo(
        &mut self,
        name: String,
        good_series: String,
        total_series: String,
        objective: String,
        window: i64,
    ) -> String {
        if self.slos.contains_key(&name) {
            return "duplicate".to_string();
        }
        let (met, out_of) = parse_fraction(&objective);
        if met <= 0 || met >= out_of {
            return "bad-objective".to_string();
        }
        self.alerts.insert(name.clone(), Vec::new());
        self.slos.insert(
            name,
            Slo {
                good: good_series,
                total: total_series,
                met,
                out_of,
                window,
            },
        );
        "ok".to_string()
    }

    pub fn sli(&mut self, name: String, at: i64) -> String {
        let slo = match self.slos.get(&name) {
            Some(slo) => slo,
            None => return String::new(),
        };
        match self.counts(slo, at, slo.window) {
            Some((bad, total)) => fraction(total - bad, total),
            None => String::new(),
        }
    }

    pub fn budget_remaining(&mut self, name: String, at: i64) -> String {
        match self.slos.get(&name).and_then(|slo| self.left(slo, at)) {
            Some((numerator, denominator)) => fraction(numerator, denominator),
            None => String::new(),
        }
    }

    pub fn burn_rate(&mut self, name: String, at: i64, lookback: i64) -> String {
        let slo = match self.slos.get(&name) {
            Some(slo) => slo,
            None => return String::new(),
        };
        match self.counts(slo, at, lookback) {
            Some((bad, total)) => fraction(bad * slo.out_of, total * slo.spare()),
            None => String::new(),
        }
    }

    pub fn time_to_exhaustion(&mut self, name: String, at: i64, lookback: i64) -> i64 {
        let slo = match self.slos.get(&name) {
            Some(slo) => slo,
            None => return -1,
        };
        let left_over = match self.left(slo, at) {
            Some((numerator, _)) => numerator,
            None => return -1,
        };
        if left_over <= 0 {
            return 0;
        }
        let (recent_bad, recent_total) = match self.counts(slo, at, lookback) {
            Some((bad, total)) if bad > 0 => (bad, total),
            _ => return -1,
        };
        let (bad, total) = self.counts(slo, at, slo.window).unwrap();
        // remaining * window / burn rate, with every product below 2^63.
        let numerator = slo.window * (total * slo.spare() - bad * slo.out_of) * recent_total;
        numerator / (total * recent_bad * slo.out_of)
    }

    // Level 4
    pub fn add_alert(
        &mut self,
        slo: String,
        severity: String,
        long_window: i64,
        short_window: i64,
        threshold: String,
    ) -> String {
        let list = match self.alerts.get_mut(&slo) {
            Some(list) => list,
            None => return "unknown-slo".to_string(),
        };
        if list.iter().any(|alert| alert.severity == severity) {
            return "duplicate".to_string();
        }
        if long_window <= 0 || short_window < 0 || short_window >= long_window {
            return "bad-windows".to_string();
        }
        let (above, below) = parse_fraction(&threshold);
        list.push(Alert {
            severity,
            long_window,
            short_window,
            above,
            below,
        });
        "ok".to_string()
    }

    pub fn firing(&mut self, slo: String, at: i64) -> Vec<String> {
        let target = match self.slos.get(&slo) {
            Some(target) => target,
            None => return Vec::new(),
        };
        self.alerts[&slo]
            .iter()
            .filter(|alert| self.fires(target, alert, at))
            .map(|alert| alert.severity.clone())
            .collect()
    }

    pub fn timeline(&mut self, slo: String, start: i64, end: i64, step: i64) -> Vec<String> {
        let target = match self.slos.get(&slo) {
            Some(target) => target,
            None => return Vec::new(),
        };
        let list = &self.alerts[&slo];
        let mut state = vec![false; list.len()];
        let mut events = Vec::new();
        let mut at = start;
        while at <= end {
            for (i, alert) in list.iter().enumerate() {
                let now = self.fires(target, alert, at);
                if now != state[i] {
                    let word = if now { "start" } else { "stop" };
                    events.push(format!("{} {} {}", at, alert.severity, word));
                    state[i] = now;
                }
            }
            at += step;
        }
        events
    }

    // Helpers
    /// The times and values of the series inside [start, end].
    fn window(&self, series: &str, start: i64, end: i64) -> (&[i64], &[i64]) {
        let (times, values) = match (self.times.get(series), self.values.get(series)) {
            (Some(times), Some(values)) => (times, values),
            _ => return (&[], &[]),
        };
        let low = times.partition_point(|&t| t < start);
        let high = times.partition_point(|&t| t <= end).max(low);
        (&times[low..high], &values[low..high])
    }

    fn increase_of(&self, series: &str, start: i64, end: i64) -> i64 {
        let (_, values) = self.window(series, start, end);
        if values.len() < 2 {
            return -1;
        }
        values
            .windows(2)
            .map(|pair| {
                if pair[1] >= pair[0] {
                    pair[1] - pair[0]
                } else {
                    pair[1]
                }
            })
            .sum()
    }

    /// The increase of every bucket over the window, or `None` when the window has no requests.
    fn buckets(&self, name: &str, start: i64, end: i64) -> Option<Vec<i64>> {
        let limits = self.bounds.get(name)?;
        let mut counts: Vec<i64> = limits
            .iter()
            .map(|bound| self.increase_of(&format!("{}:le={}", name, bound), start, end))
            .collect();
        counts.push(self.increase_of(&format!("{}:le=inf", name), start, end));
        if counts[counts.len() - 1] > 0 {
            Some(counts)
        } else {
            None
        }
    }

    /// (bad, total) over [at - span, at], or `None` without requests.
    fn counts(&self, slo: &Slo, at: i64, span: i64) -> Option<(i64, i64)> {
        let total = self.increase_of(&slo.total, at - span, at);
        let good = self.increase_of(&slo.good, at - span, at);
        if total <= 0 || good < 0 {
            None
        } else {
            Some((total - good, total))
        }
    }

    /// The share of the budget left, as (numerator, denominator).
    fn left(&self, slo: &Slo, at: i64) -> Option<(i64, i64)> {
        let (bad, total) = self.counts(slo, at, slo.window)?;
        Some((total * slo.spare() - bad * slo.out_of, total * slo.spare()))
    }

    fn burns_above(&self, slo: &Slo, at: i64, span: i64, alert: &Alert) -> bool {
        match self.counts(slo, at, span) {
            Some((bad, total)) => {
                bad * slo.out_of * alert.below > alert.above * total * slo.spare()
            }
            None => false,
        }
    }

    fn fires(&self, slo: &Slo, alert: &Alert, at: i64) -> bool {
        self.burns_above(slo, at, alert.long_window, alert)
            && (alert.short_window == 0 || self.burns_above(slo, at, alert.short_window, alert))
    }
}
