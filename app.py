from operator import or_
import os
import platform
import random
import subprocess
import sys
import threading
import requests
import re
from flask import Flask, jsonify, redirect, render_template, request
import time
from urllib.parse import parse_qs, quote, unquote, urlparse, urlunparse
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import date, datetime
from xml.etree import ElementTree
import concurrent.futures
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from selenium.common.exceptions import StaleElementReferenceException

from dateutil import parser
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import logging

from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import func
from datetime import datetime, timedelta
from dateutil import parser
from flask import request, redirect
from whois import whois
from urllib.parse import urlparse, parse_qs, unquote, urlencode, urlunparse

from selenium.webdriver.common.action_chains import ActionChains

app = Flask(__name__)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# When adding new columns, save an run this, then comment out, add the new columns
migrate = Migrate(app, db)

# Define the database model
class URLData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(200), nullable=False)

    domain = db.Column(db.String(100))
    product_name = db.Column(db.String(100))
    created_at_date = db.Column(db.String(20))
    created_days_ago = db.Column(db.Integer)  # Changed to Integer
    whois_url = db.Column(db.String(200))
    registration_date = db.Column(db.String(20))
    registration_days_ago = db.Column(db.Integer)  # Changed to Integer
    ads_library_url = db.Column(db.String(200))
    result_count = db.Column(db.Integer)  # Changed to Integer
    result_count_history = db.Column(db.String(400))
    time_taken = db.Column(db.String(50))
    added_date = db.Column(db.String(20))  # Adjust type as needed
    added_days_ago = db.Column(db.Integer)
    count_difference = db.Column(db.Integer) 

# Define the database model
class ADSData(db.Model):
    id = db.Column(db.Integer, primary_key=True) # Data ID 

    keyword = db.Column(db.String(200), nullable=False) # Keyword Phrase Used To Find Product Via FB Library
    ads_library_url = db.Column(db.String(300)) # Keyword Phrase Link Used To Find Product Via FB Library

    div_library_id = db.Column(db.String(100)) # Creative ID
    creative_start_date = db.Column(db.Date) # NEW!!!!
    div_ads_count  = db.Column(db.Integer)  # Creative Ad Count (AAs)

    page_name = db.Column(db.String(100)) # Facebook Page Name
    div_href = db.Column(db.String(300)) # Facebook Page Link
    facebook_about_page = db.Column(db.String(300)) # Facebook About Page Link
    page_id = db.Column(db.String(100)) # Facebook Page ID
    page_ads_link = db.Column(db.String(300)) # Facebook Page Ads Library Link
    faceboook_created_date = db.Column(db.Date) # NEW!!!!
    facebook_changed_date = db.Column(db.Date) # NEW!!!!

    result_count = db.Column(db.Integer) # Total Facebook Page AAs
    result_count_history = db.Column(db.String(500)) # Total Facebook Page AAs History
    count_difference = db.Column(db.Integer) # Total Facebook Page AAs Changes (Final - Start)

    added_date = db.Column(db.DateTime) # Added Product To Database (Datetime)
    last_update = db.Column(db.DateTime)  # Last Update To The Data (Datetime)

    product_name = db.Column(db.String(200)) # Product Name
    product_link = db.Column(db.String(400)) # Product Website Link
    prod_created_date = db.Column(db.Date) # NEW!!!!
    domain = db.Column(db.String(400)) # Domain Link
    products_count = db.Column(db.Integer) # Total Number Of Products In Store
    domain_reg_date = db.Column(db.Date) # NEW!!!!

    track = db.Column(db.Boolean, default=False) # Tracking Status ( Whether To Track Product )

    update_changed_date = db.Column(db.Boolean, default=False)

# Define the database model
class LogData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(200))
    info = db.Column(db.String(500))
    status = db.Column(db.String(200))
    start_time = db.Column(db.DateTime, nullable=False)  # Store as datetime
    end_time = db.Column(db.DateTime, nullable=False)  # Store as datetime
    execution_time = db.Column(db.String(100))  # Optional string field for formatted duration


# Initialize the database
with app.app_context():
    db.create_all()

def initialize_driver():
    # Automatically download and install the correct version of chromedriver
    chromedriver_autoinstaller.install()

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--incognito")
    options.add_argument("--disable-extensions")  # Disable unnecessary extensions
    options.add_argument("--disable-images")  # Disable image loading
    options.add_argument("--window-size=800x600")  # Set small window size to reduce resource usage
    options.add_argument("--disable-logging")  # Disable logging if not needed

    # Additional flags for media handling in windows
    options.add_argument("--disable-accelerated-video-decode")  # Disable accelerated video decode
    options.add_argument("--disable-video-decoder")  # Force disabling video decoding
    options.add_argument("--disable-media-playback")  # Disable media playback (if not required)
    options.add_argument("--log-level=3")  # Suppress non-critical logs
    options.add_argument("--disable-features=MediaSessionService")  # Disable media session
    options.add_argument("--disable-plugins")  # Disable plugins
    options.add_argument("--disable-software-rasterizer")  # Prevent use of software rasterizer
    options.add_argument("--media-cache-size=1")  # Limit media cache size
    options.add_argument("--disable-media-cache")  # Disable media cache
    options.add_argument("--disable-web-security")  # Disable web security features (use with caution)
    options.add_argument("--disable-media-stream")  # Disable media streams
    options.add_argument("--disable-audio-context")  # Disable audio context

    # Configure driver settings based on environment
    if os.getenv('RENDER') == 'true':  # Render environment
        chrome_bin = "/usr/bin/chromium"  # Render's default Chromium binary
        options.binary_location = chrome_bin
        service = Service(chromedriver_autoinstaller.install())
        driver = webdriver.Chrome(service=service, options=options)

    elif platform.system() == 'Windows':  # Windows-specific setup
        # Option 1 : chromedriver_autoinstaller installs the correct version in the system's PATH (DONT WORK)
        # chromedriver_path = chromedriver_autoinstaller.install()

        # Option 2 : Specify chromedriver path manually
        chromedriver_path = r"C:\Users\insaf\OneDrive\Desktop\Softwares\chromedriver.exe"  # Update with your path
        service = Service(executable_path=chromedriver_path)

        print(f"Chromedriver installed at: {chromedriver_path}")  # Check installation path
        
        driver = webdriver.Chrome(service=service, options=options)

    else:  # Mac/Linux local environment
        chromedriver_path = '/usr/local/bin/chromedriver'
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)

    return driver


# Your existing functions (extract_domain, cleanup_url, etc.)


def extract_domain(url):
    """
    Extracts the domain from a given URL and removes 'www.' if present.
    """
    print("Extracting domain from the URL.")

    # Match and remove 'http://' or 'https://' at the start
    match = re.sub(r'^(?:http://|https://)', '', url)
    
    # Extract everything up to the first '/' (or the entire string if no '/' is present)
    domain = match.split('/')[0]

    # Remove 'www.' if it exists at the beginning of the domain
    domain = re.sub(r'^www\.', '', domain)

    return domain

def cleanup_url(url):
    print("Clean URL query parameters.")
    parsed_url = urlparse(url)
    cleaned_url = urlunparse(parsed_url._replace(query=""))
    return cleaned_url

def extractable_xml(xml_url):
    print("Checking if XML extractable...")
    try:
        # Perform a GET request to the URL
        response = requests.get(xml_url, timeout=5)

        # Check if the response is valid (status code 200) and if Content-Type is XML
        if response.status_code == 200 and 'xml' in response.headers.get('Content-Type', '').lower():
            print("XML Status: Data exists")
            return True  # The content is reported as XML
        print("XML Status: No data")
        return False  # Either the status code isn't 200 or the content isn't XML

    except requests.exceptions.RequestException as e:
        # Catch any request-related exceptions (timeout, HTTP ERROR, etc.)
        print(f"XML Status: No data, ERROR: {str(e)}")
        return False
    
def new_extract_data_from_xml(xml_url):
    # print("Extracting data from XML.")
    try:
        # Fetch XML content from the URL
        response = requests.get(xml_url)
        if response.status_code != 200:
            print(f"ERROR: Unable to fetch XML from {xml_url}")
            return None, None
        
        # Parse the fetched XML content
        root = ElementTree.fromstring(response.text)
        
        created_at = root.find(".//created-at")
        product_name = root.find(".//title")

        if created_at is not None:
            date_str = created_at.text.split('T')[0]
            created_at_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            product_name_text = product_name.text if product_name is not None else None
            print("Product Name:", product_name_text)
            return created_at_date, product_name_text
        
        return None, None

    except Exception as e:
        print(f"ERROR extracting date: {str(e)}")
        return None, None
    
def convert_stringdate_to_date(date_str):
    try:
        # Parse the date string to a datetime object
        return datetime.strptime(date_str, "%d-%b-%Y").date()
    except ValueError:
        return None  # Handle invalid date format

def extract_data_from_xml(xml_url):
    # print("Extracting data from XML.")
    try:
        root = ElementTree.fromstring(xml_url)
        created_at = root.find(".//created-at")
        product_name = root.find(".//title")

        if created_at is not None:
            date_str = created_at.text.split('T')[0]
            created_at_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            today = datetime.today().date()
            delta = today - created_at_date
            formatted_date = created_at_date.strftime('%d-%b-%Y')
            days_ago = delta.days  # This will be an integer
            product_name_text = product_name.text if product_name is not None else None
            print("Product Name:", product_name_text)
            return formatted_date, days_ago, product_name_text
        
        return None, None, None

    except Exception as e:
        print(f"ERROR extracting date: {str(e)}")
        return None, None, None

def get_domain_registration_date(driver, domain):
    print("Get domain registration date using WHOIS.")
    whois_url = f"https://www.whois.com/whois/{domain}"
    registration_date = None
    days_ago = None

    try:
        driver.get(whois_url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, "//div[@class='df-row'][./div[@class='df-label'][contains(text(),'Registered On:')]]/div[@class='df-value']")))
        registration_date_element = driver.find_element(By.XPATH, "//div[@class='df-row'][./div[@class='df-label'][contains(text(),'Registered On:')]]/div[@class='df-value']")
        registration_date_text = registration_date_element.text
        registration_date = datetime.strptime(registration_date_text, '%Y-%m-%d').date()
        today = datetime.today().date()
        delta = today - registration_date
        registration_date = registration_date.strftime('%d-%b-%Y')
        days_ago = delta.days
    except Exception as e:
        print(f"ERROR retrieving registration date: {str(e)}")

    return whois_url, registration_date, days_ago

