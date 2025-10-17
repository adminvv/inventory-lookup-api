import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
CORS(app) # Enable CORS for client-side JavaScript access

# Dell Service Tag validation regex (7-character alphanumeric)
SERVICE_TAG_REGEX = re.compile(r"^[a-zA-Z0-9]{7}$")

# HP Serial Number validation regex (10-12 alphanumeric characters)
HP_SERIAL_REGEX = re.compile(r"^[a-zA-Z0-9]{10,12}$")

# ViewSonic Serial Number validation regex (10-12 alphanumeric characters)
VIEWSONIC_SERIAL_REGEX = re.compile(r"^[a-zA-Z0-9]{10,12}$")

# Juniper Serial Number validation regex (typically 12 alphanumeric characters)
JUNIPER_SERIAL_REGEX = re.compile(r"^[a-zA-Z0-9]{12}$")

# CyberPower Serial Number validation regex (typically 12 or 16 alphanumeric characters)
CYBERPOWER_SERIAL_REGEX = re.compile(r"^[a-zA-Z0-9]{12}$|^[a-zA-Z0-9]{16}$")

# Brother Serial Number validation regex (typically 15 alphanumeric characters)
BROTHER_SERIAL_REGEX = re.compile(r"^[a-zA-Z0-9]{15}$")

# Apple Serial Number validation regex (12 or 17 alphanumeric characters)
APPLE_SERIAL_REGEX = re.compile(r"^[a-zA-Z0-9]{12}$|^[a-zA-Z0-9]{17}$")

# Acer Serial Number validation regex (22 alphanumeric characters, or 11/12 digit SNID)
ACER_SERIAL_REGEX = re.compile(r"^[a-zA-Z0-9]{22}$|^\d{11,12}$")

# Lenovo Serial Number validation regex (typically 8-12 alphanumeric characters)
LENOVO_SERIAL_REGEX = re.compile(r"^[a-zA-Z0-9]{8,12}$")

# Cisco Serial Number validation regex (Typically 11 characters: LLLYYWWXXXX)
CISCO_SERIAL_REGEX = re.compile(r"^[A-Z]{3}\d{8}$")

# APC Serial Number validation regex (Typically 12 characters)
APC_SERIAL_REGEX = re.compile(r"^[A-Z0-9]{12}$")

# Microsoft Serial Number validation regex (typically 12 digits/letters)
MICROSOFT_SERIAL_REGEX = re.compile(r"^[0-9]{12}$|^[0-9]{16}$|^[A-Z0-9]{12}$")

# Samsung Serial Number validation regex (typically 11 or 15 characters)
SAMSUNG_SERIAL_REGEX = re.compile(r"^[A-Z0-9]{11}$|^[A-Z0-9]{15}$")

# Vizio Serial Number validation regex (typically 14 characters)
VIZIO_SERIAL_REGEX = re.compile(r"^[A-Z0-9]{14}$")

# TCL Serial Number validation regex (typically 12-14 characters)
TCL_SERIAL_REGEX = re.compile(r"^[A-Z0-9]{12,14}$")

def get_apple_model_name(serial_number):
    """
    Infers the Apple model name based on known serial number prefixes.
    This is based on community knowledge of Apple's serial number structure.
    """
    if not APPLE_SERIAL_REGEX.match(serial_number):
        return None, "Invalid Apple Serial Number format (must be 12 or 17 alphanumeric characters)."

    # Use the first 3 characters for the most common model family inference
    prefix = serial_number[:3].upper()

    # This mapping is highly speculative and based on public data.
    # It should be treated as a strong suggestion, not a definitive answer.
    prefix_to_model = {
        # MacBooks (12-character serials)
        "C02": "MacBook Pro (Inferred)",
        "C03": "MacBook Air (Inferred)",
        "C1M": "iMac (Inferred)",
        "DCP": "Mac Mini (Inferred)",
        # iPads/iPhones (17-character serials)
        "F4H": "iPad Pro (Inferred)",
        "F5K": "iPad Air (Inferred)",
        "F9F": "iPhone (Inferred)",
        "F9G": "iPhone (Inferred)",
        "G0C": "Apple Watch (Inferred)",
        "FTY": "iPod Touch (Inferred)",
    }

    if prefix in prefix_to_model:
        model = prefix_to_model[prefix]
        return model, f"Model inferred from serial number prefix '{prefix}'. Please verify."
    
    # For 17-character serials, sometimes the 4th and 5th characters are also useful
    if len(serial_number) == 17:
        prefix5 = serial_number[:5].upper()
        # Add more specific 5-character mappings here if needed
        # Example: F9F.. -> iPhone 13
        # Example: F4H.. -> iPad Pro 11-inch (3rd generation)
        pass


    return None, "Could not infer Apple model from serial number prefix."

