use std::collections::{BTreeMap, HashMap, HashSet};

const ROOT: &str = ".";
const MAX_CHAIN: usize = 8;
const NXDOMAIN_KEY: &str = "*";

type Rows = Vec<Vec<String>>;
type Key = (String, String);

struct RecordSet {
    ttl: i32,
    values: Vec<String>,
}

struct Entry {
    expiry: i64,
    values: Vec<String>,
}

/// What asking one address led to: a final response or a zone to descend to.
enum Step {
    Final(Rows),
    Child(String),
}

fn key(name: &str, rtype: &str) -> Key {
    (name.to_string(), rtype.to_string())
}

fn row(cells: &[&str]) -> Vec<String> {
    cells.iter().map(|cell| cell.to_string()).collect()
}

fn ancestors(name: &str) -> Vec<String> {
    if name == ROOT {
        return vec![ROOT.to_string()];
    }
    let labels: Vec<&str> = name.split('.').collect();
    let mut result: Vec<String> = (0..labels.len()).map(|i| labels[i..].join(".")).collect();
    result.push(ROOT.to_string());
    result
}

fn within(name: &str, zone: &str) -> bool {
    zone == ROOT || name == zone || name.ends_with(&format!(".{}", zone))
}

fn answer_rows(response: &Rows) -> Rows {
    response[1..].iter().filter(|row| row[0] == "answer").cloned().collect()
}

fn alias_of(response: &Rows, qtype: &str) -> Option<Vec<String>> {
    let answers = answer_rows(response);
    if qtype != "CNAME" && answers.len() == 1 && answers[0][2] == "CNAME" {
        Some(answers[0].clone())
    } else {
        None
    }
}

fn section(records: &HashMap<Key, RecordSet>, name: &str, owner: &str, rtype: &str) -> Rows {
    let set = &records[&key(owner, rtype)];
    let ttl = set.ttl.to_string();
    set.values.iter().map(|value| row(&[name, owner, rtype, ttl.as_str(), value.as_str()])).collect()
}

fn referral(records: &HashMap<Key, RecordSet>, cut: &str) -> Rows {
    let mut result = vec![row(&["NOERROR"])];
    result.extend(section(records, "authority", cut, "NS"));
    let mut additional = Vec::new();
    for target in &records[&key(cut, "NS")].values {
        for rtype in ["A", "AAAA"] {
            if records.contains_key(&key(target, rtype)) {
                additional.extend(section(records, "additional", target, rtype));
            }
        }
    }
    additional.sort_by(|a, b| (&a[1], &a[2], &a[4]).cmp(&(&b[1], &b[2], &b[4])));
    result.extend(additional);
    result
}

fn referral_zone(response: &Rows) -> Option<String> {
    if !answer_rows(response).is_empty() {
        return None;
    }
    response[1..].iter().find(|row| row[0] == "authority" && row[2] == "NS").map(|row| row[1].clone())
}

/// Servers answer from their own records the way an authoritative server does: an answer, a
/// referral to a delegated child zone, or a negative answer with the zone's SOA. The resolver
/// walks from the closest zone whose servers it knows (the root at first) down the referrals,
/// and keeps three caches: answers, which it may return; referral data (NS sets and glue), which
/// it only uses to find servers; and negative answers. Every entry expires on the virtual clock.
pub struct DnsResolver {
    servers: HashMap<String, HashMap<Key, RecordSet>>,
    hints: BTreeMap<String, Vec<String>>,
    answers: HashMap<Key, Entry>,
    referrals: HashMap<String, Entry>,
    glue: HashMap<Key, Entry>,
    negative: HashMap<Key, i64>,
    queries: Rows,
    now: i64,
}

impl DnsResolver {
    pub fn new() -> Self {
        DnsResolver {
            servers: HashMap::new(),
            hints: BTreeMap::new(),
            answers: HashMap::new(),
            referrals: HashMap::new(),
            glue: HashMap::new(),
            negative: HashMap::new(),
            queries: Vec::new(),
            now: 0,
        }
    }

