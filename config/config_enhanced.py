"""
Configuration and settings for Oracle to SQL Server migration system
Enhanced with security, SSMA integration, and modular architecture
"""

import os
from pathlib import Path
from collections import defaultdict
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

# ==================== API KEYS ====================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")  # Web search API

# ==================== LANGSMITH CONFIGURATION ====================
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "oracle-sqlserver-migration-v2"
if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
if ANTHROPIC_API_KEY:
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
if LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
if TAVILY_API_KEY:
    os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY

# ==================== MODEL CONFIGURATION ====================
GPT4_MODEL = "gpt-4"
CLAUDE_SONNET_MODEL = "claude-sonnet-4-20250514"
CLAUDE_OPUS_MODEL = "claude-opus-4-20250514"

# ==================== PRICING (USD per 1K tokens) ====================
PRICING = {
    "anthropic/claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "anthropic/claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
    "anthropic/claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "anthropic/claude-opus-4-1": {"input": 15.0, "output": 75.0},
    "openai/gpt-4": {"input": 30.0, "output": 60.0},
}

INCLUDE_LANGSMITH_COST = False
LANGSMITH_FLAT_PER_RUN = 0.00

# ==================== MIGRATION SETTINGS ====================
MAX_CREDENTIAL_ATTEMPTS = int(os.getenv("MAX_CREDENTIAL_ATTEMPTS", "5"))  # Credential retry attempts
MAX_REFLECTION_ITERATIONS = 2
MAX_REPAIR_ATTEMPTS = 3
ENABLE_WEB_SEARCH = True  # Enable/disable web search for error resolution
MAX_SEARCH_RESULTS = 5  # Top N search results to include

# ==================== SSMA INTEGRATION ====================
SSMA_ENABLED = os.getenv("SSMA_ENABLED", "false").lower() == "true"
SSMA_CONSOLE_PATH = os.getenv("SSMA_CONSOLE_PATH", None)
USE_SSMA_FIRST = True  # Try SSMA before LLM
LLM_FALLBACK_ON_SSMA_WARNINGS = True  # Use LLM if SSMA has >5 warnings

# ==================== SECURITY SETTINGS ====================
ALLOW_TABLE_DATA_TO_LLM = False  # NEVER send actual row data to LLMs
LOG_SECURITY_EVENTS = True  # Log all data access patterns
MASK_CREDENTIALS_IN_LOGS = True  # Mask passwords in log files

# ==================== ORCHESTRATION ====================
USE_ORCHESTRATOR = True  # Use orchestrator for workflow management
REFRESH_METADATA_AFTER_DEPLOY = True  # Update memory after successful deployment
LOG_UNRESOLVED_ERRORS = True  # Create detailed logs for failed migrations
UNRESOLVED_ERROR_DIR = Path("logs/unresolved")

# ==================== PATHS ====================
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

UNRESOLVED_ERROR_DIR.mkdir(parents=True, exist_ok=True)

# ==================== LOGGING ====================
LOG_FILE = LOGS_DIR / 'migration.log'
SECURITY_LOG_FILE = LOGS_DIR / 'security.log'
SSMA_LOG_FILE = LOGS_DIR / 'ssma.log'

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'

# ==================== MODULAR ARCHITECTURE ====================
# Future support for multiple sources and targets
SUPPORTED_SOURCES = ['oracle']  # Future: mysql, postgresql, db2
SUPPORTED_TARGETS = ['sqlserver']  # Future: postgresql, snowflake
CURRENT_SOURCE = 'oracle'
CURRENT_TARGET = 'sqlserver'

# ==================== AGENT CONFIGURATION ====================
AGENTS = {
    "orchestrator": {
        "enabled": True,
        "class": "MigrationOrchestrator"
    },
    "ssma": {
        "enabled": SSMA_ENABLED,
        "class": "SSMAAgent",
        "priority": 1  # Try first
    },
    "converter": {
        "enabled": True,
        "class": "LLMConverter",
        "model": CLAUDE_SONNET_MODEL,
        "priority": 2  # Fallback after SSMA
    },
    "reviewer": {
        "enabled": True,
        "class": "LLMReviewer",
        "model": CLAUDE_OPUS_MODEL
    },
    "debugger": {
        "enabled": True,
        "class": "LLMDebugger",
        "model": CLAUDE_SONNET_MODEL
    },
    "researcher": {
        "enabled": ENABLE_WEB_SEARCH,
        "class": "WebSearchHelper"
    }
}


