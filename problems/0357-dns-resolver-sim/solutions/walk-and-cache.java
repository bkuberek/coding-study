import java.util.*;

/**
 * Servers answer from their own records the way an authoritative server does: an answer, a
 * referral to a delegated child zone, or a negative answer with the zone's SOA. The resolver walks
 * from the closest zone whose servers it knows (the root at first) down the referrals, and keeps
 * three caches: answers, which it may return; referral data (NS sets and glue), which it only uses
 * to find servers; and negative answers. Every entry expires on the virtual clock.
 */
public class DnsResolver {
    private static final String ROOT = ".";
    private static final int MAX_CHAIN = 8;
    private static final Set<String> NAME_DATA = Set.of("CNAME", "NS", "MX", "SOA");
    private static final String NXDOMAIN_KEY = "*";

    private record Key(String name, String type) {}

    private static final class RecordSet {
        int ttl;
        final List<String> values = new ArrayList<>();
    }

    private record Entry(long expiry, List<String> values) {}

    /** What asking one address led to: a final response or a zone to descend to. */
    private record Step(List<List<String>> response, String child) {}

    private final Map<String, Map<Key, RecordSet>> servers = new HashMap<>();
    private final Map<String, List<String>> hints = new TreeMap<>();
    private final Map<Key, Entry> answers = new HashMap<>();
    private final Map<String, Entry> referrals = new HashMap<>();
    private final Map<Key, Entry> glue = new HashMap<>();
    private final Map<Key, Long> negative = new HashMap<>();
    private List<List<String>> queries = new ArrayList<>();
    private long now = 0;

    // Level 1
    public void addRecord(String server, String name, String rtype, int ttl, String data) {
        Map<Key, RecordSet> records = servers.computeIfAbsent(server, s -> new HashMap<>());
        String value = NAME_DATA.contains(rtype) ? data.toLowerCase(Locale.ROOT) : data;
        RecordSet set = records.computeIfAbsent(new Key(lower(name), rtype), k -> new RecordSet());
        set.ttl = ttl;
        if (!set.values.contains(value)) {
            set.values.add(value);
            Collections.sort(set.values);
        }
    }

    public List<List<String>> lookup(String server, String name, String qtype) {
        Map<Key, RecordSet> records = servers.getOrDefault(server, Map.of());
        name = lower(name);
        String zone = null;
        for (Key key : records.keySet()) {
            if (key.type().equals("SOA") && within(name, key.name())
                    && (zone == null || ancestors(key.name()).size() > ancestors(zone).size())) {
                zone = key.name();
            }
        }
        if (zone == null) {
            return rows(List.of("REFUSED"));
        }
        List<String> lineage = ancestors(name);
        for (int i = lineage.size() - 1; i >= 0; i--) {
            String node = lineage.get(i);
            if (!node.equals(zone) && within(node, zone) && records.containsKey(new Key(node, "NS"))) {
                return referral(records, node);
            }
        }
        if (records.containsKey(new Key(name, qtype))) {
            List<List<String>> result = rows(List.of("NOERROR"));
            result.addAll(section(records, "answer", name, qtype));
            return result;
        }
        if (!qtype.equals("CNAME") && records.containsKey(new Key(name, "CNAME"))) {
            List<List<String>> result = rows(List.of("NOERROR"));
            result.addAll(section(records, "answer", name, "CNAME"));
            return result;
        }
        RecordSet soa = records.get(new Key(zone, "SOA"));
        String data = soa.values.get(0);
        int ttl = Math.min(soa.ttl, Integer.parseInt(data.split(" ")[6]));
        boolean exists = false;
        for (Key key : records.keySet()) {
            exists |= within(key.name(), name);
        }
        return rows(List.of(exists ? "NOERROR" : "NXDOMAIN"),
                List.of("authority", zone, "SOA", String.valueOf(ttl), data));
    }

