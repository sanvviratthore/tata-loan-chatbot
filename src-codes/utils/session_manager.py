"""
Session Manager Utility Module

Provides session initialization, state management, and cleanup functionality
for maintaining conversation context across agent interactions.
"""

import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
from pathlib import Path


class SessionManager:
    """
    Manages user sessions with state persistence and TTL-based cleanup.
    
    Attributes:
        sessions: Dictionary storing active sessions
        session_ttl: Time-to-live for sessions in seconds
        storage_path: Optional path for session persistence
    """
    
    def __init__(self, session_ttl: int = 3600, storage_path: Optional[str] = None):
        """
        Initialize the session manager.
        
        Args:
            session_ttl: Session time-to-live in seconds (default: 3600 = 1 hour)
            storage_path: Optional path to persist sessions to disk
        """
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_ttl = session_ttl
        self.storage_path = Path(storage_path) if storage_path else None
        
        if self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self._load_sessions()
    
    def create_session(self, user_id: Optional[str] = None) -> str:
        """
        Create a new session with unique session ID.
        
        Args:
            user_id: Optional user identifier to associate with session
        
        Returns:
            Unique session ID
        """
        session_id = str(uuid.uuid4())
        
        self.sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(seconds=self.session_ttl)).isoformat(),
            "state": {},
            "conversation_history": [],
            "current_agent": None,
            "workflow_stage": "INIT"
        }
        
        self._persist_session(session_id)
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data by session ID.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session data dictionary or None if not found or expired
        """
        if session_id not in self.sessions:
            # Try loading from disk if storage is enabled
            if self.storage_path:
                self._load_session(session_id)
        
        if session_id in self.sessions:
            session = self.sessions[session_id]
            
            # Check if session has expired
            if self._is_expired(session):
                self.delete_session(session_id)
                return None
            
            # Update last accessed time
            session["last_accessed"] = datetime.now().isoformat()
            self._persist_session(session_id)
            
            return session
        
        return None
    
    def update_session_state(self, session_id: str, key: str, value: Any) -> bool:
        """
        Update a specific key in the session state.
        
        Args:
            session_id: Session identifier
            key: State key to update
            value: Value to store
        
        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session["state"][key] = value
        session["last_accessed"] = datetime.now().isoformat()
        self._persist_session(session_id)
        
        return True
    
    def get_session_state(self, session_id: str, key: str, default: Any = None) -> Any:
        """
        Retrieve a specific value from session state.
        
        Args:
            session_id: Session identifier
            key: State key to retrieve
            default: Default value if key not found
        
        Returns:
            Value from session state or default
        """
        session = self.get_session(session_id)
        if not session:
            return default
        
        return session["state"].get(key, default)
    
    def get_all_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve entire state dictionary for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Complete state dictionary or None if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        return session["state"]
    
    def add_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a message to the conversation history.
        
        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content
            agent: Optional agent name that generated the message
            metadata: Optional additional metadata
        
        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        message = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "agent": agent,
            "metadata": metadata or {}
        }
        
        session["conversation_history"].append(message)
        session["last_accessed"] = datetime.now().isoformat()
        self._persist_session(session_id)
        
        return True
    
    def get_conversation_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve conversation history for a session.
        
        Args:
            session_id: Session identifier
            limit: Optional limit on number of messages to return (most recent)
        
        Returns:
            List of conversation messages or None if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        history = session["conversation_history"]
        
        if limit and limit > 0:
            return history[-limit:]
        
        return history
    
    def set_current_agent(self, session_id: str, agent_name: str) -> bool:
        """
        Set the current active agent for the session.
        
        Args:
            session_id: Session identifier
            agent_name: Name of the current agent
        
        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session["current_agent"] = agent_name
        session["last_accessed"] = datetime.now().isoformat()
        self._persist_session(session_id)
        
        return True
    
    def get_current_agent(self, session_id: str) -> Optional[str]:
        """
        Get the current active agent for the session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Agent name or None if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        return session.get("current_agent")
    
    def set_workflow_stage(self, session_id: str, stage: str) -> bool:
        """
        Set the current workflow stage for the session.
        
        Args:
            session_id: Session identifier
            stage: Workflow stage name
        
        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session["workflow_stage"] = stage
        session["last_accessed"] = datetime.now().isoformat()
        self._persist_session(session_id)
        
        return True
    
    def get_workflow_stage(self, session_id: str) -> Optional[str]:
        """
        Get the current workflow stage for the session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Workflow stage or None if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        return session.get("workflow_stage")
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and its persisted data.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if session was deleted, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            
            # Delete persisted file if storage is enabled
            if self.storage_path:
                session_file = self.storage_path / f"{session_id}.json"
                if session_file.exists():
                    session_file.unlink()
            
            return True
        
        return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if self._is_expired(session):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.delete_session(session_id)
        
        return len(expired_sessions)
    
    def get_active_session_count(self) -> int:
        """
        Get count of active (non-expired) sessions.
        
        Returns:
            Number of active sessions
        """
        return len([s for s in self.sessions.values() if not self._is_expired(s)])
    
    def extend_session(self, session_id: str, additional_seconds: Optional[int] = None) -> bool:
        """
        Extend the TTL of a session.
        
        Args:
            session_id: Session identifier
            additional_seconds: Additional seconds to add (default: session_ttl)
        
        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        extension = additional_seconds if additional_seconds else self.session_ttl
        current_expiry = datetime.fromisoformat(session["expires_at"])
        new_expiry = current_expiry + timedelta(seconds=extension)
        
        session["expires_at"] = new_expiry.isoformat()
        session["last_accessed"] = datetime.now().isoformat()
        self._persist_session(session_id)
        
        return True
    
    def _is_expired(self, session: Dict[str, Any]) -> bool:
        """
        Check if a session has expired.
        
        Args:
            session: Session dictionary
        
        Returns:
            True if expired, False otherwise
        """
        expires_at = datetime.fromisoformat(session["expires_at"])
        return datetime.now() > expires_at
    
    def _persist_session(self, session_id: str) -> None:
        """
        Persist session to disk if storage is enabled.
        
        Args:
            session_id: Session identifier
        """
        if not self.storage_path or session_id not in self.sessions:
            return
        
        session_file = self.storage_path / f"{session_id}.json"
        
        try:
            with open(session_file, 'w') as f:
                json.dump(self.sessions[session_id], f, indent=2)
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Warning: Failed to persist session {session_id}: {e}")
    
    def _load_session(self, session_id: str) -> None:
        """
        Load a session from disk if storage is enabled.
        
        Args:
            session_id: Session identifier
        """
        if not self.storage_path:
            return
        
        session_file = self.storage_path / f"{session_id}.json"
        
        if not session_file.exists():
            return
        
        try:
            with open(session_file, 'r') as f:
                self.sessions[session_id] = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load session {session_id}: {e}")
    
    def _load_sessions(self) -> None:
        """
        Load all sessions from disk if storage is enabled.
        """
        if not self.storage_path:
            return
        
        for session_file in self.storage_path.glob("*.json"):
            session_id = session_file.stem
            self._load_session(session_id)
