"""
Session Memory - Short-term in-memory store with TTL.
Stores conversation context, active business cases, and session state.
No Redis dependency - runs purely in-process.
"""
import time
import uuid
from typing import Any, Optional


class SessionMemory:
    """Thread-safe in-memory session store with TTL expiration."""
    
    def __init__(self, default_ttl: int = 3600):
        """
        Args:
            default_ttl: Default time-to-live in seconds (1 hour)
        """
        self._store: dict[str, dict] = {}
        self._ttl = default_ttl
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new session and return its ID."""
        sid = session_id or str(uuid.uuid4())
        self._store[sid] = {
            "_created": time.time(),
            "_updated": time.time(),
            "_ttl": self._ttl,
            "history": [],
            "business_state": None,
            "stage": None,
            "active_ideas": [],
            "context": {}
        }
        return sid
    
    def get(self, session_id: str, key: str, default: Any = None) -> Any:
        """Get a value from a session."""
        self._cleanup_expired()
        session = self._store.get(session_id)
        if not session:
            return default
        return session.get(key, default)
    
    def set(self, session_id: str, key: str, value: Any) -> None:
        """Set a value in a session."""
        if session_id not in self._store:
            self.create_session(session_id)
        self._store[session_id][key] = value
        self._store[session_id]["_updated"] = time.time()
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Get full session data."""
        self._cleanup_expired()
        return self._store.get(session_id)
    
    def append_history(self, session_id: str, role: str, content: str) -> None:
        """Append to conversation history."""
        if session_id not in self._store:
            self.create_session(session_id)
        self._store[session_id]["history"].append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        self._store[session_id]["_updated"] = time.time()
    
    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        self._store.pop(session_id, None)
    
    def _cleanup_expired(self) -> None:
        """Remove expired sessions."""
        now = time.time()
        expired = [
            sid for sid, data in self._store.items()
            if now - data.get("_updated", 0) > data.get("_ttl", self._ttl)
        ]
        for sid in expired:
            del self._store[sid]


# Global instance
session_memory = SessionMemory()
