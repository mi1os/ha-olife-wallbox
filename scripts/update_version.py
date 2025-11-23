#!/usr/bin/env python3
"""Update version in manifest.json for semantic-release."""
import json
import sys
from pathlib import Path

def update_version(new_version: str) -> None:
    """Update version in manifest.json.
    
    Args:
        new_version: The new semantic version (without 'v' prefix)
    """
    manifest_path = Path(__file__).parent.parent / "custom_components" / "olife_wallbox" / "manifest.json"
    
    # Read current manifest
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    # Update version
    old_version = manifest.get('version', 'unknown')
    manifest['version'] = new_version
    
    # Write updated manifest
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write('\n')  # Add trailing newline
    
    print(f"✓ Updated manifest.json: {old_version} → {new_version}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: update_version.py <version>")
        sys.exit(1)
    
    version = sys.argv[1]
    update_version(version)