def format_to_dd_mon_yyyy(registration_date):
    try:
        if isinstance(registration_date, datetime):
            # If it's a single datetime object
            return registration_date.strftime('%d-%b-%Y')
        elif isinstance(registration_date, list) and registration_date:
            # If it's a list, use the earliest date (assuming it's sorted)
            earliest_date = min(registration_date)
            return earliest_date.strftime('%d-%b-%Y')
        elif isinstance(registration_date, str):
            # If it's a string, parse it to a datetime object
            parsed_date = datetime.strptime(registration_date, '%Y-%m-%d %H:%M:%S')
            return parsed_date.strftime('%d-%b-%Y')
        else:
            raise ValueError("Invalid registration_date format.")
    except Exception as e:
        print(f"ERROR formatting date: {e}")
        return None

def new_get_domain_registration_date(domain):
    registration_date = None
    try:
        w = whois(domain)
        registration_date = w.creation_date
        # print("Domain Raw Registration Date : ", registration_date)

        # format given examples:
        # 2013-05-21 15:20:04
        # [datetime.datetime(2012, 5, 11, 3, 31, 42), datetime.datetime(2012, 5, 10, 22, 31, 42)]
    
        formated_registration_date = convert_stringdate_to_date(str(format_to_dd_mon_yyyy(registration_date)))
        if formated_registration_date is None:
            print("ERROR - Invalid registration date format.")
            return None
        # print("Domain Formated Registration Date : ", formated_registration_date)
        
    except Exception as e:
        print(f"ERROR - Unable to retrieve registration date: {str(e)}")
        return None
    
    return formated_registration_date

       
def fetch_data_concurrently(driver, url, domain, product_xml_url):
    print("Fetching data concurrently for XML and WHOIS")
    whois_data, created_at_date, created_days_ago, product_name_text = None, None, None, None

    with concurrent.futures.ThreadPoolExecutor() as executor:

        # Submit tasks concurrently
        xml_future = executor.submit(requests.get, product_xml_url)
        whois_future = executor.submit(get_domain_registration_date, driver, domain)

        try:
            # Get the result of the XML request
            xml_response = xml_future.result()  # Block until it's finished

            if xml_response and xml_response.status_code == 200:
                xml_content = xml_response.text
                created_at_date, created_days_ago, product_name_text = extract_data_from_xml(xml_content)
            else:
                print(f"XML response was not successful: {xml_response.status_code if xml_response else 'No response'}")

        except Exception as e:
            print(f"XML - ERROR occurred: {str(e)}")

        try:
            # Get the result of the WHOIS request
            whois_data = whois_future.result()  # Block until it's finished
        except Exception as e:
            print(f"WHOIS - ERROR occurred: {str(e)}")

        return whois_data, created_at_date, created_days_ago, product_name_text


