const TYPE = "rdf:type";
const SUBCLASS = "rdfs:subClassOf";
const DOMAIN = "rdfs:domain";
const RANGE = "rdfs:range";
const TRANSITIVE = "owl:TransitiveProperty";
const INVERSE = "owl:inverseOf";
const DISJOINT = "owl:disjointWith";
const WILDCARD = "?";

const ENTAILED = "entailed";
const UNKNOWN = "unknown";
const CONTRADICTED = "contradicted";
const NO_ERROR = "no-error";
const MIN_COUNT = "sh:MinCountConstraintComponent";
const MAX_COUNT = "sh:MaxCountConstraintComponent";
const CLASS = "sh:ClassConstraintComponent";
const NO_LIMIT = -1;

type Triple = [string, string, string];
type Row = string[];

// Terms are printable ASCII without spaces, so a NUL never occurs inside one.
const SEPARATOR = "\u0000";

function keyOf(triple: Triple): string {
  return triple.join(SEPARATOR);
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function compareRows(a: Row, b: Row): number {
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    const order = compareText(a[i], b[i]);
    if (order !== 0) {
      return order;
    }
  }
  return a.length - b.length;
}

function multiMap<V>(): Map<string, Set<V>> {
  return new Map();
}

function bucket<V>(map: Map<string, Set<V>>, key: string): Set<V> {
  let found = map.get(key);
  if (found === undefined) {
    found = new Set();
    map.set(key, found);
  }
  return found;
}

/**
 * Applies the rules of the statement until nothing new appears. Every rule has two premises,
 * except the transitive rule, which has three (the declaration and two links). A new triple is
 * joined with the triples already indexed, so the premise that arrives last finds the others.
 */
class Saturation {
  private readonly known = new Map<string, Triple>();
  private readonly pairs = multiMap<Row>();
  private readonly successors = new Map<string, Map<string, Set<string>>>();
  private readonly predecessors = new Map<string, Map<string, Set<string>>>();
  private readonly membersOf = multiMap<string>();
  private readonly domains = multiMap<string>();
  private readonly ranges = multiMap<string>();
  private readonly inverses = multiMap<string>();
  private readonly superclasses = multiMap<string>();
  private readonly transitive = new Set<string>([SUBCLASS]);
  private pending: Triple[] = [];

  run(asserted: Iterable<Triple>): Map<string, Triple> {
    this.pending = [...asserted];
    while (this.pending.length > 0) {
      const triple = this.pending.pop() as Triple;
      const key = keyOf(triple);
      if (this.known.has(key)) {
        continue;
      }
      this.known.set(key, triple);
      this.index(triple);
      this.apply(triple);
    }
    return this.known;
  }

  private derive(subject: string, predicate: string, object: string): void {
    this.pending.push([subject, predicate, object]);
  }

  private neighbours(table: Map<string, Map<string, Set<string>>>, predicate: string, node: string): Set<string> {
    return table.get(predicate)?.get(node) ?? new Set();
  }

  private link(table: Map<string, Map<string, Set<string>>>, predicate: string, from: string, to: string): void {
    let byNode = table.get(predicate);
    if (byNode === undefined) {
      byNode = new Map();
      table.set(predicate, byNode);
    }
    bucket(byNode, from).add(to);
  }

  private index([subject, predicate, object]: Triple): void {
    bucket(this.pairs, predicate).add([subject, object]);
    this.link(this.successors, predicate, subject, object);
    this.link(this.predecessors, predicate, object, subject);
    if (predicate === TYPE) {
      bucket(this.membersOf, object).add(subject);
      if (object === TRANSITIVE) {
        this.transitive.add(subject);
      }
    } else if (predicate === DOMAIN) {
      bucket(this.domains, subject).add(object);
    } else if (predicate === RANGE) {
      bucket(this.ranges, subject).add(object);
    } else if (predicate === INVERSE) {
      bucket(this.inverses, subject).add(object);
      bucket(this.inverses, object).add(subject);
    } else if (predicate === SUBCLASS) {
      bucket(this.superclasses, subject).add(object);
    }
  }

  private pairsOf(predicate: string): Row[] {
    return [...(this.pairs.get(predicate) ?? [])];
  }