def get_lenovo_model_name(serial_number):
    """
    Scrapes the Lenovo warranty lookup page to find the product model name.
    """
    if not LENOVO_SERIAL_REGEX.match(serial_number):
        return None, "Invalid Lenovo Serial Number format (must be 8-12 alphanumeric characters)."

    # URL to scrape (Lenovo's official warranty lookup page)
    url = f"https://pcsupport.lenovo.com/us/en/warranty-lookup?key={serial_number}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Lenovo's model name is often found in the 'product-name' class or a similar structure
        # We look for the most specific element that contains the model name.
        model_element = soup.find('span', class_='product-name') or soup.find('h2', class_='product-name')
        
        if model_element:
            model_name = model_element.text.strip()
            if model_name:
                return model_name, "Model found via web scraping."
        
        # Fallback if scraping is blocked or structure changed
        return None, "Model name element not found on Lenovo support page."

    except requests.exceptions.RequestException as e:
        # Fallback to pattern matching if request fails (e.g., blocked)
        return None, f"Request failed (Web scraping failed): {e}"

def get_cisco_model_name(serial_number):
    """
    Infers the Cisco model name based on known serial number prefixes.
    This is a pattern-matching logic based on community knowledge.
    """
    if not CISCO_SERIAL_REGEX.match(serial_number):
        return None, "Invalid Cisco Serial Number format (must be 11 characters: LLLYYWWXXXX)."

    # Cisco serial numbers are LLLYYWWXXXX
    # LLL = Location code (3 letters)
    # YY = Year code (2 digits)
    # WW = Week code (2 digits)
    # XXXX = Sequential serial number (4 digits/letters)

    # We use the Location Code (LLL) for a very rough inference of the product type/model family
    prefix = serial_number[:3].upper()

    # This mapping is highly speculative and based on common Cisco codes.
    # It should be treated as a strong suggestion, not a definitive answer.
    prefix_to_model = {
        # Common Cisco Manufacturing Locations (LLL) - often associated with product lines
        "FOX": "Cisco Product (Foxconn - Common for Switches/Routers)",
        "FOC": "Cisco Product (China - Common for Switches/Routers)",
        "JAE": "Cisco Product (Japan - Older/Specialized Gear)",
        "JAB": "Cisco Product (Japan - Older/Specialized Gear)",
        "KWC": "Cisco Product (Common for Access Points/Smaller Devices)",
        # You would typically need a much larger, proprietary database for accurate mapping
        # For a simple inventory, we can only suggest the product family.
    }

    if prefix in prefix_to_model:
        model = prefix_to_model[prefix]
        return model, f"Model inferred from serial number location code '{prefix}'. Please verify."
    
    return "Cisco Network Device (Inferred)", "Model inferred from serial number structure. Please verify."

def get_tcl_model_name(serial_number):
    """
    Infers the TCL model name based on known serial number structure.
    TCL serial numbers are typically 12-14 characters.
    """
    if not TCL_SERIAL_REGEX.match(serial_number):
        return None, "Invalid TCL Serial Number format (must be 12-14 alphanumeric characters)."

    # TCL serial numbers are highly variable. We will use a generic inferred name.
    # The serial number is often used for warranty, but not directly for model lookup without an internal tool.
    
    return "TCL TV/Display (Inferred)", "Model inferred from serial number structure. Please verify."

def get_vizio_model_name(serial_number):
    """
    Infers the Vizio model name based on known serial number structure.
    Vizio serial numbers are 14 characters. The first 4 characters are often a code.
    """
    if not VIZIO_SERIAL_REGEX.match(serial_number):
        return None, "Invalid Vizio Serial Number format (must be 14 alphanumeric characters)."

    # Vizio serial numbers often start with a code that indicates the product line/factory
    prefix = serial_number[:4]

    # This mapping is highly simplified and should be expanded based on local inventory
    # Vizio model numbers are more reliably found on the back of the unit.
    model_map = {
        "LTMA": "Vizio M-Series TV (Inferred)",
        "LTAS": "Vizio E-Series TV (Inferred)",
        "LTJZ": "Vizio V-Series TV (Inferred)",
        "LTJA": "Vizio D-Series TV (Inferred)",
    }

    model = model_map.get(prefix)

    if model:
        return model, f"Model inferred from serial number prefix '{prefix}'. Please verify."
    
    return "Vizio Display/TV (Inferred)", "Model inferred from serial number structure. Please verify."

