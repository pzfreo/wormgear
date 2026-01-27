# Wormgear Web Interface

Browser-based worm gear design calculator with experimental 3D geometry generation.

**Live Site:** https://wormgear.studio

## Features

### Calculator Tab
- Calculate worm gear parameters from engineering constraints
- Real-time validation with DIN 3975/DIN 3996 standards
- Multiple design modes:
  - Envelope (fit within worm OD and wheel OD)
  - From wheel OD (reverse-calculate from wheel size)
  - From module (standard module-based design)
  - From centre distance (fit specific spacing)
- Export JSON Schema v2.0 for geometry generation
- Download markdown specifications
- Share designs via URL

### 3D Generator Tab (Experimental)
- Generates CNC-ready STEP files directly in browser
- Uses Pyodide + OCP + build123d (~50MB)
- Load JSON from Calculator tab or upload files
- Options for globoid worm and virtual hobbing

## Local Development

**Important**: You MUST use an HTTP server. Opening `index.html` directly (file://) will not work due to CORS restrictions.

```bash
# Build Python files for Pyodide (run from web/ directory)
./build.sh

# Start local server
python3 -m http.server 8000

# Or use the included server with CORS headers
python3 serve.py
```

Open http://localhost:8000 in your browser.

## File Structure

```
web/
├── index.html              # Main interface
├── app.js                  # Application logic
├── style.css               # Styles
├── modules/                # JavaScript modules
│   ├── pyodide-init.js    # Pyodide initialization
│   ├── parameter-handler.js # UI input collection
│   ├── schema-validator.js  # Runtime validation
│   ├── generator-ui.js      # 3D generator UI
│   ├── bore-calculator.js   # Bore calculations
│   └── validation-ui.js     # Validation display
├── generator-worker.js     # Web Worker for geometry generation
├── types/                  # Generated TypeScript types
├── build.sh               # Builds Python files for Pyodide
└── serve.py               # Local server with CORS headers
```

## Architecture

### Schema-First Design

The web interface uses types generated from Python Pydantic models:

1. **Python models** in `src/wormgear/io/loaders.py` (single source of truth)
2. **JSON Schema** generated to `schemas/`
3. **TypeScript types** generated to `web/types/`

This ensures the web UI and Python backend always agree on data structures.

### JavaScript Modules

The code is organized into ES6 modules:

- **pyodide-init.js** - Loads Pyodide and Python calculator code
- **parameter-handler.js** - Collects and validates UI inputs
- **schema-validator.js** - Runtime JSON schema validation
- **generator-ui.js** - 3D generator tab functionality
- **bore-calculator.js** - Automatic bore sizing
- **validation-ui.js** - Display validation messages

### Python/Pyodide Integration

The calculator runs Python code via Pyodide. The `build.sh` script copies Python source files from `src/wormgear/` to make them available to Pyodide.

## Deployment

### Vercel (Production)

The site is deployed via Vercel with automatic deploys on push to main.

Configuration in `vercel.json`:
- Root directory: `web/`
- CORS headers for Pyodide/WASM support

### GitHub Pages (Alternative)

Enable GitHub Pages on main branch with `/web/` as root directory.

## Browser Compatibility

Requires modern browser with WebAssembly support:
- Chrome 88+
- Firefox 89+
- Safari 15+
- Edge 88+

## Troubleshooting

### "Loading calculator..." never completes
- Check browser console for errors
- Ensure CDN access to Pyodide (cdn.jsdelivr.net)
- Verify HTTP server is running (not file://)

### Generator fails to load
- Large download (~50MB) may timeout on slow connections
- Try in different browser (Chrome/Firefox work best)
- Ensure sufficient memory (>500MB free)

### Export buttons not working
- Copy to clipboard requires HTTPS
- Check clipboard permissions in browser

## Development Workflow

When making changes:

1. Edit Python models in `src/wormgear/`
2. Regenerate schemas: `python scripts/generate_schemas.py`
3. Regenerate TypeScript: `bash scripts/generate_types.sh`
4. Run build: `cd web && ./build.sh`
5. Test locally: `python3 serve.py`
6. Commit and push to deploy
