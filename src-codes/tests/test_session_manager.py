"""
Unit tests for session manager utility module.
"""

import pytest
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from utils.session_manager import SessionManager


@pytest.fixture
def session_manager():
    """Create a session manager instance for testing."""
    return SessionManager(session_ttl=3600)


@pytest.fixture
def session_manager_with_storage():
    """Create a session manager with temporary storage."""
    temp_dir = tempfile.mkdtemp()
    manager = SessionManager(session_ttl=3600, storage_path=temp_dir)
    yield manager
    # Cleanup
    shutil.rmtree(temp_dir)


class TestSessionCreation:
    """Test cases for session creation."""
    
    def test_create_session_without_user_id(self, session_manager):
        """Test creating a session without user ID."""
        session_id = session_manager.create_session()
        
        assert session_id is not None
        assert isinstance(session_id, str)
        assert len(session_id) > 0
    
    def test_create_session_with_user_id(self, session_manager):
        """Test creating a session with user ID."""
        user_id = "user123"
        session_id = session_manager.create_session(user_id=user_id)
        
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session["user_id"] == user_id
    
    def test_session_has_required_fields(self, session_manager):
        """Test that created session has all required fields."""
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        assert "session_id" in session
        assert "user_id" in session
        assert "created_at" in session
        assert "last_accessed" in session
        assert "expires_at" in session
        assert "state" in session
        assert "conversation_history" in session
        assert "current_agent" in session
        assert "workflow_stage" in session
    
    def test_session_initial_values(self, session_manager):
        """Test initial values of created session."""
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        assert session["state"] == {}
        assert session["conversation_history"] == []
        assert session["current_agent"] is None
        assert session["workflow_stage"] == "initial"
    
    def test_unique_session_ids(self, session_manager):
        """Test that each session gets a unique ID."""
        session_id1 = session_manager.create_session()
        session_id2 = session_manager.create_session()
        
        assert session_id1 != session_id2


class TestSessionRetrieval:
    """Test cases for session retrieval."""
    
    def test_get_existing_session(self, session_manager):
        """Test retrieving an existing session."""
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        assert session is not None
        assert session["session_id"] == session_id
    
    def test_get_nonexistent_session(self, session_manager):
        """Test retrieving a non-existent session."""
        session = session_manager.get_session("nonexistent_id")
        
        assert session is None
    
    def test_get_session_updates_last_accessed(self, session_manager):
        """Test that getting a session updates last_accessed time."""
        session_id = session_manager.create_session()
        
        # Get initial last_accessed time
        session1 = session_manager.get_session(session_id)
        last_accessed1 = session1["last_accessed"]
        
        # Wait a bit and get again
        time.sleep(0.1)
        session2 = session_manager.get_session(session_id)
        last_accessed2 = session2["last_accessed"]
        
        assert last_accessed2 > last_accessed1


class TestSessionState:
    """Test cases for session state management."""
    
    def test_update_session_state(self, session_manager):
        """Test updating session state."""
        session_id = session_manager.create_session()
        
        result = session_manager.update_session_state(session_id, "user_name", "John Doe")
        
        assert result is True
        assert session_manager.get_session_state(session_id, "user_name") == "John Doe"
    
    def test_update_multiple_state_values(self, session_manager):
        """Test updating multiple state values."""
        session_id = session_manager.create_session()
        
        session_manager.update_session_state(session_id, "pan", "ABCDE1234F")
        session_manager.update_session_state(session_id, "mobile", "9876543210")
        session_manager.update_session_state(session_id, "credit_score", 750)
        
        assert session_manager.get_session_state(session_id, "pan") == "ABCDE1234F"
        assert session_manager.get_session_state(session_id, "mobile") == "9876543210"
        assert session_manager.get_session_state(session_id, "credit_score") == 750
    
    def test_get_session_state_with_default(self, session_manager):
        """Test getting session state with default value."""
        session_id = session_manager.create_session()
        
        value = session_manager.get_session_state(session_id, "nonexistent_key", "default_value")
        
        assert value == "default_value"
    
    def test_get_all_state(self, session_manager):
        """Test retrieving all state at once."""
        session_id = session_manager.create_session()
        
        session_manager.update_session_state(session_id, "key1", "value1")
        session_manager.update_session_state(session_id, "key2", "value2")
        
        all_state = session_manager.get_all_state(session_id)
        
        assert all_state == {"key1": "value1", "key2": "value2"}
    
    def test_update_state_for_nonexistent_session(self, session_manager):
        """Test updating state for non-existent session."""
        result = session_manager.update_session_state("nonexistent_id", "key", "value")
        
        assert result is False


