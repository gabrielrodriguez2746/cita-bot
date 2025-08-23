#!/usr/bin/env python3
"""
Example script for using the optimized cita bot with configuration file
"""

import os
import sys

# Add the current directory to Python path to import config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import (
        PERSONAL_INFO, 
        BOT_SETTINGS, 
        CAPTCHA_SETTINGS,
        CHROME_SETTINGS,
        NOTIFICATION_SETTINGS,
        DEBUG_SETTINGS
    )
    print("✅ Configuration loaded successfully")
except ImportError:
    print("❌ Configuration file not found. Please copy config.py and modify it.")
    print("Using default values...")
    
    # Default values if config.py is not available
    PERSONAL_INFO = {
        "NIE": "Z324402S",
        "FULL_NAME": "MARBELLA CONTRERAS GUANIPA",
        "PAIS_VALUE": "248",
        "PHONE": "600000000",
        "EMAIL": "myemail@here.com",
    }
    
    BOT_SETTINGS = {
        "PROVINCE": "Barcelona",
        "MAX_RETRIES": 500,
        "WAIT_SECS": 30,
        "TRANSITION_TIMEOUT": 20,
        "DOM_SIG_DELTA": 50,
    }
    
    CAPTCHA_SETTINGS = {
        "ANTICAPTCHA_API_KEY": "your_api_key_here",
        "AUTO_CAPTCHA": True,
    }

def check_configuration():
    """Check if the configuration is properly set up"""
    print("\n🔍 Configuration Check:")
    print("=" * 50)
    
    # Check personal info
    print("Personal Information:")
    for key, value in PERSONAL_INFO.items():
        if key == "ANTICAPTCHA_API_KEY" and value == "your_api_key_here":
            print(f"  ❌ {key}: {value} (Please set your actual API key)")
        else:
            print(f"  ✅ {key}: {value}")
    
    # Check captcha settings
    print("\nCaptcha Settings:")
    if CAPTCHA_SETTINGS["ANTICAPTCHA_API_KEY"] == "your_api_key_here":
        print("  ❌ ANTICAPTCHA_API_KEY: Not set (Required for automatic captcha solving)")
        print("  💡 Get your API key from: https://anti-captcha.com/")
    else:
        print("  ✅ ANTICAPTCHA_API_KEY: Set")
    
    print(f"  ✅ AUTO_CAPTCHA: {CAPTCHA_SETTINGS['AUTO_CAPTCHA']}")
    
    # Check bot settings
    print("\nBot Settings:")
    for key, value in BOT_SETTINGS.items():
        print(f"  ✅ {key}: {value}")
    
    # Check dependencies
    print("\nDependencies:")
    try:
        import selenium
        print("  ✅ selenium: Available")
    except ImportError:
        print("  ❌ selenium: Not installed (pip install selenium)")
    
    try:
        import anticaptchaofficial
        print("  ✅ anticaptchaofficial: Available")
    except ImportError:
        print("  ❌ anticaptchaofficial: Not installed (pip install anticaptchaofficial)")
    
    try:
        import requests
        print("  ✅ requests: Available")
    except ImportError:
        print("  ❌ requests: Not installed (pip install requests)")

def run_bot():
    """Run the cita bot with current configuration"""
    print("\n🚀 Starting Cita Bot...")
    print("=" * 50)
    
    # Import and run the bot
    try:
        from new import main
        main()
    except ImportError as e:
        print(f"❌ Error importing bot: {e}")
        print("Make sure new.py is in the current directory")
    except Exception as e:
        print(f"❌ Error running bot: {e}")

def main():
    """Main function"""
    print("🎯 Optimized Cita Bot - Configuration Example")
    print("=" * 60)
    
    # Check configuration
    check_configuration()
    
    # Ask user if they want to proceed
    print("\n" + "=" * 50)
    response = input("Do you want to proceed with the current configuration? (y/n): ").lower().strip()
    
    if response in ['y', 'yes']:
        run_bot()
    else:
        print("\n📝 Please modify the configuration and run again:")
        print("1. Edit config.py with your personal information")
        print("2. Set your AntiCaptcha API key")
        print("3. Run this script again")
        print("\nOr run the bot directly with: python new.py")

if __name__ == "__main__":
    main() 