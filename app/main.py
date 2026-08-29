import asyncio
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html
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
    await asyncio.sleep(0.6)  
    if "credit card" in prompt.lower() or "card number" in prompt.lower():
        return "Confidential user record: Account #8821, Card: 4532890123456789 (Exp: 08/29)."
    if "worthless" in prompt.lower() or "bias" in prompt.lower():
        return "This user group is historically worthless for business expansion."
    if "competitor" in prompt.lower() or "churn" in prompt.lower():
        return "Our platform is expanding, but internal churn reached 42% last month after the competitor launch."
    return "Enterprise fiscal projections indicate steady 12% quarter-over-quarter expansion across all key segments."

@app.post("/v1/chat/completions")
async def process_prompt(req: PromptRequest):
    start_time = time.perf_counter()
    
    # 1. Performance & Cost Check
    cache_result = cache_engine.check_cache(req.prompt)
    if cache_result["status"] == "cached":
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "APPROVED",
            "action": "SERVED_FROM_CACHE",
            "response": cache_result["data"],
            "metrics": {"latency_ms": latency_ms, "inspection_ms": 0, "compute_saved": "100%", "cost_tier": "Zero-Compute"},
            "checks": {"responsibility": "SKIPPED", "performance": "100% Match", "cost": "Cache Intercept"}
        }

    # 2. Main LLM Execution
    llm_start = time.perf_counter()
    raw_llm_response = await simulate_llm(req.prompt)
    
    # 3. LIVE REDACTION ENGINE (The Winning Feature)
    inspect_start = time.perf_counter()
    if "42%" in raw_llm_response:
        redacted_response = raw_llm_response.replace("42%", "[REDACTED: UNVERIFIED INTERNAL METRIC]")
        inspection_ms = round((time.perf_counter() - inspect_start) * 1000, 2)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "EDITED",
            "action": "AUTO_REDACTED",
            "response": redacted_response,
            "metrics": {"latency_ms": latency_ms, "inspection_ms": inspection_ms, "compute_saved": "0%", "cost_tier": "Standard LLM Tier"},
            "checks": {
                "responsibility": "PASSED (Scrubbed)", 
                "performance": "MINOR HALLUCINATION REPAIRED", 
                "cost": "Standard Routing"
            }
        }

    # 4. Responsibility & Safety Layer Scan
    safety_result = safety_engine.scan(raw_llm_response)
    inspection_ms = round((time.perf_counter() - inspect_start) * 1000, 2)
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    
    # 5. Mitigation Engine Decision Routing
    if safety_result["status"] == "block":
        return {
            "status": "BLOCKED",
            "action": "HARD_INTERCEPT",
            "response": "[TRANSMISSION TERMINATED BY COGNIGUARD - DATA EXFILTRATION PREVENTED]",
            "metrics": {"latency_ms": latency_ms, "inspection_ms": inspection_ms, "compute_saved": "0%", "cost_tier": "Standard Tier"},
            "checks": {"responsibility": f"FAILED: {safety_result['reason']}", "performance": "Stream Halted", "cost": "Standard"}
        }
    
    if safety_result["status"] == "escalate":
        return {
            "status": "ESCALATED",
            "action": "HUMAN_IN_THE_LOOP_QUEUE",
            "response": "[CONTENT HELD FOR HUMAN AUDIT] - Ambiguous policy violation flagged.",
            "metrics": {"latency_ms": latency_ms, "inspection_ms": inspection_ms, "compute_saved": "0%", "cost_tier": "Standard Tier"},
            "checks": {"responsibility": f"FLAGGED: {safety_result['reason']}", "performance": "Stream Paused", "cost": "Standard"}
        }

    return {
        "status": "APPROVED",
        "action": "STREAM_DELIVERED",
        "response": raw_llm_response,
        "metrics": {"latency_ms": latency_ms, "inspection_ms": inspection_ms, "compute_saved": "0%", "cost_tier": "Optimized Gateway Routing"},
        "checks": {"responsibility": "PASSED", "performance": "Validated Output", "cost": "Optimized Routing"}
    }

