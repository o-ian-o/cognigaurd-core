import chromadb

class CacheEngine:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.create_collection("verified_responses")
        
        # Pre-load verified truth to stop hallucinations
        self.collection.add(
            documents=["Our Q3 revenue grew by 8%.", "The API rate limit is 1000 requests/min."],
            metadatas=[{"verified": True}, {"verified": True}],
            ids=["q3_rev", "api_limit"]
        )

    def check_cache(self, query: str):
        results = self.collection.query(query_texts=[query], n_results=1)
        # If the query is highly similar to a verified truth, return it
        if results['distances'][0] and results['distances'][0][0] < 0.5: 
            return {"status": "cached", "data": results['documents'][0][0]}
        return {"status": "miss"}