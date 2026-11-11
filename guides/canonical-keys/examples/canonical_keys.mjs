// JavaScript compares Map keys by identity for objects and arrays, and turns plain object keys
// into strings. Both change what a "key" means.

const visits = [["paris", "lyon"], ["paris", "lyon"]];

const byArray = new Map();
for (const route of visits) {
  byArray.set(route, (byArray.get(route) ?? 0) + 1);
}
console.log("Map with array keys:", byArray.size, "entries, each counted once");

const byString = new Map();
for (const route of visits) {
  const key = JSON.stringify(route); // a canonical string: equal arrays give equal keys
  byString.set(key, (byString.get(key) ?? 0) + 1);
}
console.log("Map with JSON keys:", [...byString]);

const plain = {};
plain[["paris", "lyon"]] = "array";
plain[{ city: "nice" }] = "first object";
plain[{ city: "pau" }] = "second object";
console.log("plain object keys:", Object.keys(plain));

const values = new Map([[NaN, "not a number"]]);
console.log("Map finds NaN with NaN:", values.get(NaN));
