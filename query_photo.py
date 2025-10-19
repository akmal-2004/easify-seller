from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import json  # Assuming your DB is a JSON list of bouquets
import requests
from PIL import Image
from io import BytesIO

image_model = SentenceTransformer('clip-ViT-B-32')  # For images (base CLIP vision)
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="bouquets")

def photo_query(image_url, min_price=None, max_price=None, k=5):
    response = requests.get(image_url)
    query_image = Image.open(BytesIO(response.content)).convert('RGB')
    query_emb = image_model.encode(query_image).tolist()
    
    filters = []
    if min_price:
        filters.append({"price": {"$gte": min_price}})
    if max_price:
        filters.append({"price": {"$lte": max_price}})
    
    # Build where_filter based on number of filters
    if not filters:
        where_filter = {}
    elif len(filters) == 1:
        where_filter = filters[0]
    else:
        where_filter = {"$and": filters}
    
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=k * 2,
        where=where_filter
    )
    
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
    return top_bouquets

res = photo_query("https://imagedelivery.net/kjxkUqyuhQCleQqPHYxkVQ/a06ae574-f1a1-4a29-cc86-7a8249d97a00/public", None, None, 5)
print(json.dumps(res, indent=4))