class TestConversationHistory:
    """Test cases for conversation history management."""
    
    def test_add_conversation_message(self, session_manager):
        """Test adding a message to conversation history."""
        session_id = session_manager.create_session()
        
        result = session_manager.add_conversation_message(
            session_id, "user", "Hello, I need a loan"
        )
        
        assert result is True
        history = session_manager.get_conversation_history(session_id)
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello, I need a loan"
    
    def test_add_multiple_messages(self, session_manager):
        """Test adding multiple messages."""
        session_id = session_manager.create_session()
        
        session_manager.add_conversation_message(session_id, "user", "Hello")
        session_manager.add_conversation_message(session_id, "assistant", "Hi there!")
        session_manager.add_conversation_message(session_id, "user", "I need help")
        
        history = session_manager.get_conversation_history(session_id)
        assert len(history) == 3
    
    def test_message_with_agent_and_metadata(self, session_manager):
        """Test adding message with agent and metadata."""
        session_id = session_manager.create_session()
        
        metadata = {"intent": "loan_inquiry", "confidence": 0.95}
        session_manager.add_conversation_message(
            session_id,
            "assistant",
            "Let me help you with that",
            agent="master_agent",
            metadata=metadata
        )
        
        history = session_manager.get_conversation_history(session_id)
        message = history[0]
        
        assert message["agent"] == "master_agent"
        assert message["metadata"] == metadata
    
    def test_get_conversation_history_with_limit(self, session_manager):
        """Test retrieving limited conversation history."""
        session_id = session_manager.create_session()
        
        for i in range(10):
            session_manager.add_conversation_message(session_id, "user", f"Message {i}")
        
        history = session_manager.get_conversation_history(session_id, limit=3)
        
        assert len(history) == 3
        assert history[0]["content"] == "Message 7"
        assert history[2]["content"] == "Message 9"
    
    def test_message_has_timestamp(self, session_manager):
        """Test that messages have timestamps."""
        session_id = session_manager.create_session()
        
        session_manager.add_conversation_message(session_id, "user", "Test message")
        
        history = session_manager.get_conversation_history(session_id)
        assert "timestamp" in history[0]
        
        # Verify timestamp is valid ISO format
        timestamp = datetime.fromisoformat(history[0]["timestamp"])
        assert isinstance(timestamp, datetime)


class TestAgentTracking:
    """Test cases for current agent tracking."""
    
    def test_set_current_agent(self, session_manager):
        """Test setting current agent."""
        session_id = session_manager.create_session()
        
        result = session_manager.set_current_agent(session_id, "verification_agent")
        
        assert result is True
        assert session_manager.get_current_agent(session_id) == "verification_agent"
    
    def test_update_current_agent(self, session_manager):
        """Test updating current agent."""
        session_id = session_manager.create_session()
        
        session_manager.set_current_agent(session_id, "verification_agent")
        session_manager.set_current_agent(session_id, "credit_bureau_agent")
        
        assert session_manager.get_current_agent(session_id) == "credit_bureau_agent"
    
    def test_get_current_agent_for_nonexistent_session(self, session_manager):
        """Test getting current agent for non-existent session."""
        agent = session_manager.get_current_agent("nonexistent_id")
        
        assert agent is None


class TestWorkflowStage:
    """Test cases for workflow stage tracking."""
    
    def test_set_workflow_stage(self, session_manager):
        """Test setting workflow stage."""
        session_id = session_manager.create_session()
        
        result = session_manager.set_workflow_stage(session_id, "identity_verification")
        
        assert result is True
        assert session_manager.get_workflow_stage(session_id) == "identity_verification"
    
    def test_update_workflow_stage(self, session_manager):
        """Test updating workflow stage."""
        session_id = session_manager.create_session()
        
        session_manager.set_workflow_stage(session_id, "identity_verification")
        session_manager.set_workflow_stage(session_id, "credit_analysis")
        
        assert session_manager.get_workflow_stage(session_id) == "credit_analysis"
    
    def test_initial_workflow_stage(self, session_manager):
        """Test initial workflow stage value."""
        session_id = session_manager.create_session()
        
        assert session_manager.get_workflow_stage(session_id) == "initial"


class TestSessionDeletion:
    """Test cases for session deletion."""
    
    def test_delete_existing_session(self, session_manager):
        """Test deleting an existing session."""
        session_id = session_manager.create_session()
        
        result = session_manager.delete_session(session_id)
        
        assert result is True
        assert session_manager.get_session(session_id) is None
    
    def test_delete_nonexistent_session(self, session_manager):
        """Test deleting a non-existent session."""
        result = session_manager.delete_session("nonexistent_id")
        
        assert result is False


