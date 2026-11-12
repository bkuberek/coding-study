use std::collections::{BTreeMap, HashMap, HashSet};

const FIXED_SIZE: usize = 64;
const WINDOW: usize = 16;
const BASE: i64 = 257;
const MODULUS: i64 = 1_000_000_007;
const MIN_CHUNK: usize = 32;
const MAX_CHUNK: usize = 256;
const DIVISOR: i64 = 64;
const KINDS: [&str; 3] = ["blob", "tree", "manifest"];

/// What a folder line or a ref names: its kind and its address.
#[derive(Clone, PartialEq, Eq, Hash)]
struct Entry {
    kind: String,
    address: String,
}

impl Entry {
    fn new(kind: &str, address: &str) -> Self {
        Entry {
            kind: kind.to_string(),
            address: address.to_string(),
        }
    }
}

/// A tree or a manifest that had to be opened is missing or damaged.
struct Damaged;

fn lines(data: &[u8]) -> Vec<String> {
    let text = String::from_utf8_lossy(data);
    match text.strip_suffix('\n') {
        Some(body) => body.split('\n').map(str::to_string).collect(),
        None => Vec::new(),
    }
}

fn fixed_sizes(length: usize) -> Vec<i32> {
    (0..length)
        .step_by(FIXED_SIZE)
        .map(|start| FIXED_SIZE.min(length - start) as i32)
        .collect()
}

/// Content-defined cuts: a rolling hash of the last 16 bytes, rolled once per byte.
fn cdc_sizes(data: &[u8]) -> Vec<i32> {
    let leaving_weight = (0..WINDOW - 1).fold(1, |weight, _| weight * BASE % MODULUS);
    let mut sizes = Vec::new();
    let mut window_hash: i64 = 0;
    let mut start = 0;
    for (index, &byte) in data.iter().enumerate() {
        if index >= WINDOW {
            let leaving = i64::from(data[index - WINDOW]) * leaving_weight;
            window_hash = (window_hash - leaving).rem_euclid(MODULUS);
        }
        window_hash = (window_hash * BASE + i64::from(byte)) % MODULUS;
        let length = index - start + 1;
        if length == MAX_CHUNK || (length >= MIN_CHUNK && window_hash % DIVISOR == 0) {
            sizes.push(length as i32);
            start = index + 1;
        }
    }
    if start < data.len() {
        sizes.push((data.len() - start) as i32);
    }
    sizes
}

/// Objects are bytes filed under the SHA-256 digest of those bytes. Every read hashes what it
/// finds again, so a damaged object reads as a missing one. Folders and manifests are objects
/// that list other objects by address, and refs name the objects the collector keeps.
pub struct ContentStore {
    objects: HashMap<String, Vec<u8>>,
    file_bytes: HashMap<String, i64>,
    chunks: HashMap<String, HashMap<String, i64>>,
    refs: HashMap<String, Entry>,
}

impl ContentStore {
    pub fn new() -> Self {
        ContentStore {
            objects: HashMap::new(),
            file_bytes: HashMap::new(),
            chunks: HashMap::new(),
            refs: HashMap::new(),
        }
    }

    fn write(&mut self, data: Vec<u8>) -> String {
        let address = sha256_hex(&data);
        if self.read(&address).is_none() {
            self.objects.insert(address.clone(), data);
        }
        address
    }

    fn read(&self, address: &str) -> Option<&Vec<u8>> {
        self.objects
            .get(address)
            .filter(|data| sha256_hex(data) == address)
    }

    // Level 1
    pub fn put(&mut self, data: String) -> String {
        self.write(data.into_bytes())
    }

    pub fn get(&mut self, address: String) -> String {
        self.read(&address)
            .map(|data| String::from_utf8_lossy(data).into_owned())
            .unwrap_or_default()
    }

    pub fn check(&mut self, address: String) -> String {
        if !self.objects.contains_key(&address) {
            "missing".to_string()
        } else if self.read(&address).is_none() {
            "damaged".to_string()
        } else {
            "ok".to_string()
        }
    }

    pub fn damage(&mut self, address: String, data: String) -> bool {
        match self.objects.get_mut(&address) {
            Some(stored) => {
                *stored = data.into_bytes();
                true
            }
            None => false,
        }
    }

    pub fn count(&mut self) -> i32 {
        self.objects.len() as i32
    }

    pub fn bytes_stored(&mut self) -> i32 {
        self.objects.values().map(Vec::len).sum::<usize>() as i32
    }

    // Level 2
    pub fn snapshot(&mut self, files: Vec<Vec<String>>) -> String {
        let split = files
            .into_iter()
            .map(|file| {
                let names = file[0].split('/').map(str::to_string).collect::<Vec<_>>();
                (names, file[1].clone())
            })
            .collect();
        self.folder(split)
    }

