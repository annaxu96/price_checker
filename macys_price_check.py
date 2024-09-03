import requests
from bs4 import BeautifulSoup
import sys
from urllib.parse import urlparse, parse_qs, urlunparse
import db_utils
import datetime
import logging
from bson import ObjectId

def get_product_name(soup):
    try:
        product_name_div = soup.find('div', {'data-auto': 'product-name'})
        if product_name_div:
            product_name = product_name_div.get_text(strip=True)
            return product_name
        else:
            return None
    except Exception as e:
        logging.debug(f"An error occurred while fetching product name: {e}")
        return None


def get_product_price(soup):
    try:
        # lowest_sale_price_div = soup.find('div', {'class': 'lowest-sale-price'})
        # if lowest_sale_price_div:
            
        original_price_div = soup.find('div', {'class': 'c-strike'})
        sale_price_div = soup.find('div', {'class': 'lowest-sale-price'})
        if original_price_div:
            original_price = original_price_div.get_text(strip=True)
        if sale_price_div:
            sale_price_span = sale_price_div.find('span', {'class': 'bold c-red'})
        if sale_price_span:
            sale_price = sale_price_span.get_text(strip=True)
        else:
            logging.debug("No sales")
            return None, None
        return original_price.replace('$', ''), sale_price.replace('$', '')
    except Exception as e:
        logging.debug(f"An error occurred while fetching product price: {e}")
        return None, None


def clean_url(urls):
    clean_urls = []
    for url in urls:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        essential_params = {k: v for k, v in query_params.items() if k in ['ID']}
        cleaned_query = '&'.join([f"{key}={','.join(value)}" for key, value in essential_params.items()])
        cleaned_url = urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            cleaned_query,
            parsed_url.fragment
        ))
        clean_urls.append(cleaned_url)
    return clean_urls

def get_parser(url) -> BeautifulSoup:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.macys.com/",
    }
    try:
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            logging.debug("Status code is ${response.status_code}. Unable to get the product details.")
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup
    except Exception as e:
        logging.debug(f"Error with url: {url}")
        logging.debug(f"An error occurred while fetching the product details: {e}")
        return None

def get_product_details(urls):
    documents = []
    cleaned_urls = clean_url(urls)
    for cleaned_url in cleaned_urls:
        soup = get_parser(cleaned_url)
        if soup is None:
            continue
        logging.debug(f"Fetching product details for {cleaned_url}")
        name = get_product_name(soup)
        price, sale = get_product_price(soup)
        if price is None or sale is None or name is None:
            continue
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        document = {
            "product_name": name,
            "date": date,
            "original_price": price,
            "sale_price": sale
        }
        documents.append(document)
    return documents


def fetch_product_details_from_db(product_name, document, collection):
    if db_utils.check_if_exists(product_name, collection):
        if check_price_changed(document, collection):
            if db_utils.update_document(document, collection):
                logging.debug(f"Document for {product_name} updated successfully")
            else:
                logging.debug(f"Failed to update document for {product_name}")
        else:
            logging.debug(f"Price has not changed for {product_name}")
    else:
        if db_utils.create_document(document, collection):
            logging.debug(f"Document for {product_name} created successfully")
        else:
            logging.debug(f"Failed to create document for {product_name}")


def check_price_changed(document,collection):
    db_document = db_utils.fetch_product_details(document['product_name'], collection)
    db_sale = db_document['sale_price']
    if document['sale_price'] < db_sale:
        return True
    else:   
        return False
    

def load_urls_db(collection):
    try:
        object_id = ObjectId("66d68495ac9fe4fa400a75ed")
        # Find the document by _id and retrieve only the 'product_urls' field
        document = collection.find_one({"_id": object_id})
        return document['product_urls']
    except Exception as e:
        logging.debug(f"Failed to get product urls: {e}")
        sys.exit(1)

    
def start():
    setup_logging()
    client, collection = db_utils.createConnection()
    if collection is None:
        logging.debug("Failed to connect to MongoDB")
        sys.exit(1)
    product_urls = load_urls_db(collection)
    documents = get_product_details(product_urls)
    for document in documents:
        fetch_product_details_from_db(document['product_name'], document, collection)
    client.close()


def setup_logging(log_file='app.log'):
    # Configure the logging
    logging.basicConfig(
        level=logging.DEBUG,  # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format='%(asctime)s - %(levelname)s - %(message)s',  # Log message format
        handlers=[
            logging.FileHandler(log_file),  # Log to a file
            logging.StreamHandler()  # Optionally, also log to the console
        ]
    )

    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('bs4').setLevel(logging.WARNING)
    logging.getLogger('pymongo').setLevel(logging.WARNING)
    

if __name__ == "__main__":
    start()


