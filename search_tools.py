from sentence_transformers import SentenceTransformer
import chromadb
import json
import os
from PIL import Image
from io import BytesIO
from logger_config import get_logger

# Initialize logger
logger = get_logger("search_tools")

# Initialize models
try:
    logger.info("Loading sentence transformer models...")
    text_model = SentenceTransformer('sentence-transformers/clip-ViT-B-32-multilingual-v1')
    image_model = SentenceTransformer('clip-ViT-B-32')
    logger.info("Models loaded successfully")
except Exception as e:
    logger.error(f"Failed to load models: {e}", exc_info=True)
    raise

# Initialize ChromaDB
try:
    logger.info("Initializing ChromaDB...")
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection(name="bouquets")
    logger.info("ChromaDB initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize ChromaDB: {e}", exc_info=True)
    raise

def search_products_by_text(query_text, document_type=None, min_price=None, max_price=None, k=5):
    """
    Search for products using text query with filters.
    
    Args:
        query_text (str): Text query to search for
        document_type (str, optional): Filter by document type ("text" or "photo")
        min_price (float, optional): Minimum price filter
        max_price (float, optional): Maximum price filter
        k (int): Number of results to return
    
    Returns:
        list: List of product results with metadata
    """
    try:
        logger.info(f"Starting text search: '{query_text[:50]}...', filters: doc_type={document_type}, min_price={min_price}, max_price={max_price}, k={k}")
        
        query_emb = text_model.encode(query_text).tolist()
        logger.debug(f"Generated query embedding with {len(query_emb)} dimensions")

        filters = []
        if document_type:
            filters.append({"type": {"$eq": document_type}})
        if min_price:
            filters.append({"price": {"$gte": min_price}})
        if max_price:
            filters.append({"price": {"$lte": max_price}})
        
        # Build where_filter based on number of filters
        if not filters:
            where_filter = None  # CHANGE: Use None instead of {}
        elif len(filters) == 1:
            where_filter = filters[0]
        else:
            where_filter = {"$and": filters}
        
        logger.debug(f"Using where_filter: {where_filter}")
        
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=2 * k,  # Oversample for dedupe
            where=where_filter,
        )
        
        logger.debug(f"ChromaDB returned {len(results['ids'][0])} raw results")
        
        # Dedupe and rank by bouquet_id
        bouquet_scores = {}
        for doc_ids, distances, metadatas in zip(results['ids'], results['distances'], results['metadatas']):
            for i in range(len(doc_ids)):
                meta = metadatas[i]
                bid = meta['bouquet_id']
                score = 1 - distances[i]  # Convert distance to similarity (cosine)
                if bid not in bouquet_scores or score > bouquet_scores[bid]['score']:
                    bouquet_scores[bid] = {'score': score, 'meta': meta}
        
        top_bouquets = sorted(bouquet_scores.values(), key=lambda x: x['score'], reverse=True)[:k]
        logger.info(f"Text search completed: found {len(top_bouquets)} unique bouquets")
        return top_bouquets
        
    except Exception as e:
        logger.error(f"Error in text search: {e}", exc_info=True)
        raise

def search_products_by_photo(photo_path, min_price=None, max_price=None, k=5):
    """
    Search for products using image file with filters.
    
    Args:
        photo_path (str): Path to the image file
        min_price (float, optional): Minimum price filter
        max_price (float, optional): Maximum price filter
        k (int): Number of results to return
    
    Returns:
        list: List of product results with metadata
    """
    try:
        logger.info(f"Starting photo search: {photo_path}, filters: min_price={min_price}, max_price={max_price}, k={k}")
        
        # Load and process image
        query_image = Image.open(photo_path).convert('RGB')
        logger.debug(f"Loaded image: {query_image.size}")
        
        query_emb = image_model.encode(query_image).tolist()
        logger.debug(f"Generated image embedding with {len(query_emb)} dimensions")
        
        filters = []
        if min_price:
            filters.append({"price": {"$gte": min_price}})
        if max_price:
            filters.append({"price": {"$lte": max_price}})
        
        # Build where_filter based on number of filters
        if not filters:
            where_filter = None  # CHANGE: Use None instead of {}
        elif len(filters) == 1:
            where_filter = filters[0]
        else:
            where_filter = {"$and": filters}
        
        logger.debug(f"Using where_filter: {where_filter}")
        
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=k * 2,
            where=where_filter
        )
        
        logger.debug(f"ChromaDB returned {len(results['ids'][0])} raw results")
        
        # Similar dedupe as above, but since photo docs link to bouquets, group by bouquet_id
        bouquet_scores = {}
        for doc_ids, distances, metadatas in zip(results['ids'], results['distances'], results['metadatas']):
            for i in range(len(doc_ids)):
                meta = metadatas[i]
                bid = meta['bouquet_id']
                score = 1 - distances[i]
                if bid not in bouquet_scores or score > bouquet_scores[bid]['score']:
                    bouquet_scores[bid] = {'score': score, 'meta': meta}
        
        top_bouquets = sorted(bouquet_scores.values(), key=lambda x: x['score'], reverse=True)[:k]
        logger.info(f"Photo search completed: found {len(top_bouquets)} unique bouquets")
        return top_bouquets
        
    except Exception as e:
        logger.error(f"Error in photo search: {e}", exc_info=True)
        raise

def format_price(price):
    """Format price from smallest currency units to readable format."""
    return f"{price / 1000:.2f}"

def get_product_name(meta, language='en'):
    """Get product name in specified language."""
    name_data = meta.get('name', {})
    return name_data.get(language, name_data.get('en', 'Unknown Product'))

def get_product_description(meta, language='en'):
    """Get product description in specified language."""
    desc_data = meta.get('description', {})
    return desc_data.get(language, desc_data.get('en', 'No description available'))

def generate_payment_url(price):
    """Generate Click payment URL with the specified amount."""
    # Base URL with fixed parameters
    base_url = "https://my.click.uz/services/pay/"
    
    # Fixed parameters
    service_id = "30067"
    merchant_id = "22535"
    transaction_param = "165884"
    return_url = "https://t.me/easify_seller_bot"
    
    # Format amount to 2 decimal places
    amount = f"{price:.2f}"
    
    # Build the complete URL
    payment_url = f"{base_url}?service_id={service_id}&merchant_id={merchant_id}&amount={amount}&transaction_param={transaction_param}&return_url={return_url}"
    
    return payment_url
