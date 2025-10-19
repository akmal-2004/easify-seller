from sentence_transformers import SentenceTransformer
import chromadb
import json  # Assuming your DB is a JSON list of bouquets

text_model = SentenceTransformer('sentence-transformers/clip-ViT-B-32-multilingual-v1')  # Multilingual CLIP
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="bouquets")

def text_query(query_text, document_type=None, min_price=None, max_price=None, k=5):
    query_emb = text_model.encode(query_text).tolist()

    filters = []
    if document_type:
        filters.append({"type": {"$eq": document_type}})
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
        n_results=2 * k,  # Oversample for dedupe
        where=where_filter,
    )
    
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
    # Fetch full bouquet JSONs from your DB using [item['meta']['bouquet_id'] for item in top_bouquets]
    return top_bouquets  # Or enriched with full data


res = text_query("bouquet full of white roses", "text", None, None, 5)
print(json.dumps(res, indent=4))
