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
    return "Inventory Lookup API is running. Endpoints: /lookup/dell?tag=<DELL_TAG>, /lookup/hp?tag=<HP_SERIAL>, /lookup/viewsonic?tag=<VIEWSONIC_SERIAL>, /lookup/juniper?tag=<JUNIPER_SERIAL>, and /lookup/cyberpower?tag=<CYBERPOWER_SERIAL>""

if __name__ == '__main__':
    # Use environment variable for port, common in hosting environments
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