    fn folder(&mut self, files: Vec<(Vec<String>, String)>) -> String {
        let mut entries: BTreeMap<String, Entry> = BTreeMap::new();
        let mut below: BTreeMap<String, Vec<(Vec<String>, String)>> = BTreeMap::new();
        for (mut names, data) in files {
            if names.len() == 1 {
                let address = self.put(data);
                entries.insert(names.remove(0), Entry::new("blob", &address));
            } else {
                let first = names.remove(0);
                below.entry(first).or_default().push((names, data));
            }
        }
        for (name, inner) in below {
            let address = self.folder(inner);
            entries.insert(name, Entry::new("tree", &address));
        }
        let mut text = String::new();
        for (name, entry) in &entries {
            text.push_str(&format!("{} {} {name}\n", entry.kind, entry.address));
        }
        self.put(text)
    }

    fn open_tree(&self, address: &str) -> Result<Vec<(String, Entry)>, Damaged> {
        let data = self.read(address).ok_or(Damaged)?;
        Ok(lines(data)
            .iter()
            .map(|line| (line[70..].to_string(), Entry::new(&line[..4], &line[5..69])))
            .collect())
    }

    fn find(&self, address: &str, name: &str) -> Result<Option<Entry>, Damaged> {
        let entries = self.open_tree(address)?;
        Ok(entries
            .into_iter()
            .find(|(found, _)| found == name)
            .map(|(_, entry)| entry))
    }

    pub fn read_path(&mut self, root: String, path: String) -> String {
        let mut current = Entry::new("tree", &root);
        for name in path.split('/') {
            if current.kind != "tree" {
                return String::new();
            }
            match self.find(&current.address, name) {
                Ok(Some(entry)) => current = entry,
                _ => return String::new(),
            }
        }
        if current.kind == "blob" {
            self.get(current.address)
        } else {
            String::new()
        }
    }

    pub fn diff(&mut self, old_root: String, new_root: String) -> Vec<String> {
        let mut changes = Vec::new();
        if self
            .compare("", &old_root, &new_root, &mut changes)
            .is_err()
        {
            return Vec::new();
        }
        changes.sort();
        changes
            .into_iter()
            .map(|(path, op)| format!("{op} {path}"))
            .collect()
    }

