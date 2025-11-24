"""
Wrapper module for converter agent functions
Provides backward compatibility for migration_workflow_legacy.py

This module re-exports functions from agents.converter_agent to maintain
compatibility with legacy code that imports from 'ai_converter'.
"""

from agents.converter_agent import (
    convert_code,
    convert_table_ddl,
    reflect_code,
    try_deploy_with_repair,
    claude_sonnet
)

__all__ = [
    'convert_code',
    'convert_table_ddl',
    'reflect_code',
    'try_deploy_with_repair',
    'claude_sonnet'
]