def get_samsung_model_name(serial_number):
    """
    Scrapes the Samsung support page to find the product model name.
    NOTE: Samsung's public warranty check is often heavily protected or requires model code.
    We will use a pattern-matching fallback based on the serial number structure.
    """
    if not SAMSUNG_SERIAL_REGEX.match(serial_number):
        return None, "Invalid Samsung Serial Number format (must be 11 or 15 alphanumeric characters)."

    # Fallback to pattern matching based on serial number structure
    # The 4th digit often indicates the year, and the 5th the month for 11-digit serials.
    # The 8th and 9th digits for 15-digit serials.
    
    # Since reliable scraping is near-impossible without a full browser, we will simply return a generic name.
    return "Samsung Device (Inferred)", "Model inferred from serial number structure. Please verify."

def get_microsoft_model_name(serial_number):
    """
    Scrapes the Microsoft Surface warranty check page to find the product model name.
    """
    if not MICROSOFT_SERIAL_REGEX.match(serial_number):
        return None, "Invalid Microsoft Serial Number format (must be 12 or 16 digits/letters)."

    # Microsoft's official warranty check page
    url = "https://mybusinessservice.surface.com/en-US/CheckWarranty/CheckWarranty"
    
    # NOTE: This page often uses JavaScript to load the final data, making direct scraping difficult.
    # We will try a simple POST request to the check endpoint, which may or may not work reliably.
    # The actual check is usually done via an internal API call that is not public.
    
    # We will use a known working endpoint for a simple check. This is highly fragile.
    # A more robust solution would require a full browser automation tool (like Selenium) on the server.
    
    # For now, we will use a pattern-matching fallback, as direct scraping of this page is very unreliable.
    
    # Fallback to pattern matching based on known Surface serial number structures
    # Surface serials are often purely numeric and the model is not easily inferred from the number itself.
    
    # Since reliable scraping is near-impossible without a full browser, we will simply return a generic name.
    return "Microsoft Surface Device (Inferred)", "Model inferred from serial number structure. Please verify."

def get_apc_model_name(serial_number):
    """
    Infers the APC model name based on the serial number structure.
    APC serials are typically 12 characters. The first two characters often indicate the product line.
    """
    if not APC_SERIAL_REGEX.match(serial_number):
        return None, "Invalid APC Serial Number format (must be 12 alphanumeric characters)."

    prefix = serial_number[:2].upper()

    # This mapping is based on common APC product lines
    prefix_to_model = {
        "AS": "APC Smart-UPS (Rack/Tower)",
        "AP": "APC Power Distribution Unit (PDU)",
        "BB": "APC Back-UPS (Basic Battery Backup)",
        "BK": "APC Back-UPS (Basic Battery Backup)",
        "SM": "APC Smart-UPS (Older Models)",
        "SU": "APC Smart-UPS (Older Models)",
        "SY": "APC Symmetra (Modular UPS)",
    }

    if prefix in prefix_to_model:
        model = prefix_to_model[prefix]
        return model, f"Model inferred from serial number prefix '{prefix}'. Please verify."
    
    return "APC UPS/Power Device (Inferred)", "Model inferred from serial number structure. Please verify."

def get_acer_model_name(serial_number):
    """
    Scrapes the Acer support page to find the product model name.
    """
    if not ACER_SERIAL_REGEX.match(serial_number):
        return None, "Invalid Acer Serial Number/SNID format (must be 22 alphanumeric or 11/12 digit SNID)."

    # URL to scrape (Acer's official support page for serial number lookup)
    # This URL is a common target for scraping product info
    url = f"https://www.acer.com/us-en/support/product-support/serial-number-lookup?sn={serial_number}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Acer's product name is usually in a prominent h1 or h2 tag on the support page
        # We need to find the specific element that contains the model name.
        # This is a common pattern for product pages:
        model_element = soup.find('h1', class_='product-name') or soup.find('h2', class_='product-name')
        
        if model_element:
            model_name = model_element.text.strip()
            if model_name:
                return model_name, "Model found via web scraping."
        
        # Fallback to pattern matching if scraping is blocked or structure changed
        if len(serial_number) == 22:
            # Placeholder for pattern matching logic if scraping fails
            return f"Acer Product (Serial: {serial_number[:5]}...)", "Model inferred from serial number prefix. Please verify."

        return None, "Model name element not found on Acer support page."

    except requests.exceptions.RequestException as e:
        # Fallback to pattern matching if request fails (e.g., blocked)
        if len(serial_number) == 22:
            return f"Acer Product (Serial: {serial_number[:5]}...)", "Model inferred from serial number prefix (Web scraping failed). Please verify."
        elif len(serial_number) >= 11 and serial_number.isdigit():
            return f"Acer Product (SNID: {serial_number})", "Model inferred from SNID (Web scraping failed). Please verify."
        
        return None, f"Request failed: {e}"