class TestSessionExpiration:
    """Test cases for session expiration and cleanup."""
    
    def test_session_expiration(self):
        """Test that expired sessions are not returned."""
        # Create manager with 1 second TTL
        manager = SessionManager(session_ttl=1)
        session_id = manager.create_session()
        
        # Session should exist initially
        assert manager.get_session(session_id) is not None
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Session should be expired and return None
        assert manager.get_session(session_id) is None
    
    def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions."""
        manager = SessionManager(session_ttl=1)
        
        # Create multiple sessions
        session_id1 = manager.create_session()
        session_id2 = manager.create_session()
        session_id3 = manager.create_session()
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Cleanup expired sessions
        count = manager.cleanup_expired_sessions()
        
        assert count == 3
        assert manager.get_session(session_id1) is None
        assert manager.get_session(session_id2) is None
        assert manager.get_session(session_id3) is None
    
    def test_extend_session(self, session_manager):
        """Test extending session TTL."""
        session_id = session_manager.create_session()
        
        # Get initial expiry time
        session1 = session_manager.get_session(session_id)
        expires_at1 = datetime.fromisoformat(session1["expires_at"])
        
        # Extend session
        result = session_manager.extend_session(session_id, 1800)
        
        # Get new expiry time
        session2 = session_manager.get_session(session_id)
        expires_at2 = datetime.fromisoformat(session2["expires_at"])
        
        assert result is True
        assert expires_at2 > expires_at1
    
    def test_get_active_session_count(self):
        """Test getting count of active sessions."""
        manager = SessionManager(session_ttl=1)
        
        # Create sessions
        manager.create_session()
        manager.create_session()
        manager.create_session()
        
        assert manager.get_active_session_count() == 3
        
        # Wait for expiration
        time.sleep(1.1)
        
        assert manager.get_active_session_count() == 0


class TestSessionPersistence:
    """Test cases for session persistence to disk."""
    
    def test_session_persisted_to_disk(self, session_manager_with_storage):
        """Test that sessions are persisted to disk."""
        session_id = session_manager_with_storage.create_session()
        
        # Check that file was created
        storage_path = Path(session_manager_with_storage.storage_path)
        session_file = storage_path / f"{session_id}.json"
        
        assert session_file.exists()
    
    def test_load_session_from_disk(self):
        """Test loading session from disk."""
        temp_dir = tempfile.mkdtemp()
        
        # Create manager and session
        manager1 = SessionManager(session_ttl=3600, storage_path=temp_dir)
        session_id = manager1.create_session(user_id="user123")
        manager1.update_session_state(session_id, "test_key", "test_value")
        
        # Create new manager instance (simulating restart)
        manager2 = SessionManager(session_ttl=3600, storage_path=temp_dir)
        
        # Session should be loaded from disk
        session = manager2.get_session(session_id)
        
        assert session is not None
        assert session["user_id"] == "user123"
        assert session["state"]["test_key"] == "test_value"
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_delete_session_removes_file(self, session_manager_with_storage):
        """Test that deleting session removes persisted file."""
        session_id = session_manager_with_storage.create_session()
        
        storage_path = Path(session_manager_with_storage.storage_path)
        session_file = storage_path / f"{session_id}.json"
        
        # File should exist
        assert session_file.exists()
        
        # Delete session
        session_manager_with_storage.delete_session(session_id)
        
        # File should be removed
        assert not session_file.exists()


class TestIntegrationScenarios:
    """Integration tests for realistic session scenarios."""
    
    def test_complete_loan_journey_session(self, session_manager):
        """Test session management through complete loan journey."""
        # Create session
        session_id = session_manager.create_session(user_id="user123")
        
        # Identity verification stage
        session_manager.set_workflow_stage(session_id, "identity_verification")
        session_manager.set_current_agent(session_id, "verification_agent")
        session_manager.update_session_state(session_id, "pan", "ABCDE1234F")
        session_manager.update_session_state(session_id, "mobile", "9876543210")
        session_manager.add_conversation_message(
            session_id, "user", "My PAN is ABCDE1234F", agent="verification_agent"
        )
        
        # Credit analysis stage
        session_manager.set_workflow_stage(session_id, "credit_analysis")
        session_manager.set_current_agent(session_id, "credit_bureau_agent")
        session_manager.update_session_state(session_id, "credit_score", 750)
        session_manager.update_session_state(session_id, "active_loans", 2)
        
        # Consolidation offer stage
        session_manager.set_workflow_stage(session_id, "consolidation_offer")
        session_manager.set_current_agent(session_id, "consolidation_agent")
        session_manager.update_session_state(session_id, "offer_accepted", True)
        
        # Verify complete state
        state = session_manager.get_all_state(session_id)
        assert state["pan"] == "ABCDE1234F"
        assert state["credit_score"] == 750
        assert state["offer_accepted"] is True
        
        # Verify workflow progression
        assert session_manager.get_workflow_stage(session_id) == "consolidation_offer"
        assert session_manager.get_current_agent(session_id) == "consolidation_agent"
        
        # Verify conversation history
        history = session_manager.get_conversation_history(session_id)
        assert len(history) >= 1
    
    def test_multi_user_sessions(self, session_manager):
        """Test managing multiple user sessions simultaneously."""
        # Create sessions for different users
        session1 = session_manager.create_session(user_id="user1")
        session2 = session_manager.create_session(user_id="user2")
        session3 = session_manager.create_session(user_id="user3")
        
        # Update different states for each
        session_manager.update_session_state(session1, "credit_score", 700)
        session_manager.update_session_state(session2, "credit_score", 800)
        session_manager.update_session_state(session3, "credit_score", 650)
        
        # Verify isolation
        assert session_manager.get_session_state(session1, "credit_score") == 700
        assert session_manager.get_session_state(session2, "credit_score") == 800
        assert session_manager.get_session_state(session3, "credit_score") == 650
        
        # Verify active count
        assert session_manager.get_active_session_count() == 3
