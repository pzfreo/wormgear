# Wormgear Web Interface

Browser-based complete design system with calculator and 3D geometry generator (experimental).

## Features

### Calculator Tab (Fast Load)
- **Instant loading** - Uses lightweight Pyodide environment (~5MB)
- Calculate worm gear parameters from engineering constraints
- Real-time validation with DIN 3975/DIN 3996 standards
- Multiple design modes:
  - Envelope (fit within worm OD and wheel OD)
  - From wheel OD (reverse-calculate from wheel size)
  - From module (standard module-based design)
  - From centre distance (fit specific spacing)
- Export JSON Schema v1.0 for geometry generation
- Download markdown specifications
- Share designs via URL

### 3D Generator Tab (Lazy Loaded)
- **Lazy loading** - Only loads when you click "Load Generator"
- Generates CNC-ready STEP files directly in browser using WebAssembly
- Uses Pyodide + OCP + build123d (~50MB, loads in 30-60 seconds)
- Load JSON from Calculator tab or upload files
- Options for globoid worm and virtual hobbing
- Console output for generation progress

## Quick Start

### Local Development

**Important**: You MUST use an HTTP server. Opening `index.html` directly (file://) will not work due to CORS restrictions.

```bash
# Using Python (recommended)
cd web
python3 -m http.server 8000

# Using Node.js
npx serve web

# Using PHP
cd web
php -S localhost:8000
```

Then open http://localhost:8000 in your browser.

### Using the Interface

1. **Design your gears** in the Calculator tab (loads instantly)
2. Enter your constraints (ODs, ratio, etc.)
3. Review validation and export JSON
4. **Switch to Generator tab** when ready for 3D geometry
5. Click "Load Generator" (one-time ~1 minute wait)
6. Load JSON from calculator and generate STEP files

## Architecture

### Lazy Loading Strategy

The interface uses lazy loading to optimize user experience:

**On Page Load:**
- HTML/CSS/JavaScript loads instantly (~50KB)
- No Python/WASM loading yet
- UI is immediately interactive

**Calculator Tab (Lazy):**
- Loads Pyodide + calculator Python code when first accessed (~5MB)
- Takes ~5-10 seconds on first load
- Subsequent calculations are instant

**Generator Tab (Lazy):**
- Only loads when user clicks "Load Generator" button
- Loads Pyodide + OCP + build123d (~50MB total)
- Takes ~30-60 seconds on first load
- Users only wait if they actually need STEP file generation

This approach ensures:
- Fast initial page load
- No wasted bandwidth if user only needs calculator
- Clear expectation setting (user clicks "Load" button)

### Two Pyodide Instances

The app maintains separate Pyodide environments:

1. **Calculator Pyodide** - Lightweight, calculator-only
2. **Generator Pyodide** - Full environment with OCP + build123d

This separation:
- Keeps calculator fast and lightweight
- Avoids loading heavy 3D libraries unless needed
- Prevents memory issues from single bloated environment

## File Structure

```
web/
├── index.html              # Two-tab interface
├── app-lazy.js             # Lazy-loading application logic
├── app-backup.js           # Backup of original app.js
├── style.css               # Styles (with lazy-load overlays)
├── wormcalc/               # Python calculator code (for Pyodide)
│   ├── __init__.py
│   ├── core.py            # Calculator functions
│   ├── validation.py      # Validation rules
│   └── output.py          # JSON/Markdown export
├── wormgear-pyodide.js    # WASM geometry wrapper (experimental)
├── performance-test.html  # WASM performance testing
└── README.md              # This file
```

## Development Status

### ✅ Complete
- Calculator tab with lazy loading
- JSON Schema v1.0 export
- Validation and real-time updates
- Markdown export
- URL parameter sharing
- Tab interface with lazy initialization

### 🚧 In Progress
- Generator tab basic UI
- Lazy loading framework for OCP + build123d
- JSON input from calculator

### 📋 TODO
- Complete WASM geometry generation integration
- Progress callbacks during generation
- STEP file download
- 3D preview in browser
- Performance optimizations for large gears

## Performance

### Calculator Tab
- **Initial load**: <1 second (HTML/CSS/JS)
- **Pyodide load**: 5-10 seconds (lazy, on first calculation)
- **Calculations**: <100ms (instant after load)
- **Total data**: ~5MB

### Generator Tab
- **Initial load**: <1 second (shows "Load Generator" button)
- **Full load**: 30-60 seconds (when user clicks "Load Generator")
- **Generation**: 2-30 seconds depending on complexity
- **Total data**: ~50MB (OCP + build123d are large)

## Browser Compatibility

Requires modern browser with WebAssembly support:
- Chrome 88+
- Firefox 89+
- Safari 15+
- Edge 88+

## Deployment

### GitHub Pages

```bash
# From repository root
git add web/
git commit -m "Update web interface"
git push origin main

# Enable GitHub Pages on main branch /web/ directory
# Access at https://yourusername.github.io/worm-gear-3d/
```

### Static Hosting (Netlify, Vercel, etc.)

Point to `web/` directory as root. No build step required - pure static files.

## Technical Notes

### Why Lazy Loading?

Without lazy loading, users would wait 30-60 seconds on every page load, even if they only want to use the calculator. With lazy loading:

- **Calculator users**: 5-second wait (vs 60-second wait)
- **Generator users**: Same 60-second total wait, but split into two steps with clear indication
- **Bandwidth savings**: Users only download what they need

### Why Separate Pyodide Instances?

A single Pyodide instance with all dependencies would be:
- Slower to load (~60 seconds every time)
- Higher memory usage (~200MB vs 50MB for calculator)
- More complex error handling
- Harder to debug

Separate instances:
- Calculator stays lightweight and fast
- Generator can be reloaded independently if errors occur
- Clear separation of concerns

### CORS and File Access

When running locally with `python -m http.server`, you may encounter CORS issues if trying to load resources from different origins. Use the local server approach shown in Quick Start.

## URL Parameters

Share designs by encoding parameters in the URL:

```
https://pzfreo.github.io/worm-gear-3d/?mode=envelope&worm_od=20&wheel_od=65&ratio=30
```

All input parameters can be included for complete design sharing.

## Development

The Python files in `wormcalc/` are the calculator module. To update:

```bash
# Copy updated Python files from source if needed
# (Currently these are separate from main package)

# Commit and push
git add web/
git commit -m "Update web app"
git push
```

## Troubleshooting

### "Loading calculator..." never completes

- Check browser console for errors
- Ensure CDN access to Pyodide (cdn.jsdelivr.net)
- Try clearing browser cache
- Verify HTTP server is running (not file://)

### Generator fails to load

- Large download (~50MB) may timeout on slow connections
- Check browser console for WASM errors
- Try in different browser (Chrome/Firefox work best)
- Ensure sufficient memory available (>500MB free)

### Calculations not updating

- Check browser console for Python errors
- Verify all input fields have valid values
- Try refreshing the page

### Export buttons not working

- Copy to clipboard requires HTTPS (works on GitHub Pages)
- Check clipboard permissions in browser settings

## Known Issues

- **Generator WASM integration incomplete** - UI is ready, but full OCP + build123d integration needs completion
- **Mobile support limited** - Works on tablets, phones may struggle with large downloads
- **Safari memory** - Older Safari versions may have memory issues with large WASM files

## Future Enhancements

- [ ] Complete WASM geometry generation
- [ ] 3D preview using Three.js or OCP viewer
- [ ] Drag-and-drop JSON file upload
- [ ] Save/load designs to browser localStorage
- [ ] Design gallery with common configurations
- [ ] Export to other formats (STL, IGES)
- [ ] Integrated CAM toolpath preview

## Contributing

See [CLAUDE.md](../CLAUDE.md) for development guidelines.

## Credits

Created by Paul Fremantle (pzfreo) for designing custom worm gears for CNC manufacture and 3D printing.

Built with:
- [Pyodide](https://pyodide.org/) - Python in WebAssembly
- [build123d](https://build123d.readthedocs.io/) - CAD library (for geometry generator)
- Pure HTML/CSS/JavaScript - No build tools required

## License

MIT (to be added)

---

**Tip**: For the fastest experience, use the Calculator tab for design iteration, then switch to Generator tab only when you have a final design ready for manufacture.