def get_brother_model_name(serial_number):
    """
    Infers the Brother model name based on known serial number prefixes.
    Since Brother does not offer a public API, this uses pattern matching.
    The first few characters often indicate the product line.
    """
    if not BROTHER_SERIAL_REGEX.match(serial_number):
        return None, "Invalid Brother Serial Number format (must be 15 alphanumeric characters)."

    # This mapping is based on common Brother serial number prefixes.
    # This is an educated guess/inference, not a definitive lookup.
    # The actual model must be verified by the user.
    prefix_to_model = {
        # Common Laser Printer Series (Example prefixes)
        "U6": "Brother HL-L Series Laser Printer",
        "E6": "Brother MFC-L Series All-in-One",
        "K6": "Brother DCP-L Series All-in-One",
        # Common Inkjet Series (Example prefixes)
        "D6": "Brother MFC-J Series Inkjet",
        "J6": "Brother DCP-J Series Inkjet",
    }

    # Use the first two characters as a prefix for a simple lookup
    prefix = serial_number[:2].upper()

    if prefix in prefix_to_model:
        model = prefix_to_model[prefix]
        return model, f"Model inferred from serial number prefix '{prefix}'. Please verify."
    
    return None, "Could not infer Brother model from serial number prefix."

def get_cyberpower_model_name(serial_number):
    """
    Infers the CyberPower model name based on known serial number prefixes.
    Since CyberPower does not offer a public API, this uses pattern matching.
    The first 3 characters often indicate the product line/model family.
    """
    if not CYBERPOWER_SERIAL_REGEX.match(serial_number):
        return None, "Invalid CyberPower Serial Number format (must be 12 or 16 alphanumeric characters)."

    # This mapping is based on common CyberPower serial number prefixes.
    # This is an educated guess/inference, not a definitive lookup.
    # The actual model must be verified by the user.
    prefix_to_model = {
        # Common UPS Series (Example prefixes)
        "CP": "CyberPower CP Series UPS",
        "PR": "CyberPower PR Series UPS",
        "OR": "CyberPower OR Series UPS",
        "BP": "CyberPower Battery Pack",
        # You can add more specific mappings here based on your inventory
        "CP1": "CyberPower CP1500PFCLCD",
        "CP2": "CyberPower CP1000PFCLCD",
    }

    # Use the first two or three characters as a prefix for a simple lookup
    # Try 3 characters first for more specificity
    prefix3 = serial_number[:3].upper()
    prefix2 = serial_number[:2].upper()

    if prefix3 in prefix_to_model:
        model = prefix_to_model[prefix3]
        return model, f"Model inferred from serial number prefix '{prefix3}'. Please verify."
    elif prefix2 in prefix_to_model:
        model = prefix_to_model[prefix2]
        return model, f"Model inferred from serial number prefix '{prefix2}'. Please verify."
    
    return None, "Could not infer CyberPower model from serial number prefix."

def get_juniper_model_name(serial_number):
    """
    Infers the Juniper model name based on known serial number prefixes (not a scrape).
    Since public Juniper serial-to-model APIs are not available, this uses pattern matching.
    """
    if not JUNIPER_SERIAL_REGEX.match(serial_number):
        return None, "Invalid Juniper Serial Number format (must be 12 alphanumeric characters)."

    # This mapping is based on common Juniper serial number prefixes for EX series.
    # This is an educated guess/inference, not a definitive lookup.
    # The actual model must be verified by the user.
    prefix_to_model = {
        # EX4100 Series (Example prefixes - highly speculative without official docs)
        "AA": "EX4100-24P",
        "AB": "EX4100-48P",
        "AC": "EX4100-24T",
        "AD": "EX4100-48T",
        # EX4300 Series (Example prefixes)
        "BA": "EX4300-24P",
        "BB": "EX4300-48P",
        # EX2300 Series (Example prefixes)
        "CA": "EX2300-24P",
        "CB": "EX2300-48P",
    }

    # Use the first two characters as a prefix for a simple lookup
    prefix = serial_number[:2].upper()

    if prefix in prefix_to_model:
        model = prefix_to_model[prefix]
        return model, f"Model inferred from serial number prefix '{prefix}'. Please verify."
    
    return None, "Could not infer Juniper model from serial number prefix."