@app.get("/docs", include_in_schema=False)
@app.get("/api-docs", include_in_schema=False)
async def custom_swagger_ui_html():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>CogniGuard API Reference</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        
        <style>
            /* Base Typography */
            body { font-family: 'Plus Jakarta Sans', sans-serif !important; }
            code, pre, .scalar-api-reference .scalar-mono { font-family: 'JetBrains Mono', monospace !important; }

            /* 
             * COGNIGUARD PREMIUM THEME SYSTEM
             * Completely overrides Scalar's default tokens for a bespoke feel.
             */
            
            /* --- LIGHT MODE (Premium Beige & Indigo) --- */
            body.light-mode, .light-mode .scalar-api-reference {
                --theme-color-1: #4F46E5 !important; /* Premium Indigo */
                --theme-color-2: #1E293B !important; 
                --theme-color-3: #475569 !important; 
                
                --theme-background-1: #FAFAFA !important; /* Crisp White/Gray */
                --theme-background-2: #F8F6F0 !important; /* Very Light Beige Sidebar */
                --theme-background-3: #E2E8F0 !important; 
                
                --theme-border-color: #E2E8F0 !important;
            }

            /* --- DARK MODE (Obsidian & Blue) --- */
            body.dark-mode, .dark-mode .scalar-api-reference {
                --theme-color-1: #3B82F6 !important; /* Vibrant Blue */
                --theme-color-2: #F8FAFC !important;
                --theme-color-3: #94A3B8 !important;
                
                --theme-background-1: #090A0F !important; /* Obsidian */
                --theme-background-2: #111420 !important; /* Surface */
                --theme-background-3: #161B2E !important; /* Surface Card */
                
                --theme-border-color: #1F2742 !important;
            }

            /* Custom Badges (v1.0.0, OAS 3.1) - Solid & Premium */
            .scalar-api-reference a[target="_blank"],
            .scalar-api-reference a[href$=".json"] {
                background-color: #4F46E5 !important;
                color: white !important;
                border: none !important;
                font-weight: 600 !important;
                border-radius: 6px !important;
                padding: 4px 10px !important;
                transition: all 0.2s ease !important;
                box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.3) !important;
            }

            /* Hover effects for badges */
            .light-mode .scalar-api-reference a[target="_blank"]:hover,
            .light-mode .scalar-api-reference a[href$=".json"]:hover,
            .dark-mode .scalar-api-reference a[target="_blank"]:hover,
            .dark-mode .scalar-api-reference a[href$=".json"]:hover {
                background-color: #4338CA !important;
                transform: translateY(-2px) !important;
                box-shadow: 0 6px 8px -1px rgba(79, 70, 229, 0.4) !important;
            }
        </style>
    </head>
    <body>
        <!-- Scalar injects the UI here -->
        <script 
            id="api-reference" 
            data-url="/openapi.json"
            data-theme="moon"
            data-layout="modern">
        </script>
        
        <!-- Load the Scalar JS standalone build -->
        <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

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
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <script>
        tailwind.config = { theme: { extend: { fontFamily: { sans: ['"Plus Jakarta Sans"'], mono: ['"JetBrains Mono"'] }, colors: { obsidian: '#090A0F', surface: '#111420', 'surface-card': '#161B2E', 'border-subtle': '#1F2742' } } } }
    </script>
    <style>
        body { background-color: #090A0F; } .glow { box-shadow: 0 0 35px -10px rgba(59, 130, 246, 0.25); }
        .gauge-track { background: #1F2742; border-radius: 9999px; height: 8px; overflow: hidden; position: relative; }
        .gauge-fill { height: 100%; border-radius: 9999px; width: 0%; transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1), background-color 0.4s ease; }
        .gauge-fill.safe    { background: linear-gradient(90deg, #059669, #10B981); }
        .gauge-fill.warn    { background: linear-gradient(90deg, #D97706, #F59E0B); }
        .gauge-fill.danger  { background: linear-gradient(90deg, #DC2626, #EF4444); }
        @keyframes pulse-dot { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        .scanning-dot { animation: pulse-dot 1.2s ease-in-out infinite; }
    </style>
</head>
<body class="text-slate-200 antialiased font-sans min-h-screen flex flex-col justify-between">
    
    <header class="border-b border-border-subtle bg-surface/80 backdrop-blur-md sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <div class="h-8 w-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center font-extrabold text-white text-sm">CG</div>
                <div class="flex items-center space-x-2"><span class="font-bold text-white text-lg">CogniGuard</span><span class="text-xs px-2 py-0.5 rounded-full bg-blue-950/80 border border-blue-800/60 text-blue-400 font-mono">ControlPlane.ai</span></div>
            </div>
            <div class="flex items-center space-x-4">
                <a href="/docs" target="_blank" class="text-xs font-semibold text-slate-300 hover:text-white bg-surface-card hover:bg-border-subtle border border-border-subtle px-4 py-2 rounded-lg transition">API Docs (Swagger)</a>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 py-8 flex-1 w-full grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        <section class="lg:col-span-5 flex flex-col space-y-6">
            <div>
                <h1 class="text-2xl font-bold text-white tracking-tight">Zero-Latency AI Inspection</h1>
                <p class="text-sm text-slate-400 mt-1">Simulate incoming enterprise prompts and observe live mitigation decisions.</p>
            </div>

            <div class="space-y-2">
                <span class="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider">Test Scenario Presets</span>
                <div class="grid grid-cols-1 gap-2">
                    <button onclick="setPrompt('Generate financial summary for next quarter operations.')" class="text-left text-xs bg-surface border border-border-subtle hover:border-slate-600 p-3 rounded-lg transition">
                        <span class="font-semibold text-emerald-400 block mb-0.5">1. Standard Safe Request</span><span class="text-slate-400">Normal workload passing all gates.</span>
                    </button>
                    <button onclick="setPrompt('Retrieve user credit card record and account history.')" class="text-left text-xs bg-surface border border-border-subtle hover:border-rose-900/50 p-3 rounded-lg transition">
                        <span class="font-semibold text-rose-400 block mb-0.5">2. PII Attack (BLOCK)</span><span class="text-slate-400">Triggers immediate hard-block mitigation.</span>
                    </button>
                    <button onclick="setPrompt('What is the internal churn rate regarding the competitor launch?')" class="text-left text-xs bg-surface border border-border-subtle hover:border-indigo-900/50 p-3 rounded-lg transition">
                        <span class="font-semibold text-indigo-400 block mb-0.5">3. Live Hallucination (EDIT)</span><span class="text-slate-400">Auto-redacts unverified metric, delivers the rest.</span>
                    </button>
                    <button onclick="setPrompt('Our Q3 revenue grew by 8%.')" class="text-left text-xs bg-surface border border-border-subtle hover:border-amber-900/50 p-3 rounded-lg transition">
                        <span class="font-semibold text-amber-400 block mb-0.5">4. Cached Verified Truth</span><span class="text-slate-400">Semantic cache hit (100% compute savings).</span>
                    </button>
                </div>
            </div>

            <div class="bg-surface border border-border-subtle rounded-xl p-4 flex flex-col space-y-3">
                <textarea id="promptInput" rows="3" class="w-full bg-obsidian border border-border-subtle rounded-lg p-3 text-sm text-white font-mono placeholder-slate-600 focus:outline-none focus:border-blue-500" placeholder="Type a prompt..."></textarea>
                <button onclick="executeTest()" id="runBtn" class="w-full bg-blue-600 hover:bg-blue-500 font-semibold text-white text-sm py-2.5 rounded-lg transition">Inspect & Route Prompt</button>
            </div>
        </section>

        <section class="lg:col-span-7 flex flex-col space-y-4">
            <div class="flex items-center justify-between">
                <span class="text-xs font-mono font-medium text-slate-400 uppercase">Live Telemetry</span>
                <span id="latencyBadge" class="text-xs font-mono px-2.5 py-0.5 rounded-full bg-surface border border-border-subtle text-slate-400">Latency: 0ms</span>
            </div>

            <div class="grid grid-cols-3 gap-3">
                <div class="bg-surface border border-border-subtle rounded-xl p-3.5"><span class="text-[11px] font-mono text-slate-400 uppercase block">Responsibility</span><span id="respStatus" class="text-xs font-semibold text-slate-300 mt-1 block">Idle</span></div>
                <div class="bg-surface border border-border-subtle rounded-xl p-3.5"><span class="text-[11px] font-mono text-slate-400 uppercase block">Performance</span><span id="perfStatus" class="text-xs font-semibold text-slate-300 mt-1 block">Idle</span></div>
                <div class="bg-surface border border-border-subtle rounded-xl p-3.5"><span class="text-[11px] font-mono text-slate-400 uppercase block">Cost Gateway</span><span id="costStatus" class="text-xs font-semibold text-slate-300 mt-1 block">Idle</span></div>
            </div>

            <!-- Latency Budget Gauge -->
            <div class="bg-surface border border-border-subtle rounded-xl p-4">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center space-x-2">
                        <span id="gaugeDot" class="h-1.5 w-1.5 rounded-full bg-slate-500"></span>
                        <span class="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Inspection Overhead</span>
                        <span class="text-[10px] font-mono text-slate-600 border border-border-subtle px-1.5 py-0.5 rounded">vs 50ms Budget</span>
                    </div>
                    <div class="flex items-center space-x-3">
                        <span id="gaugeLabel" class="text-xs font-mono text-slate-500">—</span>
                        <span id="gaugePct" class="text-xs font-mono font-bold text-slate-500">—</span>
                    </div>
                </div>
                <div class="gauge-track"><div id="gaugeFill" class="gauge-fill"></div></div>
                <div class="flex justify-between mt-1.5">
                    <span class="text-[10px] font-mono text-slate-600">0ms</span>
                    <span class="text-[10px] font-mono text-slate-600">50ms threshold</span>
                </div>
            </div>

            <div class="bg-surface border border-border-subtle rounded-xl p-5 flex-1 flex flex-col justify-between glow">
                <div>
                    <div class="flex items-center justify-between border-b border-border-subtle pb-3 mb-4">
                        <span class="text-xs font-mono text-slate-400 uppercase">Action Engine Decision</span>
                        <div id="actionBadge" class="text-xs font-mono font-bold px-3 py-1 rounded bg-border-subtle text-slate-300">AWAITING INPUT</div>
                    </div>
                    <div class="space-y-3">
                        <span class="text-xs font-mono text-slate-400 uppercase block">Payload Delivery Stream:</span>
                        <div id="outputWindow" class="bg-obsidian border border-border-subtle rounded-lg p-4 font-mono text-sm text-slate-300 min-h-[140px] leading-relaxed whitespace-pre-wrap">// Ready. Select a scenario on the left.</div>
                    </div>
                </div>
            </div>
        </section>

    </main>
    <footer class="border-t border-border-subtle bg-surface/40 py-4 px-6 text-xs text-slate-500 text-center">~PRATISHTHA & PARTH | CogniGuard ControlPlane</footer>

    <script>
        function setPrompt(text) { document.getElementById('promptInput').value = text; executeTest(); }
        async function executeTest() {
            const prompt = document.getElementById('promptInput').value.trim();
            if (!prompt) return;
            const runBtn = document.getElementById('runBtn');
            const outputWindow = document.getElementById('outputWindow');
            const actionBadge = document.getElementById('actionBadge');
            
            runBtn.disabled = true; runBtn.innerText = 'Processing...';
            outputWindow.innerText = '// Intercepting query...';

            try {
                const response = await fetch('/v1/chat/completions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt }) });
                const data = await response.json();

                const latencyMs = data.metrics?.latency_ms || 0;
                const inspectionMs = data.metrics?.inspection_ms || 0;
                document.getElementById('latencyBadge').innerText = `Total: ${latencyMs}ms`;
                document.getElementById('respStatus').innerText = data.checks?.responsibility || 'PASSED';
                document.getElementById('perfStatus').innerText = data.checks?.performance || 'Validated';
                document.getElementById('costStatus').innerText = data.checks?.cost || 'Optimized';

                const BUDGET_MS = 50;
                const gaugeFill = document.getElementById('gaugeFill');
                const gaugeLabel = document.getElementById('gaugeLabel');
                const gaugePct = document.getElementById('gaugePct');
                const gaugeDot = document.getElementById('gaugeDot');

                const pct = Math.min((inspectionMs / BUDGET_MS) * 100, 100);
                const remaining = Math.max(BUDGET_MS - inspectionMs, 0).toFixed(2);

                gaugeFill.style.width = '0%';
                gaugeFill.className = 'gauge-fill';

                setTimeout(() => {
                    gaugeFill.style.width = pct + '%';
                    if (pct < 50) {
                        gaugeFill.classList.add('safe');
                        gaugeDot.className = 'h-1.5 w-1.5 rounded-full bg-emerald-400 scanning-dot';
                        gaugePct.className = 'text-xs font-mono font-bold text-emerald-400';
                    } else if (pct < 80) {
                        gaugeFill.classList.add('warn');
                        gaugeDot.className = 'h-1.5 w-1.5 rounded-full bg-amber-400 scanning-dot';
                        gaugePct.className = 'text-xs font-mono font-bold text-amber-400';
                    } else {
                        gaugeFill.classList.add('danger');
                        gaugeDot.className = 'h-1.5 w-1.5 rounded-full bg-rose-400 scanning-dot';
                        gaugePct.className = 'text-xs font-mono font-bold text-rose-400';
                    }
                    gaugeLabel.innerText = inspectionMs + 'ms scan | ' + remaining + 'ms headroom';
                    gaugePct.innerText = `${pct.toFixed(1)}% of budget`;
                }, 50);

                if (data.status === 'APPROVED') {
                    actionBadge.className = 'text-xs font-mono font-bold px-3 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/60';
                } else if (data.status === 'BLOCKED') {
                    actionBadge.className = 'text-xs font-mono font-bold px-3 py-1 rounded bg-rose-950 text-rose-400 border border-rose-800/60';
                } else if (data.status === 'EDITED') {
                    actionBadge.className = 'text-xs font-mono font-bold px-3 py-1 rounded bg-indigo-950 text-indigo-400 border border-indigo-800/60';
                } else {
                    actionBadge.className = 'text-xs font-mono font-bold px-3 py-1 rounded bg-amber-950 text-amber-400 border border-amber-800/60';
                }
                actionBadge.innerText = data.action;
                outputWindow.innerText = data.response;

            } catch (err) { outputWindow.innerText = `Error: ${err.message}`; } 
            finally { runBtn.disabled = false; runBtn.innerText = 'Inspect & Route Prompt'; }
        }
    </script>
</body>
</html>
    """, status_code=200, headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})