def extract_results(url):

    # Inititialize all data 
    domain = product_name = whois_data = created_at_date = created_days_ago = whois_url = registration_date = registration_days_ago = created_days_ago = ads_library_url = result_count = result_count_history = time_taken = added_date = added_days_ago = count_difference = None

    start_time = time.time()
    status = None

    # Check if the url already exists in the database
    existing_data = URLData.query.filter_by(url=url).first()

    if existing_data:
        status = "ERROR - URL already exists. Skipping database entry."
        print(status)
        return status

    driver = initialize_driver()

    url = cleanup_url(url)
    domain = extract_domain(url)
    if not domain:
        status = "ERROR - Invalid URL"
        print(status)
        return status

    ads_library_url = f"https://www.facebook.com/ads/library/?ad_type=all&search_type=keyword_unordered&media_type=all&active_status=active&country=ALL&q={domain}"
    product_xml_url = f"{url}.xml"

    # Check system readiness
    if not test_system_ready(driver):
        driver.quit()
        print("TRY AGAIN LATER...")
        status = "ERROR - System not ready. Try Again Later..."
        return status

    print("Extracting Ads results")
    try:
        result_count = 0
        result_count = result_counter(driver, ads_library_url)
        print("Result Count : ", result_count)

        result_count_history = result_count
        count_difference = 0

        added_date = date.today().strftime('%d-%b-%Y')
        added_days_ago = 0

        # check if have XML, else, just extract result count will suffice
        if extractable_xml(product_xml_url):
            whois_data, created_at_date, created_days_ago, product_name = fetch_data_concurrently(driver, url, domain, product_xml_url)
            whois_url, registration_date, registration_days_ago = whois_data

            # Cast created_days_ago to integer
            created_days_ago = int(created_days_ago) if created_days_ago is not None else 0
            registration_days_ago = int(registration_days_ago) if registration_days_ago is not None else 0

    except Exception as e:
        print(f"Result Count - ERROR occurred: {str(e)}")
        count_difference = added_date = added_days_ago = result_count_history = result_count = created_at_date = created_days_ago = whois_url = registration_date = registration_days_ago = product_name = None

    driver.quit()

    end_time = time.time()
    time_taken_seconds = end_time - start_time
    minutes = int(time_taken_seconds // 60)
    seconds = int(time_taken_seconds % 60)
    time_taken = f"{minutes} min {seconds} sec"

    if product_name == None:
        status = "ERROR - Non-extractable Data. Skipping database entry."
        print(status)
        return status
    
    # After extracting data, save to the database
    new_data = URLData(
        url=url,
        domain=domain,
        product_name=product_name,
        created_at_date=created_at_date,
        created_days_ago=created_days_ago,
        whois_url=whois_url,
        registration_date=registration_date,
        registration_days_ago=registration_days_ago,
        ads_library_url=ads_library_url,
        result_count=result_count,
        result_count_history=result_count_history,
        time_taken=time_taken,
        added_date = added_date,
        added_days_ago = added_days_ago,
        count_difference = count_difference
    )
    
    print("Storing data in the database")
    # Save to the database
    db.session.add(new_data)
    db.session.commit()
    status = "SUCCESS - Data stored in database successfully"
    print(status)

    return status

def clean_fb_href_link(url):
    # print("Original URL Given:", url)

    # Parse the URL
    parsed_url = urlparse(url)
    # print("Parsed URL:", parsed_url)
    
    # Extract the "u" parameter and decode it
    query_params = parse_qs(parsed_url.query)
    # print("Query Parameters from Facebook URL:", query_params)
    
    # Decode the "u" parameter
    decoded_url = unquote(query_params.get('u', [''])[0])  # Decode 'u' parameter
    # print("Decoded URL from 'u' parameter:", decoded_url)
    
    # Parse the decoded URL to check for existing query parameters
    decoded_parsed_url = urlparse(decoded_url)
    # print("Parsed Decoded URL:", decoded_parsed_url)
    
    # Rebuild the cleaned URL by removing all query parameters
    cleaned_url = decoded_parsed_url._replace(query='')  # Remove all query parameters
    # print("Cleaned URL (with no query parameters):", cleaned_url)
    
    # Rebuild the final URL
    rebuilt_url = urlunparse(cleaned_url)
    # print("Rebuilt URL:", rebuilt_url)
    
    # Final cleaned URL (ensuring no trailing '?')
    if rebuilt_url.endswith('?'):
        rebuilt_url = rebuilt_url[:-1]  # Remove trailing '?' if no query parameters exist
    
    # Print the final cleaned URL
    # print("Cleaned URL:", rebuilt_url)

    actual_cleaned_url = get_actual_url(rebuilt_url)
    # print("Actual Cleaned URL:", actual_cleaned_url)

    # Parse the URL
    final_parsed_url = urlparse(actual_cleaned_url)
    # Rebuild the URL without the query part
    final_cleaned_url = urlunparse(final_parsed_url._replace(query=''))
    # print("Final Cleaned URL:", final_cleaned_url)

    return final_cleaned_url

# Important function to open up bitly or shortened links!
def get_actual_url(input_url):
    try:
        # Use HEAD request to resolve URL
        response = requests.head(input_url, allow_redirects=True)
        # print("SUCCESS - Head Req. Completed.")
        return response.url
    except requests.RequestException:
        try:
            # print("ERROR - Unable to use HEAD Req., now use GET Req.")
            # Fallback to GET request if HEAD fails
            response = requests.get(input_url, allow_redirects=True)
            return response.url
        except requests.RequestException:
            # Return the original URL if both HEAD and GET fail
            print("ERROR - Unable to resolve URL. Returning input URL.")
            return input_url

def extract_library_ids(driver, keyword):

    print("Extracting Ads results")

    ads_library_url = "https://www.facebook.com/ads/library/?ad_type=all&search_type=keyword_unordered&country=US&active_status=active&media_type=all&q=" + str(keyword)

    # ads_library_url = "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&media_type=all&search_type=keyword_unordered&q=" + str(keyword)
    print("Ad Library Link : ", ads_library_url)

    total_result_count = result_counter(driver, ads_library_url)
    print("Total Results Available: ", total_result_count)

    current_result_count = 0

    processed_library_ids = set()  # To track already processed IDs
    processed_divs = set()  # Track processed divs to avoid reprocessing
    scroll_pause_time = 2  # Pause time between scrolls
    max_scroll_attempts = 30  # Max attempts to scroll without finding new data
    scroll_attempts = 0
    status = "Extraction Complete"
    flag = 0

    # Log data
    start_time = end_time = datetime.now().replace(microsecond=0)
    execution_duration = str(end_time - start_time)
    keyword_number = 0 # Total number of extractions for the keyword
    keyword_inclusion_count = 0 # Number of data added to database for the keyword
    loaded_results = 0 # Total AAs loaded for the keyword

    inclusion_rate_threshold = 2  # In percentage
    inclusion_rate = 0.0  # Initial rate as float
    extraction_minimum_attempts = 100
    extraction_speed = 0
    inclusion_speed = 0
    
    run = True

    log_data = LogData(
        action = "AD SEARCH",
        info = f'{{"Keyword": "{keyword}", "Available Results": {total_result_count}, "Loaded Results": {loaded_results}, "Extractions": {keyword_number}, "Extraction Speed": {extraction_speed}/h, "Inclusions": {keyword_inclusion_count}, "Inclusion Speed": {inclusion_speed}/h, "Inclusion Rate": {inclusion_rate}%}}',
        status="PROCESSING",  # Status while processing
        start_time=start_time,  # Start time
        end_time=end_time,  # End time will be updated later
        execution_time=execution_duration  # Execution time will be updated later
    )
    db.session.add(log_data)
    db.session.commit() 

    last_height = driver.execute_script("return document.body.scrollHeight")  # Get initial scroll height

    if (total_result_count == 0) :
        print("------------------------")
        status = "SUCCESS - Completed"
        print(status)

        log_data.status = status
        log_data.end_time = datetime.now().replace(microsecond=0)
        log_data.execution_time = str(datetime.now().replace(microsecond=0) - log_data.start_time)
        db.session.commit()

        return status

    while (scroll_attempts < max_scroll_attempts) and run:
        try:
            # Wait and find divs
            WebDriverWait(driver, 30).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, '_7jvw x2izyaf x1hq5gj4 x1d52u69')]"))
            )
            divs = driver.find_elements(By.XPATH, "//div[contains(@class, '_7jvw x2izyaf x1hq5gj4 x1d52u69')]")

            new_data_found = False  # Track if new data is found in this iteration

            for div in divs:
                try:
                    div_id = div.get_attribute('outerHTML')  # Unique identifier for the div
                    if div_id in processed_divs:
                        continue  # Skip already processed divs
                    processed_divs.add(div_id)

                    # Extract spans
                    spans = div.find_elements(By.TAG_NAME, 'span')
                    div_library_id = creative_start_date = div_href = page_name = None
                    div_ads_count = 1

                    # Check for anchor tag and spans (FB page link)
                    try:
                        a_tag = div.find_element(By.XPATH, ".//a[@href]")
                        div_href = a_tag.get_attribute('href')
                    except Exception:
                        div_href = None
                        continue

                    # Check for the second anchor tag's href by using find_elements
                    try:
                        # Find all anchor tags with href and then get the second one
                        a_tags = div.find_elements(By.XPATH, ".//a[@href]")
                        if len(a_tags) > 1:
                            product_href = a_tags[1].get_attribute('href')  # index 1 for second element
                            # print("Product link:", product_href)
                        else:
                            product_href = None
                            continue
                    except Exception:
                        product_href = None
                        continue

                    for span in spans:
                        text = span.text.strip()
                        # print(text)

                        # Match Library ID
                        match_id = re.search(r'Library ID[:\s]*(\d+)', text)
                        if match_id:
                            div_library_id = match_id.group(1)

                        # Correct pattern with month first
                        match_date = re.search(r'Started running on (\w{3} \d{1,2}, \d{4})', text)
                        if match_date:
                            # print(f"match date : {match_date}")
                            creative_start_date = convert_stringdate_to_date(validate_and_format_date(match_date.group(1)))

                        # Extract the number of ads using regex
                        match_ads_count = re.search(r'(\d+)\s+ads use this creative and text', text)
                        if match_ads_count:
                            div_ads_count = int(match_ads_count.group(1))  # Extract the number as an integer

                    # Process and store data
                    if div_library_id not in processed_library_ids:
    
                        processed_library_ids.add(div_library_id)  # Mark this Library ID as processed

                        print("------------------------")

                        keyword_number += 1 

                        # Calculate end time and execution time
                        log_data.end_time = datetime.now().replace(microsecond=0)
                        log_data.execution_time = str(log_data.end_time - log_data.start_time)  # String format for logging
                        log_data.status = "PROCESSING"  # Status for incomplete execution

                        # Convert execution time to seconds for speed calculations
                        execution_time_seconds = (log_data.end_time - log_data.start_time).total_seconds()

                        # Calculate speeds in per hour
                        extraction_speed = round((keyword_number / execution_time_seconds) * 3600)  # Extractions per hour
                        inclusion_speed = round((keyword_inclusion_count / execution_time_seconds) * 3600)  # Inclusions per hour

                        # Calculate Inclusion Rate (in percentage)
                        inclusion_rate = round((keyword_inclusion_count / keyword_number) * 100, 1)  # Format to 1 decimal place

                        if (keyword_number > extraction_minimum_attempts) and (inclusion_rate < inclusion_rate_threshold):
                            print(f"Inclusion Rate {inclusion_rate}% is below the threshold. Exiting...")
                            run = False
                            break  # Immediately exit the loop

                        log_data.info = f'{{"Keyword": "{keyword}", "Available Results": {total_result_count}, "Loaded Results": {loaded_results}, "Extractions": {keyword_number}, "Extraction Speed": {extraction_speed}/h, "Inclusions": {keyword_inclusion_count}, "Inclusion Speed": {inclusion_speed}/h, "Inclusion Rate": {inclusion_rate}%}}'

                        print(f"[Total Extract No. : {keyword_number}]")

                        added_date = last_update = datetime.now().replace(microsecond=0)
                        print(f"Added Date : {added_date}")
                        print(f"Last Update : {last_update}")
                        
                        current_result_count += div_ads_count
                        loaded_results += div_ads_count
                        print(f"Iteration Result Load: {current_result_count} / {total_result_count}")

                        db.session.commit()

                        print(f"Added To Database: {keyword_inclusion_count}")
    
                        print(f"Keyword: {keyword}")
                        print(f"Library ID: {div_library_id}")
                        print(f"Library ID Link : https://www.facebook.com/ads/library/?id={div_library_id}")
                        print(f"Creative Started on: {creative_start_date}")
                        print(f"Facebook Page Link: {div_href}")
                        print(f"Creative AAs: {div_ads_count}")
                        
                        # Open a new tab, go to the about page, and extract the Creation date
                        facebook_about_page = div_href + "about_profile_transparency"
                        print("Facebook About page : ", facebook_about_page)

                        # Check if have link in text or CTA button, else just skip!
                        product_link = prod_created_date = product_name = None
                    
                        try:
                            
                            if product_href:
                                print(f"Creative Product Link : {product_href}")
                                product_link = clean_fb_href_link(product_href)
                                print(f"Creative Product Link (Cleaned): {product_link}")

                                if not any(keyword in product_link for keyword in ["/products/", "/product/", "/collections/", "/pages/"]):
                                    status = "ERROR - Page is not a Shopify Product Link!"
                                    print(status)
                                    continue

                                # Extract product info from product_page (If XML not readable, skip)
                                product_xml_url = f"{product_link}.xml"
                                # print(f"product XML : {product_xml_url}")

                                try : 
                                    prod_created_date, product_name = new_extract_data_from_xml(product_xml_url)
                                    if prod_created_date == None:
                                        status = "ERROR - No XML data, skip database entry."
                                        print(status)
                                        continue
                                except Exception as e:
                                    status = "ERROR - Unable to extract XML data, skip database entry."
                                    print(status)
                                    continue

                            else:
                                status = "ERROR - Creative Product Link not found, skip database entry."
                                print(status)
                                continue

                        except Exception as e:
                            status = "ERROR - 'Shop Now' button not found, skip database entry."
                            # status = f"ERROR for shop now encountered: {e}"
                            print(status)
                            continue

                        # If Product or Library ID in database, Skip Result Counting

                        # Check if product page exists in the database
                        if ADSData.query.filter_by(product_link=product_link).first():

                            # If product in database, & last_update is more than 1 hour ago, update the product AA
                            status = "ERROR - Product Link in database, skip database entry."
                            print(status)
                            continue

                        # Check if page link exists in the database (Change to if product is diff!)
                        # if ADSData.query.filter_by(div_href=div_href).first():
                        #     status = "ERROR - Page in database, Skipping result count & entry."
                        #     print(status)
                        #     continue

                        # Check if library_id exists in the database
                        if ADSData.query.filter_by(div_library_id=div_library_id).first():
                            status = "ERROR - Library ID exist in database, skip database entry."
                            print(status)
                            continue

                        # Open new tab
                        driver.execute_script("window.open('');")
                        windows = driver.window_handles
                        driver.switch_to.window(windows[-1])  # Switch to the new tab
                        
                        # Navigate to the About Profile page
                        driver.get(facebook_about_page)
                        
                        # Wait for the creation date element to load (adjust XPath if needed)
                        faceboook_created_date = None
                        page_id = page_ads_link = None
                        result_count = None

                        #####  EXTRACT PAGE CREATION DATE & PAGE ID ####
                        try:
                            # Wait for the divs to load
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'xzsf02u x6prxxf xvq8zen x126k92a x12nagc')]"))
                            )

                            # Find all divs containing the page id
                            divs = driver.find_elements(By.XPATH, "//div[contains(@class, 'xzsf02u x6prxxf xvq8zen x126k92a x12nagc')]")
                            
                            page_id = divs[0].text.strip() 
                            page_ads_link = "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&media_type=all&search_type=page&source=page-transparency-widget&view_all_page_id=" + page_id
                            print(f"Page ID: {page_id}")

                            faceboook_created_date = convert_stringdate_to_date(validate_and_format_date(divs[1].text.strip()))
                            print(f"Facebook Creation Date: {faceboook_created_date}")

                        except Exception as e:
                            # Log ERROR but continue with the next item
                            print(f"ERROR - Failure extracting Page Info")

                            driver.close()
                            # Switch back to the original tab to continue processing
                            driver.switch_to.window(windows[0])

                            continue

                        #####  EXTRACT PAGE NAME ####
                        try:
                            # Wait until the <h1> element is present in the DOM
                            page_name_element = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'html-h1')]"))
                            )
                            # Extract the text content of the <h1> element
                            page_name = page_name_element.text
                        except Exception as e:
                            flag += 1
                            print(f"ERROR - Failed to extract page name")

                            driver.close()
                            # Switch back to the original tab to continue processing
                            driver.switch_to.window(windows[0])

                            continue

                        print(f"Page Name: {page_name}")

                        #####  EXTRACT PAGE LAST CHANGED DATE ####
                        facebook_changed_date = get_facebook_changed_date(driver)
                        update_changed_date = True
                        print(f"Facebook Latest Changed Date: {facebook_changed_date}")

                        # if facebook_changed_date != faceboook_created_date:
                        #     print("Changed and Created dates are different!")

                        # Close the current tab after extraction
                        driver.close()

                        # Switch back to the original tab to continue processing
                        driver.switch_to.window(windows[0])

                        # Open another new tab for result count extraction (if necessary)
                        try:
                            driver.execute_script("window.open('');")
                            windows = driver.window_handles
                            driver.switch_to.window(windows[-1])  # Switch to the new tab       

                            if(page_ads_link != None) :
                                result_count = result_counter(driver, page_ads_link)
                            print("Result Count : ", result_count)

                            # Close the current tab after extraction
                            driver.close()

                            # Switch back to the original tab to continue the loop
                            driver.switch_to.window(windows[0])

                        except Exception as e:
                            flag += 1
                            print(f"ERROR - Failure extracting result count")
                            continue

                        # Check for domain registration info
                        domain = extract_domain(product_link)
                        print(f"Domain : {domain}")
                        try:
                            domain_reg_date = new_get_domain_registration_date(domain)
                            print("Domain Registration Date : ", domain_reg_date)

                        except Exception as e:
                            flag += 1
                            print(f"ERROR - Failure extracting domain registration data")
                            continue

                        if domain:
                            products_count = find_products_count(domain)
                            print(f"Total Products Count: {products_count}")
                        
                        # Flag that new data was found
                        new_data_found = True

                        if(flag > 5):
                            status = "ERROR - More than 5 flags, terminate extractions"
                            print(status)
                            return status

                        # Define variables and their corresponding error messages
                        checks = [
                            (faceboook_created_date, "ERROR - Facebook Creation Date is None, skip database entry."),
                            (result_count, "ERROR - Result Count is None, skip database entry."),
                            (domain_reg_date, "ERROR - Domain Registration Date is None, skip database entry."),
                            (creative_start_date, "ERROR - Creative Start Date is None, skip database entry."),
                            (products_count, "ERROR - Total Product Count is None, skip database entry."),
                            (div_library_id, "ERROR - Library ID is None, skip database entry."),
                            (facebook_changed_date, "ERROR - Facebook Changed Date is None, skip database entry.")
                        ]

                        exit = False
                        for variable, error_message in checks:
                            if variable is None:
                                status = error_message
                                flag += 1  # Increment flag for each issue, if needed
                                exit = True
                                print(status)
                                continue  # Dont have to check other variable if one alredy has issues
                        if exit:
                            continue
                        
                        if products_count <= 0:
                            status = "ERROR - Total Products Count is <= 0, skip database entry."
                            flag += 1
                            print(status)
                            continue

                        # After extracting data, save to the database
                        new_data = ADSData(
                            keyword=keyword,
                            page_name = page_name,
                            ads_library_url=ads_library_url,
                            div_href=div_href,
                            div_library_id=div_library_id,
                            creative_start_date=creative_start_date,
                            div_ads_count=div_ads_count,
                            facebook_about_page=facebook_about_page,
                            page_id=page_id,
                            page_ads_link=page_ads_link,
                            faceboook_created_date=faceboook_created_date,
                            result_count=result_count,
                            result_count_history = result_count,
                            count_difference = 0,
                            product_name = product_name,
                            product_link = product_link,
                            prod_created_date = prod_created_date,
                            domain_reg_date = domain_reg_date,
                            products_count = products_count,
                            domain = domain,
                            last_update = last_update,
                            added_date = added_date,
                            facebook_changed_date = facebook_changed_date,
                            update_changed_date = update_changed_date # remove once all done
                        )
                        db.session.add(new_data)

                        # Update log data
                        keyword_inclusion_count += 1

                        log_data.end_time = datetime.now().replace(microsecond=0)
                        log_data.execution_time = str(log_data.end_time - log_data.start_time)

                        # Convert execution time to seconds for speed calculations
                        execution_time_seconds = (log_data.end_time - log_data.start_time).total_seconds()

                        # Calculate speeds in per hour
                        extraction_speed = round((keyword_number / execution_time_seconds) * 3600)  # Extractions per hour
                        inclusion_speed = round((keyword_inclusion_count / execution_time_seconds) * 3600)  # Inclusions per hour

                        log_data.info = f'{{"Keyword": "{keyword}", "Available Results": {total_result_count}, "Loaded Results": {loaded_results}, "Extractions": {keyword_number}, "Extraction Speed": {extraction_speed}/h, "Inclusions": {keyword_inclusion_count}, "Inclusion Speed": {inclusion_speed}/h, "Inclusion Rate": {inclusion_rate}%}}'

                        print("Storing data in the database")
                        # Save to the database
                        db.session.commit()
                        
                        status = "SUCCESS - Data stored in database successfully"
                        print(status)

                        # Give 1 sec break, for other task to step in...
                        time.sleep(1)

                        flag = 0 # Reset to 0 since no issue storing into database


                # ADD THE EXCEPT HERE
                except Exception as e:
                    status = "ERROR - Issue within loop"
                    print(status)
                    continue

            # Scroll to load more content
            if new_data_found:
                scroll_attempts = 0  # Reset attempts since new data was found
            else:
                scroll_attempts += 1

            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(scroll_pause_time)

            # Check if scrolling has reached the bottom
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                scroll_attempts += 1
            else:
                last_height = new_height

        except Exception as e:
            status = "ERROR - Exception"
            print(f"ERROR encountered: {e}")

            log_data.status = status
            log_data.end_time = datetime.now().replace(microsecond=0)
            log_data.execution_time = str(datetime.now().replace(microsecond=0) - log_data.start_time)
            db.session.commit()

            return status
    
    print("------------------------")
    if run:
        status = "SUCCESS - Completed"
    else:
        status = "ERROR - Extraction"

    print(status)

    log_data.status = status
    log_data.end_time = datetime.now().replace(microsecond=0)
    log_data.execution_time = str(datetime.now().replace(microsecond=0) - log_data.start_time)
    db.session.commit()

    return status