    // Level 2
    public List<List<String>> follow(String server, String name, String qtype) {
        String current = lower(name);
        Set<String> visited = new HashSet<>(Set.of(current));
        List<List<String>> chain = new ArrayList<>();
        while (true) {
            List<List<String>> response = lookup(server, current, qtype);
            if (response.get(0).get(0).equals("REFUSED")) {
                return chain.isEmpty() ? response : prefixed("NOERROR", chain);
            }
            List<String> alias = aliasOf(response, qtype);
            if (alias == null) {
                List<List<String>> result = prefixed(response.get(0).get(0), chain);
                result.addAll(response.subList(1, response.size()));
                return result;
            }
            chain.add(alias);
            current = alias.get(4);
            if (!visited.add(current) || chain.size() > MAX_CHAIN) {
                return prefixed("SERVFAIL", chain);
            }
        }
    }

    // Level 3
    public void addRootHint(String name, String address) {
        List<String> addresses = hints.computeIfAbsent(lower(name), n -> new ArrayList<>());
        if (!addresses.contains(address)) {
            addresses.add(address);
            Collections.sort(addresses);
        }
    }

    public List<List<String>> resolve(String name, String qtype, long now) {
        this.now = now;
        queries = new ArrayList<>();
        List<List<String>> chain = new ArrayList<>();
        String code = resolveName(lower(name), qtype, Set.of(), chain);
        return prefixed(code, chain);
    }

    public List<List<String>> trace() {
        List<List<String>> copy = new ArrayList<>();
        for (List<String> query : queries) {
            copy.add(new ArrayList<>(query));
        }
        return copy;
    }

    // Level 4
    public List<List<String>> negatives(long now) {
        List<List<String>> result = new ArrayList<>();
        for (Map.Entry<Key, Long> item : negative.entrySet()) {
            if (now < item.getValue()) {
                Key key = item.getKey();
                result.add(List.of(key.name(), key.type(), String.valueOf(item.getValue() - now)));
            }
        }
        result.sort(Comparator.<List<String>, String>comparing(row -> row.get(0))
                .thenComparing(row -> row.get(1)));
        return result;
    }

    // Names
    private static String lower(String name) {
        return name.toLowerCase(Locale.ROOT);
    }

    private static List<String> ancestors(String name) {
        List<String> result = new ArrayList<>();
        if (!name.equals(ROOT)) {
            String[] labels = name.split("\\.");
            for (int i = 0; i < labels.length; i++) {
                result.add(String.join(".", Arrays.copyOfRange(labels, i, labels.length)));
            }
        }
        result.add(ROOT);
        return result;
    }

    private static boolean within(String name, String zone) {
        return zone.equals(ROOT) || name.equals(zone) || name.endsWith("." + zone);
    }

    @SafeVarargs
    private static List<List<String>> rows(List<String>... rows) {
        return new ArrayList<>(Arrays.asList(rows));
    }

    private static List<List<String>> prefixed(String code, List<List<String>> rows) {
        List<List<String>> result = rows(List.of(code));
        result.addAll(rows);
        return result;
    }

    // Server side
    private static List<List<String>> section(Map<Key, RecordSet> records, String section, String owner, String type) {
        RecordSet set = records.get(new Key(owner, type));
        List<List<String>> result = new ArrayList<>();
        for (String value : set.values) {
            result.add(List.of(section, owner, type, String.valueOf(set.ttl), value));
        }
        return result;
    }

    private static List<List<String>> referral(Map<Key, RecordSet> records, String cut) {
        List<List<String>> result = rows(List.of("NOERROR"));
        result.addAll(section(records, "authority", cut, "NS"));
        List<List<String>> additional = new ArrayList<>();
        for (String target : records.get(new Key(cut, "NS")).values) {
            for (String type : List.of("A", "AAAA")) {
                if (records.containsKey(new Key(target, type))) {
                    additional.addAll(section(records, "additional", target, type));
                }
            }
        }
        additional.sort(Comparator.<List<String>, String>comparing(row -> row.get(1))
                .thenComparing(row -> row.get(2))
                .thenComparing(row -> row.get(4)));
        result.addAll(additional);
        return result;
    }