    // Level 1
    pub fn add_record(&mut self, server: String, name: String, rtype: String, ttl: i32, data: String) {
        let records = self.servers.entry(server).or_default();
        let value = if ["CNAME", "NS", "MX", "SOA"].contains(&rtype.as_str()) {
            data.to_lowercase()
        } else {
            data
        };
        let set = records
            .entry((name.to_lowercase(), rtype))
            .or_insert_with(|| RecordSet { ttl, values: Vec::new() });
        set.ttl = ttl;
        if !set.values.contains(&value) {
            set.values.push(value);
            set.values.sort();
        }
    }

    pub fn lookup(&mut self, server: String, name: String, qtype: String) -> Vec<Vec<String>> {
        self.answer(&server, &name.to_lowercase(), &qtype)
    }

    // Level 2
    pub fn follow(&mut self, server: String, name: String, qtype: String) -> Vec<Vec<String>> {
        let mut current = name.to_lowercase();
        let mut visited: HashSet<String> = HashSet::from([current.clone()]);
        let mut chain: Rows = Vec::new();
        loop {
            let response = self.answer(&server, &current, &qtype);
            if response[0][0] == "REFUSED" {
                if chain.is_empty() {
                    return response;
                }
                return [vec![row(&["NOERROR"])], chain].concat();
            }
            let alias = match alias_of(&response, &qtype) {
                Some(alias) => alias,
                None => return [vec![response[0].clone()], chain, response[1..].to_vec()].concat(),
            };
            current = alias[4].clone();
            chain.push(alias);
            if !visited.insert(current.clone()) || chain.len() > MAX_CHAIN {
                return [vec![row(&["SERVFAIL"])], chain].concat();
            }
        }
    }

    // Level 3
    pub fn add_root_hint(&mut self, name: String, address: String) {
        let addresses = self.hints.entry(name.to_lowercase()).or_default();
        if !addresses.contains(&address) {
            addresses.push(address);
            addresses.sort();
        }
    }

    pub fn resolve(&mut self, name: String, qtype: String, now: i64) -> Vec<Vec<String>> {
        self.now = now;
        self.queries = Vec::new();
        let (code, rows) = self.resolve_name(&name.to_lowercase(), &qtype, &HashSet::new());
        [vec![row(&[code.as_str()])], rows].concat()
    }

    pub fn trace(&mut self) -> Vec<Vec<String>> {
        self.queries.clone()
    }

    // Level 4
    pub fn negatives(&mut self, now: i64) -> Vec<Vec<String>> {
        let mut rows: Rows = self
            .negative
            .iter()
            .filter(|(_, expiry)| now < **expiry)
            .map(|((name, rtype), expiry)| {
                let ttl = (expiry - now).to_string();
                row(&[name.as_str(), rtype.as_str(), ttl.as_str()])
            })
            .collect();
        rows.sort_by(|a, b| (&a[0], &a[1]).cmp(&(&b[0], &b[1])));
        rows
    }

    // Server side
    fn answer(&self, server: &str, name: &str, qtype: &str) -> Rows {
        let empty = HashMap::new();
        let records = self.servers.get(server).unwrap_or(&empty);
        let zone = records
            .keys()
            .filter(|(owner, rtype)| rtype == "SOA" && within(name, owner))
            .map(|(owner, _)| owner.clone())
            .max_by_key(|owner| ancestors(owner).len());
        let zone = match zone {
            Some(zone) => zone,
            None => return vec![row(&["REFUSED"])],
        };
        for node in ancestors(name).iter().rev() {
            if *node != zone && within(node, &zone) && records.contains_key(&key(node, "NS")) {
                return referral(records, node);
            }
        }
        if records.contains_key(&key(name, qtype)) {
            return [vec![row(&["NOERROR"])], section(records, "answer", name, qtype)].concat();
        }
        if qtype != "CNAME" && records.contains_key(&key(name, "CNAME")) {
            return [vec![row(&["NOERROR"])], section(records, "answer", name, "CNAME")].concat();
        }
        let soa = &records[&key(&zone, "SOA")];
        let minimum: i32 = soa.values[0].split(' ').nth(6).and_then(|field| field.parse().ok()).unwrap_or(0);
        let ttl = soa.ttl.min(minimum).to_string();
        let exists = records.keys().any(|(owner, _)| within(owner, name));
        let code = if exists { "NOERROR" } else { "NXDOMAIN" };
        vec![row(&[code]), row(&["authority", zone.as_str(), "SOA", ttl.as_str(), soa.values[0].as_str()])]
    }