def get_facebook_changed_date(driver):
    facebook_changed_date = None
    try:
        driver.execute_script("""
            var elements = document.querySelectorAll('div[aria-label="See All"].x1i10hfl');
            elements.forEach(function(element) {
                element.click();  // Simulate click on the 'See All' button
            });
        """)

        # print("Clicked 'See All' Button...")

        # Wait until at least 3 elements are found
        WebDriverWait(driver, 10).until(
            lambda driver: len(driver.find_elements(By.XPATH, "//*[contains(@class, 'x676frb') and contains(@class, 'x1nxh6w3')]")) >= 2
        )

        # Now that we know there are more than 2 elements, find them
        elements = driver.find_elements(By.XPATH, "//*[contains(@class, 'x676frb') and contains(@class, 'x1nxh6w3')]")

        found = False

        for index in range(len(elements)):
            try:
                # Attempt to parse the text of the current element as a date
                text = elements[index].text.strip()
                print(f"Index {index}: {text}")
                
                datetime.strptime(text, "%B %d, %Y") # If this passes, the text is a valid date (Else, goes to ValueError)

                facebook_changed_date = convert_stringdate_to_date(validate_and_format_date(text))
                found = True
                # print(f"Facebook Latest Changed Date Found: {facebook_changed_date}")
                break  # Exit the loop once a valid date is found
            except ValueError:
                # If parsing fails, the text is not a valid date
                continue

        if not found:
            facebook_changed_date = None
            print("No valid date found in the elements. Facebook Changed Date set as None.")

    except Exception as e:
        print(f"Error: {e}")
        facebook_changed_date = None
        return facebook_changed_date
    
    return facebook_changed_date


def find_products_count(domain):
    # Ensure the domain has the proper scheme (https://)
    if not domain.startswith("http://") and not domain.startswith("https://"):
        domain = "https://" + domain  # Add https:// if not present
    
    url = f"{domain}/products.json"

    def has_products(page):
        """Check if the page contains products."""
        try:
            response = requests.get(f"{url}?page={page}")
            if response.status_code == 200:
                data = response.json()
                return 'products' in data and len(data['products']) > 0, len(data['products'])
            return False, 0
        except Exception as e:
            print(f"ERROR on page {page}: {e}")
            return False, 0

    # Step 1: Find the upper bound for the number of pages
    low, high = 1, 1
    while True:
        has_product, _ = has_products(high)
        if not has_product:
            break
        high *= 2  # Double the high bound until no products are found

    # Step 2: Perform binary search to find the last page with products
    last_page = 0
    products_on_last_page = 0
    while low <= high:
        mid = (low + high) // 2
        has_product, product_count = has_products(mid)
        if has_product:
            last_page = mid
            products_on_last_page = product_count
            low = mid + 1  # Move to the next range
        else:
            high = mid - 1  # Move to the previous range

    # Step 3: Calculate the total number of products
    if last_page == 0:
        return 0  # No products found

    # Total products = (Full pages * 30) + products on the last page
    total_products = (last_page - 1) * 30 + products_on_last_page
    return total_products


def update_total_products_count():
    try:
        # Use app context correctly to interact with the database
        with app.app_context():
            all_data = ADSData.query.filter(
                ADSData.products_count == None,
            ).all()

            data_count = len(all_data)
            
            print(f"Total records to process: {data_count}")
            
            # A list to collect data to delete or update
            delete_data = []
            update_data = []

            def process_data(data):
                try:
                    # Ensure each thread has its own application context
                    with app.app_context():  # This ensures application context within the thread
                        domain = extract_domain(data.product_link)
                        print(f"Processing ID-{data.id} ( {domain} ),")
                        
                        products_count = find_products_count(domain)
                        
                        if products_count is None or products_count <= 0:
                            delete_data.append(data)  # Mark data for deletion
                            print(f"Marking ID-{data.id} ( {domain} ), for deletion due to invalid product count ({products_count}).")
                            return
                        
                        data.products_count = products_count
                        update_data.append(data)  # Mark data for update
                        print(f"Marking ID-{data.id} ( {domain} ), for update with product count {products_count}.")
                    
                except Exception as e:
                    print(f"ERROR processing {data.id} ( {domain} ) : {e}")

            totalCount = len(all_data)
            count = 0

            # Using ThreadPoolExecutor to process data with multiple threads
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(process_data, data) for data in all_data]
                
                for future in as_completed(futures):
                    count += 1
                    try:
                        future.result()  # Retrieve results to catch exceptions
                        print(f"----- Executed {count}/{totalCount} -----")
                        
                    except Exception as e:
                        print(f"Unhandled exception in thread: {e}")
            
            # After all threads finish, perform the commit
          
            for data in delete_data:
                db.session.delete(data)
            db.session.commit()  # Commit deletions
            print(f"Deleted {len(delete_data)} records.")

            # Then perform updates
            for data in update_data:
                db.session.add(data)  # Mark data as updated
            db.session.commit()  # Commit updates
            print(f"Updated {len(update_data)} records.")
    
    except Exception as e:
        print(f"ERROR during app context setup: {e}")



def search_ad_library(keyword):
    with app.app_context(): 
        status = None
        current_result_count = total_result_count = None

        driver = initialize_driver()

        # Check system readiness
        if not test_system_ready(driver):
            driver.quit()
            print("TRY AGAIN LATER...")
            status = "ERROR - System not ready. Try Again Later..."
            return status
        
        try:
            # Execute main functionality
            status= extract_library_ids(driver, keyword)

        except Exception as e:
            print(f"ERROR occurred: {str(e)}")
            status = f"ERROR - {str(e)}"

        finally:
            driver.quit()

    return status

@app.route('/')
def home():
    return render_template('home.html')

@app.route("/prod_search", methods=["GET", "POST"])
def prod_search():
    data = None  # To store the specific result for the given URL
    status = None  # Initialize status to ensure it exists in all cases

    if request.method == "POST":
        url = request.form.get("url")
        if url:
            # Process the URL with extract_results
            status = extract_results(url)
            # Check if the URL data already exists in the database
            data = URLData.query.filter_by(url=url).first()

    return render_template("prod_search.html", data=data, status=status)

