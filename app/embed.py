from sentence_transformers import SentenceTransformer
import chromadb
import json  # Assuming your DB is a JSON list of bouquets
from PIL import Image
import requests
from io import BytesIO

# Load separate models
text_model = SentenceTransformer('sentence-transformers/clip-ViT-B-32-multilingual-v1')  # For text (multilingual)
image_model = SentenceTransformer('clip-ViT-B-32')  # For images (base CLIP vision)
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="bouquets")

# Load your bouquet DB (e.g., from file or API)
bouquets = json.load(open('data/bouquets.json'))  # List of dicts like your sample

def normalize_photo_url(photo_url_or_uuid):
    """
    Normalize photo URL to full URL format.
    Handles both UUID format (needs construction) and full URL format (use as-is).

    Args:
        photo_url_or_uuid: Either a UUID string or a full URL string

    Returns:
        Full URL string
    """
    if not photo_url_or_uuid:
        return None

    # If it's already a full URL (starts with http:// or https://), use it as-is
    if photo_url_or_uuid.startswith('http://') or photo_url_or_uuid.startswith('https://'):
        return photo_url_or_uuid

    # Otherwise, assume it's a UUID and construct the imagedelivery.net URL
    return f"https://imagedelivery.net/kjxkUqyuhQCleQqPHYxkVQ/{photo_url_or_uuid}/public"

def embed_text(bouquet):
    tags_en = [tag['en'] for tag in bouquet['tags']]
    text = (
        f"Bouquet Name: {bouquet['name']['en']}. "
        f"Description: {bouquet['description']['en']}. "
        f"Tags: {', '.join(tags_en)}. "
    )
    embedding = text_model.encode(text).tolist()
    doc_id = f"text_{bouquet['id']}"

    photo_url = normalize_photo_url(bouquet['photo_urls'][0]) if bouquet.get('photo_urls') else None

    metadata = {
        "bouquet_id": bouquet['id'],
        "type": "text",
        "name_en": bouquet['name']['en'],
        "description_en": bouquet['description']['en'],
        "tags_en": ', '.join(tags_en),
        "quantity": bouquet['quantity'],
        "price": bouquet['price'],
        "photo_url": photo_url,
    }
    collection.upsert(  # Use upsert for updates
        ids=[doc_id],
        embeddings=[embedding],
        # documents=[text],
        metadatas=[metadata]
    )


def embed_photo(bouquet):
    if not bouquet['photo_urls']:
        return
    photo_url_or_uuid = bouquet['photo_urls'][0]
    img_url = normalize_photo_url(photo_url_or_uuid)

    response = requests.get(img_url, timeout=30)
    image = Image.open(BytesIO(response.content)).convert('RGB')
    embedding = image_model.encode(image).tolist()  # CLIP image encoder
    doc_id = f"photo_{bouquet['id']}"

    metadata = {
        "bouquet_id": bouquet['id'],
        "type": "photo",
        "name_en": bouquet['name']['en'],
        "description_en": bouquet['description']['en'],
        "tags_en": ', '.join([tag['en'] for tag in bouquet['tags']]),
        "quantity": bouquet['quantity'],
        "price": bouquet['price'],
        "photo_url": img_url,
    }
    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        # documents=[f"Photo of {bouquet['name']['en']} bouquet"],
        metadatas=[metadata]
    )

# Batch embed
# print the progress
for i, bouquet in enumerate(bouquets):
    print(f"Embedding bouquet {i+1} of {len(bouquets)}")
    if bouquet.get('deleted_at') is None:  # Skip deleted
        embed_text(bouquet)
        embed_photo(bouquet)
