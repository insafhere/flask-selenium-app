import os
import requests
import re
from flask import Flask, render_template, request
import time
from urllib.parse import urlparse, urlunparse
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from xml.etree import ElementTree
import concurrent.futures

app = Flask(__name__)

def extract_domain(url):
    print("Extract domain from the URL.")
    match = re.search(r'://([^/]+)', url)
    if match:
        return match.group(1)
    return None

def cleanup_url(url):
    print("Clean URL query parameters.")
    parsed_url = urlparse(url)
    cleaned_url = urlunparse(parsed_url._replace(query=""))
    return cleaned_url

def extract_date_from_xml(xml_content):
    print("Extracting creation date from XML.")
    try:
        root = ElementTree.fromstring(xml_content)
        created_at = root.find(".//created-at")
        product_name = root.find(".//title")

        if created_at is not None:
            date_str = created_at.text.split('T')[0]
            created_at_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            today = datetime.today().date()
            delta = today - created_at_date
            formatted_date = created_at_date.strftime('%d-%b-%Y')
            days_ago = f"({delta.days} days ago)"
            product_name_text = product_name.text if product_name is not None else None
            print("Product Name:", product_name_text)
            return formatted_date, days_ago, product_name_text
        
        return None, None, None

    except Exception as e:
        return f"Error extracting date: {str(e)}", None, None

def get_domain_registration_date(driver, domain):
    print("Get domain registration date using WHOIS.")
    whois_url = f"https://www.whois.com/whois/{domain}"
    registration_date = None
    days_ago = None

    try:
        driver.get(whois_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@class='df-row'][./div[@class='df-label'][contains(text(),'Registered On:')]]/div[@class='df-value']")))
        registration_date_element = driver.find_element(By.XPATH, "//div[@class='df-row'][./div[@class='df-label'][contains(text(),'Registered On:')]]/div[@class='df-value']")
        registration_date_text = registration_date_element.text
        registration_date = datetime.strptime(registration_date_text, '%Y-%m-%d').date()
        today = datetime.today().date()
        delta = today - registration_date
        registration_date = registration_date.strftime('%d-%b-%Y')
        days_ago = f"({delta.days} days ago)"
    except Exception as e:
        print(f"Error retrieving registration date: {str(e)}")

    return whois_url, registration_date, days_ago

def fetch_data_concurrently(driver, url, domain, product_xml_url):
    print("Fetch data concurrently for XML and WHOIS")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        xml_future = executor.submit(requests.get, product_xml_url)
        whois_future = executor.submit(get_domain_registration_date, driver, domain)

        xml_response = xml_future.result()
        whois_data = whois_future.result()

        created_at_date, created_days_ago, product_name_text = None, None, None
        if xml_response.status_code == 200:
            xml_content = xml_response.text
            created_at_date, created_days_ago, product_name_text = extract_date_from_xml(xml_content)

        return whois_data, created_at_date, created_days_ago, product_name_text

def extract_results(url):
    start_time = time.time()

    # Automatically download and install the correct version of chromedriver
    chromedriver_autoinstaller.install()

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    
    # Use the installed chromedriver without specifying the path manually
    service = Service(chromedriver_autoinstaller.install())
    driver = webdriver.Chrome(service=service, options=options)

    url = cleanup_url(url)
    domain = extract_domain(url)
    if not domain:
        return "Invalid URL", None, None, None, None, None, None, None, None, None, None

    ads_library_url = f"https://www.facebook.com/ads/library/?ad_type=all&search_type=keyword_unordered&media_type=all&active_status=active&country=ALL&q={domain}"
    product_xml_url = f"{url}.xml"

    print("Extracting Ads results")
    try:
        driver.get(ads_library_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[contains(@aria-level, '3') and contains(text(), 'result')]")))

        result_text = driver.find_element(By.XPATH, "//div[@aria-level='3' and contains(text(), 'result')]").text
        matches = re.search(r'(\d+)', result_text)
        result_count = matches.group(1) if matches else "Result not found"

        whois_data, created_at_date, created_days_ago, product_name_text = fetch_data_concurrently(driver, url, domain, product_xml_url)
        whois_url, registration_date, registration_days_ago = whois_data

    except Exception as e:
        result_count = f"Error occurred: {str(e)}"
        created_at_date = created_days_ago = whois_url = registration_date = registration_days_ago = product_name_text = None

    driver.quit()

    end_time = time.time()
    time_taken_seconds = end_time - start_time
    minutes = int(time_taken_seconds // 60)
    seconds = int(time_taken_seconds % 60)
    time_taken = f"{minutes} min {seconds} sec"

    return result_count, ads_library_url, domain, product_xml_url, created_at_date, created_days_ago, whois_url, registration_date, registration_days_ago, time_taken, product_name_text

@app.route("/", methods=["GET", "POST"])
def home():
    result = ads_library_url = domain = product_xml_url = created_at_date = created_days_ago = whois_url = registration_date = registration_days_ago = url = time_taken = product_name_text = None
    if request.method == "POST":
        url = request.form.get("url")
        if url:
            result, ads_library_url, domain, product_xml_url, created_at_date, created_days_ago, whois_url, registration_date, registration_days_ago, time_taken, product_name_text = extract_results(url)
    return render_template("index.html", 
                           result=result, 
                           ads_library_url=ads_library_url, 
                           domain=domain, 
                           url=url, 
                           product_xml_url=product_xml_url, 
                           created_at_date=created_at_date, 
                           created_days_ago=created_days_ago, 
                           whois_url=whois_url, 
                           registration_date=registration_date, 
                           registration_days_ago=registration_days_ago, 
                           time_taken=time_taken,  
                           product_name_text=product_name_text)

if __name__ == "__main__":
    # Determine the host and port
    host = "0.0.0.0"  # Render requires the app to bind to 0.0.0.0
    port = int(os.getenv('PORT', 5000))  # Default to 5000 locally, use Render's PORT env variable

    app.run(debug=True, host=host, port=port)
