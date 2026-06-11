// Headless test of the web generator's WASM stack.
//
// Runs real Pyodide (the same WASM runtime the browser uses) under Node and
// executes the exact Python snippets shipped in dist/generator-worker.js —
// extracted from the built file, not re-typed — so it catches:
//   * package-resolution breakage (PyPI / OCP.wasm index changes)
//   * Pyodide-version drift between package.json and the worker's CDN pin
//   * API drift between the worker's embedded Python and src/wormgear
//
// Prerequisites: `bash web/build.sh` (creates dist/), `npm ci` in web/.
// Usage: node web/tests/wasm/run-worker-test.mjs
import { loadPyodide, version as pyodideVersion } from "pyodide";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const REPO = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const DIST = join(REPO, "dist");
const worker = readFileSync(join(DIST, "generator-worker.js"), "utf8");

// The npm pyodide running this test must match the version the worker pins,
// otherwise we're not testing what ships.
const pinned = worker.match(/cdn\.jsdelivr\.net\/pyodide\/v(\d+\.\d+\.\d+)\//)?.[1];
if (pinned !== pyodideVersion) {
  console.error(`✗ Pyodide version drift: worker pins v${pinned}, npm has v${pyodideVersion}`);
  console.error("  Update web/package.json and the CDN URLs together.");
  process.exit(1);
}
console.log(`Pyodide ${pyodideVersion} (matches worker pin)`);

function extract(startMarker) {
  const re = new RegExp("runPythonAsync\\(`\\n(" + startMarker + "[\\s\\S]*?)\\n\\s*`\\)");
  const m = worker.match(re);
  if (!m) throw new Error("could not extract worker snippet starting with: " + startMarker);
  return m[1];
}

const installSnippet = extract("import micropip");
const testImportSnippet = extract("import wormgear");
const generateSnippet = extract("import json");

const pyodide = await loadPyodide({
  stdout: (t) => t.trim() && console.log("[py]", t),
  stderr: (t) => t.trim() && console.log("[py:err]", t),
});

console.log("=== loadPackage(micropip, pydantic) ===");
await pyodide.loadPackage(["micropip", "pydantic"]);

console.log("=== Install snippet from generator-worker.js ===");
const t0 = Date.now();
const result = await pyodide.runPythonAsync(installSnippet);
console.log(`Install: ${result} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
if (result !== "SUCCESS") process.exit(1);

console.log("=== Loading wormgear package from dist/ ===");
const manifest = JSON.parse(readFileSync(join(DIST, "wormgear-manifest.json"), "utf8"));
const dirs = new Set();
for (const p of manifest) {
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
for (const p of manifest) {
  pyodide.FS.writeFile("/home/pyodide/" + p, readFileSync(join(DIST, p), "utf8"));
}
console.log(`Loaded ${manifest.length} files; running worker's test-import snippet...`);
await pyodide.runPythonAsync(testImportSnippet);

// Produce the design the way the real app does: calculator → JSON → generator.
const designJson = await pyodide.runPythonAsync(`
import json
from wormgear.calculator import design_from_module, to_json
_d = json.loads(to_json(design_from_module(module=1.0, ratio=12)))
_d['features'] = {
    'worm': {'bore_diameter_mm': 4.0, 'anti_rotation': 'ddcut'},
    'wheel': {'bore_diameter_mm': 6.0, 'anti_rotation': 'DIN6885'},
}
json.dumps(_d)
`);

console.log("=== Generation snippet (cylindrical, both parts) ===");
globalThis.postProgressUpdate = (m, p) => console.log(`[progress] ${m} (${p}%)`);
const progressCallback = pyodide.runPython(`
def progress_callback(message, percent):
    import js
    js.postProgressUpdate(message, percent)

progress_callback
`);
pyodide.globals.set("design_json_str", designJson);
pyodide.globals.set("worm_length", 20.0);
pyodide.globals.set("wheel_width_val", null);
pyodide.globals.set("virtual_hobbing_val", false);
pyodide.globals.set("hobbing_steps_val", 6);
pyodide.globals.set("generate_type", "both");
pyodide.globals.set("generation_method_val", "sweep");
pyodide.globals.set("progress_callback_fn", progressCallback);

const t1 = Date.now();
const genResult = await pyodide.runPythonAsync(generateSnippet);
const success = genResult.get("success");
const zip = genResult.get("zip");
console.log(
  `=== Generation ${success ? "SUCCEEDED" : "FAILED"} in ${((Date.now() - t1) / 1000).toFixed(0)}s; ` +
  `zip=${zip ? (zip.length / 1024).toFixed(0) + " KB b64" : "missing"} ===`
);
process.exit(success && zip ? 0 : 1);
