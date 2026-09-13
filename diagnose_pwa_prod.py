#!/usr/bin/env python3
"""Diagnostic PWA : vérifier que tous les assets listés dans le manifest en prod sont accessibles."""

import json
import urllib.request
import urllib.error

MANIFEST_URL = "https://tradiaries.onrender.com/manifest.webmanifest"
PROD_BASE = "https://tradiaries.onrender.com"

def check_url(url):
    """Check if a URL is accessible (200 status)."""
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            content_type = response.headers.get('Content-Type', 'N/A')
            return status, content_type
    except urllib.error.HTTPError as e:
        return e.code, "N/A"
    except Exception as e:
        return None, str(e)

# 1. Fetch manifest
print("🔍 Fetching manifest from production...")
try:
    with urllib.request.urlopen(MANIFEST_URL, timeout=10) as response:
        manifest_json = json.loads(response.read().decode('utf-8'))
        print(f"✅ Manifest is valid JSON ({response.status})")
except Exception as e:
    print(f"❌ Failed to fetch manifest: {e}")
    exit(1)

# 2. Check display and basic properties
print(f"\n📋 Manifest properties:")
print(f"  name: {manifest_json.get('name')}")
print(f"  display: {manifest_json.get('display')}")
print(f"  scope: {manifest_json.get('scope')}")
print(f"  start_url: {manifest_json.get('start_url')}")

# 3. Check all icons
print(f"\n🖼️ Checking icons accessibility:")
icon_errors = []
for icon in manifest_json.get('icons', []):
    icon_src = icon.get('src')
    icon_sizes = icon.get('sizes')
    icon_type = icon.get('type')
    
    # Build full URL
    if icon_src.startswith('/'):
        full_url = f"{PROD_BASE}{icon_src}"
    else:
        full_url = f"{PROD_BASE}/{icon_src}"
    
    status, content_type = check_url(full_url)
    
    if status == 200:
        print(f"  ✅ {icon_sizes:8s} {icon_type:16s} {icon_src}")
    else:
        print(f"  ❌ {icon_sizes:8s} {icon_type:16s} {icon_src} → {status}")
        icon_errors.append(f"{icon_src} ({status})")

# 4. Check manifest itself
print(f"\n📦 Checking manifest URL:")
status, ct = check_url(MANIFEST_URL)
if status == 200:
    print(f"  ✅ manifest.webmanifest is accessible ({ct})")
else:
    print(f"  ❌ manifest.webmanifest returned {status}")

# 5. Check service worker
print(f"\n⚙️ Checking service worker:")
sw_url = f"{PROD_BASE}/service-worker.js"
status, ct = check_url(sw_url)
if status == 200:
    print(f"  ✅ /service-worker.js is accessible ({ct})")
    # Try to fetch and check for content
    try:
        with urllib.request.urlopen(sw_url, timeout=10) as response:
            sw_content = response.read().decode('utf-8')
            if 'CACHE_NAME' in sw_content:
                print(f"  ✅ Service worker contains expected code")
            else:
                print(f"  ⚠️ Service worker might be invalid")
    except Exception as e:
        print(f"  ⚠️ Could not read service worker: {e}")
else:
    print(f"  ❌ /service-worker.js returned {status}")

# Summary
print(f"\n{'='*60}")
if icon_errors:
    print(f"⚠️ ISSUES FOUND:")
    print(f"Missing or inaccessible icons:")
    for err in icon_errors:
        print(f"  - {err}")
    print(f"\nSolution: Run 'python manage.py collectstatic' on Render")
    print(f"or ensure candlestick-icon-*.png files exist in static/icons/")
else:
    print(f"✅ All PWA assets are accessible in production!")
