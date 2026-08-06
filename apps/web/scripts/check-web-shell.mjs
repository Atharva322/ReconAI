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
if (!appSource.includes("Northstar Beverages")) {
  throw new Error("Web shell does not expose the seeded demo tenant");
}

console.log("ReconAI web shell structure OK");