@app.route("/view_product_data")
def view_product_data():

    # Get the current page number and search term from query parameters
    page = int(request.args.get("page", 1))
    per_page = 5  # Number of rows per page
    search_query = request.args.get("search", "").strip()  # Get search term

    # Query the database with a filter if search_query is provided
    if search_query:
        # Dynamically build a search across all columns
        query = URLData.query.filter(
            URLData.id.ilike(f"%{search_query}%") |
            URLData.domain.ilike(f"%{search_query}%") |
            URLData.url.ilike(f"%{search_query}%") |
            URLData.product_name.ilike(f"%{search_query}%")
        )
    else:
        query = URLData.query

    total_count = query.count()

    # Paginate the filtered data
    paginated_data = query.order_by(URLData.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    # Extract the paginated items for the current page
    all_data = paginated_data.items
    total_pages = paginated_data.pages
    current_page = paginated_data.page

    return render_template(
        "view_product_data.html",
        all_data=all_data,
        page=current_page,
        total_pages=total_pages,
        search_query=search_query,  # Pass search query to the template
        total_count=total_count
    )



def format_time_string(time_str):
    # Split the time string into hours, minutes, and seconds
    hours, minutes, seconds = map(int, time_str.split(':'))
    
    # Build the human-readable format
    if hours == 0 and minutes == 0:
        return f"{seconds}s"
    elif hours == 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{hours}h {minutes}m {seconds}s"


@app.route("/view_log_data")
def view_log_data():
    # Get the current page number and search term from query parameters
    page = int(request.args.get("page", 1))
    per_page = 8  # Number of rows per page
    search_query = request.args.get("search", "").strip()  # Get search term

    # Count rows with status == "PROCESSING" in the entire table
    processing_count = LogData.query.filter_by(status="PROCESSING").count()

    # Query the database with a filter if search_query is provided
    if search_query:
        # Dynamically build a search across all columns
        query = LogData.query.filter(
            LogData.id.ilike(f"%{search_query}%") |
            LogData.action.ilike(f"%{search_query}%") |
            LogData.info.ilike(f"%{search_query}%") |
            LogData.start_time.ilike(f"%{search_query}%") |
            LogData.end_time.ilike(f"%{search_query}%") |
            LogData.execution_time.ilike(f"%{search_query}%") |
            LogData.status.ilike(f"%{search_query}%")
        )
    else:
        query = LogData.query

    total_count = query.count()

    # Paginate the filtered data
    paginated_data = query.order_by(LogData.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    # Extract the paginated items for the current page
    all_data = paginated_data.items
    total_pages = paginated_data.pages
    current_page = paginated_data.page

    # Add formatted dates to the data
    for data in all_data:
        data.formatted_start_time, data.time_ago_start_time = format_datetime(data.start_time)
        data.formatted_end_time, data.time_ago_end_time  = format_datetime(data.end_time)
        data.formatted_execution_time = format_time_string(data.execution_time)

    return render_template(
        "view_log_data.html",
        all_data=all_data,
        page=current_page,
        total_pages=total_pages,
        search_query=search_query,  # Pass search query to the template
        total_count=total_count,
        processing_count=processing_count
    )


import queue

# Define the function to get random combinations
def get_random_combination(keywords_list):
    # Randomly choose between a single keyword or a pair
    if random.choice([True, False]):
        # Single keyword
        return random.choice(keywords_list)
    else:
        # Random pair of two keywords
        return " | ".join(random.sample(keywords_list, 2))



def keyword_loop_search():

    print("Starting Keyword Loop Search")
    
    """
    Function to handle keyword searching using a queue and ThreadPoolExecutor.
    Returns the status of completed tasks.
    """
    continue_search = True

    # Load keywords from the file
    with open("keywords.txt", "r") as file:
        keywords_list = [line.strip() for line in file if line.strip()]  # Remove empty lines

    task_queue = queue.Queue()

    # Fill the queue with initial random combinations
    for _ in range(2):  # Start with 2 tasks
        task_queue.put(get_random_combination(keywords_list))

    # Use ThreadPoolExecutor to handle keyword searches
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = []

        # As long as there's a task in the queue, submit it
        while continue_search:
            # If the number of running tasks is less than max workers (i.e., a worker is available)
            if len(futures) < 2:
                # Get the next keyword from the queue and submit the task
                keyword = task_queue.get()
                future = executor.submit(search_ad_library, keyword)
                futures.append(future)
                print(f"Task submitted: {keyword}")

            # Check if any tasks have completed and remove them
            for future in futures[:]:
                if future.done():  # Check if the task is finished
                    futures.remove(future)  # Remove the completed task
                    print("A task has completed. Preparing new task...")
                    # Add a new task to the queue when a worker is ready
                    task_queue.put(get_random_combination(keywords_list))

            # Sleep briefly to avoid excessive CPU usage in the loop
            time.sleep(1)

        # Wait for all tasks to finish and collect results
        status = []
        for future in futures:
            result = future.result()  # This blocks until the task is completed
            status.append(result)

    return status

@app.route("/ad_search", methods=["GET", "POST"])
def ad_searcher():
    url_status = keyword_status = None

    if request.method == "POST":

        keyword = request.form.get("keyword")
        url = request.form.get("adliburl")

        if keyword:
            # Start a new thread for a single keyword search using ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(search_ad_library, keyword)
                keyword_status = future.result()  # Wait for the result

            print("------ Completed Keyword Search ------")

            
        if url:
            # Start a new thread for a single keyword search using ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(ads_info, url)
                url_status = future.result()  # Wait for the result

            print("------ Completed AD Lib Search ------")

    return render_template("ad_search.html", keyword_status=keyword_status,url_status=url_status )


@app.route("/view_product_data/<int:days_ago>")
def view_product_data_by_days_ago(days_ago):
    # Filter rows with created_days_ago less than the provided days_ago value
    filtered_data = URLData.query.filter(URLData.created_days_ago < days_ago).all()
    return render_template("view_product_data.html", all_data=filtered_data)

@app.route("/delete_all_product_data", methods=["POST"])
def delete_all_product_data():
    # Delete all entries in the URLData table
    try:
        URLData.query.delete()  # Delete all records
        db.session.commit()  # Commit the changes to the database
        print("All data deleted.")
    except Exception as e:
        db.session.rollback()  # In case of ERROR, rollback any changes
        print(f"ERROR deleting data: {str(e)}")
    
    return redirect("/view_product_data")  # Redirect back to the /view_product_data page after deletion

@app.route("/delete_page_data/<int:id>", methods=["POST"])
def delete_page_data(id):
    try:
        data_to_delete = ADSData.query.get(id)  # Find the record by its ID
        if data_to_delete:
            db.session.delete(data_to_delete)  # Delete the record
            db.session.commit()  # Commit the changes to the database
            print(f"Data with ID {id} deleted.")
        else:
            print(f"Data with ID {id} not found.")
    except Exception as e:
        db.session.rollback()  # Rollback in case of ERROR
        print(f"ERROR deleting data with ID {id}: {str(e)}")
    
    return redirect(request.referrer or "/view_page_data")  # Redirect back dynamically

@app.route("/delete_product_data/<int:id>", methods=["POST"])
def delete_product_data(id):
    try:
        data_to_delete = URLData.query.get(id)  # Find the record by its ID
        if data_to_delete:
            db.session.delete(data_to_delete)  # Delete the record
            db.session.commit()  # Commit the changes to the database
            print(f"Data with ID {id} deleted.")
        else:
            print(f"Data with ID {id} not found.")
    except Exception as e:
        db.session.rollback()  # Rollback in case of ERROR
        print(f"ERROR deleting data with ID {id}: {str(e)}")
    
    return redirect("/view_product_data")  # Redirect back to the view data page

def get_product_data_by_id(data_id):
    try:
        # Query the database to get the URLData by its ID
        data = URLData.query.get(data_id)
        return data
    except Exception as e:
        print(f"ERROR fetching data with ID {data_id}: {str(e)}")
        return None
    
def get_page_data_by_id(data_id):
    try:
        # Query the database to get the URLData by its ID
        data = ADSData.query.get(data_id)
        return data
    except Exception as e:
        print(f"ERROR fetching data with ID {data_id}: {str(e)}")
        return None

def result_counter(driver, adlibrary_url):
    driver.get(adlibrary_url)
    
    result_count = None  # Default to None if an ERROR occurs
    
    try:
        # Wait for the element that contains the result count
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@aria-level, '3') and contains(text(), 'result')]"))
        )
        
        # Extract result count from the page
        result_text = driver.find_element(By.XPATH, "//div[@aria-level='3' and contains(text(), 'result')]").text
        matches = re.search(r'(\d{1,3}(?:,\d{3})*)', result_text)  # Updated regex to handle commas
        if matches:
            result_count = int(matches.group(1).replace(',', ''))  # Remove commas before converting to int
    
    except Exception as e:
        # Log the ERROR for debugging purposes (optional)
        print(f"ERROR extracting result count: {e}")
    
    return result_count

def test_system_ready(driver):
    print("Checking system readiness...")

    try:
        adliburl_test = "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&content_languages[0]=en&country=US&media_type=all&q=Clinically%20Tested%20%7C%20Risk-free&search_type=keyword_unordered"
        
        result_count = result_counter(driver, adliburl_test)

        # print("Result count : ", result_count)

        # If result count is zero, the system may not be ready
        if result_count == 0:
            print("System Status: NOT READY!!!")
            return False  # Return False if the system is not ready
    except Exception as e:
        print(f"ERROR fetching result count for TEST: {e}")
        return False  # Return False if an ERROR occurs during the check

    print("System Status: READY!")
    return True  # Return True if the system is ready

def get_count_difference(count_history, result_count):
    return result_count - int(count_history.split('>')[0].strip())

@app.route('/update_page_count/<int:data_id>', methods=['POST'])
def update_page_count(data_id):
    # Fetch the data from the database by id
    data = get_page_data_by_id(data_id)  # Replace with the actual method to fetch data
    if data:
        driver = initialize_driver()

        # Check system readiness
        if not test_system_ready(driver):
            driver.quit()
            return redirect(request.referrer or "/view_page_data")  # Redirect back dynamically

        result_count = result_counter(driver, data.page_ads_link)

        driver.quit()

        print("Old Total AAs", data.result_count)
        print("New Total AAs", int(result_count))

        if data.result_count != int(result_count): 
            data.result_count_history += f" > {result_count}"
            print("New Total AAs History", data.result_count_history)

        # Update the result count in the database for this entry
        data.result_count = result_count

        # Update count difference for this entry
        data.count_difference = get_count_difference(data.result_count_history, data.result_count)
        print("Count Difference", data.count_difference)

        data.last_update = datetime.now().replace(microsecond=0)
        print(f"Last Update : {data.last_update}")
        
        # Save the changes to the database
        db.session.commit()

    # Redirect back to the referring URL or fallback to "/view_page_data"
    return redirect(request.referrer or "/view_page_data")