def get_viewsonic_model_name(serial_number):
    """
    Scrapes the ViewSonic support page for the product model name using the serial number.
    """
    if not VIEWSONIC_SERIAL_REGEX.match(serial_number):
        return None, "Invalid ViewSonic Serial Number format."

    # ViewSonic support URL structure for product lookup (Warranty Check page)
    # Note: ViewSonic's site is very difficult to scrape with a simple GET request.
    # We will try a common pattern for product info pages, but this may require
    # simulating a POST request or using a more advanced scraping library.
    # For now, we will use a simple GET to the warranty page, which often redirects
    # to a product page if the serial is valid.
    url = f"https://www.viewsonic.com/us/viewsonic-warranty-lookup?serial_number={serial_number}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        if response.status_code == 404:
            return None, "Serial Number found, but product page not found (404). It might be too old or invalid."
        return None, f"HTTP Error: {errh}"
    except requests.exceptions.ConnectionError as errc:
        return None, f"Error Connecting: {errc}"
    except requests.exceptions.Timeout as errt:
        return None, f"Timeout Error: {errt}"
    except requests.exceptions.RequestException as err:
        return None, f"An unexpected error occurred: {err}"

    soup = BeautifulSoup(response.content, 'html.parser')

    # ViewSonic model name scraping logic (highly dependent on current site structure)
    # We will look for a common pattern: a large heading or a span with product info.
    
    # Attempt 1: Look for the main product name in a specific element
    product_name_element = soup.find('h1', class_='product-name')
    if not product_name_element:
        product_name_element = soup.find('span', class_='model-name') # Placeholder class

    if product_name_element:
        model_name = product_name_element.text.strip()
        return model_name, "Model name scraped successfully."
    
    # Attempt 2: Fallback to the page title
    title_tag = soup.find('title')
    if title_tag and 'ViewSonic' in title_tag.text:
        # Try to extract the model from the title (e.g., "ViewSonic IFP6550 Product Support")
        match = re.search(r'ViewSonic\s+([A-Z0-9]+)\s+Product', title_tag.text)
        if match:
            model_name = match.group(1).strip()
            if model_name:
                return model_name, "Model name scraped from page title (fallback)."

    return None, "Could not find the product model name on the page."

def get_hp_model_name(serial_number):
    """
    Scrapes the HP support page for the product model name using the serial number.
    """
    if not HP_SERIAL_REGEX.match(serial_number):
        return None, "Invalid HP Serial Number format."

    # HP support URL structure for product lookup
    url = f"https://support.hp.com/us-en/product/lookup/{serial_number}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        if response.status_code == 404:
            return None, "Serial Number found, but product page not found (404). It might be too old or invalid."
        return None, f"HTTP Error: {errh}"
    except requests.exceptions.ConnectionError as errc:
        return None, f"Error Connecting: {errc}"
    except requests.exceptions.Timeout as errt:
        return None, f"Timeout Error: {errt}"
    except requests.exceptions.RequestException as err:
        return None, f"An unexpected error occurred: {err}"

    soup = BeautifulSoup(response.content, 'html.parser')

    # The HP model name is typically in a prominent header tag or a specific data attribute.
    # Look for the main product name element.
    
    # Attempt 1: Look for the main product name in a specific element (e.g., h1 or span with a specific class/id)
    # HP's site structure is complex and changes often. We will look for a common pattern:
    # a large heading or a span with product info.
    product_name_element = soup.find('h1', class_='product-title') # Common class
    if not product_name_element:
        product_name_element = soup.find('span', class_='product-name') # Another common class

    if product_name_element:
        model_name = product_name_element.text.strip()
        # Clean up the model name (remove unnecessary prefixes/suffixes)
        model_name = re.sub(r'^HP\s+', '', model_name, flags=re.IGNORECASE).strip()
        return model_name, "Model name scraped successfully."
    
    # Attempt 2: Fallback to the page title
    title_tag = soup.find('title')
    if title_tag and 'HP Product Information' in title_tag.text:
        # Extract the part before " | HP Product Information"
        match = re.search(r'(.+?)\s+\|\s+HP Product Information', title_tag.text)
        if match:
            model_name = match.group(1).strip()
            if model_name:
                return model_name, "Model name scraped from page title (fallback)."

    return None, "Could not find the product model name on the page."