    private static List<List<String>> answerRows(List<List<String>> response) {
        List<List<String>> result = new ArrayList<>();
        for (List<String> row : response.subList(1, response.size())) {
            if (row.get(0).equals("answer")) {
                result.add(row);
            }
        }
        return result;
    }

    private static List<String> aliasOf(List<List<String>> response, String qtype) {
        List<List<String>> found = answerRows(response);
        if (!qtype.equals("CNAME") && found.size() == 1 && found.get(0).get(2).equals("CNAME")) {
            return found.get(0);
        }
        return null;
    }

    // Resolver side
    private List<String> valid(Entry entry) {
        return entry != null && now < entry.expiry() ? entry.values() : null;
    }

    private List<List<String>> cached(String name, String type) {
        Entry entry = answers.get(new Key(name, type));
        if (entry == null || now >= entry.expiry()) {
            return null;
        }
        List<List<String>> result = new ArrayList<>();
        for (String value : entry.values()) {
            result.add(List.of("answer", name, type, String.valueOf(entry.expiry() - now), value));
        }
        return result;
    }

    /** Resolves into {@code chain} and returns the response code. */
    private String resolveName(String qname, String qtype, Set<String> pending, List<List<String>> chain) {
        Set<String> visited = new HashSet<>(Set.of(qname));
        String current = qname;
        while (true) {
            List<List<String>> found = cached(current, qtype);
            if (found != null) {
                chain.addAll(found);
                return "NOERROR";
            }
            List<String> alias = null;
            if (!qtype.equals("CNAME")) {
                List<List<String>> link = cached(current, "CNAME");
                alias = link == null ? null : link.get(0);
            }
            if (alias == null) {
                String negativeCode = negativeAnswer(current, qtype);
                if (negativeCode != null) {
                    return negativeCode;
                }
                List<List<String>> response = ask(current, qtype, pending);
                if (response == null) {
                    return "SERVFAIL";
                }
                alias = absorb(response, current, qtype);
                if (alias == null) {
                    chain.addAll(answerRows(response));
                    return response.get(0).get(0);
                }
            }
            chain.add(alias);
            current = alias.get(4);
            if (!visited.add(current) || chain.size() > MAX_CHAIN) {
                return "SERVFAIL";
            }
        }
    }

    /** Caches a final response and returns its CNAME when it is an alias. */
    private List<String> absorb(List<List<String>> response, String qname, String qtype) {
        List<List<String>> found = answerRows(response);
        if (!found.isEmpty()) {
            List<String> values = new ArrayList<>();
            for (List<String> row : found) {
                values.add(row.get(4));
            }
            long ttl = Long.parseLong(found.get(0).get(3));
            answers.put(new Key(qname, found.get(0).get(2)), new Entry(now + ttl, values));
            return aliasOf(response, qtype);
        }
        for (List<String> row : response.subList(1, response.size())) {
            if (row.get(2).equals("SOA")) {
                String type = response.get(0).get(0).equals("NXDOMAIN") ? NXDOMAIN_KEY : qtype;
                negative.put(new Key(qname, type), now + Long.parseLong(row.get(3)));
                break;
            }
        }
        return null;
    }

    private String negativeAnswer(String name, String qtype) {
        if (now < negative.getOrDefault(new Key(name, NXDOMAIN_KEY), now)) {
            return "NXDOMAIN";
        }
        if (now < negative.getOrDefault(new Key(name, qtype), now)) {
            return "NOERROR";
        }
        return null;
    }

    private List<String> nsNames(String zone) {
        if (zone.equals(ROOT)) {
            return hints.isEmpty() ? null : new ArrayList<>(hints.keySet());
        }
        List<String> answered = valid(answers.get(new Key(zone, "NS")));
        return answered != null ? answered : valid(referrals.get(zone));
    }

    private List<String> knownAddresses(String zone, String server) {
        if (zone.equals(ROOT)) {
            return hints.getOrDefault(server, List.of());
        }
        for (Map<Key, Entry> source : List.of(answers, glue)) {
            List<String> found = new ArrayList<>();
            for (String type : List.of("A", "AAAA")) {
                List<String> values = valid(source.get(new Key(server, type)));
                if (values != null) {
                    found.addAll(values);
                }
            }
            if (!found.isEmpty()) {
                return found;
            }
        }
        return List.of();
    }