@app.route('/update_product_count/<int:data_id>', methods=['POST'])
def update_product_count(data_id):
    # Fetch the data from the database by id
    data = get_product_data_by_id(data_id)  # Replace with the actual method to fetch data
    if data:
        driver = initialize_driver()

        # Check system readiness
        if not test_system_ready(driver):
            driver.quit()
            return redirect("/view_product_data")  # Redirect if the system is not ready

        result_count = result_counter(driver, data.ads_library_url)

        driver.quit()

        print("Old Result Count",data.result_count)
        print("New Result Count",int(result_count))

        if data.result_count != int(result_count): 
            data.result_count_history += f" > {result_count}"
            print("New Count History",data.result_count_history)

        # Update the result count in the database for this entry
        data.result_count = result_count

        # Update count difference for this entry
        data.count_difference = get_count_difference(data.result_count_history, data.result_count)
        print("Count Difference", data.count_difference)
        
        # Save the changes to the database
        db.session.commit()

    return redirect("/view_product_data")  # Redirect back to the view data page

def update_all_page_count_loop():
    with app.app_context():
        log_data = LogData(
            action = "PAGE COUNT UPDATE (ALL)",
            info = "-",
            status="PROCESSING",  # Status while processing
            start_time=datetime.now().replace(microsecond=0),
            end_time=datetime.now().replace(microsecond=0),
            execution_time=str(datetime.now().replace(microsecond=0) - datetime.now().replace(microsecond=0))
        )
        db.session.add(log_data)
        db.session.commit() 

        print("Updating page count ...")

        # Get all data based on the query filters
        all_data = ADSData.query.all()

        data_count = len(all_data)
        # print("Total Pages' Data to be updated : ",data_count )

        driver = initialize_driver()
        
        # Check system readiness
        if not test_system_ready(driver):
            driver.quit()
            return redirect("/view_page_data")  # Redirect if the system is not ready

        # Loop through all the records
        count = 1
        for data in all_data:
            try:

                result_count = result_counter(driver, data.page_ads_link)

                # print("Old Total AAs", data.result_count)
                # print("New Total AAs", int(result_count))

                if data.result_count != int(result_count): 
                    data.result_count_history += f" > {result_count}"
                    # print("New Total AAs History", data.result_count_history)

                # Update the result count in the database for this entry
                data.result_count = result_count

                # Update count difference for this entry
                data.count_difference = get_count_difference(data.result_count_history, data.result_count)
                # print("Count Difference", data.count_difference)
                
                # Save the changes to the database
                # print(f"Update Data : {count}/{data_count}")
                log_data.info = f"Update Data : {count}/{data_count}"
                log_data.end_time = datetime.now().replace(microsecond=0)
                log_data.execution_time = str(datetime.now().replace(microsecond=0) - log_data.start_time)
                
                db.session.commit()

                count += 1

            except Exception as e:
                status = "ERROR - Exception"
                log_data.status = status
                log_data.end_time = datetime.now().replace(microsecond=0)
                log_data.execution_time = str(datetime.now().replace(microsecond=0) - log_data.start_time)
                db.session.commit()

                print(f"ERROR fetching result count for {data.page_name}: {e}")
        
        driver.quit()

        status = "SUCCESS - Completed"
        log_data.status = status
        log_data.end_time = datetime.now().replace(microsecond=0)
        log_data.execution_time = str(datetime.now().replace(microsecond=0) - log_data.start_time)
        db.session.commit()

    # Redirect to the view_product_data page or render a success message
    return redirect("/view_page_data")


@app.route('/update_all_page_count/<tracked>', methods=['POST'])
def update_all_page_count(tracked):
    with app.app_context():

        action_text = (
            "PAGE COUNT UPDATE (TRACKED)" if tracked is True else
            "PAGE COUNT UPDATE (UNTRACKED)" if tracked is False else
            "PAGE COUNT UPDATE (ALL)"
        )

        log_data = LogData(
            action = action_text,
            info = "-",
            status="PROCESSING",  # Status while processing
            start_time=datetime.now().replace(microsecond=0),
            end_time=datetime.now().replace(microsecond=0),
            execution_time=str(datetime.now().replace(microsecond=0) - datetime.now().replace(microsecond=0))
        )
        db.session.add(log_data)
        db.session.commit() 

        print("Updating page count ...")

        # Start with the base query
        query = ADSData.query

        # Apply tracked filter based on value
        if tracked == True:  # If 'tracked' is 'true', filter by track=True
            query = query.filter_by(track=True)
        elif tracked == False:  # If 'tracked' is 'false', filter by track=False
            query = query.filter_by(track=False)
        # If tracked is 'all', no filter is applied (both tracked and untracked will be included)
        elif tracked == 'all':  # If tracked is 'all', don't apply any filter for 'track'
            pass  # No filter needed, include both

        # Get all data based on the query filters
        all_data = query.all()

        data_count = len(all_data)
        print("Total Pages' Data to be updated : ",data_count )

        driver = initialize_driver()
        
        # Check system readiness
        if not test_system_ready(driver):
            driver.quit()
            return redirect("/view_page_data")  # Redirect if the system is not ready

        # Loop through all the records
        count = 1
        total_count = len(all_data)
        for data in all_data:
            try:
                print(f"[Updating Count {count}/{total_count}]")
                result_count = result_counter(driver, data.page_ads_link)

                # print("Old Total AAs", data.result_count)
                # print("New Total AAs", int(result_count))

                if data.result_count != int(result_count): 
                    data.result_count_history += f" > {result_count}"
                    # print("New Total AAs History", data.result_count_history)

                    # Update the result count in the database for this entry
                    data.result_count = result_count

                    # Update count difference for this entry
                    data.count_difference = get_count_difference(data.result_count_history, data.result_count)
                    # print("Count Difference", data.count_difference)

                data.last_update = datetime.now().replace(microsecond=0)
                # print(f"Last Update : {data.last_update}")
                
                # Save the changes to the database
                # print(f"Update Data : {count}/{data_count}")
                log_data.info = f"Update Data : {count}/{data_count}"
                log_data.end_time = datetime.now().replace(microsecond=0)
                log_data.execution_time = str(datetime.now().replace(microsecond=0) - log_data.start_time)
                log_data.status = "PROCESSING"

                db.session.commit()

                count += 1

            except Exception as e:
                status = "ERROR - Exception"
                log_data.status = status
                log_data.end_time = datetime.now().replace(microsecond=0)
                log_data.execution_time = str(datetime.now().replace(microsecond=0) - log_data.start_time)
                db.session.commit()

                print(f"ERROR fetching result count for {data.page_name}: {e}")
        
        driver.quit()

        status = "SUCCESS - Completed"
        log_data.status = status
        log_data.end_time = datetime.now().replace(microsecond=0)
        log_data.execution_time = str(datetime.now().replace(microsecond=0) - log_data.start_time)
        db.session.commit()

    # Redirect to the view_product_data page or render a success message
    return redirect("/view_page_data")


@app.route('/update_all_product_count/<int:created_days_ago>', methods=['POST'])
def update_all_product_count(created_days_ago):
    # Query all records from the URLData table
    #all_data = URLData.query.all()

    # filter only those created_days_ago < 20
    all_data = URLData.query.filter(URLData.created_days_ago <= created_days_ago).all()

    data_count = len(all_data)
    print("Total Data to be updated : ",data_count )

    driver = initialize_driver()
    
    # Check system readiness
    if not test_system_ready(driver):
        driver.quit()
        return redirect("/view_product_data")  # Redirect if the system is not ready

    # Loop through all the records
    count=1
    for data in all_data:
        
        print(f"Updating Data : {count}/{data_count}")
        count += 1
        url = data.url
        if url:
            # Fetch the updated result count
            try:
                result_count = result_counter(driver, data.ads_library_url)

                print(f"Result Count for: {data.product_name} ({data.created_days_ago} days ago)")
                print("Old Result Count",data.result_count)
                print("New Result Count",int(result_count))

                if data.result_count != int(result_count): 
                    data.result_count_history += f" > {result_count}"
                    print("New Count History",data.result_count_history)
                    
                # Update the result count in the database for this entry
                data.result_count = result_count

                # Update count difference for this entry
                data.count_difference = get_count_difference(data.result_count_history, data.result_count)
                print("Count Difference", data.count_difference)

                # Save the changes to the database
                db.session.commit()
                
            except Exception as e:
                print(f"ERROR fetching result count for {url}: {e}")
    
    driver.quit()

    # Redirect to the view_product_data page or render a success message
    return redirect("/view_product_data")

# Helper function to calculate days ago
def days_ago(date_string):
    # Get the current date
    today = date.today()
    
    if date_string:
        try:
            # Try to parse the date in "DD-MMM-YYYY" format
            parsed_date = datetime.strptime(date_string, "%d-%b-%Y").date()
            return (today - parsed_date).days
        except ValueError:
            print(f"Invalid date format: {date_string}")
            return None
    return None


@app.route('/update_product_days_ago', methods=['POST'])
def update_product_days_ago():
    # Query all records in the URLData table
    records = URLData.query.all()

    # Iterate over each record and update created_days_ago, registration_days_ago, and added_days_ago
    for record in records:
        # Update created_days_ago using the days_ago function
        record.created_days_ago = days_ago(record.created_at_date)
        if record.created_days_ago is not None:
            print(f"Updated created_at_date for {record.product_name}")
        
        # Update registration_days_ago using the days_ago function
        record.registration_days_ago = days_ago(record.registration_date)
        if record.registration_days_ago is not None:
            print(f"Updated registration_date for {record.product_name}")
        
        # Update added_days_ago using the days_ago function
        record.added_days_ago = days_ago(record.added_date)
        if record.added_days_ago is not None:
            print(f"Updated added_date for {record.product_name}")
    
    # Commit the changes to the database
    db.session.commit()

    # Redirect to the view_product_data page or render a success message
    return redirect("/view_product_data")



def validate_and_format_date(date_string):
    try:
        today = datetime.today()
        
        # Handle relative date strings explicitly
        if date_string.lower() == "today":
            parsed_date = today
        elif date_string.lower() == "yesterday":
            parsed_date = today - timedelta(days=1)
        else:
            # Handle ISO 8601 format explicitly
            if "T" in date_string and "Z" in date_string:
                parsed_date = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ')
            else:
                # If no year is provided, append the current year
                if len(date_string.split()) == 2:  # If only day and month are provided
                    date_string = f"{date_string} {today.year}"
                parsed_date = parser.parse(date_string)
        
        # Return the date in the format DD-Mon-YYYY
        return parsed_date.strftime('%d-%b-%Y')
    
    except (ValueError, OverflowError) as e:
        print(f"ERROR parsing date: {e}")
        return None

    
