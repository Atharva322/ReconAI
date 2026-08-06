import { existsSync } from "node:fs";

const nodeMajor = Number.parseInt(process.versions.node.split(".")[0], 10);

if (nodeMajor < 20) {
  throw new Error(`Node 20+ required, found ${process.version}`);
}

if (!existsSync("docs/RECONAI_WORK_PLAN.md")) {
  throw new Error("Expected repo docs are missing");
}

console.log(`React/TypeScript toolchain baseline OK on Node ${process.version}`);
