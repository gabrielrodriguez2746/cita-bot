import os
import random
import time
import re
import json
import tempfile
import logging
from base64 import b64decode
from datetime import datetime as dt
from shutil import which
from typing import Optional, Dict, Any

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("Note: python-dotenv not available. Install with: pip install python-dotenv")

import requests
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    WebDriverException,
)

# Try to import anticaptcha, but make it optional
try:
    from anticaptchaofficial.imagecaptcha import imagecaptcha
    from anticaptchaofficial.recaptchav3proxyless import recaptchaV3Proxyless
    ANTICAPTCHA_AVAILABLE = True
except ImportError:
    ANTICAPTCHA_AVAILABLE = False
    print("Warning: anticaptcha not available. Install with: pip install anticaptchaofficial")

# -------------------------
# Config
# -------------------------
START_URL = "https://icp.administracionelectronica.gob.es/icpplustiem/index.html"

# Configuration function to read from environment variables
def get_config():
    """Get configuration from environment variables with fallbacks"""
    config = {
        # Personal Information
        "NIE": os.environ.get("NIE"),
        "FULL_NAME": os.environ.get("FULL_NAME"),
        "PAIS_VALUE": os.environ.get("PAIS_VALUE", "248"),
        "PHONE": os.environ.get("PHONE"),
        "EMAIL": os.environ.get("EMAIL"),
        
        # Bot Settings
        "PROVINCE": os.environ.get("PROVINCE", "Barcelona"),
        "MAX_RETRIES": int(os.environ.get("MAX_RETRIES", "500")),
        "WAIT_SECS": int(os.environ.get("WAIT_SECS", "30")),
        "TRANSITION_TIMEOUT": int(os.environ.get("TRANSITION_TIMEOUT", "20")),
        "DOM_SIG_DELTA": int(os.environ.get("DOM_SIG_DELTA", "50")),
        
        # Captcha Settings
        "ANTICAPTCHA_API_KEY": os.environ.get("ANTICAPTCHA_API_KEY"),
        "AUTO_CAPTCHA": os.environ.get("AUTO_CAPTCHA", "True").lower() == "true",
    }
    
    return config

# Load configuration
CONFIG = get_config()

# Personal Information
NIE = CONFIG["NIE"]
FULL_NAME = CONFIG["FULL_NAME"]
PAIS_VALUE = CONFIG["PAIS_VALUE"]  # VENEZUELA
PHONE = CONFIG["PHONE"]  # Phone number
EMAIL = CONFIG["EMAIL"]  # Email

# Bot Settings
PROVINCE = CONFIG["PROVINCE"]
MAX_RETRIES = CONFIG["MAX_RETRIES"]
WAIT_SECS = CONFIG["WAIT_SECS"]  # explicit wait
TRANSITION_TIMEOUT = CONFIG["TRANSITION_TIMEOUT"]  # how long to wait for nav/DOM change after a click
DOM_SIG_DELTA = CONFIG["DOM_SIG_DELTA"]       # minimum DOM length delta to consider "changed"

# Anticaptcha API key - Read from environment variable
ANTICAPTCHA_API_KEY = CONFIG["ANTICAPTCHA_API_KEY"]
AUTO_CAPTCHA = CONFIG["AUTO_CAPTCHA"]

# -------------------------
# Speakers
# -------------------------
class eSpeakSpeaker:
    @classmethod
    def is_applicable(cls):
        return which("espeak") is not None
    def say(self, phrase):
        os.system("espeak '" + phrase + "'")

class saySpeaker:
    @classmethod
    def is_applicable(cls):
        return which("say") is not None
    def say(self, phrase):
        os.system("say '" + phrase + "'")

class wSaySpeaker:
    @classmethod
    def is_applicable(cls):
        return which("wsay") is not None
    def say(self, phrase):
        os.system('wsay "' + phrase + '"')

def new_speaker():
    for cls in [saySpeaker, eSpeakSpeaker, wSaySpeaker]:
        if cls.is_applicable():
            return cls()
    return None

def play_alarm(phrase="success", seconds=30):
    sp = new_speaker()
    if sp:
        t0 = time.time()
        while time.time() - t0 < seconds:
            sp.say(phrase)
            time.sleep(1)
    else:
        t0 = time.time()
        while time.time() - t0 < seconds:
            print(f"\a{phrase.upper()}", flush=True)
            time.sleep(1)