@app.route("/edit_page_data", methods=["POST"])
def edit_page_data():
    print("CALLLED UPDATE DATA!!")
    try:
        # Retrieve data from the form
        id = request.form['id']
        page_name = request.form['page_name']
        div_href = request.form['div_href']
        facebook_about_page = request.form['facebook_about_page']
        page_id = request.form['page_id']
        page_ads_link = request.form['page_ads_link']
        result_count = request.form['result_count']
        result_count_history = request.form['result_count_history']
        count_difference = request.form['count_difference']
        div_library_id = request.form['div_library_id']
        div_ads_count = request.form['div_ads_count']
        keyword = request.form['keyword']
        ads_library_url = request.form['ads_library_url']
        
        # Find the record by its ID
        data_to_update = ADSData.query.get(id)
        
        if data_to_update:
            # Update the record with new values
            data_to_update.page_name = page_name
            data_to_update.div_href = div_href
            data_to_update.facebook_about_page = facebook_about_page
            data_to_update.page_id = page_id
            data_to_update.page_ads_link = page_ads_link
            data_to_update.result_count = result_count
            data_to_update.result_count_history = result_count_history
            data_to_update.count_difference = count_difference
            data_to_update.div_library_id = div_library_id
            data_to_update.div_ads_count = div_ads_count
            data_to_update.keyword = keyword
            data_to_update.ads_library_url = ads_library_url

            # Commit the changes to the database
            db.session.commit()
            
            print(f"Data with ID {id} updated.")
        else:
            print(f"Data with ID {id} not found.")
    
    except Exception as e:
        db.session.rollback()  # Rollback in case of ERROR
        print(f"ERROR updating data with ID {id}: {str(e)}")
    
    return redirect("/view_page_data")  # Redirect back to the view data page

@app.route("/edit_product_data", methods=["POST"])
def edit_product_data():
    print("CALLLED UPDATE DATA!!")
    try:
        # Retrieve data from the form
        id = request.form['id']
        product_name = request.form['product_name']
        url = request.form['url']
        created_at_date = request.form['created_at_date']
        whois_url = request.form['whois_url']
        registration_date = request.form['registration_date']
        ads_library_url = request.form['ads_library_url']
        result_count = request.form['result_count']
        result_count_history = request.form['result_count_history']
        added_date = request.form['added_date']
        count_difference = request.form['count_difference']
        
        # Find the record by its ID
        data_to_update = URLData.query.get(id)
        
        if data_to_update:
            # Update the record with new values
            data_to_update.product_name = product_name
            data_to_update.url = url
            data_to_update.created_at_date = validate_and_format_date(created_at_date)
            data_to_update.created_days_ago = days_ago(data_to_update.created_at_date)
            data_to_update.whois_url = whois_url
            data_to_update.registration_date = validate_and_format_date(registration_date)
            data_to_update.registration_days_ago = days_ago(data_to_update.registration_date)
            data_to_update.ads_library_url = ads_library_url
            data_to_update.result_count = result_count
            data_to_update.result_count_history = result_count_history
            data_to_update.count_difference = count_difference
            data_to_update.added_date = validate_and_format_date(added_date)
            data_to_update.added_days_ago =  days_ago(data_to_update.added_date)
            
            # Commit the changes to the database
            db.session.commit()
            
            print(f"Data with ID {id} updated.")
        else:
            print(f"Data with ID {id} not found.")
    
    except Exception as e:
        db.session.rollback()  # Rollback in case of ERROR
        print(f"ERROR updating data with ID {id}: {str(e)}")
    
    return redirect("/view_product_data")  # Redirect back to the view data page

# Process dates for formatting
def format_datetime(date_time):
    if date_time is None:
        return None, None  # Return None for both formatted date and time ago

    now = datetime.now()
    time_diff = now - date_time
    days_ago = time_diff.days
    seconds_ago = time_diff.total_seconds()
    formatted_date = date_time.strftime("%d-%b-%Y %I:%M%p")

    # Determine "X Time Ago"
    if seconds_ago < 60:
        time_ago = f"{int(seconds_ago)} seconds ago"
    elif seconds_ago < 3600:
        time_ago = f"{int(seconds_ago // 60)} minutes ago"
    elif seconds_ago < 86400:
        time_ago = f"{int(seconds_ago // 3600)} hours ago"
    else:
        time_ago = f"{days_ago} days ago"

    return formatted_date, time_ago

# Future use 
def format_date(date):
    try:
        today = datetime.now().date()
        days_ago = (today - date).days
        formatted_date = date.strftime("%d-%b-%Y")

        if days_ago == 0:
            return formatted_date, "Today"
        elif days_ago == 1:
            return formatted_date, "Yesterday"
        else:
            return formatted_date, f"{days_ago} days ago"
    
    except Exception as e:
        return None, None

@app.route("/view_page_data")
def view_page_data():
    try:
        # Get the current page number and search term from query parameters
        page = int(request.args.get("page", 1))
        per_page = 5  # Number of rows per page
        search_query = request.args.get("search", "").strip()  # Get search term

        # Check if the 'tracked' parameter exists in the URL (via request.args)
        track_filter = request.args.get('track_filter', 'all')

        sort_by = request.args.get("sortBy", "id")  # Default to 'id'
        sort_order = request.args.get("sortOrder", "desc")  # Default to 'desc'

        query = ADSData.query

        # page_created_days_threshold = request.args.get('pageCreatedDateThreshold', type=int)
        page_changed_days_threshold = request.args.get('pageChangedDateThreshold', type=int)
        result_count_threshold = request.args.get('resultCountThreshold', type=int)
        product_created_days_threshold = request.args.get('productCreatedDateThreshold', type=int)
        product_domain_days_threshold = request.args.get('productDomainDateThreshold', type=int)
        productsCount = request.args.get('productsCount', type=int)
        added_days = request.args.get('addedDays', type=int)

        # Now, the filter will only apply if the values are provided
        # if page_created_days_threshold is not None:
        #     query = query.filter(ADSData.faceboook_created_date >= datetime.today().date() - timedelta(days=page_created_days_threshold))
        if page_changed_days_threshold is not None:
            query = query.filter(ADSData.facebook_changed_date >= datetime.today().date() - timedelta(days=page_changed_days_threshold))
        if result_count_threshold is not None:
            query = query.filter(ADSData.result_count >= result_count_threshold)
        if product_created_days_threshold is not None:
            query = query.filter(ADSData.prod_created_date >= datetime.today().date() - timedelta(days=product_created_days_threshold))
        if product_domain_days_threshold is not None:
            query = query.filter(ADSData.domain_reg_date >= datetime.today().date() - timedelta(days=product_domain_days_threshold))
        if productsCount is not None:
            query = query.filter(ADSData.products_count <= productsCount)
        if added_days is not None:
            query = query.filter(ADSData.added_date >= datetime.today().date() - timedelta(days=added_days))

        # Apply track filter if it's set
        if track_filter == 'true':
            query = query.filter_by(track=True)
            track_filter = 'true'
        elif track_filter == 'false':
            query = query.filter_by(track=False)
            track_filter = 'false'
        else:
            track_filter = 'all'
        
        if search_query:
            # Split the search query into individual terms
            search_terms = [term.strip() for term in search_query.split("|")]

            # Dynamically build search filters for all string columns
            search_filters = []
            for term in search_terms:
                term_filters = db.or_(
                    ADSData.id.ilike(f"%{term}%"),
                    ADSData.keyword.ilike(f"%{term}%"),
                    ADSData.page_name.ilike(f"%{term}%"),
                    ADSData.ads_library_url.ilike(f"%{term}%"),
                    ADSData.div_href.ilike(f"%{term}%"),
                    ADSData.div_library_id.ilike(f"%{term}%"),
                    ADSData.facebook_about_page.ilike(f"%{term}%"),
                    ADSData.page_id.ilike(f"%{term}%"),
                    ADSData.page_ads_link.ilike(f"%{term}%"),
                    ADSData.product_name.ilike(f"%{term}%"),
                    ADSData.product_link.ilike(f"%{term}%"),
                    ADSData.domain.ilike(f"%{term}%")
                )
                search_filters.append(term_filters)

            # Combine all term filters with AND logic
            query = query.filter(db.and_(*search_filters))

        total_count = query.count()

        # Dynamically determine the sorting column
        sort_column = getattr(ADSData, sort_by, ADSData.id)  # Fallback to ADSData.id if invalid

        # Apply sorting
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Paginate the results
        paginated_data = query.paginate(page=page, per_page=per_page, error_out=False)

        # Extract the paginated items for the current page
        all_data = paginated_data.items
        total_pages = paginated_data.pages
        current_page = paginated_data.page

        # Add formatted dates to the data
        for data in all_data:
            data.formatted_last_update, data.time_ago_last_update = format_datetime(data.last_update)
            data.formatted_added_date, data.time_ago_added_date  = format_datetime(data.added_date)
            data.formatted_creative_start_date, data.days_ago_creative_start_date = format_date(data.creative_start_date)
            # data.formatted_faceboook_created_date, data.days_ago_faceboook_created_date = format_date(data.faceboook_created_date)
            data.formatted_facebook_changed_date, data.days_ago_facebook_changed_date = format_date(data.facebook_changed_date)
            data.formatted_prod_created_date, data.days_ago_prod_created_date = format_date(data.prod_created_date)
            data.formatted_domain_reg_date, data.days_ago_domain_reg_date = format_date(data.domain_reg_date)

        # Return filtered data to the template for rendering
        return render_template("view_page_data.html", 
                                    all_data=all_data, 
                                    page=current_page,
                                    total_pages=total_pages,
                                    search_query=search_query,  # Pass search query to the template
                                    total_count=total_count,
                                    track_filter = track_filter,
                                    # page_created_days_threshold = page_created_days_threshold,
                                    page_changed_days_threshold = page_changed_days_threshold,
                                    productsCount = productsCount,
                                    result_count_threshold = result_count_threshold,
                                    product_created_days_threshold = product_created_days_threshold,
                                    product_domain_days_threshold = product_domain_days_threshold,
                                    sortBy=sort_by,
                                    sortOrder=sort_order,
                                    addedDays = added_days
                                )

    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"ERROR": "Failed to filter data"}), 400


