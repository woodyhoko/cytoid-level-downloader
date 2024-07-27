import json
import os
import time
import random
import logging
import requests
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
GRAPHQL_URL = "https://services.cytoid.io/graphql"
USERNAME = "xxx@gmail.com"
PASSWORD = "password"
DOWNLOAD_DIR = "levels"
MAX_RETRIES = 10
PAGE_LOAD_TIMEOUT = 60
TURNSTILE_TIMEOUT = 120
RETRY_DELAY = 15


def login(turnstile_token):
    """Logs into Cytoid.io and returns the session token."""
    payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "captcha": turnstile_token,
        "remember": False
    }
    response = requests.post(f"{GRAPHQL_URL}/session", json=payload)
    if response.status_code == 200:
        data = response.json()
        logger.info("Login successful")
        return data["token"]
    else:
        logger.error(f"Login failed: Status code {response.status_code}")
        return None

def get_levels(token):
    """Fetches level data using GraphQL."""
    query = """
    query MyLevels($start: Int, $limit: Int) {
        my {
            levels(start: $start, limit: $limit) {
                id
                uid
                title
            }
        }
    }
    """
    headers = {"Authorization": f"Bearer {token}"}
    start = 0
    limit = 100  # Fetch levels in batches of 100
    all_levels = []

    while True:
        variables = {"start": start, "limit": limit}
        response = requests.post(GRAPHQL_URL, json={'query': query, 'variables': variables}, headers=headers)
        if response.status_code == 200:
            data = response.json()
            levels = data["data"]["my"]["levels"]
            all_levels.extend(levels)
            if len(levels) < limit:
                break  # All levels fetched
            start += limit
        else:
            logger.error(f"Error fetching levels: Status code {response.status_code}")
            break  # Stop fetching on error

    logger.info(f"Fetched {len(all_levels)} levels")
    return all_levels

def download_level(token, level_id, level_uid, level_title, turnstile_token):
    """Downloads a level file."""
    url = f"https://services.cytoid.io/levels/{level_id}/resources"
    headers = {
        "Authorization": f"Bearer {token}",
        "Captcha": turnstile_token 
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        file_url = data["package"]

        # Download the level file
        response = requests.get(file_url)
        if response.status_code == 200:
            # Save the level file
            file_path = os.path.join(DOWNLOAD_DIR, f"{level_uid}_{level_title}.cytoidlevel")
            with open(file_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"Downloaded: {level_title} ({level_uid})")
        else:
            logger.error(f"Error downloading level '{level_title}' ({level_uid}): Status code {response.status_code}")
    else:
        logger.error(f"Error getting level download URL for '{level_title}' ({level_uid}): Status code {response.status_code}")


def check_network_connectivity():
    """Checks if there's an active internet connection."""
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

def wait_for_turnstile_load(driver):
    """Waits for Turnstile to load and become interactive."""
    try:
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, 'challenges.cloudflare.com')]"))
        )
        logger.info("Turnstile iframe found")
        
        # Switch to the Turnstile iframe
        iframe = driver.find_element(By.XPATH, "//iframe[contains(@src, 'challenges.cloudflare.com')]")
        driver.switch_to.frame(iframe)
        
        # Wait for the Turnstile checkbox to be clickable
        WebDriverWait(driver, TURNSTILE_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox']"))
        )
        logger.info("Turnstile checkbox is clickable")
        
        # Switch back to the main content
        driver.switch_to.default_content()
        return True
    except (TimeoutException, NoSuchElementException) as e:
        logger.error(f"Error waiting for Turnstile: {str(e)}")
        return False


def get_turnstile_token(driver):
    """Gets a Turnstile token using Undetected Chromedriver."""
    for attempt in range(MAX_RETRIES):
        try:
            driver.get("https://cytoid.io/session/login")

            # Wait for the page load
            WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Wait for Turnstile iframe to load
            WebDriverWait(driver, TURNSTILE_TIMEOUT).until(
                EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[contains(@src, 'challenges.cloudflare.com')]"))
            )
            
            # Wait for Turnstile to finish and get the token
            turnstile_element = WebDriverWait(driver, TURNSTILE_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-cf-response], [cf-turnstile-response]'))
            )
            
            turnstile_token = turnstile_element.get_attribute('data-cf-response') or turnstile_element.get_attribute('cf-turnstile-response')
            
            if not turnstile_token:
                raise ValueError("Turnstile token is empty")
            
            logger.info("Turnstile token obtained successfully")
            return turnstile_token

        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error("Max retries reached. Could not obtain Turnstile token.")
                return None

    return None

if __name__ == "__main__":
    # Set up ChromeOptions
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Add user-agent rotation
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    ]
    options.add_argument(f'user-agent={random.choice(user_agents)}')

    # Use WebDriver Manager to get the appropriate ChromeDriver
    service = Service(ChromeDriverManager().install())

    # Initialize the WebDriver
    driver = webdriver.Chrome(service=service, options=options)

    try:
        turnstile_token = get_turnstile_token(driver)
        if turnstile_token:
            # Proceed with login and other operations
            logger.info("Successfully obtained Turnstile token")
            # Add your login and level downloading code here
        else:
            logger.error("Failed to obtain Turnstile token. Script exiting.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        driver.quit()

logger.info("Script execution completed.")