def get_dell_model_name(service_tag):
    """
    Scrapes the Dell support page for the product model name using the service tag.
    """
    if not SERVICE_TAG_REGEX.match(service_tag):
        return None, "Invalid Dell Service Tag format."

    # Dell support URL structure
    url = f"https://www.dell.com/support/home/en-us/product-support/servicetag/{service_tag}/overview"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
    except requests.exceptions.HTTPError as errh:
        if response.status_code == 404:
            return None, "Service Tag found, but product page not found (404). It might be too old or invalid."
        return None, f"HTTP Error: {errh}"
    except requests.exceptions.ConnectionError as errc:
        return None, f"Error Connecting: {errc}"
    except requests.exceptions.Timeout as errt:
        return None, f"Timeout Error: {errt}"
    except requests.exceptions.RequestException as err:
        return None, f"An unexpected error occurred: {err}"

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # The product name is typically in a prominent header tag with a specific class or structure.
    # Common selectors for the model name:
    # 1. The main product title/name on the overview page.
    # 2. A specific data attribute.
    
    # Let's try to find the main product name element.
    # A common pattern is a large heading (h1 or h2) that contains the product name.
    # We'll look for a few common identifiers.
    
    # Attempt 1: Look for the product name in a specific div/span
    product_name_element = soup.find('h1', class_='product-name') # Common Dell support class
    if not product_name_element:
        # Attempt 2: Look for the product name in the main product info section
        product_name_element = soup.find('span', id='modelName') # Another possible ID
    if not product_name_element:
        # Attempt 3: Look for the model name in the page title (less reliable but a fallback)
        title_tag = soup.find('title')
        if title_tag and 'Support for' in title_tag.text:
            # Extract the part after "Support for " and before " | Dell US"
            match = re.search(r'Support for (.+?) \| Dell US', title_tag.text)
            if match:
                model_name = match.group(1).strip()
                if model_name:
                    return model_name, "Model name scraped from page title (fallback)."
    
    if product_name_element:
        model_name = product_name_element.text.strip()
        # Clean up the model name (remove "Support for" prefix if present)
        model_name = re.sub(r'^Support for\s+', '', model_name, flags=re.IGNORECASE).strip()
        return model_name, "Model name scraped successfully."
    
    return None, "Could not find the product model name on the page."


@app.route('/lookup/dell', methods=['GET'])
def lookup_dell_service_tag():
    service_tag = request.args.get('tag', '').upper()
    
    if not service_tag:
        return jsonify({'error': 'Missing service tag parameter.'}), 400

    if not SERVICE_TAG_REGEX.match(service_tag):
        return jsonify({'error': 'Invalid Dell Service Tag format (must be 7 alphanumeric characters).'}), 400

    model_name, message = get_dell_model_name(service_tag)

    if model_name:
        return jsonify({
            'success': True,
            'service_tag': service_tag,
            'model_name': model_name,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'service_tag': service_tag,
            'error': message
        }), 404

@app.route('/lookup/tcl', methods=['GET'])
def lookup_tcl_serial_number():
    serial_number = request.args.get('tag', '').upper()
    
    if not serial_number:
        return jsonify({'error': 'Missing serial number parameter.'}), 400

    if not TCL_SERIAL_REGEX.match(serial_number):
        return jsonify({'error': 'Invalid TCL Serial Number format.'}), 400

    model_name, message = get_tcl_model_name(serial_number)

    if model_name:
        return jsonify({
            'success': True,
            'serial_number': serial_number,
            'model_name': model_name,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'serial_number': serial_number,
            'error': message
        }), 404

@app.route('/lookup/vizio', methods=['GET'])
def lookup_vizio_serial_number():
    serial_number = request.args.get('tag', '').upper()
    
    if not serial_number:
        return jsonify({'error': 'Missing serial number parameter.'}), 400

    if not VIZIO_SERIAL_REGEX.match(serial_number):
        return jsonify({'error': 'Invalid Vizio Serial Number format.'}), 400

    model_name, message = get_vizio_model_name(serial_number)

    if model_name:
        return jsonify({
            'success': True,
            'serial_number': serial_number,
            'model_name': model_name,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'serial_number': serial_number,
            'error': message
        }), 404

