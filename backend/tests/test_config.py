"""Tests for configuration validation.

These tests validate that config values are sensible.
The test_max_results_is_positive test will FAIL with the current config,
exposing the MAX_RESULTS=0 bug.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import config, Config


class TestConfigValidation:
    """Test configuration values are valid"""

    def test_max_results_is_positive(self):
        """MAX_RESULTS must be > 0 for vector search to return results.

        This test will FAIL with the current config (MAX_RESULTS=0),
        which causes all searches to return empty results.
        """
        assert config.MAX_RESULTS > 0, (
            f"MAX_RESULTS is {config.MAX_RESULTS}, but must be > 0 "
            "for vector search to return any results"
        )

    def test_max_results_reasonable_upper_bound(self):
        """MAX_RESULTS should not be excessively large"""
        assert config.MAX_RESULTS <= 100, (
            f"MAX_RESULTS is {config.MAX_RESULTS}, which seems excessive"
        )

    def test_chunk_size_is_positive(self):
        """CHUNK_SIZE must be positive for document processing"""
        assert config.CHUNK_SIZE > 0

    def test_chunk_overlap_less_than_chunk_size(self):
        """CHUNK_OVERLAP must be less than CHUNK_SIZE"""
        assert config.CHUNK_OVERLAP < config.CHUNK_SIZE, (
            f"CHUNK_OVERLAP ({config.CHUNK_OVERLAP}) must be less than "
            f"CHUNK_SIZE ({config.CHUNK_SIZE})"
        )

    def test_max_history_is_non_negative(self):
        """MAX_HISTORY should be >= 0"""
        assert config.MAX_HISTORY >= 0

    def test_embedding_model_is_set(self):
        """EMBEDDING_MODEL must be specified"""
        assert config.EMBEDDING_MODEL
        assert len(config.EMBEDDING_MODEL) > 0

    def test_anthropic_model_is_set(self):
        """ANTHROPIC_MODEL must be specified"""
        assert config.ANTHROPIC_MODEL
        assert len(config.ANTHROPIC_MODEL) > 0

    def test_chroma_path_is_set(self):
        """CHROMA_PATH must be specified"""
        assert config.CHROMA_PATH
        assert len(config.CHROMA_PATH) > 0


class TestConfigDefaults:
    """Test that config defaults are sensible"""

    def test_default_chunk_size(self):
        """Default chunk size should be reasonable for context"""
        assert 100 <= config.CHUNK_SIZE <= 2000

    def test_default_chunk_overlap(self):
        """Default chunk overlap should maintain context continuity"""
        assert config.CHUNK_OVERLAP >= 50

    def test_default_max_history(self):
        """Default max history should be reasonable"""
        assert 1 <= config.MAX_HISTORY <= 20


class TestConfigInstance:
    """Test config singleton behavior"""

    def test_config_is_dataclass_instance(self):
        """Config should be a Config dataclass instance"""
        assert isinstance(config, Config)

    def test_config_attributes_accessible(self):
        """All expected config attributes should be accessible"""
        required_attrs = [
            'ANTHROPIC_API_KEY',
            'ANTHROPIC_MODEL',
            'EMBEDDING_MODEL',
            'CHUNK_SIZE',
            'CHUNK_OVERLAP',
            'MAX_RESULTS',
            'MAX_HISTORY',
            'CHROMA_PATH'
        ]
        for attr in required_attrs:
            assert hasattr(config, attr), f"Config missing attribute: {attr}"