# ==================== COST TRACKER ====================

def _approx_tokens(text: str) -> int:
    """Approximate token count (4 chars per token)"""
    return max(1, int(len(text or "") / 4))


class CostTracker:
    """Track API costs across the migration"""
    
    def __init__(self):
        self.rows: List[Dict] = []
    
    def add(self, provider: str, model: str, prompt: str, completion: str):
        """Add a cost entry"""
        key = f"{provider}/{model}"
        price = PRICING.get(key)
        in_tok = _approx_tokens(prompt)
        out_tok = _approx_tokens(completion)
        in_cost = out_cost = 0.0
        
        if price:
            in_cost = (in_tok / 1000.0) * price["input"]
            out_cost = (out_tok / 1000.0) * price["output"]
        
        self.rows.append({
            "provider": provider,
            "model": model,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "input_cost": in_cost,
            "output_cost": out_cost,
            "total_cost": in_cost + out_cost
        })
    
    @property
    def total(self) -> float:
        """Calculate total cost"""
        s = sum(r["total_cost"] for r in self.rows)
        if INCLUDE_LANGSMITH_COST:
            s += LANGSMITH_FLAT_PER_RUN
        return round(s, 4)
    
    def summary(self) -> str:
        """Generate cost summary report"""
        agg = defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0})
        
        for r in self.rows:
            k = f"{r['provider']}/{r['model']}"
            agg[k]["input_tokens"] += r["input_tokens"]
            agg[k]["output_tokens"] += r["output_tokens"]
            agg[k]["total_cost"] += r["total_cost"]
        
        lines = ["\nðŸ'° Cost summary (approx):"]
        for k, v in agg.items():
            lines.append(
                f"  - {k}: {v['input_tokens']} in tok, "
                f"{v['output_tokens']} out tok, ${v['total_cost']:.4f}"
            )
        
        if INCLUDE_LANGSMITH_COST and LANGSMITH_FLAT_PER_RUN:
            lines.append(f"  - langsmith: ${LANGSMITH_FLAT_PER_RUN:.4f}")
        
        lines.append(f"  => GRAND TOTAL â‰ˆ ${self.total:.4f}")
        return "\n".join(lines)
    
    def get_stats(self) -> Dict:
        """Get detailed statistics"""
        return {
            "total_cost": self.total,
            "total_requests": len(self.rows),
            "total_input_tokens": sum(r["input_tokens"] for r in self.rows),
            "total_output_tokens": sum(r["output_tokens"] for r in self.rows),
            "by_model": dict(agg)
        } if (agg := defaultdict(lambda: {"requests": 0, "cost": 0.0})) or True else {}


# ==================== SECURITY LOGGER ====================

def setup_logging():
    """Setup comprehensive logging system"""
    import logging
    import sys
    
    # Create logs directory
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Main logger
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Security logger
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.INFO)
    security_handler = logging.FileHandler(SECURITY_LOG_FILE)
    security_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    security_logger.addHandler(security_handler)
    
    # SSMA logger
    ssma_logger = logging.getLogger('ssma')
    ssma_logger.setLevel(logging.INFO)
    ssma_handler = logging.FileHandler(SSMA_LOG_FILE)
    ssma_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    ssma_logger.addHandler(ssma_handler)


class SecurityLogger:
    """Log security-relevant events"""
    
    @staticmethod
    def log_data_access(operation: str, table_name: str, row_count: int):
        """Log when table data is accessed"""
        if LOG_SECURITY_EVENTS:
            import logging
            sec_logger = logging.getLogger('security')
            sec_logger.info(
                f"DATA_ACCESS: operation={operation}, "
                f"table={table_name}, rows={row_count}, "
                f"llm_involved=False"
            )
    
    @staticmethod
    def log_credential_usage(credential_type: str, masked_value: str):
        """Log credential usage (masked)"""
        if LOG_SECURITY_EVENTS and MASK_CREDENTIALS_IN_LOGS:
            import logging
            sec_logger = logging.getLogger('security')
            sec_logger.info(
                f"CREDENTIAL_USAGE: type={credential_type}, "
                f"value={masked_value}"
            )
    
    @staticmethod
    def mask_credential(value: str) -> str:
        """Mask sensitive credential values"""
        if not MASK_CREDENTIALS_IN_LOGS:
            return value
        
        if len(value) <= 4:
            return "****"
        
        return value[:2] + "*" * (len(value) - 4) + value[-2:]
