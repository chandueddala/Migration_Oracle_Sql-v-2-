"""
SSMA Agent - Microsoft SQL Server Migration Assistant Integration
Primary conversion tool, LLMs used only when SSMA fails or produces warnings
"""

import logging
import subprocess
import tempfile
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class SSMAAgent:
    """
    Integrates with Microsoft SSMA for Oracle to SQL Server conversion
    
    SSMA is the PRIMARY conversion tool
    LLMs are used ONLY when SSMA fails or produces significant warnings
    """
    
    def __init__(self, ssma_console_path: Optional[str] = None):
        """
        Initialize SSMA Agent
        
        Args:
            ssma_console_path: Path to SSMAforOracleConsole.exe
        """
        self.ssma_console_path = ssma_console_path or self._find_ssma()
        self.available = self._check_availability()
        
        if self.available:
            logger.info(f"SSMA Agent initialized: {self.ssma_console_path}")
        else:
            logger.warning("SSMA not available - will use LLM fallback for all conversions")
    
    def _find_ssma(self) -> Optional[str]:
        """
        Attempt to locate SSMA installation
        
        Common paths:
        - C:\\Program Files\\Microsoft SQL Server Migration Assistant for Oracle\\bin\\SSMAforOracleConsole.exe
        - /usr/local/bin/ssma (custom installation)
        """
        possible_paths = [
            "C:\\Program Files\\Microsoft SQL Server Migration Assistant for Oracle\\bin\\SSMAforOracleConsole.exe",
            "C:\\Program Files (x86)\\Microsoft SQL Server Migration Assistant for Oracle\\bin\\SSMAforOracleConsole.exe",
            "/usr/local/bin/ssma",
            "/opt/ssma/SSMAforOracleConsole"
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                return path
        
        return None
    
    def _check_availability(self) -> bool:
        """Check if SSMA is available and executable"""
        if not self.ssma_console_path:
            return False
        
        if not Path(self.ssma_console_path).exists():
            return False
        
        try:
            # Try to run SSMA with --version or --help
            result = subprocess.run(
                [self.ssma_console_path, "--help"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"SSMA availability check failed: {e}")
            return False
    
    def convert_object(self, oracle_code: str, object_name: str, 
                      object_type: str) -> Dict[str, Any]:
        """
        Convert Oracle object using SSMA
        
        Args:
            oracle_code: Oracle PL/SQL or DDL
            object_name: Name of object
            object_type: TABLE, PROCEDURE, FUNCTION, TRIGGER
            
        Returns:
            Dict with:
            - status: 'success', 'warning', or 'error'
            - tsql: Converted T-SQL code
            - warnings: List of SSMA warnings
            - errors: List of SSMA errors
            - ssma_logs: Raw SSMA output
            - use_llm_fallback: Boolean indicating if LLM should be used
        """
        if not self.available:
            return {
                "status": "error",
                "message": "SSMA not available",
                "use_llm_fallback": True
            }
        
        try:
            logger.info(f"Converting {object_type} {object_name} with SSMA")
            
            # Create temporary files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Write Oracle code to file
                oracle_file = temp_path / f"{object_name}.sql"
                oracle_file.write_text(oracle_code)
                
                # Output file for T-SQL
                tsql_file = temp_path / f"{object_name}_converted.sql"
                
                # Log file
                log_file = temp_path / "ssma_log.txt"
                
                # Run SSMA conversion
                cmd = [
                    self.ssma_console_path,
                    "-s", str(oracle_file),  # Source file
                    "-t", str(tsql_file),    # Target file
                    "-l", str(log_file),     # Log file
                    "-ObjectType", object_type
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60  # 1 minute timeout
                )
                
                # Parse results
                tsql = tsql_file.read_text() if tsql_file.exists() else ""
                logs = log_file.read_text() if log_file.exists() else result.stdout
                
                # Parse warnings and errors from logs
                warnings = self._parse_warnings(logs)
                errors = self._parse_errors(logs)
                
                # Determine if LLM fallback is needed
                use_llm_fallback = self._should_use_llm_fallback(
                    tsql, warnings, errors, result.returncode
                )
                
                status = "success"
                if errors:
                    status = "error"
                elif warnings:
                    status = "warning"
                
                logger.info(f"SSMA conversion {status}: {len(warnings)} warnings, {len(errors)} errors")
                
                return {
                    "status": status,
                    "tsql": tsql,
                    "warnings": warnings,
                    "errors": errors,
                    "ssma_logs": logs,
                    "use_llm_fallback": use_llm_fallback,
                    "returncode": result.returncode
                }
        
        except subprocess.TimeoutExpired:
            logger.error(f"SSMA conversion timeout for {object_name}")
            return {
                "status": "error",
                "message": "SSMA conversion timeout",
                "use_llm_fallback": True
            }
        
        except Exception as e:
            logger.error(f"SSMA conversion failed: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "use_llm_fallback": True
            }
    
    def _parse_warnings(self, logs: str) -> List[str]:
        """Parse SSMA warnings from log output"""
        warnings = []
        for line in logs.split('\n'):
            if 'WARNING:' in line or 'Warning:' in line:
                warnings.append(line.strip())
        return warnings
    
    def _parse_errors(self, logs: str) -> List[str]:
        """Parse SSMA errors from log output"""
        errors = []
        for line in logs.split('\n'):
            if 'ERROR:' in line or 'Error:' in line:
                errors.append(line.strip())
        return errors
    
    def _should_use_llm_fallback(self, tsql: str, warnings: List, 
                                 errors: List, returncode: int) -> bool:
        """
        Determine if LLM fallback should be used
        
        Use LLM when:
        - SSMA returned errors
        - SSMA produced no output
        - More than 5 warnings
        - Critical warnings detected
        """
        if errors:
            return True
        
        if not tsql or len(tsql.strip()) < 10:
            return True
        
        if len(warnings) > 5:
            return True
        
        if returncode != 0:
            return True
        
        # Check for critical warnings
        critical_keywords = [
            'not supported',
            'cannot convert',
            'manual intervention',
            'incomplete conversion'
        ]
        
        for warning in warnings:
            for keyword in critical_keywords:
                if keyword.lower() in warning.lower():
                    return True
        
        return False
    
    def convert_batch(self, objects: List[Dict]) -> List[Dict]:
        """
        Convert multiple objects in batch
        
        Args:
            objects: List of dicts with 'code', 'name', 'type'
            
        Returns:
            List of conversion results
        """
        results = []
        
        for obj in objects:
            result = self.convert_object(
                obj['code'],
                obj['name'],
                obj['type']
            )
            result['object_name'] = obj['name']
            result['object_type'] = obj['type']
            results.append(result)
        
        return results
    
    def get_conversion_statistics(self, results: List[Dict]) -> Dict:
        """Get statistics from batch conversion results"""
        stats = {
            "total": len(results),
            "success": 0,
            "warnings": 0,
            "errors": 0,
            "llm_fallback_needed": 0
        }
        
        for result in results:
            if result['status'] == 'success':
                stats['success'] += 1
            elif result['status'] == 'warning':
                stats['warnings'] += 1
            elif result['status'] == 'error':
                stats['errors'] += 1
            
            if result.get('use_llm_fallback'):
                stats['llm_fallback_needed'] += 1
        
        return stats


# Global SSMA agent instance
_ssma_agent = None


def get_ssma_agent(ssma_path: Optional[str] = None) -> SSMAAgent:
    """Get or create global SSMA agent"""
    global _ssma_agent
    if _ssma_agent is None:
        _ssma_agent = SSMAAgent(ssma_path)
    return _ssma_agent


def is_ssma_available() -> bool:
    """Check if SSMA is available"""
    agent = get_ssma_agent()
    return agent.available