  private apply([subject, predicate, object]: Triple): void {
    for (const cls of this.domains.get(predicate) ?? []) {
      this.derive(subject, TYPE, cls);
    }
    for (const cls of this.ranges.get(predicate) ?? []) {
      this.derive(object, TYPE, cls);
    }
    for (const other of this.inverses.get(predicate) ?? []) {
      this.derive(object, other, subject);
    }
    if (this.transitive.has(predicate)) {
      for (const after of this.neighbours(this.successors, predicate, object)) {
        this.derive(subject, predicate, after);
      }
      for (const before of this.neighbours(this.predecessors, predicate, subject)) {
        this.derive(before, predicate, object);
      }
    }
    if (predicate === TYPE) {
      for (const parent of this.superclasses.get(object) ?? []) {
        this.derive(subject, TYPE, parent);
      }
      if (object === TRANSITIVE) {
        for (const [left, middle] of this.pairsOf(subject)) {
          for (const right of this.neighbours(this.successors, subject, middle)) {
            this.derive(left, subject, right);
          }
        }
      }
    } else if (predicate === SUBCLASS) {
      for (const member of this.membersOf.get(subject) ?? []) {
        this.derive(member, TYPE, object);
      }
    } else if (predicate === DOMAIN) {
      for (const [member] of this.pairsOf(subject)) {
        this.derive(member, TYPE, object);
      }
    } else if (predicate === RANGE) {
      for (const [, member] of this.pairsOf(subject)) {
        this.derive(member, TYPE, object);
      }
    } else if (predicate === INVERSE) {
      for (const [left, right] of this.pairsOf(subject)) {
        this.derive(right, object, left);
      }
      for (const [left, right] of this.pairsOf(object)) {
        this.derive(right, subject, left);
      }
    }
  }
}

interface PropertyConstraint {
  minimum: number;
  maximum: number;
  valueClass: string;
}

export class KnowledgeBase {
  private readonly asserted = new Map<string, Triple>();
  private closureCache: Map<string, Triple> | null = null;
  private readonly shapes = new Map<string, string>();
  private readonly properties = new Map<string, Map<string, PropertyConstraint>>();

  // Level 1
  add(subject: string, predicate: string, obj: string): boolean {
    const triple: Triple = [subject, predicate, obj];
    const key = keyOf(triple);
    if (this.asserted.has(key)) {
      return false;
    }
    this.asserted.set(key, triple);
    this.closureCache = null;
    return true;
  }

  closure(subject: string, predicate: string, obj: string): string[][] {
    const fits = (wanted: string, actual: string): boolean => wanted === WILDCARD || wanted === actual;
    return [...this.entailed().values()]
      .filter(([s, p, o]) => fits(subject, s) && fits(predicate, p) && fits(obj, o))
      .map((triple) => [...triple])
      .sort(compareRows);
  }

  types(resource: string): string[] {
    return this.objectsOf(resource, TYPE);
  }

  instances(className: string): string[] {
    const found = new Set<string>();
    for (const [s, p, o] of this.entailed().values()) {
      if (p === TYPE && o === className) {
        found.add(s);
      }
    }
    return [...found].sort(compareText);
  }

  superClasses(className: string): string[] {
    return this.objectsOf(className, SUBCLASS).filter((cls) => cls !== className);
  }

  // Level 2
  ask(subject: string, predicate: string, obj: string): string {
    if (this.entailed().has(keyOf([subject, predicate, obj]))) {
      return ENTAILED;
    }
    return predicate === TYPE && this.wouldClash(subject, obj) ? CONTRADICTED : UNKNOWN;
  }

  // Level 3
  inconsistencies(): string[][] {
    const members = new Map<string, Set<string>>();
    for (const [s, p, o] of this.entailed().values()) {
      if (p === TYPE) {
        bucket(members, o).add(s);
      }
    }
    const rows = new Map<string, Row>();
    for (const [first, second] of this.disjointPairs()) {
      for (const resource of members.get(first) ?? []) {
        if (members.get(second)?.has(resource)) {
          rows.set(keyOf([resource, first, second]), [resource, first, second]);
        }
      }
    }
    return [...rows.values()].sort(compareRows);
  }

  // Level 4
  addShape(shape: string, targetClass: string): boolean {
    if (this.shapes.has(shape)) {
      return false;
    }
    this.shapes.set(shape, targetClass);
    this.properties.set(shape, new Map());
    return true;
  }

