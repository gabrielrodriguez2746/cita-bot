# Optimized Cita Bot

This is an optimized version of the cita bot that completes the entire appointment booking process automatically, from start to finish.

## Features

- **Complete Automation**: Goes through all 6 steps of the cita process
- **Automatic Captcha Solving**: Integrates with AntiCaptcha service
- **Smart Office Selection**: Automatically selects available offices
- **Appointment Slot Detection**: Finds and books available time slots
- **SMS Verification Support**: Handles SMS verification step
- **Error Handling**: Robust error handling with retry logic
- **Sound Notifications**: Audio alerts for success/failure
- **Configurable**: Easy configuration through config.py

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Get an AntiCaptcha API key:
   - Go to [https://anti-captcha.com/](https://anti-captcha.com/)
   - Create an account and add funds
   - Copy your API key

## Configuration

1. Copy `config.py` and modify it with your personal information:
```python
PERSONAL_INFO = {
    "NIE": "YOUR_NIE_HERE",
    "FULL_NAME": "YOUR_FULL_NAME",
    "PAIS_VALUE": "YOUR_COUNTRY_CODE",
    "PHONE": "YOUR_PHONE",
    "EMAIL": "YOUR_EMAIL",
}

CAPTCHA_SETTINGS = {
    "ANTICAPTCHA_API_KEY": "your_actual_api_key_here",
    "AUTO_CAPTCHA": True,
}
```

2. Or modify the variables directly in `new.py`:
```python
NIE = "YOUR_NIE_HERE"
FULL_NAME = "YOUR_FULL_NAME"
PAIS_VALUE = "YOUR_COUNTRY_CODE"
PHONE = "YOUR_PHONE"
EMAIL = "YOUR_EMAIL"
ANTICAPTCHA_API_KEY = "your_actual_api_key_here"
```

## Usage

### Basic Usage
```bash
python new.py
```

### Manual Captcha Solving
If you prefer to solve captchas manually:
```python
AUTO_CAPTCHA = False
```

### Headless Mode
To run without opening a browser window:
```python
DEBUG_SETTINGS = {
    "headless_mode": True,
}
```

## How It Works

The bot follows this complete flow:

1. **Province Selection**: Selects the specified province
2. **Trámite Selection**: Chooses the last available trámite
3. **Personal Information**: Fills in NIE, name, and country
4. **Office Selection**: Automatically selects an available office
5. **Contact Information**: Enters phone and email
6. **Appointment Selection**: Finds and selects available time slots
7. **Captcha Solving**: Automatically solves any captchas
8. **Confirmation**: Confirms the appointment and handles SMS verification

## Captcha Handling

### Automatic (Recommended)
- Set `ANTICAPTCHA_API_KEY` with your API key
- Set `AUTO_CAPTCHA = True`
- The bot will automatically solve reCAPTCHA and image captchas

### Manual
- Set `AUTO_CAPTCHA = False`
- When a captcha appears, solve it manually and press Enter

## Office Selection

The bot automatically selects offices in this order:
1. If specific offices are preferred, tries those first
2. Otherwise, selects a random available office
3. Excludes any offices in the exclude list

## Error Handling

The bot handles various error scenarios:
- **Rate Limiting**: Automatically backs off when hitting rate limits
- **Request Rejection**: Retries on WAF rejections
- **Session Timeouts**: Handles expired sessions
- **Element Not Found**: Waits for elements to load
- **Captcha Failures**: Retries with new captcha solutions

## Monitoring and Debugging

### Screenshots
The bot saves screenshots at key steps when `save_screenshots = True`

### Logging
Detailed logging shows progress through each step

### Sound Alerts
- Success: Plays success sound for 30 seconds
- Failure: Plays failure sound for 30 seconds

## Troubleshooting

### Common Issues

1. **"Anticaptcha not available"**
   - Install: `pip install anticaptchaofficial`

2. **"API key not set"**
   - Set your AntiCaptcha API key in config.py or new.py

3. **"Chrome driver not found"**
   - Install ChromeDriver: `brew install chromedriver` (macOS)
   - Or download from: https://chromedriver.chromium.org/

4. **"No trámites available"**
   - The system might be temporarily unavailable
   - Try again later

### Performance Tips

1. **Use a separate Chrome profile** to avoid login issues
2. **Set reasonable retry limits** to avoid overwhelming the system
3. **Monitor the logs** to see where the process might be failing

## Security Notes

- Never commit your API keys to version control
- Use environment variables for sensitive information
- The bot uses a separate Chrome profile to avoid conflicts

## Legal Disclaimer

This bot is for educational purposes. Please ensure you comply with the website's terms of service and local laws. The authors are not responsible for any misuse of this tool.

## Support

If you encounter issues:
1. Check the logs for error messages
2. Verify your configuration settings
3. Ensure all dependencies are installed
4. Check if the website structure has changed

## Changelog

### v2.0 (Current)
- Complete automation of all 6 steps
- Automatic captcha solving
- Smart office selection
- SMS verification handling
- Robust error handling
- Configuration file support

### v1.0 (Original)
- Basic personal info submission
- Manual intervention required 