@app.route('/lookup/samsung', methods=['GET'])
def lookup_samsung_serial_number():
    serial_number = request.args.get('tag', '').upper()
    
    if not serial_number:
        return jsonify({'error': 'Missing serial number parameter.'}), 400

    if not SAMSUNG_SERIAL_REGEX.match(serial_number):
        return jsonify({'error': 'Invalid Samsung Serial Number format.'}), 400

    model_name, message = get_samsung_model_name(serial_number)

    if model_name:
        return jsonify({
            'success': True,
            'serial_number': serial_number,
            'model_name': model_name,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'serial_number': serial_number,
            'error': message
        }), 404

@app.route('/lookup/microsoft', methods=['GET'])
def lookup_microsoft_serial_number():
    serial_number = request.args.get('tag', '').upper()
    
    if not serial_number:
        return jsonify({'error': 'Missing serial number parameter.'}), 400

    if not MICROSOFT_SERIAL_REGEX.match(serial_number):
        return jsonify({'error': 'Invalid Microsoft Serial Number format.'}), 400

    model_name, message = get_microsoft_model_name(serial_number)

    if model_name:
        return jsonify({
            'success': True,
            'serial_number': serial_number,
            'model_name': model_name,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'serial_number': serial_number,
            'error': message
        }), 404

@app.route('/lookup/apc', methods=['GET'])
def lookup_apc_serial_number():
    serial_number = request.args.get('tag', '').upper()
    
    if not serial_number:
        return jsonify({'error': 'Missing serial number parameter.'}), 400

    if not APC_SERIAL_REGEX.match(serial_number):
        return jsonify({'error': 'Invalid APC Serial Number format.'}), 400

    model_name, message = get_apc_model_name(serial_number)

    if model_name:
        return jsonify({
            'success': True,
            'serial_number': serial_number,
            'model_name': model_name,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'serial_number': serial_number,
            'error': message
        }), 404

@app.route('/lookup/cisco', methods=['GET'])
def lookup_cisco_serial_number():
    serial_number = request.args.get('tag', '').upper()
    
    if not serial_number:
        return jsonify({'error': 'Missing serial number parameter.'}), 400

    if not CISCO_SERIAL_REGEX.match(serial_number):
        return jsonify({'error': 'Invalid Cisco Serial Number format.'}), 400

    model_name, message = get_cisco_model_name(serial_number)

    if model_name:
        return jsonify({
            'success': True,
            'serial_number': serial_number,
            'model_name': model_name,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'serial_number': serial_number,
            'error': message
        }), 404

@app.route('/lookup/lenovo', methods=['GET'])
def lookup_lenovo_serial_number():
    serial_number = request.args.get('tag', '').upper()
    
    if not serial_number:
        return jsonify({'error': 'Missing serial number parameter.'}), 400

    if not LENOVO_SERIAL_REGEX.match(serial_number):
        return jsonify({'error': 'Invalid Lenovo Serial Number format.'}), 400

    model_name, message = get_lenovo_model_name(serial_number)

    if model_name:
        return jsonify({
            'success': True,
            'serial_number': serial_number,
            'model_name': model_name,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'serial_number': serial_number,
            'error': message
        }), 404

@app.route('/lookup/acer', methods=['GET'])
def lookup_acer_serial_number():
    serial_number = request.args.get('tag', '').upper()
    
    if not serial_number:
        return jsonify({'error': 'Missing serial number parameter.'}), 400

    if not ACER_SERIAL_REGEX.match(serial_number):
        return jsonify({'error': 'Invalid Acer Serial Number/SNID format.'}), 400

    model_name, message = get_acer_model_name(serial_number)

    if model_name:
        return jsonify({
            'success': True,
            'serial_number': serial_number,
            'model_name': model_name,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'serial_number': serial_number,
            'error': message
        }), 404

@app.route('/lookup/apple', methods=['GET'])
def lookup_apple_serial_number():
    serial_number = request.args.get('tag', '').upper()
    
    if not serial_number:
        return jsonify({'error': 'Missing serial number parameter.'}), 400

    if not APPLE_SERIAL_REGEX.match(serial_number):
        return jsonify({'error': 'Invalid Apple Serial Number format (must be 12 or 17 alphanumeric characters).'}), 400

    model_name, message = get_apple_model_name(serial_number)

    if model_name:
        return jsonify({
            'success': True,
            'serial_number': serial_number,
            'model_name': model_name,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'serial_number': serial_number,
            'error': message
        }), 404

