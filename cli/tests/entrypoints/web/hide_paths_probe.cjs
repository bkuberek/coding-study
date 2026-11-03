'use strict';
// Opens the file `.cs/build/secret.txt` of the workspace given as the first argument by every
// way a language server might, and prints what each did as one JSON object: READ, or the error
// code. `test_hide_paths.py` runs it with and without `hide_paths.cjs` preloaded.
const fs = require('node:fs');
const path = require('node:path');
const childProcess = require('node:child_process');

const workspace = process.argv[2];
const secret = path.join(workspace, '.cs', 'build', 'secret.txt');
const outcome = {};

const tried = (label, action) => {
  try {
    const value = action();
    outcome[label] = value === 'SECRET' || value === true ? 'READ' : String(value);
  } catch (error) {
    outcome[label] = error.code || String(error);
  }
};
const read = (name) => fs.readFileSync(name, 'utf8').trim() === 'SECRET' ? 'SECRET' : 'OTHER';

tried('direct', () => read(secret));
tried('dot-dot', () => read(`${workspace}/typescript/practice/../../.cs/build/secret.txt`));
tried('link', () => read(path.join(workspace, 'link', 'secret.txt')));
tried('dot-dot-after-a-link', () => read(`${workspace}/projects/foo/.venv/../../.cs/build/secret.txt`));
tried('upper-case', () => read(path.join(workspace, '.CS', 'Build', 'secret.txt')));
tried('firmlink', () => read(`/System/Volumes/Data${fs.realpathSync(secret)}`));
tried('proc-self-root', () => read(`/proc/self/root${fs.realpathSync(secret)}`));
tried('relative', () => {
  process.chdir(path.join(workspace, 'typescript'));
  return read('../.cs/build/secret.txt');
});
tried('url', () => read(new URL(`file://${secret}`)));
tried('buffer', () => read(Buffer.from(secret)));
tried('open', () => fs.closeSync(fs.openSync(secret, 'r')) === undefined ? 'SECRET' : '');
tried('exists', () => fs.existsSync(secret));
tried('stat-quiet', () => (fs.statSync(secret, { throwIfNoEntry: false }) ? 'SECRET' : 'ENOENT'));
tried('readdir', () => (fs.readdirSync(path.join(workspace, '.cs', 'build')).length ? 'SECRET' : ''));
tried('directory', () => (fs.statSync(path.join(workspace, '.cs', 'build')).isDirectory() ? 'SECRET' : ''));
tried('realpath', () => (fs.realpathSync.native(secret) ? 'SECRET' : ''));
tried('other-hidden-directory', () => read(path.join(workspace, '.cs', 'cases', 'secret.txt')));
tried('a-file-that-may-be-read', () => (read(path.join(workspace, 'typescript', 'practice', 'fine.txt')) === 'OTHER' ? 'SECRET' : ''));

(async () => {
  try {
    outcome.promise = (await fs.promises.readFile(secret, 'utf8')).trim() === 'SECRET' ? 'READ' : 'OTHER';
  } catch (error) {
    outcome.promise = error.code;
  }
  await new Promise((resolve) => {
    fs.readFile(secret, 'utf8', (error, data) => {
      outcome.callback = error ? error.code : data.trim() === 'SECRET' ? 'READ' : 'OTHER';
      resolve();
    });
  });
  await new Promise((resolve) => {
    const stream = fs.createReadStream(secret);
    stream.on('error', (error) => {
      outcome.stream = error.code;
      resolve();
    });
    stream.on('data', () => {
      outcome.stream = 'READ';
      resolve();
    });
  });
  const script = `try { require('fs').readFileSync(${JSON.stringify(secret)}); console.log('READ'); } catch (error) { console.log(error.code); }`;
  outcome.child = childProcess.execFileSync(process.execPath, ['-e', script]).toString().trim();
  const { readFileSync } = await import('node:fs');
  try {
    outcome.esm = readFileSync(secret, 'utf8').trim() === 'SECRET' ? 'READ' : 'OTHER';
  } catch (error) {
    outcome.esm = error.code;
  }
  console.log(JSON.stringify(outcome));
})();
