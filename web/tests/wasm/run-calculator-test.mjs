// Headless test of the web calculator path (pyodide-init.js) under Node:
// real Pyodide + loadPackage('pydantic') + the calculator file subset +
// a js_bridge.calculate() round-trip. Mirrors what the browser does on the
// calculator page, without build123d.
//
// Prerequisites: `bash web/build.sh` (creates dist/), `npm ci` in web/.
// Usage: node web/tests/wasm/run-calculator-test.mjs
import { loadPyodide, version as pyodideVersion } from "pyodide";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const REPO = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const DIST = join(REPO, "dist");

const initJs = readFileSync(join(REPO, "web", "modules", "pyodide-init.js"), "utf8");
const pinned = initJs.match(/cdn\.jsdelivr\.net\/pyodide\/v(\d+\.\d+\.\d+)\//)?.[1];
if (pinned !== pyodideVersion) {
  console.error(`✗ Pyodide version drift: pyodide-init.js pins v${pinned}, npm has v${pyodideVersion}`);
  process.exit(1);
}
console.log(`Pyodide ${pyodideVersion} (matches pyodide-init.js pin)`);

const pyodide = await loadPyodide();
await pyodide.loadPackage(["micropip", "pydantic"]);
console.log("pydantic:", pyodide.runPython("import pydantic; pydantic.__version__"));

// Calculator subset — mirror pyodide-init.js, which loads calculator/, io/,
// enums, and the build123d-free parts of core/.
const manifest = JSON.parse(readFileSync(join(DIST, "wormgear-manifest.json"), "utf8"));
const files = manifest.filter((p) =>
  p.startsWith("wormgear/calculator/") ||
  p.startsWith("wormgear/io/") ||
  p === "wormgear/__init__.py" ||
  p === "wormgear/enums.py" ||
  p === "wormgear/core/__init__.py" ||
  p === "wormgear/core/bore_sizing.py"
);
const dirs = new Set();
for (const p of files) {
  const parts = p.split("/");
  for (let i = 1; i < parts.length; i++) dirs.add("/home/pyodide/" + parts.slice(0, i).join("/"));
}
await pyodide.runPythonAsync(`
import os, sys
for d in ${JSON.stringify([...dirs].sort())}:
    os.makedirs(d, exist_ok=True)
if '/home/pyodide' not in sys.path:
    sys.path.insert(0, '/home/pyodide')
`);
for (const p of files) {
  pyodide.FS.writeFile("/home/pyodide/" + p, readFileSync(join(DIST, p), "utf8"));
}
console.log(`Loaded ${files.length} calculator files`);

pyodide.globals.set("input_json", JSON.stringify({
  mode: "from-module",
  module: 2.0,
  ratio: 30,
  num_starts: 1,
}));
const resultJson = await pyodide.runPythonAsync(`
from wormgear.calculator.js_bridge import calculate
calculate(input_json)
`);
const result = JSON.parse(resultJson);
const design = result.design_json ? JSON.parse(result.design_json) : null;
const ok = result.success && result.valid && design?.worm?.module_mm === 2.0 && design?.wheel?.num_teeth === 30;
console.log("success:", result.success, "valid:", result.valid, "error:", result.error);
console.log("worm module:", design?.worm?.module_mm, "wheel teeth:", design?.wheel?.num_teeth);
console.log(ok ? "=== CALCULATOR OK ===" : "=== CALCULATOR FAILED ===");
process.exit(ok ? 0 : 1);
