from pymongo import MongoClient
from pymongo.collection import Collection
import logging
import os
import sys

def createConnection() -> Collection:
    # Connect to your MongoDB cluster
    connection_str = os.getenv('MONGO_DB_CONNECTION_URL')
    if not connection_str:
        logging.debug("MongoDB connection string not found")
        sys.exit(1)       
    client = MongoClient(connection_str)
    collection = client['price_check']['price_details']
    try:
        client.server_info() 
        return client, collection
    except Exception as err:
        logging.debug(f"Failed to connect to MongoDB: {err}")
        return None, None

def check_if_exists(product_name, collection):
    existing_document = collection.find_one({"product_name": product_name})
    if existing_document:
        return True
    else:
        return False

def update_document(document, collection):
    # Update the document
    result = collection.replace_one(
        {"product_name": document['product_name']},  
        document  
    )
    return result.matched_count > 0

def create_document(document, collection):
    # Insert the document into the collection
    result = collection.insert_one(document)
    return result.inserted_id is not None

def fetch_product_details(product_name, collection):
    document = collection.find_one({"product_name": product_name})
    return document

    