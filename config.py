# Configuration file for the Cita Bot
# Copy this file and modify it with your personal information

# Personal Information
PERSONAL_INFO = {
    "NIE": "Z324402S",  # Your NIE number
    "FULL_NAME": "MARBELLA CONTRERAS GUANIPA",  # Your full name
    "PAIS_VALUE": "248",  # Country code (248 = Venezuela)
    "PHONE": "600000000",  # Your phone number
    "EMAIL": "myemail@here.com",  # Your email address
}

# Bot Settings
BOT_SETTINGS = {
    "PROVINCE": "Barcelona",  # Province for appointment
    "MAX_RETRIES": 500,  # Maximum number of attempts
    "WAIT_SECS": 30,  # Explicit wait time for elements
    "TRANSITION_TIMEOUT": 20,  # Timeout for page transitions
    "DOM_SIG_DELTA": 50,  # Minimum DOM change to detect transition
}

# Captcha Settings
CAPTCHA_SETTINGS = {
    "ANTICAPTCHA_API_KEY": "your_api_key_here",  # Get from https://anti-captcha.com/
    "AUTO_CAPTCHA": True,  # Set to False for manual captcha solving
}

# Office Preferences (optional)
# If you want to specify preferred offices, uncomment and modify:
# OFFICE_PREFERENCES = {
#     "preferred_offices": ["Barcelona", "Badalona"],  # Office names
#     "exclude_offices": ["Some Office"],  # Offices to avoid
# }

# Time Preferences (optional)
# If you want to specify time constraints, uncomment and modify:
# TIME_PREFERENCES = {
#     "min_date": "01/01/2025",  # Format: dd/mm/yyyy
#     "max_date": "31/12/2025",  # Format: dd/mm/yyyy
#     "min_time": "09:00",  # Format: hh:mm
#     "max_time": "17:00",  # Format: hh:mm
# }

# Chrome Settings
CHROME_SETTINGS = {
    "use_separate_profile": True,  # Use separate Chrome profile
    "profile_path": "~/.selenium-icp-profile",  # Profile directory
}

# Notification Settings
NOTIFICATION_SETTINGS = {
    "play_sound_on_success": True,
    "play_sound_on_failure": True,
    "success_sound_duration": 30,  # seconds
    "failure_sound_duration": 30,  # seconds
}

# Debug Settings
DEBUG_SETTINGS = {
    "save_screenshots": True,  # Save screenshots on important steps
    "verbose_logging": True,  # Enable detailed logging
    "headless_mode": False,  # Run browser in headless mode
} 