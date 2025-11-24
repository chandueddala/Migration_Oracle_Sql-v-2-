#!/usr/bin/env python3
"""
Setup Script for Oracle → SQL Server Migration System v2.0
Production Version

This script helps you set up the migration system quickly.

Usage:
    python setup.py
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_step(step, text):
    print(f"\n[Step {step}] {text}")

def check_python_version():
    """Check if Python version is 3.9 or higher"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"❌ Python 3.9+ required. You have {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_pip():
    """Check if pip is available"""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      capture_output=True, check=True)
        print("✅ pip is available")
        return True
    except:
        print("❌ pip not found")
        return False

def install_dependencies():
    """Install required dependencies"""
    print("\nInstalling dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                      check=True)
        print("✅ Dependencies installed")
        return True
    except:
        print("❌ Failed to install dependencies")
        return False

def create_env_file():
    """Create .env file from template"""
    if Path(".env").exists():
        print("ℹ️  .env file already exists")
        response = input("Do you want to overwrite it? [y/N]: ").strip().lower()
        if response != 'y':
            print("✅ Keeping existing .env file")
            return True
    
    if not Path(".env.example").exists():
        print("❌ .env.example not found")
        return False
    
    # Copy template
    with open(".env.example", "r") as f:
        template = f.read()
    
    with open(".env", "w") as f:
        f.write(template)
    
    print("✅ Created .env file from template")
    return True

def configure_api_keys():
    """Help user configure API keys"""
    print("\n" + "-"*70)
    print("API KEY CONFIGURATION")
    print("-"*70)
    
    print("\nYou need to add your API keys to the .env file.")
    print("\nRequired keys:")
    print("  1. ANTHROPIC_API_KEY (get from: https://console.anthropic.com/)")
    print("  2. LANGCHAIN_API_KEY (get from: https://smith.langchain.com/)")
    
    print("\nOptional but recommended:")
    print("  3. TAVILY_API_KEY (get from: https://tavily.com/)")
    
    response = input("\nWould you like to enter your API keys now? [y/N]: ").strip().lower()
    
    if response == 'y':
        anthropic_key = input("\nEnter ANTHROPIC_API_KEY: ").strip()
        langchain_key = input("Enter LANGCHAIN_API_KEY (optional, press Enter to skip): ").strip()
        tavily_key = input("Enter TAVILY_API_KEY (optional, press Enter to skip): ").strip()
        
        # Update .env file
        with open(".env", "r") as f:
            content = f.read()
        
        if anthropic_key:
            content = content.replace("ANTHROPIC_API_KEY=sk-ant-your-key-here", 
                                    f"ANTHROPIC_API_KEY={anthropic_key}")
        if langchain_key:
            content = content.replace("LANGCHAIN_API_KEY=ls__your-key-here",
                                    f"LANGCHAIN_API_KEY={langchain_key}")
        if tavily_key:
            content = content.replace("TAVILY_API_KEY=tvly-your-key-here",
                                    f"TAVILY_API_KEY={tavily_key}")
        
        with open(".env", "w") as f:
            f.write(content)
        
        print("\n✅ API keys configured")
    else:
        print("\nℹ️  You can edit .env file manually later")
        print("   Required: ANTHROPIC_API_KEY")

def create_directories():
    """Create necessary directories"""
    dirs = ["logs", "output", "logs/unresolved", "output/migration_reports"]
    
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    
    print("✅ Created necessary directories")
    return True

def verify_installation():
    """Verify the installation"""
    print("\nVerifying installation...")
    
    errors = []
    
    # Check .env exists
    if not Path(".env").exists():
        errors.append(".env file not found")
    
    # Check main directories
    required_dirs = ["agents", "external_tools", "database", "config", "utils"]
    for d in required_dirs:
        if not Path(d).exists():
            errors.append(f"{d}/ directory not found")
    
    # Check main files
    required_files = [
        "main.py",
        "requirements.txt",
        "agents/orchestrator_agent.py",
        "external_tools/ssma_integration.py",
        "database/oracle_connector.py"
    ]
    
    for file in required_files:
        if not Path(file).exists():
            errors.append(f"{file} not found")
    
    # Try importing key modules
    try:
        sys.path.insert(0, ".")
        import anthropic
        print("✅ Anthropic library available")
    except ImportError:
        errors.append("Anthropic library not installed")
    
    try:
        import langchain
        print("✅ LangChain library available")
    except ImportError:
        errors.append("LangChain library not installed")
    
    if errors:
        print("\n❌ Verification failed:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    print("\n✅ Installation verified successfully!")
    return True

def main():
    print_header("Oracle → SQL Server Migration System v2.0")
    print_header("PRODUCTION VERSION - SETUP WIZARD")
    
    print("\nThis wizard will help you set up the migration system.\n")
    
    # Step 1: Check Python version
    print_step(1, "Checking Python version...")
    if not check_python_version():
        print("\n❌ Setup failed: Python 3.9+ required")
        return 1
    
    # Step 2: Check pip
    print_step(2, "Checking pip...")
    if not check_pip():
        print("\n❌ Setup failed: pip not found")
        return 1
    
    # Step 3: Install dependencies
    print_step(3, "Installing dependencies...")
    response = input("Install dependencies from requirements.txt? [Y/n]: ").strip().lower()
    if response != 'n':
        if not install_dependencies():
            print("\n❌ Setup failed: Could not install dependencies")
            return 1
    else:
        print("⏭️  Skipped dependency installation")
    
    # Step 4: Create .env file
    print_step(4, "Creating .env file...")
    if not create_env_file():
        print("\n❌ Setup failed: Could not create .env file")
        return 1
    
    # Step 5: Configure API keys
    print_step(5, "Configuring API keys...")
    configure_api_keys()
    
    # Step 6: Create directories
    print_step(6, "Creating directories...")
    create_directories()
    
    # Step 7: Verify installation
    print_step(7, "Verifying installation...")
    if not verify_installation():
        print("\n⚠️  Setup completed with warnings")
        print("   Please fix the errors above before running the migration")
        return 1
    
    # Success!
    print("\n" + "="*70)
    print("  🎉 SETUP COMPLETE!")
    print("="*70)
    
    print("\n✅ The migration system is ready to use!")
    print("\nNext steps:")
    print("  1. Review .env file to verify API keys")
    print("  2. Run the migration: python main.py")
    print("  3. Follow interactive prompts")
    
    print("\n📚 Documentation:")
    print("  - README.md - Production architecture guide")
    print("  - docs/QUICK_REFERENCE.md - Quick commands")
    print("  - docs/ARCHITECTURE.md - Technical details")
    print("  - PRODUCTION_STRUCTURE.md - Folder structure")
    
    print("\n" + "="*70)
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)