# -------------------------
# Backoff (decorrelated jitter)
# -------------------------
def backoff_sleep(base=5.0, cap=600.0, previous=0.0):
    if previous <= 0:
        delay = base + random.random() * base
    else:
        delay = min(cap, random.uniform(base, previous * 3))
    print(f"[backoff] Sleeping {delay:.1f}s...")
    time.sleep(delay)
    return delay

# -------------------------
# Selenium helpers
# -------------------------
def human_pause(a=0.3, b=1.2):
    time.sleep(a + random.random() * (b - a))

def wait_ready(wait):
    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

def start_driver():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    # Optional: look more "human" with a separate profile
    opts.add_argument(f"--user-data-dir={os.path.expanduser('~')}/.selenium-icp-profile")

    driver = webdriver.Chrome(options=opts)
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        })
        driver.execute_cdp_cmd("Network.enable", {})
        ua = driver.execute_script("return navigator.userAgent")
        driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {
            "headers": {"Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}
        })
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": ua,
            "platform": "MacIntel",
            "acceptLanguage": "es-ES,es;q=0.9,en;q=0.8",
            "userAgentMetadata": {
                "brands": [{"brand": "Chromium", "version": "129"}, {"brand": "Not.A/Brand", "version": "24"}],
                "fullVersion": "129.0.0.0",
                "platform": "macOS",
                "platformVersion": "14.5",
                "architecture": "x86",
                "model": "",
                "mobile": False
            }
        })
    except Exception:
        pass
    return driver

def is_request_rejected(driver):
    src = (driver.page_source or "").lower()
    return ("request rejected" in src) or ("support id" in src and "go back" in src)

def is_rate_limited_429(driver):
    try:
        title = (driver.title or "").strip().lower()
    except Exception:
        title = ""
    page = (driver.page_source or "").lower()
    return ("429 too many requests" in title) or ("too many requests" in page)

def get_dom_signature(driver):
    try:
        return int(driver.execute_script("return document.documentElement.outerHTML.length"))
    except Exception:
        return -1

def wait_for_transition(driver, clicked_el=None, prev_url=None, prev_sig=None, timeout=TRANSITION_TIMEOUT):
    """
    Waits for either:
      - URL change, or
      - clicked_el becomes stale, or
      - document DOM signature changes significantly
    Returns True if transition detected, False otherwise.
    """
    end = time.time() + timeout
    while time.time() < end:
        # URL change
        cur_url = driver.current_url
        if prev_url and cur_url != prev_url:
            return True

        # Element staleness
        if clicked_el is not None:
            try:
                _ = clicked_el.is_enabled()  # will raise if stale
            except StaleElementReferenceException:
                return True

        # DOM change
        try:
            cur_sig = get_dom_signature(driver)
            if prev_sig is not None and cur_sig != -1 and abs(cur_sig - prev_sig) >= DOM_SIG_DELTA:
                return True
        except Exception:
            pass

        time.sleep(0.5)
    return False

def click_with_transition(driver, el):
    prev_url = driver.current_url
    prev_sig = get_dom_signature(driver)
    ActionChains(driver).move_to_element(el).pause(0.25).click().perform()
    transitioned = wait_for_transition(driver, clicked_el=el, prev_url=prev_url, prev_sig=prev_sig)
    return transitioned

def handle_cookies_if_any(driver, wait):
    # Accept cookie banner here if one appears (region dependent)
    pass

def get_body_text(driver):
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        return ""

# -------------------------
# Captcha handling
# -------------------------
def process_captcha(driver):
    if not AUTO_CAPTCHA:
        print("Manual captcha solving required. Solve the captcha and press ENTER...")
        for i in range(10):
            if new_speaker():
                new_speaker().say("ALARM")
        input()
        return True

    if not ANTICAPTCHA_AVAILABLE:
        print("Anticaptcha not available. Please install: pip install anticaptchaofficial")
        return False

    if not ANTICAPTCHA_API_KEY or ANTICAPTCHA_API_KEY == "your_api_key_here":
        print("Anticaptcha API key not set. Please set ANTICAPTCHA_API_KEY variable.")
        return False

    # Check for reCAPTCHA
    if len(driver.find_elements(By.ID, "reCAPTCHA_site_key")) > 0:
        return solve_recaptcha(driver)
    # Check for image captcha
    elif len(driver.find_elements(By.CSS_SELECTOR, "img.img-thumbnail")) > 0:
        return solve_image_captcha(driver)
    else:
        return True

