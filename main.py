import requests
import re
import os
import sys
import threading
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# List of payment gateways to search for
PAYMENT_GATEWAYS = [
    "PayPal", "Stripe", "Braintree", "Square", "magento", "Convergepay",
    "PaySimple", "oceanpayments", "eProcessing", "hipay", "worldpay", "cybersourse",
    "payjunction", "Authorize.Net", "2Checkout", "Adyen", "Checkout.com", "PayFlow",
    "Payeezy", "usaepay", "creo", "SquareUp", "Authnet", "ebizcharge", "cpay",
    "Moneris", "recurly", "cardknox", "payeezy", "matt sorra", "ebizcharge",
    "payflow", "Chargify", "payflow", "Paytrace", "hostedpayments", "securepay",
    "eWay", "blackbaud", "LawPay", "clover", "cardconnect", "bluepay", "fluidpay",
    "Worldpay", "Ebiz", "chasepaymentech", "cardknox", "2checkout", "Auruspay",
    "sagepayments", "paycomet", "geomerchant", "realexpayments",
    "Rocketgateway", "Rocketgate", "Rocket", "Auth.net", "Authnet", "rocketgate.com",
    "Shopify", "WooCommerce", "BigCommerce", "Magento Payments",
    "OpenCart", "PrestaShop", "Razorpay"
]

# Security indicators
SECURITY_INDICATORS = {
    'captcha': ['captcha', 'protected by recaptcha', "i'm not a robot", 'recaptcha/api.js'],
    'cloudflare': ['cloudflare', 'cdnjs.cloudflare.com', 'challenges.cloudflare.com']
}

def normalize_url(url):
    """Ensure the URL has a scheme."""
    if not re.match(r'^https?://', url, re.I):
        url = 'http://' + url
    return url

def find_payment_gateways(content):
    """Find payment gateways in the given content."""
    detected = set()
    for gateway in PAYMENT_GATEWAYS:
        # Use word boundaries to ensure accurate matching
        if re.search(r'\b' + re.escape(gateway) + r'\b', content, re.I):
            detected.add(gateway)
    return list(detected)

def check_security(content):
    """Check for captcha and cloudflare in the content."""
    captcha_present = any(re.search(indicator, content, re.I) for indicator in SECURITY_INDICATORS['captcha'])
    cloudflare_present = any(re.search(indicator, content, re.I) for indicator in SECURITY_INDICATORS['cloudflare'])
    return captcha_present, cloudflare_present

def read_urls_from_file(file_path):
    """Read URLs from a text file."""
    if not os.path.isfile(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)
    with open(file_path, 'r', encoding='utf-8') as file:
        urls = [line.strip() for line in file if line.strip()]
    return urls

def fetch_content(url, session):
    """Fetch the content of a URL using a requests.Session."""
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
        return None

def save_result(entry, output_file, lock):
    """Save a single entry to the output file in a thread-safe manner."""
    with lock:
        with open(output_file, 'a', encoding='utf-8') as file:
            file.write(f"--------------------------------------------------\n")
            file.write(f"URL: {entry['url']}\n")
            file.write(f"Gateways: {', '.join(entry['gateways'])}\n")
            security = []
            security.append("Captcha: " + ("No" if not entry['captcha'] else "Yes"))
            security.append("Cloudflare: " + ("No" if not entry['cloudflare'] else "Yes"))
            file.write(f"Security: {', '.join(security)}\n\n")
            file.write(f"@Mod_By_Kamal\n\n")
            file.write(f"--------------------------------------------------\n")
            file.flush()  # Ensure data is written to disk immediately

def process_url(url, session, output_file, lock):
    """Process a single URL: fetch content, detect gateways, check security, and save if criteria met."""
    normalized = normalize_url(url)
    content = fetch_content(normalized, session)
    if content is None:
        return  # Skip if fetching failed
    gateways = find_payment_gateways(content)
    captcha, cloudflare = check_security(content)
    
    # Skip if no gateways detected or only Unknown gateway
    if not gateways:
        print(f"Skipped (No Gateways): {normalized}")
        return
        
    if not captcha and not cloudflare:
        entry = {
            'url': normalized,
            'gateways': gateways,
            'captcha': captcha,
            'cloudflare': cloudflare
        }
        save_result(entry, output_file, lock)
        print(f"Saved: {normalized}")
    else:
        print(f"Skipped (Security Detected): {normalized}")

def main():
    print("=== Gateway Filter Script ===\n")
    input_file = "urls.txt"  # Replace with your input file name if different
    if not os.path.isfile(input_file):
        print(f"Error: File '{input_file}' does not exist.")
        sys.exit(1)
    urls = read_urls_from_file(input_file)
    
    if not urls:
        print("No URLs found in the input file.")
        sys.exit(0)
    
    output_file = "filtered_results_no_captcha_cloudflare.txt"
    
    # Ensure the output file is empty before starting
    open(output_file, 'w', encoding='utf-8').close()
    
    print(f"Processing {len(urls)} URLs...\n")
    
    # Initialize a threading lock for safe file writing
    lock = threading.Lock()
    
    # Initialize a requests.Session for connection pooling
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    # Define the number of threads
    max_threads = min(32, os.cpu_count() + 4)  # Adjust based on your system
    
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [
            executor.submit(process_url, url, session, output_file, lock)
            for url in urls
        ]
        
        # Optionally, display progress as URLs are processed
        for future in as_completed(futures):
            pass  # All progress is already printed in process_url
    
    print(f"\nProcessing complete. Results saved to '{output_file}'.")

if __name__ == "__main__":
    main()
