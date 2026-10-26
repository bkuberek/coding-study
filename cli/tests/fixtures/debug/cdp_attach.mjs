// A minimal Chrome DevTools Protocol client for the Node inspector, used by the end-to-end tests
// of `cstudy test --debug`: break once at FILE:LINE (1-based), report the stop, resume and detach.
// Usage: node cdp_attach.mjs PORT FILE LINE
import { pathToFileURL } from "node:url";

const [port, file, lineArgument] = process.argv.slice(2);
const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const socket = new WebSocket(targets[0].webSocketDebuggerUrl);
const pending = new Map();
let lastId = 0;

const send = (method, params = {}) =>
  new Promise((resolve) => {
    lastId += 1;
    pending.set(lastId, resolve);
    socket.send(JSON.stringify({ id: lastId, method, params }));
  });

socket.onmessage = async (message) => {
  const data = JSON.parse(message.data);
  if (data.id && pending.has(data.id)) {
    pending.get(data.id)(data);
    pending.delete(data.id);
    return;
  }
  if (data.method !== "Debugger.paused") {
    return;
  }
  const top = data.params.callFrames[0];
  if (!data.params.hitBreakpoints?.length) {
    await send("Debugger.resume");
    return;
  }
  const source = await send("Debugger.getScriptSource", { scriptId: top.location.scriptId });
  const text = source.result.scriptSource.split("\n")[top.location.lineNumber];
  console.log(`STOP AT line ${top.location.lineNumber + 1} in ${top.functionName}: ${text.trim()}`);
  await send("Debugger.removeBreakpoint", { breakpointId: data.params.hitBreakpoints[0] });
  await send("Debugger.resume");
  setTimeout(() => process.exit(0), 300);
};

socket.onopen = async () => {
  await send("Runtime.enable");
  await send("Debugger.enable");
  await send("Debugger.setBreakpointByUrl", {
    url: pathToFileURL(file).href,
    lineNumber: Number(lineArgument) - 1,
  });
  await send("Runtime.runIfWaitingForDebugger");
};
