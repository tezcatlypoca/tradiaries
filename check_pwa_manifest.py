#!/usr/bin/env python3
"""Check if PWA manifest is correctly rendered with icon URLs."""

import json
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.template.loader import render_to_string

# Rendre le manifest
manifest_html = render_to_string('pwa/manifest.webmanifest', {})
manifest_json = json.loads(manifest_html)

print("✅ Manifest JSON is valid")
print(f"\nManifest properties:")
print(f"  - name: {manifest_json.get('name')}")
print(f"  - short_name: {manifest_json.get('short_name')}")
print(f"  - display: {manifest_json.get('display')}")
print(f"  - scope: {manifest_json.get('scope')}")
print(f"  - start_url: {manifest_json.get('start_url')}")
print(f"  - theme_color: {manifest_json.get('theme_color')}")

print(f"\n📦 Icons ({len(manifest_json.get('icons', []))} total):")
for icon in manifest_json.get('icons', []):
    print(f"  - src: {icon.get('src')}")
    print(f"    sizes: {icon.get('sizes')}")
    print(f"    type: {icon.get('type')}")
    print(f"    purpose: {icon.get('purpose', 'any')}")

print(f"\n🖼️ Screenshots ({len(manifest_json.get('screenshots', []))} total):")
for ss in manifest_json.get('screenshots', []):
    print(f"  - src: {ss.get('src')}")
    print(f"    sizes: {ss.get('sizes')}")
    print(f"    form_factor: {ss.get('form_factor')}")

# Check for critical PWA requirements
print(f"\n✓ PWA Installability Checklist:")
errors = []

if not manifest_json.get('name'):
    errors.append("❌ Missing 'name'")
else:
    print("✅ Has 'name'")

if not manifest_json.get('short_name'):
    errors.append("❌ Missing 'short_name'")
else:
    print("✅ Has 'short_name'")

if manifest_json.get('display') != 'standalone':
    errors.append("❌ display is not 'standalone'")
else:
    print("✅ display is 'standalone'")

if not manifest_json.get('start_url'):
    errors.append("❌ Missing 'start_url'")
else:
    print("✅ Has 'start_url'")

if not manifest_json.get('scope'):
    errors.append("❌ Missing 'scope'")
else:
    print("✅ Has 'scope'")

# Check for at least 2 PNG icons (Chrome requirement)
png_icons = [i for i in manifest_json.get('icons', []) if i.get('type') == 'image/png']
if len(png_icons) < 2:
    errors.append(f"❌ Need at least 2 PNG icons (have {len(png_icons)})")
else:
    print(f"✅ Has {len(png_icons)} PNG icons")

# Check for 192x192 and 512x512
sizes_512 = any(i.get('sizes') == '512x512' for i in manifest_json.get('icons', []))
sizes_192 = any(i.get('sizes') == '192x192' for i in manifest_json.get('icons', []))

if not sizes_512:
    errors.append("❌ Missing 512x512 icon")
else:
    print("✅ Has 512x512 icon")

if not sizes_192:
    errors.append("❌ Missing 192x192 icon")
else:
    print("✅ Has 192x192 icon")

if errors:
    print("\n⚠️ Issues found:")
    for error in errors:
        print(f"  {error}")
else:
    print("\n🎉 All PWA requirements met!")