  addProperty(shape: string, path: string, minCount: number, maxCount: number, valueClass: string): boolean {
    const constraints = this.properties.get(shape);
    if (constraints === undefined || constraints.has(path)) {
      return false;
    }
    constraints.set(path, { minimum: minCount, maximum: maxCount, valueClass });
    return true;
  }

  validate(): string[][] {
    return this.violations();
  }

  contrast(): string[][] {
    const closure = this.entailed();
    return this.violations().map(([focus, shape, path, component, value]) => {
      const rule = this.properties.get(shape)?.get(path) as PropertyConstraint;
      let answer: string;
      if (component === MAX_COUNT) {
        answer = NO_ERROR;
      } else if (component === MIN_COUNT) {
        answer = this.objectsOf(focus, path).length >= rule.minimum ? ENTAILED : UNKNOWN;
      } else {
        answer = closure.has(keyOf([value, TYPE, rule.valueClass])) ? ENTAILED : UNKNOWN;
      }
      return [focus, shape, path, component, value, answer];
    });
  }

  // Helpers
  private entailed(): Map<string, Triple> {
    if (this.closureCache === null) {
      this.closureCache = new Saturation().run(this.asserted.values());
    }
    return this.closureCache;
  }

  private objectsOf(subject: string, predicate: string): string[] {
    const found = new Set<string>();
    for (const [s, p, o] of this.entailed().values()) {
      if (s === subject && p === predicate) {
        found.add(o);
      }
    }
    return [...found].sort(compareText);
  }

  private disjointPairs(): Row[] {
    const pairs = new Map<string, Row>();
    for (const [a, p, b] of this.entailed().values()) {
      if (p === DISJOINT) {
        const pair = a <= b ? [a, b] : [b, a];
        pairs.set(keyOf([pair[0], "", pair[1]]), pair);
      }
    }
    return [...pairs.values()];
  }

  private wouldClash(subject: string, cls: string): boolean {
    const held = new Set(this.objectsOf(subject, TYPE));
    const added = new Set([cls, ...this.objectsOf(cls, SUBCLASS)]);
    return this.disjointPairs().some(([a, b]) => (held.has(a) && added.has(b)) || (held.has(b) && added.has(a)));
  }

  private violations(): string[][] {
    const parents = new Map<string, Set<string>>();
    const values = new Map<string, Set<string>>();
    const direct = new Map<string, Set<string>>();
    for (const [s, p, o] of this.asserted.values()) {
      bucket(values, s + SEPARATOR + p).add(o);
      if (p === SUBCLASS) {
        bucket(parents, s).add(o);
      } else if (p === TYPE) {
        bucket(direct, s).add(o);
      }
    }
    const memo = new Map<string, Set<string>>();
    // The asserted types of a node and all their asserted superclasses.
    const shaclTypes = (node: string): Set<string> => {
      let found = memo.get(node);
      if (found === undefined) {
        found = new Set(direct.get(node) ?? []);
        const stack = [...found];
        while (stack.length > 0) {
          for (const parent of parents.get(stack.pop() as string) ?? []) {
            if (!found.has(parent)) {
              found.add(parent);
              stack.push(parent);
            }
          }
        }
        memo.set(node, found);
      }
      return found;
    };
    const rows = new Map<string, Row>();
    const report = (row: Row): void => {
      rows.set(keyOf([row[0], row[1], row[2]]) + SEPARATOR + row[3] + SEPARATOR + row[4], row);
    };
    for (const [shape, target] of this.shapes) {
      for (const focus of direct.keys()) {
        if (!shaclTypes(focus).has(target)) {
          continue;
        }
        for (const [path, rule] of this.properties.get(shape) ?? []) {
          const nodes = values.get(focus + SEPARATOR + path) ?? new Set<string>();
          if (nodes.size < rule.minimum) {
            report([focus, shape, path, MIN_COUNT, ""]);
          }
          if (rule.maximum !== NO_LIMIT && nodes.size > rule.maximum) {
            report([focus, shape, path, MAX_COUNT, ""]);
          }
          if (rule.valueClass !== "") {
            for (const node of nodes) {
              if (!shaclTypes(node).has(rule.valueClass)) {
                report([focus, shape, path, CLASS, node]);
              }
            }
          }
        }
      }
    }
    return [...rows.values()].sort(compareRows);
  }
}