def solve_recaptcha(driver):
    try:
        site_key = driver.find_element(By.ID, "reCAPTCHA_site_key").get_attribute("value")
        page_action = driver.find_element(By.ID, "action").get_attribute("value")
        print(f"Solving reCAPTCHA: site_key={site_key}, action={page_action}")

        solver = recaptchaV3Proxyless()
        solver.set_verbose(1)
        solver.set_key(ANTICAPTCHA_API_KEY)
        solver.set_website_url("https://icp.administracionelectronica.gob.es")
        solver.set_website_key(site_key)
        solver.set_page_action(page_action)
        solver.set_min_score(0.9)

        g_response = solver.solve_and_return_solution()
        if g_response != 0:
            print(f"reCAPTCHA solved: {g_response}")
            driver.execute_script(
                f"document.getElementById('g-recaptcha-response').value = '{g_response}'"
            )
            return True
        else:
            print(f"reCAPTCHA failed: {solver.err_string}")
            return False
    except Exception as e:
        print(f"Error solving reCAPTCHA: {e}")
        return False

def solve_image_captcha(driver):
    try:
        img = driver.find_elements(By.CSS_SELECTOR, "img.img-thumbnail")[0]
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(b64decode(img.get_attribute("src").split(",")[1].strip()))
        tmp.close()

        solver = imagecaptcha()
        solver.set_verbose(1)
        solver.set_key(ANTICAPTCHA_API_KEY)

        captcha_result = solver.solve_and_return_solution(tmp.name)
        if captcha_result != 0:
            print(f"Image captcha solved: {captcha_result}")
            element = driver.find_element(By.ID, "captcha")
            element.send_keys(captcha_result)
            os.unlink(tmp.name)
            return True
        else:
            print(f"Image captcha failed: {solver.err_string}")
            os.unlink(tmp.name)
            return False
    except Exception as e:
        print(f"Error solving image captcha: {e}")
        try:
            os.unlink(tmp.name)
        except:
            pass
        return False

# -------------------------
# Main flow functions
# -------------------------
def select_province_and_accept(driver, wait):
    driver.get(START_URL)
    wait_ready(wait)
    handle_cookies_if_any(driver, wait)

    province_select = Select(WebDriverWait(driver, WAIT_SECS).until(
        EC.presence_of_element_located((By.ID, "form"))
    ))
    province_select.select_by_visible_text(PROVINCE)
    human_pause()

    aceptar = WebDriverWait(driver, WAIT_SECS).until(EC.element_to_be_clickable((By.ID, "btnAceptar")))
    if not click_with_transition(driver, aceptar):
        return False  # no transition; treat as failure to retry
    wait_ready(wait)
    return True

def select_last_tramite_and_accept(driver, wait):
    tramite_el = WebDriverWait(driver, WAIT_SECS).until(
        EC.presence_of_element_located((By.NAME, "tramiteGrupo[0]"))
    )
    tramite = Select(tramite_el)
    last_index = len(tramite.options) - 1
    if last_index <= 0:
        raise RuntimeError("No trámites available.")
    tramite.select_by_index(last_index)
    human_pause()

    aceptar = WebDriverWait(driver, WAIT_SECS).until(EC.element_to_be_clickable((By.ID, "btnAceptar")))
    if not click_with_transition(driver, aceptar):
        return False
    wait_ready(wait)
    return True

def go_to_acEntrada_via_acInfo(driver, wait):
    WebDriverWait(driver, WAIT_SECS).until(EC.url_contains("/icpplustieb/acInfo"))
    btn_entrar = WebDriverWait(driver, WAIT_SECS).until(
        EC.presence_of_element_located((By.ID, "btnEntrar"))
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_entrar)
    human_pause()
    if not click_with_transition(driver, btn_entrar):
        return False
    wait_ready(wait)
    try:
        WebDriverWait(driver, WAIT_SECS).until(EC.any_of(
            EC.url_contains("/icpplustieb/acEntrada"),
            EC.presence_of_element_located((By.ID, "txtIdCitado"))
        ))
    except TimeoutException:
        pass
    return True

