"""
SAFE Framework Integration Template
====================================
Copy this file to your app root and customize for your data streams.
"""

from typing import Dict, List, Optional
from datetime import datetime


# Define your app's data streams here
# These must match the stream IDs in safe-app-manifest.json
APP_STREAMS = [
    {
        "stream_id": "primary_data",
        "purpose": "Describe what this data is used for",
        "retention": "session",
        "required": True,
        "prompt": "May I access your data this session?"
    }
]


class SAFESession:
    """Manages SAFE session lifecycle and consent."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.started_at = datetime.now()
        self.consents = {}
        self.active = True

    def on_session_start(self) -> Dict:
        return {
            "session_id": self.session_id,
            "authorization_requests": APP_STREAMS
        }

    def on_consent_granted(self, stream_id: str, granted: bool) -> Dict:
        self.consents[stream_id] = {
            "granted": granted,
            "timestamp": datetime.now().isoformat()
        }
        if not granted:
            required = next((s for s in APP_STREAMS if s["stream_id"] == stream_id and s.get("required")), None)
            if required:
                return {"status": "consent_required", "message": f"{stream_id} consent required to use this app."}
        return {"status": "ok"}

    def can_access_stream(self, stream_id: str) -> bool:
        return self.consents.get(stream_id, {}).get("granted", False)

    def on_session_end(self) -> Dict:
        self.active = False
        actions = []
        for stream in APP_STREAMS:
            sid = stream["stream_id"]
            if self.can_access_stream(sid):
                retention = stream.get("retention", "session")
                actions.append({
                    "action": "retain" if retention == "permanent" else "delete",
                    "stream": sid,
                    "reason": "permanent_consent" if retention == "permanent" else "session_ended"
                })
        return {
            "session_id": self.session_id,
            "ended_at": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - self.started_at).total_seconds(),
            "cleanup_actions": actions
        }

    def on_revoke(self, stream_id: str) -> Dict:
        if stream_id in self.consents:
            self.consents[stream_id]["granted"] = False
            self.consents[stream_id]["revoked_at"] = datetime.now().isoformat()
        return {"status": "revoked", "stream": stream_id, "action": "data_deleted"}
