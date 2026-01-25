# Wormgear Studio - Vercel Deployment Guide

Deploying the Wormgear web interface to Vercel at **wormgear.studio**.

## Prerequisites

- Vercel account
- Domain **wormgear.studio** configured in Vercel
- GitHub repository connected to Vercel

## Deployment Configuration

### 1. Vercel Project Settings

In your Vercel project dashboard:

**Framework Preset:** Other

**Root Directory:** `web`

**Build Command:** (leave empty - static site, no build needed)

**Output Directory:** (leave empty - serves from root)

**Install Command:** (leave empty - no dependencies)

### 2. Environment Variables

No environment variables needed for the web interface.

### 3. Domain Configuration

**Production Domain:** wormgear.studio

**Git Branch:** main

Add the domain in Vercel:
1. Project Settings → Domains
2. Add: `wormgear.studio`
3. Configure DNS:
   - Type: A
   - Name: @
   - Value: 76.76.21.21 (Vercel IP)

   OR

   - Type: CNAME
   - Name: @
   - Value: cname.vercel-dns.com

4. Add: `www.wormgear.studio`
   - Type: CNAME
   - Name: www
   - Value: cname.vercel-dns.com

## Files for Deployment

### vercel.json
```json
{
  "version": 2,
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Cross-Origin-Embedder-Policy",
          "value": "require-corp"
        },
        {
          "key": "Cross-Origin-Opener-Policy",
          "value": "same-origin"
        }
      ]
    }
  ]
}
```

**Why these headers?**
- Required for SharedArrayBuffer support in Pyodide/WASM
- Enables multi-threading in WebAssembly
- Necessary for OCP + build123d to work in browser

### .vercelignore
Excludes Python source, tests, and documentation from deployment to keep deployment size minimal.

## Deployment Steps

### Option 1: Deploy via Git (Recommended)

```bash
# Push to main branch
git add .
git commit -m "Configure Vercel deployment"
git push origin main

# Vercel automatically deploys on push to main
```

### Option 2: Deploy via Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy to production
vercel --prod

# Or deploy preview
vercel
```

## Testing Deployment

After deployment:

1. **Visit:** https://wormgear.studio
2. **Test Calculator:**
   - Should load in ~5 seconds
   - Enter parameters, see results
   - Export JSON
3. **Test Generator (when implemented):**
   - Click "Load Generator"
   - Should load Pyodide + OCP (~60 seconds)
   - Load JSON from calculator
   - See design summary

## Troubleshooting

### "Loading calculator..." never completes

**Check:**
- Browser console for errors
- Network tab for failed requests
- CDN access to Pyodide (cdn.jsdelivr.net)

**Solution:**
- Clear browser cache
- Try different browser
- Check Vercel function logs

### CORS errors

**Check:**
- vercel.json headers are deployed
- Browser supports SharedArrayBuffer

**Solution:**
- Redeploy to ensure headers are applied
- Use modern browser (Chrome 88+, Firefox 89+, Safari 15+)

### Python files not loading

**Check:**
- web/wormcalc/*.py files are in deployment
- File paths in app-lazy.js are correct
- Content-Type headers

**Solution:**
- Ensure .vercelignore doesn't exclude web/wormcalc/
- Check Vercel deployment logs
- Verify file permissions

## Custom Domain Setup

### DNS Configuration

If using external DNS provider:

**For Apex Domain (@):**
```
Type: A
Name: @
Value: 76.76.21.21
TTL: 3600
```

**For WWW:**
```
Type: CNAME
Name: www
Value: cname.vercel-dns.com
TTL: 3600
```

### SSL Certificate

Vercel automatically provisions SSL certificates via Let's Encrypt.

**Verification:**
- Check: https://wormgear.studio (should have valid cert)
- Check: https://www.wormgear.studio (should redirect to apex or have cert)

## Performance Optimization

### Caching

Vercel automatically caches static assets:
- HTML/CSS/JS: Edge cache
- Python files: Edge cache
- WASM files: Edge cache with long TTL

### CDN

Vercel uses global edge network:
- Pyodide loads from cdn.jsdelivr.net (separate CDN)
- Static files served from nearest edge location
- Calculator ~5s first load, instant on reload

## Monitoring

### Vercel Analytics

Enable in project settings:
- Page views
- Performance metrics
- Geographic distribution

### Error Tracking

Monitor Vercel function logs for:
- 404 errors (missing files)
- 500 errors (server issues)
- CORS errors

## Rollback

To rollback to previous deployment:

1. Go to Vercel dashboard → Deployments
2. Find working deployment
3. Click "..." → Promote to Production

Or via CLI:
```bash
vercel rollback
```

## Production Checklist

- [ ] Root directory set to `web` in Vercel project
- [ ] vercel.json committed with CORS headers
- [ ] Domain wormgear.studio added to project
- [ ] DNS configured (A or CNAME records)
- [ ] SSL certificate provisioned (automatic)
- [ ] Test calculator tab loads and works
- [ ] Test generator tab UI (full WASM pending)
- [ ] Test on mobile devices
- [ ] Analytics enabled (optional)

## URLs

**Production:** https://wormgear.studio
**Preview:** https://worm-gear-3d-[hash].vercel.app (for PR previews)
**Repository:** https://github.com/pzfreo/worm-gear-3d

## Support

- **Vercel Docs:** https://vercel.com/docs
- **Pyodide Docs:** https://pyodide.org/
- **Repository Issues:** https://github.com/pzfreo/worm-gear-3d/issues

---

**Last Updated:** 2026-01-25
