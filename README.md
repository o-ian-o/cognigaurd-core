# CogniGuard ControlPlane
## ENTERPRISE AI GOVERNANCE & INSPECTION MIDDLEWARE

CogniGuard ControlPlane is a high-performance middleware designed to govern, inspect, and route Enterprise Al prompts in real-time. Operating as an intelligent gateway, it evaluates Large Language Model (LLM) interactions against customizable safety policies, actively detecting Personally Identifiable Information (PII) leaks, mitigating hallucinations, and filtering biased or toxic content with minimal latency overhead.

### Key Capabilities
* Dynamic Policy Governance: Enables seamless transitions between zero-downtime profiles (e.g., Customer-Facing, Internal Copilot, Batch Processing) with highly configurable latency budgets and risk tolerance parameters.
* Semantic Caching & Hallucination Prevention: Intercepts unverified metrics utilizing a ChromaDB-powered vector cache to deliver verified truths instantaneously, thereby eliminating compute costs on cache hits.
* Live PII Redaction: Instantly identifies and sanitizes sensitive data payloads (e.g., financial records, identification numbers) via high-speed pattern recognition before transmission outside the enterprise network.
* Bias & Toxicity Filtering: Deploys an advanced machine learning classifier (TF-IDF coupled with LinearSVC) to systematically detect and escalate ambiguous or unsafe content for mandatory human review.
* Real-Time Telemetry Dashboard: Provides a zero-dependency control interface to simulate high-throughput workloads, monitor inspection latency overheads, and visualize policy enforcements dynamically.

### Solution Architecture
CogniGuard is engineered upon a decoupled, modular architecture to maximize both throughput and systemic extensibility.
* Core API Gateway: Engineered via FastAPI, this foundational layer manages asynchronous prompt routing, policy enforcement orchestration, and hosts the interactive user interface.
* Safety Engine: The primary defense layer utilizing Scikit-learn to vectorize text and classify intent via a Support Vector Machine (SVM). This module concurrently manages regex-based PII interception algorithms.
* Cache Engine: Leverages ChromaDB to sustain a localized collection of verified baseline responses. It executes similarity searches to immediately furnish safe, cached resolutions for standard inquiries.
* Policy Engine: A Singleton configuration manager retaining the active governance profile and individual module overrides, allowing the platform to adapt enforcement strictness (Block, Redact, Escalate) without requiring service interruptions.

### Implementation Methodology
The system enforces Al governance via a "Gatekeeper Proxy" methodology:
* Asynchronous Processing: Utilizes Python's asyncio framework and FastAPI to ensure the proxy layer does not bottleneck the underlying LLM data stream.
* Tiered Inspection Pipeline: Prompts are subjected to a rigorous multi-stage pipeline:
  * Stage 1: Semantic Cache Check for cost and latency optimization.
  * Stage 2: Simulated LLM Execution.
  * Stage 3: Hallucination and Fact-Checking validation.
  * Stage 4: Responsibility and Safety Layer Scan for Pll and Toxicity.
* Action Engine Decisions: Predicated on the active policy, detected violations dynamically trigger protocol actions such as AUTO_REDACTED, HARD_INTERCEPT, HUMAN_IN_THE_LOOP_QUEUE, or STREAM_DELIVERED.

### Technical Dependencies
The architecture relies on a highly optimized Python technology stack:
* FastAPI & Uvicorn: High-performance web framework and ASGI server for the core proxy and API documentation.
* Pydantic: Strict data validation and settings management.
* ChromaDB: Localized vector database for rapid semantic caching operations.
* Scikit-learn: Machine learning library deployed for the training and execution of the bias/ toxicity classifier.
* Tailwind CSS: Client-side styling for the real-time telemetry dashboard.

### Execution Instructions

#### 1. System Prerequisites
Ensure a Python environment (version 3.9 or higher) is configured on the host machine.

#### 2. Installation Guide
Clone the project repository and initialize the requisite dependencies:
```bash
git clone [repository-url]
cd cogniguard-core
python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate
pip install fastapi uvicorn pydantic chromadb scikit-learn
```

#### 3. Server Initialization
Launch the ControlPlane proxy application utilizing Uvicorn:
```bash
uvicorn app.main: appreloadport 8000
```

#### 4. Platform Access
* Live Dashboard: http://localhost:8000/
* Policy Configuration: http://localhost:8000/policy
* API Documentation: http://localhost:8000/docs

Contributors: Parth, Pratishtha
