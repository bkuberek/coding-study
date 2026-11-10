import assert from "node:assert/strict";
import { test } from "node:test";

import { needMarkers, needsRefusal } from "../src/page/needs-model.ts";
import type { NeedRow, Requires } from "../src/page/types.ts";

const REQUIRES: Requires = { docker: true, services: [], mocks: ["room-vendor"], lock: "pnpm-lock.yaml", install_mb: 27, images_mb: { app: 81 }, memory_mb: 150 };

function row(label: string, problem: string | null = null): NeedRow {
  return { label, text: `${label} text`, problem };
}

test("a service project is marked with docker", () => {
  assert.deepEqual(needMarkers(REQUIRES), ["docker"]);
});

test("each backing service follows docker, as cstudy list's NEEDS column says", () => {
  assert.deepEqual(needMarkers({ ...REQUIRES, services: ["postgres", "redis"] }), ["docker", "postgres", "redis"]);
});

test("a problem that needs nothing beyond its toolchain has no marker", () => {
  assert.deepEqual(needMarkers(null), []);
});

test("a requirement that is not met here refuses the start with its reason", () => {
  assert.equal(needsRefusal([row("docker", "Docker is not installed."), row("total")]), "Docker is not installed.");
});

test("every requirement met refuses nothing", () => {
  assert.equal(needsRefusal([row("docker"), row("language"), row("total")]), null);
});