@app.route('/toggle_track/<int:id>', methods=['POST'])
def toggle_track(id):
    try:
        # Find the ADSData item with the given id
        data_item = ADSData.query.get(id)
        
        if data_item:
            # Toggle the track status
            data_item.track = not data_item.track
            db.session.commit()  # Save the change to the database
            
            # Return the updated track status
            return jsonify({"track": data_item.track}), 200
        else:
            return jsonify({"ERROR": "Data not found"}), 404
    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"ERROR": "Failed to update track state"}), 400

# Run on a separate thread for 'all'
def update_all_page_count_scheduler():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.submit(update_all_page_count, 'all')

# Run on a separate thread for 'tracked'
def update_all_page_count_scheduler_tracked():
    print("run update_all_page_count_scheduler_tracked()")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.submit(update_all_page_count, True)

def update_error():
    
    with app.app_context():

        print("updating error...")

        # Log data
        # log_data = LogData(
        #     action = "UPDATE LOG ERRORS",
        #     info = "-",
        #     status="PROCESSING",  # Status while processing
        #     start_time=datetime.now().replace(microsecond=0),
        #     end_time=datetime.now().replace(microsecond=0),
        #     execution_time=str(datetime.now().replace(microsecond=0) - datetime.now().replace(microsecond=0))
        # )
        # db.session.add(log_data)
        # db.session.commit() 

        # Get all log entries with status "PROCESSING"
        processing_logs = LogData.query.filter_by(status="PROCESSING").all()
        processing_count = 0
        
        # Current time
        now = datetime.now()
        for log in processing_logs:
            # Check if end_time is more than 1 minute old
            if log.end_time and (now - log.end_time > timedelta(minutes=1)):
                log.status = "ERROR - Incomplete"
                processing_count += 1

        # status= "SUCCESS - Completed"
        # log_data.status = status
        # log_data.info = f'Total Updates: {processing_count}'
        # log_data.end_time = datetime.now().replace(microsecond=0)
        # log_data.execution_time = str(datetime.now().replace(microsecond=0) - log_data.start_time)
        
        # Commit the changes to the database
        db.session.commit()

def update_all_facebook_changed_dates():
    with app.app_context():

        # # Query records where the 'facebook_changed_date' field is None
        # records_to_update = ADSData.query.filter(
        #     ADSData.facebook_changed_date.is_(None)
        # ).all()

        # # Query all records
        # records_to_update = ADSData.query.all()

        # # Query records where the 'update_changed_date' field is False
        records_to_update = ADSData.query.filter(
            or_(
                ADSData.update_changed_date.is_(None),
                ADSData.facebook_changed_date.is_(None)
            )
        ).all()

    
        total_count = len(records_to_update)
        print(f"Total records to update: {total_count}")


        # Initialize the driver
        driver = initialize_driver()

        for count, record in enumerate(records_to_update, start=1):
            try:
                print(f"[{count}/{total_count}] Updating record for ID: {record.id}")
                facebook_about_page = record.div_href + "about_profile_transparency"
                print(f"Facebook About Page Link: {facebook_about_page}")

                driver.get(facebook_about_page)

                print(f"Facebook Created Date: {record.faceboook_created_date}")
                
                # Call function to get the latest changed date
                facebook_changed_date = get_facebook_changed_date(driver)
                print(f"Facebook Latest Changed Date: {facebook_changed_date}")

                # Skip if None
                if facebook_changed_date is None:
                    db.session.delete(record)
                    db.session.commit()
                    print(f"Page Changed Date is None. Deleting record/")
                    continue
                else:
                    record.update_changed_date = True


                # Update the record with the new date
                record.facebook_changed_date = facebook_changed_date
                
                # Commit after every record if needed (optional based on batch commit preference)
                db.session.commit()

            except Exception as e:
                print(f"Error while processing record ID {record.id}: {e}")

        # Commit all the updates at once
        # db.session.commit()

        # Close the driver after all records are updated
        driver.quit()

        print("All records updated successfully!")


def delete_records_with_none_dates():
    with app.app_context():
        # Query records where the field is None
        records_to_delete = ADSData.query.filter(
            ADSData.domain_reg_date.is_(None)
        ).all()

        total_count = len(records_to_delete)
        print(f"Total records to delete: {total_count}")

        for count, record in enumerate(records_to_delete, start=1):
            print(f"[{count}/{total_count}] Deleting record with ID: {record.id}")
            # db.session.delete(record)

        # db.session.commit()
        print("All records deleted successfully!")

def update_all_dates():
    with app.app_context():
        # Query records where either field is None
        records_to_update = ADSData.query.filter(
                ADSData.prod_created_date.is_(None)
            ).all()

        total_count = len(records_to_update)
        print(f"Total records to update: {total_count}")

        for count, record in enumerate(records_to_update, start=1):

            print(f"[{count}/{total_count}] Updating record for ID: {record.id}")

        # db.session.commit()
        print("All records updated successfully!")

# Set up the scheduler and jobs
def start_scheduler():
    
    scheduler = BackgroundScheduler()

    # Run the function every 2 hours ( seconds=30 , minutes = 1 , hours=1)
    # scheduler.add_job(update_all_page_count_scheduler, 'interval', hours=5)

    scheduler.add_job(update_error, 'interval', minutes=1)

    # Stagger the second job by adding a 1-minute offset
    scheduler.add_job(update_all_page_count_scheduler_tracked, 'interval', hours=1, minutes=30)

    scheduler.start()
    
    # Shut down the scheduler gracefully when the app exits
    atexit.register(lambda: scheduler.shutdown())

def ads_info(adlib_url):
    print("Extracting Ads results")
    print("Ad Library Link:", adlib_url)

    driver = initialize_driver()
    total_result_count = result_counter(driver, adlib_url)
    print("Total Results Available:", total_result_count)

    processed_divs = set()  # Track processed divs
    product_ads_count = {}  # Dictionary to store sum of ads for each product link
    scroll_pause_time = 0.5  # Pause time between scrolls
    max_scroll_attempts = 10  # Max attempts to scroll without new data
    scroll_attempts = 0

    last_height = driver.execute_script("return document.body.scrollHeight")  # Get initial scroll height

    extraction_count = 0
    overallAAs = 0

    while scroll_attempts < max_scroll_attempts:
        try:
            # Wait and find all relevant divs
            WebDriverWait(driver, 30).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, '_7jvw x2izyaf x1hq5gj4 x1d52u69')]"))
            )
            divs = driver.find_elements(By.XPATH, "//div[contains(@class, '_7jvw x2izyaf x1hq5gj4 x1d52u69')]")
            new_data_found = False

            for div in divs:
                try:
                    div_id = div.get_attribute('outerHTML')  # Use unique identifier for div
                    if div_id in processed_divs:
                        continue  # Skip already processed divs
                    processed_divs.add(div_id)

                    extraction_count += 1
                    print(f"[Extraction No. : {extraction_count}]")

                    # Extract spans and product link
                    spans = div.find_elements(By.TAG_NAME, 'span')
                    div_ads_count = 1  # Default count is 1 if no specific count found
                    product_href = None

                    # Extract product link from the second anchor tag
                    a_tags = div.find_elements(By.XPATH, ".//a[@href]")
                    if len(a_tags) > 1:
                        product_href = clean_fb_href_link(a_tags[1].get_attribute('href'))
                    else:
                        continue

                    # Extract the number of ads using regex
                    for span in spans:
                        text = span.text.strip()
                        # print(f"text : {text}")
                        match_ads_count = re.search(r'(\d+)\s+ads use this creative and text', text)
                        if match_ads_count:
                            div_ads_count = int(match_ads_count.group(1))

                    # Update the total ads count for this product link
                    if product_href:
                        if product_href not in product_ads_count:
                            product_ads_count[product_href] = 0
                        product_ads_count[product_href] += div_ads_count

                    overallAAs += div_ads_count

                    print(f"Product Link: {product_href}")
                    print(f"Creative AAs: {div_ads_count}")
                    print(f"Product AAs: {product_ads_count[product_href]}")
                    print(f"Overall AAs: {overallAAs} / {total_result_count}")
                    print(f"-----------------------------------")

                    new_data_found = True  # Mark new data found in this iteration

                except Exception as e:
                    print("Error processing div:", e)
                    continue

            # Scroll to load more content
            if new_data_found:
                scroll_attempts = 0  # Reset attempts since new data was found
            else:
                scroll_attempts += 1

            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(scroll_pause_time)

            # Check if scrolling has reached the bottom
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                scroll_attempts += 1
            else:
                last_height = new_height

        except Exception as e:
            print("Error during scrolling or element extraction:", e)
            continue

    # Close driver and return result
    driver.quit()
    print("Extraction Complete")
    # print(f"product_ads_count : {product_ads_count}")

    for key, value in product_ads_count.items():
        print(f"AAs: {value} ({key})")

    return product_ads_count

# def restart_in_new_terminal():
#     """
#     Restart the Flask app in a new terminal window on the detected OS.
#     """
#     python = sys.executable  # Path to the Python interpreter
#     script = sys.argv[0]  # Path to the current script

#     if platform.system() == "Windows":
#         # For Windows, directly open cmd.exe and run the command
#         command = f'python {script}'  # Format the command to include the full path to the script
#         subprocess.Popen(['cmd', '/c', f'start cmd /k {command}'], shell=True)
#     elif platform.system() == "Darwin":
#         # For macOS
#         applescript = f"""
#         tell application "Terminal"
#             do script "{python} {script}"
#         end tell
#         """
#         subprocess.Popen(['osascript', '-e', applescript])
#     elif platform.system() == "Linux":
#         # For Linux
#         subprocess.Popen(['x-terminal-emulator', '-e', f"{python} {script}"])
#     else:
#         raise OSError("Unsupported operating system for restarting the app.")

#     sys.exit()  # Exit the current process

# @app.route('/restart', methods=['POST'])
# def restart_app():
#     """
#     Endpoint to trigger a restart of the Flask application.
#     """
#     restart_in_new_terminal()
#     return jsonify({"message": "App is restarting in a new terminal window."})

if __name__ == "__main__":
    # Start the scheduler only if running locally
    if os.getenv('RENDER') != 'true':
        host = "0.0.0.0"
        port = int(os.getenv('PORT', 5000))

        # Ensure scheduler starts only once in debug mode (else it runs 2 times...)
        if os.getenv('WERKZEUG_RUN_MAIN') != 'true':
            start_scheduler()  # Start the scheduler
            
            # Run keyword loop search - have to run in a seperate thread to not block main app
            thread = threading.Thread(target=keyword_loop_search)
            thread.daemon = True  # Make the thread a daemon so it exits when the main program exits
            thread.start()

            thread = threading.Thread(target=update_all_facebook_changed_dates)
            thread.daemon = True
            thread.start()

        app.run(debug=True, threaded=True, host=host, port=port, use_reloader=False)