    /** Walks down from the closest zone with known servers to a final response. */
    private List<List<String>> ask(String qname, String qtype, Set<String> pending) {
        String zone = ROOT;
        for (String candidate : ancestors(qname)) {
            if (candidate.equals(ROOT) || nsNames(candidate) != null) {
                zone = candidate;
                break;
            }
        }
        while (true) {
            Step step = askZone(zone, qname, qtype, pending);
            if (step == null) {
                return null;
            }
            if (step.response() != null) {
                return step.response();
            }
            zone = step.child();
        }
    }

    /**
     * Asks the servers of one zone: those whose addresses are known first, then the others, each
     * looked up first; an address is asked once per zone.
     */
    private Step askZone(String zone, String qname, String qtype, Set<String> pending) {
        List<String> names = nsNames(zone);
        if (names == null) {
            names = List.of();
        }
        Set<String> seen = new HashSet<>();
        List<List<String>> known = new ArrayList<>();
        for (String server : names) {
            known.add(knownAddresses(zone, server));
        }
        for (List<String> addresses : known) {
            Step step = tryAll(addresses, seen, zone, qname, qtype);
            if (step != null) {
                return step;
            }
        }
        for (int i = 0; i < names.size(); i++) {
            if (!known.get(i).isEmpty()) {
                continue;
            }
            String server = names.get(i);
            List<String> addresses = knownAddresses(zone, server);
            if (addresses.isEmpty() && !pending.contains(server)) {
                Set<String> nested = new HashSet<>(pending);
                nested.add(server);
                List<List<String>> found = new ArrayList<>();
                resolveName(server, "A", nested, found);
                addresses = new ArrayList<>();
                for (List<String> row : found) {
                    if (row.get(2).equals("A")) {
                        addresses.add(row.get(4));
                    }
                }
            }
            Step step = tryAll(addresses, seen, zone, qname, qtype);
            if (step != null) {
                return step;
            }
        }
        return null;
    }

    private Step tryAll(List<String> addresses, Set<String> seen, String zone, String qname, String qtype) {
        for (String address : addresses) {
            if (seen.add(address)) {
                Step step = askAddress(address, zone, qname, qtype);
                if (step != null) {
                    return step;
                }
            }
        }
        return null;
    }

    private Step askAddress(String address, String zone, String qname, String qtype) {
        queries.add(List.of(address, qname, qtype));
        List<List<String>> response = lookup(address, qname, qtype);
        if (response.get(0).get(0).equals("REFUSED")) {
            return null;
        }
        String cut = referralZone(response);
        if (cut == null) {
            return new Step(response, null);
        }
        if (!cut.equals(zone) && within(cut, zone) && within(qname, cut)) {
            rememberReferral(response, zone);
            return new Step(null, cut);
        }
        return null;
    }

    private static String referralZone(List<List<String>> response) {
        if (!answerRows(response).isEmpty()) {
            return null;
        }
        for (List<String> row : response.subList(1, response.size())) {
            if (row.get(0).equals("authority") && row.get(2).equals("NS")) {
                return row.get(1);
            }
        }
        return null;
    }

    private void rememberReferral(List<List<String>> response, String zone) {
        List<String> ns = new ArrayList<>();
        String cut = null;
        long nsTtl = 0;
        Map<Key, Entry> learned = new LinkedHashMap<>();
        for (List<String> row : response.subList(1, response.size())) {
            long ttl = Long.parseLong(row.get(3));
            if (row.get(0).equals("authority")) {
                cut = row.get(1);
                nsTtl = ttl;
                ns.add(row.get(4));
            } else if (row.get(0).equals("additional") && within(row.get(1), zone)) {
                Key key = new Key(row.get(1), row.get(2));
                learned.computeIfAbsent(key, k -> new Entry(now + ttl, new ArrayList<>())).values().add(row.get(4));
            }
        }
        referrals.put(cut, new Entry(now + nsTtl, ns));
        glue.putAll(learned);
    }
}
