import { existsSync, readFileSync } from "node:fs";

const requiredFiles = [
  "index.html",
  "src/App.tsx",
  "src/main.tsx",
  "src/styles.css",
  "vite.config.ts",
  "tsconfig.json"
];

for (const file of requiredFiles) {
  if (!existsSync(file)) {
    throw new Error(`Missing web shell file: ${file}`);
  }
}

const appSource = readFileSync("src/App.tsx", "utf8");
for (const phrase of ["Review workspace", "Extraction evidence", "Reconciliation", "Audit timeline", "getGoldenReviewCase", "submitReviewDecision"]) {
  if (!appSource.includes(phrase)) {
    throw new Error(`Review workspace is missing: ${phrase}`);
  }
}

console.log("ReconAI review workspace structure OK");
