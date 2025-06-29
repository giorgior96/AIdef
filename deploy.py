#!/usr/bin/env python3
"""
Boat Filter AI - Deployment Script
==================================

This script helps you quickly set up and deploy the Boat Filter AI application.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def install_dependencies():
    """Install required dependencies."""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def check_dataset():
    """Check if the dataset file exists."""
    dataset_file = "output_with_contact.json"
    if not Path(dataset_file).exists():
        print(f"⚠️  Dataset file '{dataset_file}' not found")
        print("Please ensure your boat dataset JSON file is named 'output_with_contact.json'")
        return False
    
    try:
        with open(dataset_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Dataset loaded: {len(data)} boats found")
        return True
    except Exception as e:
        print(f"❌ Error loading dataset: {e}")
        return False

def setup_api_key():
    """Help user set up API key."""
    env_file = ".env"
    
    if Path(env_file).exists():
        print("✅ .env file already exists")
        return True
    
    print("\n🔑 Setting up API key...")
    print("You need a Google Gemini API key to use this application.")
    print("Get a free key from: https://makersuite.google.com/app/apikey")
    
    api_key = input("Enter your Gemini API key: ").strip()
    
    if not api_key:
        print("❌ API key is required")
        return False
    
    try:
        with open(env_file, 'w') as f:
            f.write(f"GEMINI_API_KEYS={api_key}\n")
        print("✅ API key saved to .env file")
        return True
    except Exception as e:
        print(f"❌ Failed to save API key: {e}")
        return False

def run_application():
    """Run the Streamlit application."""
    print("\n🚀 Starting Boat Filter AI...")
    print("The application will open in your browser at: http://localhost:8501")
    print("Press Ctrl+C to stop the application")
    
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
    except KeyboardInterrupt:
        print("\n👋 Application stopped")
    except Exception as e:
        print(f"❌ Failed to start application: {e}")

def main():
    """Main deployment function."""
    print("🚤 Boat Filter AI - Deployment Script")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Check dataset
    if not check_dataset():
        print("\n💡 You can still continue, but you'll need to add your dataset file later")
        response = input("Continue anyway? (y/n): ").lower()
        if response != 'y':
            sys.exit(1)
    
    # Setup API key
    if not setup_api_key():
        sys.exit(1)
    
    # Run application
    run_application()

if __name__ == "__main__":
    main() 