"""
Unit tests for recovery engine and storage reader.
"""

from antigravity_export.config import AntigravityConfig
from antigravity_export.models import Conversation
from antigravity_export.recovery import ConversationRecovery
from antigravity_export.storage import StorageReader


def test_storage_reader_default_config():
    reader = StorageReader()
    assert reader.config.root.name == "antigravity"


def test_recovery_instantiation():
    recovery = ConversationRecovery()
    assert recovery.config is not None
    assert recovery.storage is not None
    assert recovery.parser is not None