def fill_acEntrada_and_submit(driver, wait):
    nie = WebDriverWait(driver, WAIT_SECS).until(
        EC.presence_of_element_located((By.ID, "txtIdCitado"))
    )
    nie.clear(); human_pause(0.1, 0.25); nie.send_keys(NIE)

    nombre = WebDriverWait(driver, WAIT_SECS).until(
        EC.presence_of_element_located((By.ID, "txtDesCitado"))
    )
    try:
        driver.execute_script("arguments[0].setAttribute('pattern','[a-zA-Z ]*');", nombre)
    except Exception:
        pass
    nombre.clear(); human_pause(0.1, 0.25); nombre.send_keys(FULL_NAME)
    driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}))", nombre)

    pais = WebDriverWait(driver, WAIT_SECS).until(
        EC.presence_of_element_located((By.ID, "txtPaisNac"))
    )
    Select(pais).select_by_value(PAIS_VALUE)
    human_pause()

    aceptar = WebDriverWait(driver, WAIT_SECS).until(
        EC.element_to_be_clickable((By.ID, "btnEnviar"))
    )
    # Click and confirm transition
    prev_url = driver.current_url
    prev_sig = get_dom_signature(driver)
    ActionChains(driver).move_to_element(aceptar).pause(0.25).click().perform()
    transitioned = wait_for_transition(driver, clicked_el=aceptar, prev_url=prev_url, prev_sig=prev_sig)

    if not transitioned:
        return "no_transition"

    wait_ready(wait)

    # Now classify outcome
    url = driver.current_url
    if "infogenerica" in url:
        return "timeout"
    if is_request_rejected(driver):
        return "rejected"
    if is_rate_limited_429(driver):
        return "rate_limited"
    if "/icpplustieb/acValidarEntrada" in url:
        return "validate"

    # If still on acEntrada but button went stale & DOM changed, treat as not-success (e.g., validation error)
    if "/icpplustieb/acEntrada" in url:
        try:
            # If btnEnviar still present, we definitely didn't move
            driver.find_element(By.ID, "btnEnviar")
            return "no_transition"
        except Exception:
            # Button stale but still on same URL -> likely server returned same page (validation)
            return "no_transition"

    # Otherwise consider OK (e.g., acCitar or next step)
    return "ok"

def wait_for_btnConsultar(driver, wait):
    """Wait for the 'Consultar' button to appear after personal info submission"""
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "btnConsultar")))
        return True
    except TimeoutException:
        print("Timeout waiting for Consultar button")
        return False

def click_btnConsultar(driver, wait):
    """Click the Consultar button to proceed to office selection"""
    try:
        btn_consultar = driver.find_element(By.ID, "btnConsultar")
        btn_consultar.click()
        wait_ready(wait)
        return True
    except Exception as e:
        print(f"Error clicking Consultar button: {e}")
        return False

def office_selection(driver, wait):
    """Handle office selection step"""
    print("[Step 2/6] Office selection")
    
    # Wait for office selection page
    try:
        WebDriverWait(driver, WAIT_SECS).until(
            EC.presence_of_element_located((By.ID, "idSede"))
        )
    except TimeoutException:
        print("Timeout waiting for office selection page")
        return False

    # Select a random office (you can customize this logic)
    try:
        office_select = Select(driver.find_element(By.ID, "idSede"))
        # Skip first option if it's empty
        start_index = 1 if office_select.options[0].get_attribute("value") == "" else 0
        if len(office_select.options) > start_index:
            random_index = random.randint(start_index, len(office_select.options) - 1)
            office_select.select_by_index(random_index)
            print(f"Selected office: {office_select.options[random_index].text}")
        else:
            print("No offices available")
            return False
    except Exception as e:
        print(f"Error selecting office: {e}")
        return False

    # Click next button
    try:
        btn_siguiente = WebDriverWait(driver, WAIT_SECS).until(
            EC.element_to_be_clickable((By.ID, "btnSiguiente"))
        )
        btn_siguiente.click()
        wait_ready(wait)
        return True
    except Exception as e:
        print(f"Error clicking siguiente button: {e}")
        return False

def contact_info(driver, wait):
    """Handle contact information step"""
    print("[Step 3/6] Contact info")
    
    try:
        # Wait for contact info page
        phone_field = WebDriverWait(driver, WAIT_SECS).until(
            EC.presence_of_element_located((By.ID, "txtTelefonoCitado"))
        )
        
        # Fill phone number
        phone_field.clear()
        phone_field.send_keys(PHONE)
        
        # Fill email fields if they exist
        try:
            email_uno = driver.find_element(By.ID, "emailUNO")
            email_uno.clear()
            email_uno.send_keys(EMAIL)
            
            email_dos = driver.find_element(By.ID, "emailDOS")
            email_dos.clear()
            email_dos.send_keys(EMAIL)
        except Exception:
            pass  # Email fields might not exist
        
        # Submit contact info
        driver.execute_script("enviar();")
        wait_ready(wait)
        return True
        
    except Exception as e:
        print(f"Error in contact info step: {e}")
        return False