    fn compare(
        &self,
        prefix: &str,
        old_tree: &str,
        new_tree: &str,
        changes: &mut Vec<(String, &'static str)>,
    ) -> Result<(), Damaged> {
        if old_tree == new_tree {
            return Ok(());
        }
        let before: HashMap<String, Entry> = self.open_tree(old_tree)?.into_iter().collect();
        let after: HashMap<String, Entry> = self.open_tree(new_tree)?.into_iter().collect();
        let names: HashSet<&String> = before.keys().chain(after.keys()).collect();
        for name in names {
            let path = format!("{prefix}{name}");
            match (before.get(name), after.get(name)) {
                (Some(was), Some(now)) if was == now => {}
                (Some(was), Some(now)) if was.kind == now.kind && was.kind == "blob" => {
                    changes.push((path, "M"));
                }
                (Some(was), Some(now)) if was.kind == now.kind => {
                    self.compare(&format!("{path}/"), &was.address, &now.address, changes)?;
                }
                (was, now) => {
                    if let Some(was) = was {
                        self.list_files("D", &path, was, changes)?;
                    }
                    if let Some(now) = now {
                        self.list_files("A", &path, now, changes)?;
                    }
                }
            }
        }
        Ok(())
    }

    fn list_files(
        &self,
        op: &'static str,
        path: &str,
        entry: &Entry,
        changes: &mut Vec<(String, &'static str)>,
    ) -> Result<(), Damaged> {
        if entry.kind == "blob" {
            changes.push((path.to_string(), op));
            return Ok(());
        }
        for (name, inner) in self.open_tree(&entry.address)? {
            self.list_files(op, &format!("{path}/{name}"), &inner, changes)?;
        }
        Ok(())
    }

    // Level 3
    pub fn chunk_sizes(&mut self, data: String, method: String) -> Vec<i32> {
        if method == "fixed" {
            fixed_sizes(data.len())
        } else {
            cdc_sizes(data.as_bytes())
        }
    }

    pub fn put_file(&mut self, data: String, method: String) -> String {
        let raw = data.as_bytes();
        let mut manifest = String::new();
        let mut start = 0;
        for size in self.chunk_sizes(data.clone(), method.clone()) {
            let size = size as usize;
            let address = self.write(raw[start..start + size].to_vec());
            self.chunks
                .entry(method.clone())
                .or_default()
                .insert(address.clone(), size as i64);
            manifest.push_str(&address);
            manifest.push('\n');
            start += size;
        }
        *self.file_bytes.entry(method).or_default() += raw.len() as i64;
        self.put(manifest)
    }

    pub fn read_file(&mut self, manifest: String) -> String {
        let Some(listing) = self.read(&manifest) else {
            return String::new();
        };
        let mut parts = Vec::new();
        for address in lines(listing) {
            match self.read(&address) {
                Some(chunk) => parts.extend_from_slice(chunk),
                None => return String::new(),
            }
        }
        String::from_utf8_lossy(&parts).into_owned()
    }

    pub fn dedup_ratio(&mut self, method: String) -> f64 {
        let stored: i64 = self
            .chunks
            .get(&method)
            .map_or(0, |sizes| sizes.values().sum());
        if stored == 0 {
            return 0.0;
        }
        self.file_bytes.get(&method).copied().unwrap_or(0) as f64 / stored as f64
    }

    // Level 4
    pub fn set_ref(&mut self, name: String, kind: String, address: String) -> bool {
        if !KINDS.contains(&kind.as_str()) || !self.objects.contains_key(&address) {
            return false;
        }
        self.refs.insert(name, Entry::new(&kind, &address));
        true
    }

    pub fn get_ref(&mut self, name: String) -> String {
        self.refs
            .get(&name)
            .map(|entry| entry.address.clone())
            .unwrap_or_default()
    }

    pub fn delete_ref(&mut self, name: String) -> bool {
        self.refs.remove(&name).is_some()
    }

    pub fn collect_garbage(&mut self) -> i32 {
        let Ok(live) = self.mark() else {
            return -1;
        };
        let mut freed = 0;
        self.objects.retain(|address, data| {
            let keep = live.contains(address);
            if !keep {
                freed += data.len();
            }
            keep
        });
        freed as i32
    }

    fn mark(&self) -> Result<HashSet<String>, Damaged> {
        let mut live = HashSet::new();
        let mut visited = HashSet::new();
        let mut pending: Vec<Entry> = self.refs.values().cloned().collect();
        while let Some(entry) = pending.pop() {
            if !visited.insert(entry.clone()) {
                continue;
            }
            live.insert(entry.address.clone());
            match entry.kind.as_str() {
                "tree" => {
                    let entries = self.open_tree(&entry.address)?;
                    pending.extend(entries.into_iter().map(|(_, inner)| inner));
                }
                "manifest" => {
                    let listing = self.read(&entry.address).ok_or(Damaged)?;
                    pending.extend(
                        lines(listing)
                            .iter()
                            .map(|address| Entry::new("blob", address)),
                    );
                }
                _ => {}
            }
        }
        Ok(live)
    }
}

/// The SHA-256 digest of `data` (FIPS 180-4): 32 bytes. Rust's standard library has no SHA-256,
/// so the starter provides it; use it as it is.
pub fn sha256(data: &[u8]) -> [u8; 32] {
    let mut state = SHA256_INITIAL;
    let mut padded = data.to_vec();
    padded.push(0x80);
    while padded.len() % 64 != 56 {
        padded.push(0);
    }
    padded.extend_from_slice(&((data.len() as u64) * 8).to_be_bytes());
    for block in padded.chunks_exact(64) {
        sha256_compress(&mut state, block);
    }
    let mut digest = [0u8; 32];
    for (bytes, word) in digest.chunks_exact_mut(4).zip(state) {
        bytes.copy_from_slice(&word.to_be_bytes());
    }
    digest
}

/// The SHA-256 digest of `data` as 64 lowercase hexadecimal characters.
pub fn sha256_hex(data: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut text = String::with_capacity(64);
    for byte in sha256(data) {
        text.push(char::from(DIGITS[usize::from(byte >> 4)]));
        text.push(char::from(DIGITS[usize::from(byte & 0x0f)]));
    }
    text
}

const SHA256_INITIAL: [u32; 8] = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
];

const SHA256_ROUND: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

fn sha256_compress(state: &mut [u32; 8], block: &[u8]) {
    let mut schedule = [0u32; 64];
    for (word, bytes) in schedule.iter_mut().zip(block.chunks_exact(4)) {
        *word = u32::from_be_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]);
    }
    for t in 16..64 {
        let w15 = schedule[t - 15];
        let w2 = schedule[t - 2];
        let sigma0 = w15.rotate_right(7) ^ w15.rotate_right(18) ^ (w15 >> 3);
        let sigma1 = w2.rotate_right(17) ^ w2.rotate_right(19) ^ (w2 >> 10);
        schedule[t] = sigma1
            .wrapping_add(schedule[t - 7])
            .wrapping_add(sigma0)
            .wrapping_add(schedule[t - 16]);
    }
    let [mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut h] = *state;
    for (round, word) in SHA256_ROUND.iter().zip(schedule) {
        let big_sigma1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
        let choose = (e & f) ^ (!e & g);
        let t1 = h
            .wrapping_add(big_sigma1)
            .wrapping_add(choose)
            .wrapping_add(*round)
            .wrapping_add(word);
        let big_sigma0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
        let majority = (a & b) ^ (a & c) ^ (b & c);
        let t2 = big_sigma0.wrapping_add(majority);
        h = g;
        g = f;
        f = e;
        e = d.wrapping_add(t1);
        d = c;
        c = b;
        b = a;
        a = t1.wrapping_add(t2);
    }
    for (word, value) in state.iter_mut().zip([a, b, c, d, e, f, g, h]) {
        *word = word.wrapping_add(value);
    }
}

#[cfg(test)]
mod sha256_tests {
    use super::sha256_hex;

    #[test]
    fn digest_of_abc() {
        assert_eq!(
            sha256_hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[test]
    fn digest_of_the_empty_message() {
        assert_eq!(
            sha256_hex(b""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
    }

    #[test]
    fn digest_of_the_448_bit_message() {
        assert_eq!(
            sha256_hex(b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"),
            "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"
        );
    }
}
