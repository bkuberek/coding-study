'use strict';
// Preloaded into a Node language server (NODE_OPTIONS=--require=<this file>, so into every Node
// process the server starts, tsserver included): the directories that the JSON array in
// CSTUDY_HIDDEN_DIRECTORIES names do not exist for it. Whatever the page makes the server open,
// a reference solution, a generated case or run data never reaches an answer
// (docs/specs/web-ui.md#hidden-directories).
//
// A path is judged by where the kernel takes it, not by how it is spelt: it is resolved with
// realpath (so `..` after a link, a link and `/proc/self/root` all count), and then each
// directory from the file up is compared with the hidden ones by name, in Unicode decomposed form
// and lower case, and by what it is on the disk (device and inode), which catches another
// spelling of the same directory, such as /System/Volumes/Data on macOS. What the server opens
// that does not exist is left to fail by itself.

const fs = require('node:fs');
const path = require('node:path');
const { fileURLToPath } = require('node:url');
const { Readable } = require('node:stream');

const realpath = fs.realpathSync.native;
const stat = fs.statSync;
const READS = [
  'access', 'copyFile', 'cp', 'createReadStream', 'lstat', 'open', 'opendir', 'readdir',
  'readFile', 'readlink', 'realpath', 'stat', 'statfs',
];
const MEMO_LIMIT = 200000;
const LOOK_AGAIN_MS = 1000; // for a hidden directory that did not exist yet

const folded = (name) => name.normalize('NFD').toLowerCase();

function hiddenCheck(directories) {
  const named = new Set();
  const identities = [];
  const kept = new Map();
  let looked = 0;

  // `directory` as the kernel spells it, though it is not there yet: its nearest directory that
  // is there, resolved, and the rest.
  const resolvedEvenIfMissing = (directory) => {
    const rest = [];
    for (let head = directory; ; head = path.dirname(head)) {
      try {
        return path.join(realpath(head), ...rest);
      } catch {
        if (path.dirname(head) === head) return directory;
        rest.unshift(path.basename(head));
      }
    }
  };

  const remember = (directory) => {
    named.add(folded(directory));
    named.add(folded(resolvedEvenIfMissing(directory)));
    try {
      const { dev, ino } = stat(directory);
      if (!identities.some((known) => known.dev === dev && known.ino === ino)) {
        identities.push({ dev, ino });
      }
    } catch {
      // not there yet: its names count, and its identity is looked for again later
    }
  };
  const rememberAll = () => directories.forEach((directory) => remember(path.resolve(directory)));
  rememberAll();

  const sameAsHidden = (directory) => {
    if (identities.length < directories.length && Date.now() - looked > LOOK_AGAIN_MS) {
      looked = Date.now();
      rememberAll();
    }
    try {
      const { dev, ino } = stat(directory);
      return identities.some((known) => known.dev === dev && known.ino === ino);
    } catch {
      return false;
    }
  };

  // Whether `real`, a path as the kernel resolves it, is a hidden directory or lies in one.
  const holds = (real) => {
    if (kept.has(real)) return kept.get(real);
    let found = named.has(folded(real)) || sameAsHidden(real);
    if (!found) {
      const parent = path.dirname(real);
      found = parent !== real && holds(parent);
    }
    if (kept.size >= MEMO_LIMIT) kept.clear();
    kept.set(real, found);
    return found;
  };

  return (target) => {
    try {
      let name;
      if (typeof target === 'string') name = target;
      else if (Buffer.isBuffer(target)) name = target.toString();
      else if (target instanceof URL && target.protocol === 'file:') name = fileURLToPath(target);
      else return false;
      return holds(realpath(path.isAbsolute(name) ? name : process.cwd() + path.sep + name));
    } catch {
      return false; // nothing there for the real call to open either
    }
  };
}

function refusal(syscall, target) {
  const shown = Buffer.isBuffer(target) ? target.toString() : String(target);
  const error = new Error(`ENOENT: no such file or directory, ${syscall} '${shown}'`);
  return Object.assign(error, { errno: -2, code: 'ENOENT', syscall, path: shown });
}

function install(isHidden) {
  const guardSync = (name, original) =>
    Object.assign(function (target, ...rest) {
      if (isHidden(target)) {
        const options = rest[0];
        const quiet = (name === 'stat' || name === 'lstat') && options && options.throwIfNoEntry === false;
        if (quiet) return undefined;
        throw refusal(name, target);
      }
      return original.call(this, target, ...rest);
    }, original);

  const guardCallback = (name, original) =>
    Object.assign(function (target, ...rest) {
      if (isHidden(target)) {
        const error = refusal(name, target);
        if (name === 'createReadStream') {
          return new Readable({ read() { this.destroy(error); } });
        }
        const callback = rest.find((argument) => typeof argument === 'function');
        if (callback) process.nextTick(callback, error);
        return undefined;
      }
      return original.call(this, target, ...rest);
    }, original);

  const guardPromise = (name, original) =>
    async function (target, ...rest) {
      if (isHidden(target)) throw refusal(name, target);
      return original.call(this, target, ...rest);
    };

  for (const name of READS) {
    if (typeof fs[name] === 'function') fs[name] = guardCallback(name, fs[name]);
    if (typeof fs[`${name}Sync`] === 'function') fs[`${name}Sync`] = guardSync(name, fs[`${name}Sync`]);
    if (typeof fs.promises[name] === 'function') fs.promises[name] = guardPromise(name, fs.promises[name]);
  }
  if (typeof fs.openAsBlob === 'function') fs.openAsBlob = guardPromise('openAsBlob', fs.openAsBlob);
  fs.realpath.native = guardCallback('realpath', fs.realpath.native);
  fs.realpathSync.native = guardSync('realpath', fs.realpathSync.native);

  const exists = fs.exists;
  fs.exists = Object.assign(function (target, callback) {
    if (isHidden(target)) process.nextTick(callback, false);
    else exists.call(this, target, callback);
  }, exists);
  const existsSync = fs.existsSync;
  fs.existsSync = (target) => !isHidden(target) && existsSync(target);
  require('node:module').syncBuiltinESMExports();
}

const directories = JSON.parse(process.env.CSTUDY_HIDDEN_DIRECTORIES || '[]');
if (directories.length > 0) install(hiddenCheck(directories));
