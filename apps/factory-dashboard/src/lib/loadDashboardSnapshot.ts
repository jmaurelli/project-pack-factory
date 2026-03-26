import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import type { DashboardSnapshot } from "./dashboardTypes";

const REQUIRED_KEYS = [
  "schema_version",
  "dashboard_build_id",
  "generated_at",
  "what_matters_most",
  "environment_board",
  "quality_now",
  "automation_now",
  "factory_learning",
  "agent_memory",
  "ideas_lab",
  "recent_motion",
  "focused_portfolio",
  "mismatch_warnings",
] as const;

function fixturePath(): string {
  return resolve(process.cwd(), "fixtures", "dashboard-snapshot.fixture.json");
}

function resolveSnapshotPath(): string {
  return process.env.PACK_FACTORY_DASHBOARD_SNAPSHOT_PATH || fixturePath();
}

function validateSnapshotShape(payload: unknown, sourcePath: string): DashboardSnapshot {
  if (typeof payload !== "object" || payload === null) {
    throw new Error(`Dashboard snapshot at ${sourcePath} must contain an object.`);
  }
  const candidate = payload as Record<string, unknown>;
  for (const key of REQUIRED_KEYS) {
    if (!(key in candidate)) {
      throw new Error(`Dashboard snapshot at ${sourcePath} is missing required key: ${key}`);
    }
  }
  return candidate as DashboardSnapshot;
}

export async function loadDashboardSnapshot(): Promise<DashboardSnapshot> {
  const snapshotPath = resolveSnapshotPath();
  const raw = await readFile(snapshotPath, "utf-8");
  return validateSnapshotShape(JSON.parse(raw), snapshotPath);
}
