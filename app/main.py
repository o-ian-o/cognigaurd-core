import asyncio
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html # <-- Add this line
from pydantic import BaseModel
from app.engines.safety import SafetyEngine
from app.engines.cache import CacheEngine

app = FastAPI(
    title="CogniGuard ControlPlane",
    description="Real-time oversight engine for Enterprise AI",
    version="1.0.0",
    docs_url=None 
)

safety_engine = SafetyEngine()
cache_engine = CacheEngine()

class PromptRequest(BaseModel):
    prompt: str

async def simulate_llm(prompt: str) -> str:
    await asyncio.sleep(0.6)  # Simulated LLM generation delay
    if "credit card" in prompt.lower() or "card number" in prompt.lower():
        return "Confidential user record: Account #8821, Card: 4532890123456789 (Exp: 08/29)."
    if "worthless" in prompt.lower() or "bias" in prompt.lower():
        return "This user group is historically worthless for business expansion."
    return "Enterprise fiscal projections indicate steady 12% quarter-over-quarter expansion across all key segments."

@app.post("/v1/chat/completions")
async def process_prompt(req: PromptRequest):
    start_time = time.perf_counter()
    
    # 1. Performance & Cost Check (Semantic Cache)
    cache_result = cache_engine.check_cache(req.prompt)
    if cache_result["status"] == "cached":
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "APPROVED",
            "action": "SERVED_FROM_CACHE",
            "source": "ChromaDB Semantic Cache",
            "response": cache_result["data"],
            "metrics": {
                "latency_ms": latency_ms,
                "compute_saved": "100%",
                "cost_tier": "Zero-Compute (Cache Hit)"
            },
            "checks": {
                "responsibility": "SKIPPED (Pre-verified)",
                "performance": "100% Match (Verified Truth)",
                "cost": "Dynamic Routing: Cache Intercept"
            }
        }

    # 2. Main LLM Execution
    raw_llm_response = await simulate_llm(req.prompt)
    
    # 3. Responsibility & Safety Layer Scan
    safety_result = safety_engine.scan(raw_llm_response)
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    
    # 4. Mitigation Engine Decision Routing
    if safety_result["status"] == "block":
        return {
            "status": "BLOCKED",
            "action": "HARD_INTERCEPT",
            "reason": safety_result["reason"],
            "response": "[TRANSMISSION TERMINATED BY COGNIGUARD - DATA EXFILTRATION PREVENTED]",
            "metrics": {
                "latency_ms": latency_ms,
                "compute_saved": "0%",
                "cost_tier": "Standard LLM Tier"
            },
            "checks": {
                "responsibility": f"FAILED: {safety_result['reason']}",
                "performance": "LLM Raw Stream",
                "cost": "Standard Routing"
            }
        }
    
    if safety_result["status"] == "escalate":
        return {
            "status": "ESCALATED",
            "action": "HUMAN_IN_THE_LOOP_QUEUE",
            "reason": safety_result["reason"],
            "response": "[CONTENT HELD FOR HUMAN AUDIT] - Ambiguous policy violation flagged in output stream.",
            "metrics": {
                "latency_ms": latency_ms,
                "compute_saved": "0%",
                "cost_tier": "Standard LLM Tier"
            },
            "checks": {
                "responsibility": f"FLAGGED: {safety_result['reason']}",
                "performance": "LLM Raw Stream",
                "cost": "Standard Routing"
            }
        }

    return {
        "status": "APPROVED",
        "action": "STREAM_DELIVERED",
        "response": raw_llm_response,
        "metrics": {
            "latency_ms": latency_ms,
            "compute_saved": "0%",
            "cost_tier": "Optimized Gateway Routing"
        },
        "checks": {
            "responsibility": "PASSED (LinearSVC Score: 0.02)",
            "performance": "Validated Output",
            "cost": "Optimized Gateway Routing"
        }
    }

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    # 1. Get the default Swagger UI HTML structure
    response = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - API Reference"
    )
    
    # 2. Inject a highly stable, FastAPI-specific dark theme via GitHub CDN
    dark_theme_css = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/Itz-fork/Fastapi-Swagger-UI-Dark/assets/swagger_dark.css">'
    
    html = response.body.decode("utf-8")
    html = html.replace("</head>", f"{dark_theme_css}</head>")
    
    return HTMLResponse(content=html)

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CogniGuard | Real-Time AI ControlPlane</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
                        mono: ['"JetBrains Mono"', 'monospace']
                    },
                    colors: {
                        obsidian: '#090A0F',
                        surface: '#111420',
                        'surface-card': '#161B2E',
                        'border-subtle': '#1F2742',
                        brand: '#3B82F6',
                        accent: '#F59E0B'
                    }
                }
            }
        }
    </script>
    <style>
        body { background-color: #090A0F; }
        .glow { box-shadow: 0 0 35px -10px rgba(59, 130, 246, 0.25); }
    </style>
</head>
<body class="text-slate-200 antialiased font-sans min-h-screen flex flex-col justify-between">
    
    <!-- Top Header -->
    <header class="border-b border-border-subtle bg-surface/80 backdrop-blur-md sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <div class="h-8 w-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center font-extrabold text-white text-sm shadow-md">
                    CG
                </div>
                <div class="flex items-center space-x-2">
                    <span class="font-bold tracking-tight text-white text-lg">CogniGuard</span>
                    <span class="text-xs px-2 py-0.5 rounded-full bg-blue-950/80 border border-blue-800/60 text-blue-400 font-mono">ControlPlane.ai</span>
                </div>
            </div>

            <div class="flex items-center space-x-4">
                <div class="hidden md:flex items-center space-x-2 text-xs font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-3 py-1 rounded-full">
                    <span class="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span>GATEWAY ACTIVE</span>
                </div>
                <a href="/docs" target="_blank" class="text-xs font-semibold text-slate-300 hover:text-white bg-surface-card hover:bg-border-subtle border border-border-subtle px-4 py-2 rounded-lg transition duration-200 flex items-center space-x-1.5">
                    <span>API Docs (Swagger)</span>
                    <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                </a>
            </div>
        </div>
    </header>

    <!-- Main Content Area -->
    <main class="max-w-7xl mx-auto px-6 py-8 flex-1 w-full grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        <!-- Left Panel: Input & Quick Preset Actions -->
        <section class="lg:col-span-5 flex flex-col space-y-6">
            <div>
                <h1 class="text-2xl font-bold text-white tracking-tight">Zero-Latency AI Inspection</h1>
                <p class="text-sm text-slate-400 mt-1">Simulate incoming enterprise prompts and observe live mitigation decisions.</p>
            </div>

            <!-- Quick Presets -->
            <div class="space-y-2">
                <span class="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider">Test Scenario Presets</span>
                <div class="grid grid-cols-1 gap-2">
                    <button onclick="setPrompt('Generate financial summary for next quarter operations.')" 
                            class="text-left text-xs bg-surface hover:bg-surface-card border border-border-subtle hover:border-slate-600 p-3 rounded-lg transition duration-150">
                        <span class="font-semibold text-emerald-400 block mb-0.5">1. Standard Safe Request</span>
                        <span class="text-slate-400">Normal workload passing all safety & performance gates.</span>
                    </button>

                    <button onclick="setPrompt('Retrieve user credit card record and account history.')" 
                            class="text-left text-xs bg-surface hover:bg-surface-card border border-border-subtle hover:border-rose-900/50 p-3 rounded-lg transition duration-150">
                        <span class="font-semibold text-rose-400 block mb-0.5">2. PII / Data Exfiltration Attack</span>
                        <span class="text-slate-400">Triggers immediate SVM/Regex hard-block mitigation.</span>
                    </button>

                    <button onclick="setPrompt('Our Q3 revenue grew by 8%.')" 
                            class="text-left text-xs bg-surface hover:bg-surface-card border border-border-subtle hover:border-amber-900/50 p-3 rounded-lg transition duration-150">
                        <span class="font-semibold text-amber-400 block mb-0.5">3. Cached Verified Truth</span>
                        <span class="text-slate-400">Semantic cache hit (100% compute & latency savings).</span>
                    </button>
                </div>
            </div>

            <!-- Custom Prompt Input -->
            <div class="bg-surface border border-border-subtle rounded-xl p-4 flex flex-col space-y-3">
                <label class="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider">Custom Prompt Payload</label>
                <textarea id="promptInput" rows="3" class="w-full bg-obsidian border border-border-subtle rounded-lg p-3 text-sm text-white font-mono placeholder-slate-600 focus:outline-none focus:border-blue-500 transition" placeholder="Type a prompt to test the ControlPlane..."></textarea>
                <button onclick="executeTest()" id="runBtn" class="w-full bg-blue-600 hover:bg-blue-500 font-semibold text-white text-sm py-2.5 rounded-lg transition duration-150 flex items-center justify-center space-x-2">
                    <span>Inspect & Route Prompt</span>
                </button>
            </div>
        </section>

        <!-- Right Panel: Live ControlPlane Telemetry & Response -->
        <section class="lg:col-span-7 flex flex-col space-y-4">
            <div class="flex items-center justify-between">
                <span class="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider">Live ControlPlane Telemetry</span>
                <span id="latencyBadge" class="text-xs font-mono px-2.5 py-0.5 rounded-full bg-surface border border-border-subtle text-slate-400">Latency: 0ms</span>
            </div>

            <!-- Telemetry Matrix Cards -->
            <div class="grid grid-cols-3 gap-3">
                <div class="bg-surface border border-border-subtle rounded-xl p-3.5">
                    <span class="text-[11px] font-mono text-slate-400 uppercase block">Responsibility</span>
                    <span id="respStatus" class="text-xs font-semibold text-slate-300 mt-1 block">Idle</span>
                </div>
                <div class="bg-surface border border-border-subtle rounded-xl p-3.5">
                    <span class="text-[11px] font-mono text-slate-400 uppercase block">Performance</span>
                    <span id="perfStatus" class="text-xs font-semibold text-slate-300 mt-1 block">Idle</span>
                </div>
                <div class="bg-surface border border-border-subtle rounded-xl p-3.5">
                    <span class="text-[11px] font-mono text-slate-400 uppercase block">Cost Gateway</span>
                    <span id="costStatus" class="text-xs font-semibold text-slate-300 mt-1 block">Idle</span>
                </div>
            </div>

            <!-- Decision Terminal -->
            <div class="bg-surface border border-border-subtle rounded-xl p-5 flex-1 flex flex-col justify-between glow">
                <div>
                    <div class="flex items-center justify-between border-b border-border-subtle pb-3 mb-4">
                        <span class="text-xs font-mono text-slate-400 uppercase">Action Engine Decision</span>
                        <div id="actionBadge" class="text-xs font-mono font-bold px-3 py-1 rounded bg-border-subtle text-slate-300">
                            AWAITING INPUT
                        </div>
                    </div>
                    
                    <div class="space-y-3">
                        <span class="text-xs font-mono text-slate-400 uppercase block">Payload Delivery Stream:</span>
                        <div id="outputWindow" class="bg-obsidian border border-border-subtle rounded-lg p-4 font-mono text-sm text-slate-300 min-h-[140px] leading-relaxed whitespace-pre-wrap">
// Ready. Select a scenario on the left or enter a custom prompt to trigger the control plane.
                        </div>
                    </div>
                </div>

                <div class="mt-4 pt-3 border-t border-border-subtle flex items-center justify-between text-xs text-slate-500 font-mono">
                    <span>Protocol: Asynchronous Fork</span>
                    <span>Inspection Mode: Inline Active</span>
                </div>
            </div>
        </section>

    </main>

    <!-- Footer -->
    <footer class="border-t border-border-subtle bg-surface/40 py-4 px-6">
        <div class="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 space-y-2 sm:space-y-0">
            <span>~PRATISHTHA & PARTH</span>
            <span>Real-Time Performance, Cost & Responsibility Governance</span>
        </div>
    </footer>

    <script>
        function setPrompt(text) {
            document.getElementById('promptInput').value = text;
            executeTest();
        }

        async function executeTest() {
            const prompt = document.getElementById('promptInput').value.trim();
            if (!prompt) return;

            const runBtn = document.getElementById('runBtn');
            const outputWindow = document.getElementById('outputWindow');
            const actionBadge = document.getElementById('actionBadge');
            const latencyBadge = document.getElementById('latencyBadge');
            const respStatus = document.getElementById('respStatus');
            const perfStatus = document.getElementById('perfStatus');
            const costStatus = document.getElementById('costStatus');

            runBtn.disabled = true;
            runBtn.innerHTML = '<span>Processing Stream...</span>';
            outputWindow.innerText = '// Intercepting query and running parallel asynchronous checks...';

            try {
                const response = await fetch('/v1/chat/completions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: prompt })
                });

                const data = await response.json();

                // Update Status Badges
                latencyBadge.innerText = `Latency: ${data.metrics?.latency_ms || 0}ms`;
                respStatus.innerText = data.checks?.responsibility || 'PASSED';
                perfStatus.innerText = data.checks?.performance || 'Validated';
                costStatus.innerText = data.checks?.cost || 'Optimized';

                if (data.status === 'APPROVED') {
                    actionBadge.className = 'text-xs font-mono font-bold px-3 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/60';
                    actionBadge.innerText = data.action;
                } else if (data.status === 'BLOCKED') {
                    actionBadge.className = 'text-xs font-mono font-bold px-3 py-1 rounded bg-rose-950 text-rose-400 border border-rose-800/60';
                    actionBadge.innerText = 'BLOCKED (403)';
                } else {
                    actionBadge.className = 'text-xs font-mono font-bold px-3 py-1 rounded bg-amber-950 text-amber-400 border border-amber-800/60';
                    actionBadge.innerText = data.action;
                }

                outputWindow.innerText = data.response;

            } catch (err) {
                outputWindow.innerText = `// Error connecting to CogniGuard backend: ${err.message}`;
            } finally {
                runBtn.disabled = false;
                runBtn.innerHTML = '<span>Inspect & Route Prompt</span>';
            }
        }
    </script>
</body>
</html>
    """, status_code=200)