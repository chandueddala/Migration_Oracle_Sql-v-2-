"""
Wrapper module for memory agent functions
Provides backward compatibility for migration_workflow_legacy.py

This module re-exports functions from agents.memory_agent to maintain
compatibility with legacy code that imports from 'shared_memory'.
"""

from agents.memory_agent import (
    get_shared_memory,
    ensure_schema_exists,
    fix_schema_references
)

__all__ = [
    'get_shared_memory',
    'ensure_schema_exists',
    'fix_schema_references'
]