    // Resolver side
    fn valid<'a>(&self, entry: Option<&'a Entry>) -> Option<&'a Vec<String>> {
        entry.filter(|entry| self.now < entry.expiry).map(|entry| &entry.values)
    }

    fn cached(&self, name: &str, rtype: &str) -> Option<Rows> {
        let entry = self.answers.get(&key(name, rtype))?;
        if self.now >= entry.expiry {
            return None;
        }
        let ttl = (entry.expiry - self.now).to_string();
        Some(entry.values.iter().map(|value| row(&["answer", name, rtype, ttl.as_str(), value.as_str()])).collect())
    }

    fn resolve_name(&mut self, qname: &str, qtype: &str, pending: &HashSet<String>) -> (String, Rows) {
        let mut chain: Rows = Vec::new();
        let mut visited: HashSet<String> = HashSet::from([qname.to_string()]);
        let mut current = qname.to_string();
        loop {
            if let Some(found) = self.cached(&current, qtype) {
                chain.extend(found);
                return ("NOERROR".to_string(), chain);
            }
            let mut alias = if qtype != "CNAME" {
                self.cached(&current, "CNAME").map(|rows| rows[0].clone())
            } else {
                None
            };
            if alias.is_none() {
                if let Some(code) = self.negative_answer(&current, qtype) {
                    return (code.to_string(), chain);
                }
                let response = match self.ask(&current, qtype, pending) {
                    Some(response) => response,
                    None => return ("SERVFAIL".to_string(), chain),
                };
                alias = self.absorb(&response, &current, qtype);
                if alias.is_none() {
                    chain.extend(answer_rows(&response));
                    return (response[0][0].clone(), chain);
                }
            }
            let alias = alias.unwrap_or_default();
            current = alias[4].clone();
            chain.push(alias);
            if !visited.insert(current.clone()) || chain.len() > MAX_CHAIN {
                return ("SERVFAIL".to_string(), chain);
            }
        }
    }

    /// Caches a final response and returns its CNAME when it is an alias.
    fn absorb(&mut self, response: &Rows, qname: &str, qtype: &str) -> Option<Vec<String>> {
        let found = answer_rows(response);
        if !found.is_empty() {
            let ttl: i64 = found[0][3].parse().unwrap_or(0);
            let values = found.iter().map(|row| row[4].clone()).collect();
            self.answers.insert(key(qname, &found[0][2]), Entry { expiry: self.now + ttl, values });
            return alias_of(response, qtype);
        }
        if let Some(soa) = response[1..].iter().find(|row| row[2] == "SOA") {
            let ttl: i64 = soa[3].parse().unwrap_or(0);
            let rtype = if response[0][0] == "NXDOMAIN" { NXDOMAIN_KEY } else { qtype };
            self.negative.insert(key(qname, rtype), self.now + ttl);
        }
        None
    }

    fn negative_answer(&self, name: &str, qtype: &str) -> Option<&'static str> {
        let fresh = |rtype: &str| self.negative.get(&key(name, rtype)).map_or(false, |expiry| self.now < *expiry);
        if fresh(NXDOMAIN_KEY) {
            Some("NXDOMAIN")
        } else if fresh(qtype) {
            Some("NOERROR")
        } else {
            None
        }
    }

    fn ns_names(&self, zone: &str) -> Option<Vec<String>> {
        if zone == ROOT {
            return if self.hints.is_empty() { None } else { Some(self.hints.keys().cloned().collect()) };
        }
        self.valid(self.answers.get(&key(zone, "NS")))
            .or_else(|| self.valid(self.referrals.get(zone)))
            .cloned()
    }

    fn known_addresses(&self, zone: &str, server: &str) -> Vec<String> {
        if zone == ROOT {
            return self.hints.get(server).cloned().unwrap_or_default();
        }
        for source in [&self.answers, &self.glue] {
            let found: Vec<String> = ["A", "AAAA"]
                .iter()
                .filter_map(|rtype| self.valid(source.get(&key(server, rtype))))
                .flatten()
                .cloned()
                .collect();
            if !found.is_empty() {
                return found;
            }
        }
        Vec::new()
    }

    /// Walks down from the closest zone with known servers to a final response.
    fn ask(&mut self, qname: &str, qtype: &str, pending: &HashSet<String>) -> Option<Rows> {
        let mut zone = ancestors(qname)
            .into_iter()
            .find(|candidate| candidate == ROOT || self.ns_names(candidate).is_some())
            .unwrap_or_else(|| ROOT.to_string());
        loop {
            match self.ask_zone(&zone, qname, qtype, pending)? {
                Step::Final(response) => return Some(response),
                Step::Child(child) => zone = child,
            }
        }
    }

    /// Asks the servers of one zone: those whose addresses are known first, then the others,
    /// each looked up first; an address is asked once per zone.
    fn ask_zone(&mut self, zone: &str, qname: &str, qtype: &str, pending: &HashSet<String>) -> Option<Step> {
        let names = self.ns_names(zone).unwrap_or_default();
        let mut seen: HashSet<String> = HashSet::new();
        let known: Vec<Vec<String>> = names.iter().map(|server| self.known_addresses(zone, server)).collect();
        for addresses in &known {
            if let Some(step) = self.try_all(addresses, &mut seen, zone, qname, qtype) {
                return Some(step);
            }
        }
        for (server, first) in names.iter().zip(&known) {
            if !first.is_empty() {
                continue;
            }
            let mut addresses = self.known_addresses(zone, server);
            if addresses.is_empty() && !pending.contains(server) {
                let mut nested = pending.clone();
                nested.insert(server.clone());
                let (_, rows) = self.resolve_name(server, "A", &nested);
                addresses = rows.into_iter().filter(|row| row[2] == "A").map(|row| row[4].clone()).collect();
            }
            if let Some(step) = self.try_all(&addresses, &mut seen, zone, qname, qtype) {
                return Some(step);
            }
        }
        None
    }

    fn try_all(
        &mut self,
        addresses: &[String],
        seen: &mut HashSet<String>,
        zone: &str,
        qname: &str,
        qtype: &str,
    ) -> Option<Step> {
        for address in addresses {
            if seen.insert(address.clone()) {
                if let Some(step) = self.ask_address(address, zone, qname, qtype) {
                    return Some(step);
                }
            }
        }
        None
    }

    fn ask_address(&mut self, address: &str, zone: &str, qname: &str, qtype: &str) -> Option<Step> {
        self.queries.push(row(&[address, qname, qtype]));
        let response = self.answer(address, qname, qtype);
        if response[0][0] == "REFUSED" {
            return None;
        }
        let cut = match referral_zone(&response) {
            Some(cut) => cut,
            None => return Some(Step::Final(response)),
        };
        if cut != zone && within(&cut, zone) && within(qname, &cut) {
            self.remember_referral(&response, zone);
            return Some(Step::Child(cut));
        }
        None
    }

    fn remember_referral(&mut self, response: &Rows, zone: &str) {
        let ns: Vec<&Vec<String>> = response[1..].iter().filter(|row| row[0] == "authority").collect();
        let ttl: i64 = ns[0][3].parse().unwrap_or(0);
        let names = ns.iter().map(|row| row[4].clone()).collect();
        self.referrals.insert(ns[0][1].clone(), Entry { expiry: self.now + ttl, values: names });
        let mut learned: Vec<(Key, Entry)> = Vec::new();
        for row in response[1..].iter().filter(|row| row[0] == "additional" && within(&row[1], zone)) {
            let k = key(&row[1], &row[2]);
            match learned.iter_mut().find(|(existing, _)| *existing == k) {
                Some((_, entry)) => entry.values.push(row[4].clone()),
                None => {
                    let ttl: i64 = row[3].parse().unwrap_or(0);
                    learned.push((k, Entry { expiry: self.now + ttl, values: vec![row[4].clone()] }));
                }
            }
        }
        self.glue.extend(learned);
    }
}
