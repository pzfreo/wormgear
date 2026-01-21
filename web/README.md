# Worm Gear 3D - Web Interface (Experimental Prototype)

Browser-based 3D CAD generation for worm gears using Pyodide and build123d.

## Overview

**Status: 🚧 Experimental Prototype**

This web interface is a proof-of-concept that demonstrates browser-based STEP file generation with no server-side processing. It accepts JSON design files from the [wormgearcalc](https://pzfreo.github.io/wormgearcalc/) tool and generates 3D geometry using build123d running in WebAssembly via Pyodide.

**What works:** Core CAD generation, STEP downloads
**In progress:** 3D visualization, progress indicators, UI/UX polish
**Planned:** Full integration per [WEB_TOOL_SPEC_V2.md](../docs/WEB_TOOL_SPEC_V2.md)

## Features

- ✅ **Client-side Processing**: All CAD generation happens in your browser
- ✅ **No Installation**: No Python or dependencies to install locally
- ✅ **JSON Import**: Load designs from wormgearcalc or paste JSON directly
- ✅ **Interactive Controls**: Adjust worm length, wheel width, and features
- ✅ **STEP Export**: Download CNC-ready files for machining
- 🚧 **3D Preview**: Real-time visualization (coming soon)

## Quick Start

### Option 1: Local Development Server

```bash
# From the worm-gear-3d directory
cd web
python3 -m http.server 8000
```

Then open http://localhost:8000 in your browser.

### Option 2: Static Hosting

Upload the `web/` directory to any static hosting service:
- GitHub Pages
- Netlify
- Vercel
- AWS S3
- Or any web server

## Usage

### 1. Load a Design

**Option A: Use Sample Designs**
- Click "Sample M2 Ratio 30:1" or "7mm Design" buttons
- Pre-loaded example designs from the calculator

**Option B: Upload JSON File**
- Drag and drop a `.json` file from wormgearcalc
- Or click the drop zone to browse

**Option C: Paste JSON**
- Copy JSON from the calculator
- Paste directly into the text area

### 2. Configure Parameters

- **Worm Length**: Physical length of worm gear (default: 40mm)
- **Wheel Width**: Face width of wheel (leave blank for auto-calculation)
- **Wheel Type**:
  - Helical (default): Simpler flat-bottomed teeth
  - Hobbed: Throated teeth matching worm curvature
- **Add Bore**: Include central bore
- **Add Keyway**: Add DIN 6885 standard keyway

### 3. Generate

Click "Generate STEP Files" to create the geometry. Download buttons will appear for:
- `worm.step` - Worm gear
- `wheel.step` - Wheel gear

## Technical Details

### Architecture

```
┌─────────────────────────────────────────┐
│  index.html (Single Page App)          │
├─────────────────────────────────────────┤
│  Pyodide v0.25.0                        │
│  ├─ Python 3.11 in WebAssembly          │
│  ├─ micropip (package installer)        │
│  └─ build123d + OCP (CAD kernel)        │
├─────────────────────────────────────────┤
│  wormgear_geometry package              │
│  ├─ Loaded from ../src/                 │
│  ├─ WormGeometry class                  │
│  └─ WheelGeometry class                 │
├─────────────────────────────────────────┤
│  Three.js / model-viewer (planned)      │
│  └─ WebGL 3D visualization              │
└─────────────────────────────────────────┘
```

### Dependencies

**Loaded from CDN:**
- Pyodide 0.25.0 - Python runtime in WebAssembly
- build123d - CAD library (installed via micropip)
- OCP - OpenCascade bindings (bundled with build123d)

**Local:**
- wormgear_geometry - This project's source code

### Current Status

**✅ Implemented:**
- Pyodide initialization and loading
- OCP.wasm integration via package index
- build123d installation from WebAssembly builds
- UI for JSON input (file upload, drag-drop, paste)
- Parameter controls (worm length, wheel width, wheel type)
- Console output with color-coded logging
- Sample design loading from examples/
- wormgear_geometry package loading
- Full geometry generation (worm + wheel)
- STEP file download to browser
- GitHub Pages deployment workflow

**🚧 In Progress:**
- 3D visualization with Three.js/model-viewer
- Progress indicators for long operations

**📋 Planned:**
- Mobile responsive design improvements
- Advanced error recovery
- Offline support with service worker
- Geometry preview thumbnails

## Known Issues

### build123d in Pyodide

build123d depends on OCP (OpenCascade), which requires a special WebAssembly build. The standard `micropip install build123d` may not work out of the box.

**Solutions being explored:**
1. Use pre-built OCP.wasm from [yet-another-cad-viewer](https://github.com/yeicor-3d/yet-another-cad-viewer)
2. Build custom Pyodide package with OCP included
3. Alternative: Generate GLTF/STL instead of STEP using pure Python geometry

### Browser Compatibility

Requires modern browser with:
- WebAssembly support
- ES6+ JavaScript
- Sufficient memory (recommend 4GB+ RAM)

**Tested browsers:**
- Chrome 90+
- Firefox 88+
- Safari 15+
- Edge 90+

## Development

### Project Structure

```
web/
├── index.html          # Main application (self-contained)
├── README.md           # This file
└── serve.py            # Development server helper
```

### Testing Locally

```bash
# Install build123d normally (for comparison)
pip install build123d

# Run the web interface
cd web
python3 -m http.server 8000
```

### Debugging

The interface includes a console panel that shows:
- Pyodide loading status
- Package installation progress
- Python errors and output
- JSON validation messages

Browser DevTools console shows additional technical details.

## Integration with Calculator

### Standalone Deployment

Deploy this web app independently and link from wormgearcalc:

```html
<a href="https://yoursite.com/worm-gear-3d-web/?design=..."
   target="_blank">
  Generate 3D Models
</a>
```

### Embedded Widget

Embed in the calculator page using iframe:

```html
<iframe src="https://yoursite.com/worm-gear-3d-web/"
        width="100%" height="800px">
</iframe>
```

Pass design data via postMessage:

```javascript
iframe.contentWindow.postMessage({
  type: 'loadDesign',
  design: designJSON
}, '*');
```

## Deployment

**Note:** This is an experimental prototype. While functional for testing, consider completing the items in the deployment checklist below before production use.

### Quick Deploy to GitHub Pages (for testing/development)

1. Push to main branch:
   ```bash
   git push origin main
   ```

2. Enable GitHub Pages:
   - Go to repository Settings → Pages
   - Source: "GitHub Actions"

3. Wait for deployment (2-3 minutes)

4. Access at:
   ```
   https://your-username.github.io/worm-gear-3d/
   ```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions including Netlify, Vercel, Cloudflare Pages, and custom domains.

## Deployment Checklist

**✅ Prototype Complete (Current State):**
- [x] OCP.wasm integration complete
- [x] Geometry generation functional
- [x] STEP file download working
- [x] GitHub Pages workflow configured

**🚧 Required Before Production Deployment:**
- [ ] Test with all sample designs
- [ ] Verify on multiple browsers (Chrome, Firefox, Safari, Edge)
- [ ] Test on mobile devices
- [ ] Add 3D visualization
- [ ] Add loading progress indicators
- [ ] Optimize initial load time (currently ~30-60s)
- [ ] Add error recovery and user-friendly error messages
- [ ] Comprehensive UI/UX review and improvements

**📋 Optional Enhancements:**
- [ ] Add usage analytics
- [ ] Implement service worker for offline support
- [ ] Add geometry preview thumbnails

## Contributing

This is part of the [worm-gear-3d](https://github.com/pzfreo/worm-gear-3d) project.

See the main project README for contribution guidelines.

## License

Same as parent project - see LICENSE file.

## Resources

- [Pyodide Documentation](https://pyodide.org/)
- [build123d Documentation](https://build123d.readthedocs.io/)
- [wormgearcalc Calculator](https://pzfreo.github.io/wormgearcalc/)
- [Yet Another CAD Viewer](https://github.com/yeicor-3d/yet-another-cad-viewer) - Reference implementation
