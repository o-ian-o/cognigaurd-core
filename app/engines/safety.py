import re
from sklearn.svm import LinearSVC
from sklearn.feature_extraction.text import TfidfVectorizer

class SafetyEngine:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.classifier = LinearSVC()
        
        # Mock dataset for the prototype (1 = toxic/biased, 0 = safe)
        # Expanded mock dataset for the prototype (1 = toxic/biased/unsafe, 0 = safe)
        X = [
            "You are worthless", 
            "The sales numbers look great", 
            "Steal the data", 
            "Process the invoice",
            "Enterprise fiscal projections indicate steady 12% quarter-over-quarter expansion across all key segments.",
            "Financial summary for next quarter operations looks positive."
        ]
        y = [1, 0, 1, 0, 0, 0]
        self.vectorizer.fit(X)
        self.classifier.fit(self.vectorizer.transform(X), y)

    def scan(self, text: str) -> dict:
        # Instantly detect PII leaks (e.g., Credit Card numbers)
        if re.search(r'\b\d{16}\b', text): 
            return {"status": "block", "reason": "PII Leak Detected"}
        
        # Detect subtle bias or toxic responses
        vec = self.vectorizer.transform([text])
        if self.classifier.predict(vec)[0] == 1:
            return {"status": "escalate", "reason": "Policy Violation - Requires Human Review"}
            
        return {"status": "pass"}