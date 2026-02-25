# Willow Seed — Quickstart

## What You're Starting From

You cloned willow-seed. This is the minimal bootstrap for a SAFE-compliant app in the Willow ecosystem.

## Setup

1. **Rename the manifest**
   ```
   cp safe-app-manifest.template.json safe-app-manifest.json
   ```
   Edit `safe-app-manifest.json` with your app's identity.

2. **Copy the integration layer**
   ```
   cp safe_integration.template.py safe_integration.py
   ```
   Edit `APP_STREAMS` to match your data streams.

3. **Install deps**
   ```
   pip install -r requirements.txt
   ```

4. **Build your app**
   Your app code goes in a module matching the `entry_point` in your manifest.

## SAFE Principles

- **Session consent**: Ask permission every time. It expires when the session ends.
- **Local-first**: Data lives on the user's machine.
- **Minimal permissions**: Only request what you actually use.
- **No engagement optimization**: Your app is a tool, not a trap.

## Connecting to Willow

When your Willow node is running (default port 8420), your app can register via opauth:

```python
import requests
resp = requests.post("http://localhost:8420/api/opauth/register", json={
    "app_id": "your-app-id",
    "manifest_path": "safe-app-manifest.json"
})
```

## ΔΣ=42