def cita_selection(driver, wait):
    """Handle cita (appointment) selection step"""
    print("[Step 4/6] Cita selection")
    
    resp_text = get_body_text(driver)
    
    if "DISPONE DE 5 MINUTOS" in resp_text:
        print("Found appointment slots with 5-minute timer!")
        return handle_timer_slots(driver, wait)
    elif "Seleccione una de las siguientes citas disponibles" in resp_text:
        print("Found appointment slots with time selection!")
        return handle_time_slots(driver, wait)
    else:
        print("No appointment slots found")
        return False

def handle_timer_slots(driver, wait):
    """Handle slots with 5-minute timer"""
    try:
        # Find available slots
        slot_elements = driver.find_elements(By.CSS_SELECTOR, "input[type='radio'][name='rdbCita']")
        if not slot_elements:
            print("No slot elements found")
            return False
        
        # Select first available slot
        slot_elements[0].click()
        print("Selected first available slot")
        
        # Process captcha if needed
        if not process_captcha(driver):
            return False
        
        # Submit selection
        driver.execute_script("envia();")
        time.sleep(0.5)
        
        # Handle alert if present
        try:
            alert = driver.switch_to.alert
            alert.accept()
        except Exception:
            pass
        
        return True
        
    except Exception as e:
        print(f"Error handling timer slots: {e}")
        return False

def handle_time_slots(driver, wait):
    """Handle slots with time selection"""
    try:
        # Find date headers
        date_elements = driver.find_elements(By.CSS_SELECTOR, "#CitaMAP_HORAS thead [class^=colFecha]")
        if not date_elements:
            print("No date elements found")
            return False
        
        dates = [el.text for el in date_elements]
        print(f"Available dates: {dates}")
        
        # Find first available slot
        slot_table = driver.find_element(By.CSS_SELECTOR, "#CitaMAP_HORAS tbody")
        slot_found = False
        
        for row in slot_table.find_elements(By.CSS_SELECTOR, "tr"):
            if slot_found:
                break
                
            for idx, cell in enumerate(row.find_elements(By.TAG_NAME, "td")):
                if idx >= len(dates):
                    continue
                    
                try:
                    slot_element = cell.find_element(By.CSS_SELECTOR, "[id^=HUECO]")
                    slot_id = slot_element.get_attribute("id")
                    if slot_id:
                        print(f"Found slot: {slot_id} for date: {dates[idx]}")
                        
                        # Process captcha if needed
                        if not process_captcha(driver):
                            return False
                        
                        # Confirm slot
                        driver.execute_script(f"confirmarHueco({{id: '{slot_id}'}}, {slot_id[5:]});")
                        
                        # Handle alert if present
                        try:
                            alert = driver.switch_to.alert
                            alert.accept()
                        except Exception:
                            pass
                        
                        slot_found = True
                        break
                        
                except Exception:
                    continue
        
        return slot_found
        
    except Exception as e:
        print(f"Error handling time slots: {e}")
        return False

def confirmation_step(driver, wait):
    """Handle the final confirmation step"""
    print("[Step 5/6] Confirmation")
    
    resp_text = get_body_text(driver)
    
    if "Debe confirmar los datos de la cita asignada" in resp_text:
        print("Appointment confirmation page found!")
        
        # Check if SMS verification is required
        try:
            sms_field = driver.find_element(By.ID, "txtCodigoVerificacion")
            print("SMS verification required")
            
            # For now, we'll ask for manual input
            # In a full implementation, you could integrate with SMS webhook services
            print("Please enter the SMS code manually:")
            sms_code = input("SMS Code: ")
            sms_field.send_keys(sms_code)
            
        except Exception:
            print("No SMS verification required")
        
        # Confirm appointment
        try:
            # Check required checkboxes
            try:
                chk_total = driver.find_element(By.ID, "chkTotal")
                if not chk_total.is_selected():
                    chk_total.click()
            except Exception:
                pass
            
            try:
                chk_email = driver.find_element(By.ID, "enviarCorreo")
                if not chk_email.is_selected():
                    chk_email.click()
            except Exception:
                pass
            
            # Click confirm button
            btn_confirmar = driver.find_element(By.ID, "btnConfirmar")
            btn_confirmar.click()
            wait_ready(wait)
            
            # Check final result
            final_text = get_body_text(driver)
            if "CITA CONFIRMADA Y GRABADA" in final_text:
                print("✅ APPOINTMENT CONFIRMED SUCCESSFULLY!")
                return "success"
            else:
                print("Appointment confirmation failed")
                return "failed"
                
        except Exception as e:
            print(f"Error confirming appointment: {e}")
            return "error"
    
    else:
        print("Not on confirmation page")
        return "not_confirmation"