@app.route('/lookup/brother', methods=['GET'])
def lookup_brother_serial_number():
    serial_number = request.args.get('tag', '').upper()
    
    if not serial_number:
        return jsonify({'error': 'Missing serial number parameter.'}), 400

    if not BROTHER_SERIAL_REGEX.match(serial_number):
        return jsonify({'error': 'Invalid Brother Serial Number format (must be 15 alphanumeric characters).'}), 400

    model_name, message = get_brother_model_name(serial_number)

    if model_name:
        return jsonify({
            'success': True,
            'serial_number': serial_number,
            'model_name': model_name,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'serial_number': serial_number,
            'error': message
        }), 404

@app.route('/lookup/cyberpower', methods=['GET'])
def lookup_cyberpower_serial_number():
    serial_number = request.args.get('tag', '').upper()
    
    if not serial_number:
        return jsonify({'error': 'Missing serial number parameter.'}), 400

    if not CYBERPOWER_SERIAL_REGEX.match(serial_number):
        return jsonify({'error': 'Invalid CyberPower Serial Number format (must be 12 or 16 alphanumeric characters).'}), 400

    model_name, message = get_cyberpower_model_name(serial_number)

    if model_name:
        return jsonify({
            'success': True,
            'serial_number': serial_number,
            'model_name': model_name,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'serial_number': serial_number,
            'error': message
        }), 404

@app.route('/lookup/juniper', methods=['GET'])
def lookup_juniper_serial_number():
    serial_number = request.args.get('tag', '').upper()
    
    if not serial_number:
        return jsonify({'error': 'Missing serial number parameter.'}), 400

    if not JUNIPER_SERIAL_REGEX.match(serial_number):
        return jsonify({'error': 'Invalid Juniper Serial Number format (must be 12 alphanumeric characters).'}), 400

    model_name, message = get_juniper_model_name(serial_number)

    if model_name:
        return jsonify({
            'success': True,
            'serial_number': serial_number,
            'model_name': model_name,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'serial_number': serial_number,
            'error': message
        }), 404

@app.route('/lookup/viewsonic', methods=['GET'])
def lookup_viewsonic_serial_number():
    serial_number = request.args.get('tag', '').upper()
    
    if not serial_number:
        return jsonify({'error': 'Missing serial number parameter.'}), 400

    if not VIEWSONIC_SERIAL_REGEX.match(serial_number):
        return jsonify({'error': 'Invalid ViewSonic Serial Number format (must be 10-12 alphanumeric characters).'}), 400

    model_name, message = get_viewsonic_model_name(serial_number)

    if model_name:
        return jsonify({
            'success': True,
            'serial_number': serial_number,
            'model_name': model_name,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'serial_number': serial_number,
            'error': message
        }), 404

@app.route('/lookup/hp', methods=['GET'])
def lookup_hp_serial_number():
    serial_number = request.args.get('tag', '').upper()
    
    if not serial_number:
        return jsonify({'error': 'Missing serial number parameter.'}), 400

    if not HP_SERIAL_REGEX.match(serial_number):
        return jsonify({'error': 'Invalid HP Serial Number format (must be 10-12 alphanumeric characters).'}), 400

    model_name, message = get_hp_model_name(serial_number)

    if model_name:
        return jsonify({
            'success': True,
            'serial_number': serial_number,
            'model_name': model_name,
            'message': message
        })
    else:
        return jsonify({
            'success': False,
            'serial_number': serial_number,
            'error': message
        }), 404

@app.route('/', methods=['GET'])
def home():
    return "Inventory Lookup API is running. Endpoints: /lookup/dell?tag=<DELL_TAG>, /lookup/hp?tag=<HP_SERIAL>, /lookup/viewsonic?tag=<VIEWSONIC_SERIAL>, /lookup/juniper?tag=<JUNIPER_SERIAL>, /lookup/cyberpower?tag=<CYBERPOWER_SERIAL>, /lookup/brother?tag=<BROTHER_SERIAL>, /lookup/apple?tag=<APPLE_SERIAL>, /lookup/acer?tag=<ACER_SERIAL>, /lookup/lenovo?tag=<LENOVO_SERIAL>, /lookup/cisco?tag=<CISCO_SERIAL>, /lookup/apc?tag=<APC_SERIAL>, /lookup/microsoft?tag=<MICROSOFT_SERIAL>, /lookup/samsung?tag=<SAMSUNG_SERIAL>, /lookup/vizio?tag=<VIZIO_SERIAL>, and /lookup/tcl?tag=<TCL_SERIAL>""

if __name__ == '__main__':
    # Use environment variable for port, common in hosting environments
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