def run_complete_flow_once(keep_open_on_success=False):
    """
    Runs the complete cita flow once
    Returns (outcome, driver_or_none)
    """
    driver = None
    try:
        driver = start_driver()
        wait = WebDriverWait(driver, WAIT_SECS)

        # Step 1: Select province and accept
        if not select_province_and_accept(driver, wait):
            driver.quit(); return "no_transition", None
        if is_request_rejected(driver): driver.quit(); return "rejected", None
        if is_rate_limited_429(driver): driver.quit(); return "rate_limited", None

        # Step 2: Select trámite and accept
        if not select_last_tramite_and_accept(driver, wait):
            driver.quit(); return "no_transition", None
        if is_request_rejected(driver): driver.quit(); return "rejected", None
        if is_rate_limited_429(driver): driver.quit(); return "rate_limited", None

        # Step 3: Go to acEntrada via acInfo
        if not go_to_acEntrada_via_acInfo(driver, wait):
            driver.quit(); return "no_transition", None
        if "infogenerica" in driver.current_url: driver.quit(); return "timeout", None
        if is_request_rejected(driver): driver.quit(); return "rejected", None
        if is_rate_limited_429(driver): driver.quit(); return "rate_limited", None

        # Step 4: Fill personal info and submit
        result = fill_acEntrada_and_submit(driver, wait)
        if result != "ok":
            driver.quit(); return result, None

        # Step 5: Wait for Consultar button and click it
        if not wait_for_btnConsultar(driver, wait):
            driver.quit(); return "no_consultar", None
        
        if not click_btnConsultar(driver, wait):
            driver.quit(); return "no_consultar_click", None

        # Step 6: Office selection
        if not office_selection(driver, wait):
            driver.quit(); return "office_selection_failed", None

        # Step 7: Contact info
        if not contact_info(driver, wait):
            driver.quit(); return "contact_info_failed", None

        # Step 8: Cita selection
        if not cita_selection(driver, wait):
            driver.quit(); return "cita_selection_failed", None

        # Step 9: Confirmation
        confirmation_result = confirmation_step(driver, wait)
        if confirmation_result == "success":
            if keep_open_on_success:
                return "success", driver
            driver.quit(); return "success", None
        else:
            driver.quit(); return confirmation_result, None

    except (WebDriverException, TimeoutException) as e:
        print(f"[error] Flow exception: {e}")
        try:
            if driver: driver.quit()
        except Exception:
            pass
        return "error", None

def main():
    # Check anticaptcha setup
    if AUTO_CAPTCHA and not ANTICAPTCHA_AVAILABLE:
        print("Error: AUTO_CAPTCHA is True but anticaptcha is not available")
        print("Install with: pip install anticaptchaofficial")
        return
    
    if AUTO_CAPTCHA and not ANTICAPTCHA_API_KEY:
        print("❌ Error: ANTICAPTCHA_API_KEY environment variable not set")
        print("💡 Set it with: export ANTICAPTCHA_API_KEY='your_actual_key'")
        print("💡 Or create a .env file with: ANTICAPTCHA_API_KEY=your_key")
        print("🔑 Get your key from: https://anti-captcha.com/")
        print("\nAlternatively, set AUTO_CAPTCHA=False for manual captcha solving")
        return

    last_backoff = 0.0
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"--- Attempt {attempt}/{MAX_RETRIES} ---")
        outcome, driver = run_complete_flow_once(keep_open_on_success=True)
        print(f"[info] Outcome: {outcome}")

        if outcome == "success" and driver is not None:
            print("🎉 SUCCESS! Appointment confirmed!")
            play_alarm("success", 30)
            print("✅ Browser left OPEN. Press Ctrl+C here to end the script (will close the driver).")
            try:
                while True:
                    time.sleep(3600)  # keep process alive
            except KeyboardInterrupt:
                try:
                    driver.quit()
                except Exception:
                    pass
                return

        if outcome == "rate_limited":
            print("[warn] 429 Too Many Requests — backing off…")
            last_backoff = backoff_sleep(base=5.0, cap=600.0, previous=last_backoff)
            continue

        # Other non-success outcomes: brief cool-off to avoid hammering
        time.sleep(1.0 + random.random() * 1.5)

    print("[fatal] Reached max retries without success.")
    print("failure")
    play_alarm("failure", 30)

if __name__ == "__main__":
    main()
