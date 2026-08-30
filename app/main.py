import asyncio
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from app.engines.safety import SafetyEngine
from app.engines.cache import CacheEngine
from app.engines.policy import PolicyEngine, POLICY_PROFILES

app = FastAPI(
    title="CogniGuard ControlPlane",
    description="Real-time oversight engine for Enterprise AI",
    version="1.0.0",
    docs_url=None
)

safety_engine = SafetyEngine()
cache_engine = CacheEngine()
policy_engine = PolicyEngine()


class PromptRequest(BaseModel):
    prompt: str


class PolicyUpdateRequest(BaseModel):
    profile: str
    overrides: dict = {}


async def simulate_llm(prompt: str) -> str:
    await asyncio.sleep(0.6)
    if "credit card" in prompt.lower() or "card number" in prompt.lower():
        return "Confidential user record: Account #8821, Card: 4532890123456789 (Exp: 08/29)."
    if "worthless" in prompt.lower() or "bias" in prompt.lower():
        return "This user group is historically worthless for business expansion."
    if "competitor" in prompt.lower() or "churn" in prompt.lower():
        return "Our platform is expanding, but internal churn reached 42% last month after the competitor launch."
    return "Enterprise fiscal projections indicate steady 12% quarter-over-quarter expansion across all key segments."


# ─────────────────────────────────────────────
#  POLICY API ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/v1/policy")
async def get_policy():
    """Return the currently active policy profile and all available profiles."""
    return policy_engine.get_status()


@app.post("/v1/policy")
async def set_policy(req: PolicyUpdateRequest):
    """Switch the active policy profile, with optional per-module overrides."""
    if req.profile not in POLICY_PROFILES:
        raise HTTPException(status_code=400, detail=f"Unknown profile '{req.profile}'. Valid options: {list(POLICY_PROFILES.keys())}")
    policy_engine.set_profile(req.profile, req.overrides)
    return {"success": True, "active_profile": req.profile, "policy": policy_engine.active_policy}


# ─────────────────────────────────────────────
#  CORE INSPECTION ENDPOINT
# ─────────────────────────────────────────────

@app.post("/v1/chat/completions")
async def process_prompt(req: PromptRequest):
    start_time = time.perf_counter()
    policy = policy_engine.active_policy

    # 1. Performance & Cost Check — Cache
    cache_result = cache_engine.check_cache(req.prompt)
    if cache_result["status"] == "cached":
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "APPROVED",
            "action": "SERVED_FROM_CACHE",
            "response": cache_result["data"],
            "metrics": {"latency_ms": latency_ms, "inspection_ms": 0, "compute_saved": "100%", "cost_tier": "Zero-Compute"},
            "checks": {"responsibility": "SKIPPED", "performance": "100% Match", "cost": "Cache Intercept"},
            "active_profile": policy_engine.active_profile_key,
        }

    # 2. Main LLM Execution
    raw_llm_response = await simulate_llm(req.prompt)

    # 3. LIVE REDACTION ENGINE — hallucination check (policy-aware)
    inspect_start = time.perf_counter()
    if policy.get("hallucination_check", True) and "42%" in raw_llm_response:
        action = policy.get("on_hallucination", "redact")
        inspection_ms = round((time.perf_counter() - inspect_start) * 1000, 2)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if action == "redact":
            redacted = raw_llm_response.replace("42%", "[REDACTED: UNVERIFIED INTERNAL METRIC]")
            return {
                "status": "EDITED",
                "action": "AUTO_REDACTED",
                "response": redacted,
                "metrics": {"latency_ms": latency_ms, "inspection_ms": inspection_ms, "compute_saved": "0%", "cost_tier": "Standard LLM Tier"},
                "checks": {"responsibility": "PASSED (Scrubbed)", "performance": "MINOR HALLUCINATION REPAIRED", "cost": "Standard Routing"},
                "active_profile": policy_engine.active_profile_key,
            }
        elif action == "flag":
            return {
                "status": "ESCALATED",
                "action": "HUMAN_IN_THE_LOOP_QUEUE",
                "response": f"[CONTENT HELD FOR AUDIT — Policy: {policy['name']}] Unverified metric detected.",
                "metrics": {"latency_ms": latency_ms, "inspection_ms": inspection_ms, "compute_saved": "0%", "cost_tier": "Standard LLM Tier"},
                "checks": {"responsibility": "FLAGGED: Unverified Metric", "performance": "Stream Paused", "cost": "Standard"},
                "active_profile": policy_engine.active_profile_key,
            }
        # risk_tolerance=high → pass through with a note
        else:
            raw_llm_response = raw_llm_response + " [NOTE: Unverified metric detected — logged for audit]"

    # 4. Responsibility & Safety Layer Scan (policy-aware)
    safety_result = safety_engine.scan(raw_llm_response)
    inspection_ms = round((time.perf_counter() - inspect_start) * 1000, 2)
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    if safety_result["status"] == "block":
        pii_action = policy.get("on_pii", "block") if "PII" in safety_result.get("reason", "") else policy.get("on_bias", "block")

        if pii_action == "redact":
            return {
                "status": "EDITED",
                "action": "PII_REDACTED",
                "response": "[SENSITIVE DATA REDACTED BY COGNIGUARD — Content sanitised per active policy]",
                "metrics": {"latency_ms": latency_ms, "inspection_ms": inspection_ms, "compute_saved": "0%", "cost_tier": "Standard Tier"},
                "checks": {"responsibility": f"REDACTED: {safety_result['reason']}", "performance": "Sanitised Output", "cost": "Standard"},
                "active_profile": policy_engine.active_profile_key,
            }
        # Default: hard block
        return {
            "status": "BLOCKED",
            "action": "HARD_INTERCEPT",
            "response": "[TRANSMISSION TERMINATED BY COGNIGUARD - DATA EXFILTRATION PREVENTED]",
            "metrics": {"latency_ms": latency_ms, "inspection_ms": inspection_ms, "compute_saved": "0%", "cost_tier": "Standard Tier"},
            "checks": {"responsibility": f"FAILED: {safety_result['reason']}", "performance": "Stream Halted", "cost": "Standard"},
            "active_profile": policy_engine.active_profile_key,
        }

    if safety_result["status"] == "escalate":
        bias_action = policy.get("on_bias", "escalate")
        if bias_action == "block":
            return {
                "status": "BLOCKED",
                "action": "HARD_INTERCEPT",
                "response": "[TRANSMISSION TERMINATED — Bias/Policy Violation detected under active strict policy]",
                "metrics": {"latency_ms": latency_ms, "inspection_ms": inspection_ms, "compute_saved": "0%", "cost_tier": "Standard Tier"},
                "checks": {"responsibility": f"BLOCKED: {safety_result['reason']}", "performance": "Stream Halted", "cost": "Standard"},
                "active_profile": policy_engine.active_profile_key,
            }
        return {
            "status": "ESCALATED",
            "action": "HUMAN_IN_THE_LOOP_QUEUE",
            "response": "[CONTENT HELD FOR HUMAN AUDIT] - Ambiguous policy violation flagged.",
            "metrics": {"latency_ms": latency_ms, "inspection_ms": inspection_ms, "compute_saved": "0%", "cost_tier": "Standard Tier"},
            "checks": {"responsibility": f"FLAGGED: {safety_result['reason']}", "performance": "Stream Paused", "cost": "Standard"},
            "active_profile": policy_engine.active_profile_key,
        }

    return {
        "status": "APPROVED",
        "action": "STREAM_DELIVERED",
        "response": raw_llm_response,
        "metrics": {"latency_ms": latency_ms, "inspection_ms": inspection_ms, "compute_saved": "0%", "cost_tier": "Optimized Gateway Routing"},
        "checks": {"responsibility": "PASSED", "performance": "Validated Output", "cost": "Optimized Routing"},
        "active_profile": policy_engine.active_profile_key,
    }


# ─────────────────────────────────────────────
#  API DOCS
# ─────────────────────────────────────────────

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
            body { font-family: 'Plus Jakarta Sans', sans-serif !important; }
            code, pre { font-family: 'JetBrains Mono', monospace !important; }
            body.dark-mode, .dark-mode .scalar-api-reference {
                --theme-color-1: #3B82F6 !important;
                --theme-color-2: #F8FAFC !important;
                --theme-color-3: #94A3B8 !important;
                --theme-background-1: #090A0F !important;
                --theme-background-2: #111420 !important;
                --theme-background-3: #161B2E !important;
                --theme-border-color: #1F2742 !important;
            }
        </style>
    </head>
    <body>
        <script id="api-reference" data-url="/openapi.json" data-theme="moon" data-layout="modern"></script>
        <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ─────────────────────────────────────────────
#  MAIN DASHBOARD
# ─────────────────────────────────────────────

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
        body { background-color: #090A0F; }
        .glow { box-shadow: 0 0 35px -10px rgba(59, 130, 246, 0.25); }
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
            <div class="flex items-center space-x-3">
                <span id="headerProfileBadge" class="text-xs font-mono px-2.5 py-1 rounded-full bg-surface-card border border-border-subtle text-slate-400">Policy: —</span>
                <a href="/policy" class="text-xs font-semibold text-indigo-300 hover:text-white bg-indigo-950/60 hover:bg-indigo-900/60 border border-indigo-800/60 px-4 py-2 rounded-lg transition">⚙ Policy Config</a>
                <a href="/docs" target="_blank" class="text-xs font-semibold text-slate-300 hover:text-white bg-surface-card hover:bg-border-subtle border border-border-subtle px-4 py-2 rounded-lg transition">API Docs</a>
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
                        <span id="budgetLabel" class="text-[10px] font-mono text-slate-600 border border-border-subtle px-1.5 py-0.5 rounded">vs Budget</span>
                    </div>
                    <div class="flex items-center space-x-3">
                        <span id="gaugeLabel" class="text-xs font-mono text-slate-500">—</span>
                        <span id="gaugePct" class="text-xs font-mono font-bold text-slate-500">—</span>
                    </div>
                </div>
                <div class="gauge-track"><div id="gaugeFill" class="gauge-fill"></div></div>
                <div class="flex justify-between mt-1.5">
                    <span class="text-[10px] font-mono text-slate-600">0ms</span>
                    <span id="budgetMax" class="text-[10px] font-mono text-slate-600">threshold</span>
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
        // Load active policy on page load to show current profile in header
        async function loadActivePolicy() {
            try {
                const res = await fetch('/v1/policy');
                const data = await res.json();
                const profileNames = {
                    customer_facing: 'Customer-Facing',
                    internal_copilot: 'Internal Copilot',
                    batch_processing: 'Batch Processing'
                };
                const badge = document.getElementById('headerProfileBadge');
                badge.innerText = 'Policy: ' + (profileNames[data.active_profile] || data.active_profile);
                // Update budget label
                const budget = data.policy?.latency_budget_ms || 50;
                document.getElementById('budgetLabel').innerText = `vs ${budget}ms Budget`;
                document.getElementById('budgetMax').innerText = `${budget}ms threshold`;
            } catch(e) {}
        }
        loadActivePolicy();

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

                // Fetch current budget from policy
                let BUDGET_MS = 50;
                try {
                    const pRes = await fetch('/v1/policy');
                    const pData = await pRes.json();
                    BUDGET_MS = pData.policy?.latency_budget_ms || 50;
                    const profileNames = { customer_facing: 'Customer-Facing', internal_copilot: 'Internal Copilot', batch_processing: 'Batch Processing' };
                    document.getElementById('headerProfileBadge').innerText = 'Policy: ' + (profileNames[pData.active_profile] || pData.active_profile);
                    document.getElementById('budgetLabel').innerText = `vs ${BUDGET_MS}ms Budget`;
                    document.getElementById('budgetMax').innerText = `${BUDGET_MS}ms threshold`;
                } catch(e) {}

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


# ─────────────────────────────────────────────
#  POLICY CONFIGURATION PAGE
# ─────────────────────────────────────────────

@app.get("/policy", response_class=HTMLResponse)
async def policy_page():
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CogniGuard | Policy Configuration</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <script>
        tailwind.config = { theme: { extend: { fontFamily: { sans: ['"Plus Jakarta Sans"'], mono: ['"JetBrains Mono"'] }, colors: { obsidian: '#090A0F', surface: '#111420', 'surface-card': '#161B2E', 'border-subtle': '#1F2742' } } } }
    </script>
    <style>
        body { background-color: #090A0F; }
        .profile-card { cursor: pointer; transition: all 0.2s ease; border: 2px solid #1F2742; }
        .profile-card:hover { border-color: #3B82F6; transform: translateY(-2px); box-shadow: 0 0 24px -6px rgba(59,130,246,0.3); }
        .profile-card.active { border-color: #3B82F6; background: linear-gradient(135deg, #0f1e3a 0%, #111420 100%); box-shadow: 0 0 32px -8px rgba(59,130,246,0.4); }
        .profile-card.active-green { border-color: #10B981; background: linear-gradient(135deg, #0a2018 0%, #111420 100%); box-shadow: 0 0 32px -8px rgba(16,185,129,0.3); }
        .profile-card.active-amber { border-color: #F59E0B; background: linear-gradient(135deg, #1f1500 0%, #111420 100%); box-shadow: 0 0 32px -8px rgba(245,158,11,0.3); }
        .toggle-switch { position: relative; display: inline-block; width: 42px; height: 24px; }
        .toggle-switch input { opacity: 0; width: 0; height: 0; }
        .toggle-slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #1F2742; border-radius: 24px; transition: .3s; }
        .toggle-slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: #475569; border-radius: 50%; transition: .3s; }
        input:checked + .toggle-slider { background-color: #2563EB; }
        input:checked + .toggle-slider:before { transform: translateX(18px); background-color: white; }
        .select-styled { background: #111420; border: 1px solid #1F2742; color: #CBD5E1; border-radius: 8px; padding: 6px 10px; font-family: 'JetBrains Mono', monospace; font-size: 12px; outline: none; cursor: pointer; }
        .select-styled:focus { border-color: #3B82F6; }
        @keyframes slide-in { from { opacity:0; transform: translateY(8px); } to { opacity:1; transform: translateY(0); } }
        .slide-in { animation: slide-in 0.3s ease forwards; }
        @keyframes pulse-ring { 0%, 100% { box-shadow: 0 0 0 0 rgba(59,130,246,0.4); } 50% { box-shadow: 0 0 0 6px rgba(59,130,246,0); } }
        .active-pulse { animation: pulse-ring 2s ease infinite; }
    </style>
</head>
<body class="text-slate-200 antialiased font-sans min-h-screen flex flex-col">

    <!-- Header -->
    <header class="border-b border-border-subtle bg-surface/80 backdrop-blur-md sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-4">
                <a href="/" class="flex items-center space-x-3 group">
                    <div class="h-8 w-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center font-extrabold text-white text-sm">CG</div>
                    <span class="font-bold text-white text-lg group-hover:text-blue-400 transition">CogniGuard</span>
                </a>
                <span class="text-border-subtle">/</span>
                <span class="text-sm font-semibold text-indigo-400">Policy Configuration</span>
            </div>
            <div class="flex items-center space-x-3">
                <span id="headerStatus" class="text-xs font-mono px-2.5 py-1 rounded-full bg-surface-card border border-border-subtle text-slate-400">Loading...</span>
                <a href="/" class="text-xs font-semibold text-slate-300 hover:text-white bg-surface-card hover:bg-border-subtle border border-border-subtle px-4 py-2 rounded-lg transition">← Back to Dashboard</a>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 py-10 w-full flex-1">

        <!-- Page Title -->
        <div class="mb-10">
            <h1 class="text-3xl font-bold text-white tracking-tight">Governance Policy Center</h1>
            <p class="text-slate-400 mt-2 max-w-2xl">Configure CogniGuard's detection behaviour per use-case. Changes take effect immediately on the next prompt inspection — no restart required.</p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">

            <!-- LEFT: Profile Selector -->
            <div class="lg:col-span-5 space-y-4">
                <div class="flex items-center justify-between">
                    <span class="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider">Use-Case Profiles</span>
                    <span class="text-[10px] font-mono text-slate-600 bg-surface-card border border-border-subtle px-2 py-0.5 rounded">Click to activate</span>
                </div>

                <!-- Profile: Customer-Facing -->
                <div id="card-customer_facing" class="profile-card rounded-2xl p-5" onclick="selectProfile('customer_facing')">
                    <div class="flex items-start justify-between mb-3">
                        <div class="flex items-center space-x-3">
                            <div class="h-10 w-10 rounded-xl bg-rose-950/60 border border-rose-800/40 flex items-center justify-center text-lg">🛡️</div>
                            <div>
                                <div class="font-semibold text-white text-sm">Customer-Facing Chatbot</div>
                                <div class="text-[11px] text-rose-400 font-mono mt-0.5">Risk: LOW · Budget: 30ms</div>
                            </div>
                        </div>
                        <div id="badge-customer_facing" class="hidden text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-blue-950 text-blue-400 border border-blue-800/60 active-pulse">ACTIVE</div>
                    </div>
                    <p class="text-xs text-slate-400 leading-relaxed">Real-time, user-visible responses. Hard blocks on PII. Zero tolerance for bias. Strict 30ms inspection overhead.</p>
                    <div class="flex flex-wrap gap-2 mt-3">
                        <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950/50 text-rose-400 border border-rose-900/50">PII → BLOCK</span>
                        <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950/50 text-indigo-400 border border-indigo-900/50">Hallucination → REDACT</span>
                        <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950/50 text-rose-400 border border-rose-900/50">Bias → BLOCK</span>
                    </div>
                </div>

                <!-- Profile: Internal Copilot -->
                <div id="card-internal_copilot" class="profile-card rounded-2xl p-5" onclick="selectProfile('internal_copilot')">
                    <div class="flex items-start justify-between mb-3">
                        <div class="flex items-center space-x-3">
                            <div class="h-10 w-10 rounded-xl bg-amber-950/60 border border-amber-800/40 flex items-center justify-center text-lg">🏢</div>
                            <div>
                                <div class="font-semibold text-white text-sm">Internal Employee Copilot</div>
                                <div class="text-[11px] text-amber-400 font-mono mt-0.5">Risk: MEDIUM · Budget: 100ms</div>
                            </div>
                        </div>
                        <div id="badge-internal_copilot" class="hidden text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-blue-950 text-blue-400 border border-blue-800/60 active-pulse">ACTIVE</div>
                    </div>
                    <p class="text-xs text-slate-400 leading-relaxed">Internal tooling for employees. Medium risk tolerance. Escalates ambiguous content for human review instead of hard blocking.</p>
                    <div class="flex flex-wrap gap-2 mt-3">
                        <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/50 text-amber-400 border border-amber-900/50">PII → REDACT</span>
                        <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/50 text-amber-400 border border-amber-900/50">Hallucination → FLAG</span>
                        <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/50 text-amber-400 border border-amber-900/50">Bias → ESCALATE</span>
                    </div>
                </div>

                <!-- Profile: Batch Processing -->
                <div id="card-batch_processing" class="profile-card rounded-2xl p-5" onclick="selectProfile('batch_processing')">
                    <div class="flex items-start justify-between mb-3">
                        <div class="flex items-center space-x-3">
                            <div class="h-10 w-10 rounded-xl bg-emerald-950/60 border border-emerald-800/40 flex items-center justify-center text-lg">⚙️</div>
                            <div>
                                <div class="font-semibold text-white text-sm">Batch / Offline Processing</div>
                                <div class="text-[11px] text-emerald-400 font-mono mt-0.5">Risk: HIGH · Budget: 500ms</div>
                            </div>
                        </div>
                        <div id="badge-batch_processing" class="hidden text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-blue-950 text-blue-400 border border-blue-800/60 active-pulse">ACTIVE</div>
                    </div>
                    <p class="text-xs text-slate-400 leading-relaxed">No real-time latency constraint. Full deep-scan mode. All violations logged for post-hoc audit. Throughput optimised.</p>
                    <div class="flex flex-wrap gap-2 mt-3">
                        <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/50 text-emerald-400 border border-emerald-900/50">PII → REDACT</span>
                        <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/50 text-emerald-400 border border-emerald-900/50">Hallucination → REDACT</span>
                        <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/50 text-emerald-400 border border-emerald-900/50">Bias → FLAG</span>
                    </div>
                </div>
            </div>

            <!-- RIGHT: Module Controls & Live Policy State -->
            <div class="lg:col-span-7 space-y-5">

                <!-- Module Toggles -->
                <div class="bg-surface border border-border-subtle rounded-2xl p-6">
                    <div class="flex items-center justify-between mb-5">
                        <h2 class="text-sm font-semibold text-white">Detection Module Overrides</h2>
                        <span class="text-[10px] font-mono text-slate-500 bg-surface-card border border-border-subtle px-2 py-0.5 rounded">Applied on top of active profile</span>
                    </div>

                    <div class="space-y-5">
                        <!-- PII Detection -->
                        <div class="flex items-center justify-between p-4 bg-obsidian rounded-xl border border-border-subtle">
                            <div class="flex items-center space-x-3">
                                <div class="h-8 w-8 rounded-lg bg-rose-950/60 border border-rose-900/40 flex items-center justify-center text-sm">🔒</div>
                                <div>
                                    <div class="text-sm font-semibold text-white">PII Detection</div>
                                    <div class="text-[11px] text-slate-500 mt-0.5">Regex + pattern scan for credit cards, SSNs, emails</div>
                                </div>
                            </div>
                            <div class="flex items-center space-x-3">
                                <select id="pii_action" class="select-styled" onchange="scheduleOverrideUpdate()">
                                    <option value="block">BLOCK</option>
                                    <option value="redact">REDACT</option>
                                    <option value="flag">FLAG</option>
                                </select>
                                <label class="toggle-switch">
                                    <input type="checkbox" id="pii_enabled" checked onchange="scheduleOverrideUpdate()">
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>
                        </div>

                        <!-- Hallucination Check -->
                        <div class="flex items-center justify-between p-4 bg-obsidian rounded-xl border border-border-subtle">
                            <div class="flex items-center space-x-3">
                                <div class="h-8 w-8 rounded-lg bg-indigo-950/60 border border-indigo-900/40 flex items-center justify-center text-sm">🧠</div>
                                <div>
                                    <div class="text-sm font-semibold text-white">Hallucination Check</div>
                                    <div class="text-[11px] text-slate-500 mt-0.5">Unverified metrics detected against semantic cache</div>
                                </div>
                            </div>
                            <div class="flex items-center space-x-3">
                                <select id="hallucination_action" class="select-styled" onchange="scheduleOverrideUpdate()">
                                    <option value="redact">REDACT</option>
                                    <option value="flag">FLAG</option>
                                    <option value="block">BLOCK</option>
                                </select>
                                <label class="toggle-switch">
                                    <input type="checkbox" id="hallucination_enabled" checked onchange="scheduleOverrideUpdate()">
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>
                        </div>

                        <!-- Bias Filter -->
                        <div class="flex items-center justify-between p-4 bg-obsidian rounded-xl border border-border-subtle">
                            <div class="flex items-center space-x-3">
                                <div class="h-8 w-8 rounded-lg bg-amber-950/60 border border-amber-900/40 flex items-center justify-center text-sm">⚖️</div>
                                <div>
                                    <div class="text-sm font-semibold text-white">Bias & Toxicity Filter</div>
                                    <div class="text-[11px] text-slate-500 mt-0.5">ML classifier (TF-IDF + LinearSVC) for toxic content</div>
                                </div>
                            </div>
                            <div class="flex items-center space-x-3">
                                <select id="bias_action" class="select-styled" onchange="scheduleOverrideUpdate()">
                                    <option value="escalate">ESCALATE</option>
                                    <option value="block">BLOCK</option>
                                    <option value="flag">FLAG</option>
                                </select>
                                <label class="toggle-switch">
                                    <input type="checkbox" id="bias_enabled" checked onchange="scheduleOverrideUpdate()">
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>
                        </div>

                        <!-- Audit Trail -->
                        <div class="flex items-center justify-between p-4 bg-obsidian rounded-xl border border-border-subtle">
                            <div class="flex items-center space-x-3">
                                <div class="h-8 w-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-sm">📋</div>
                                <div>
                                    <div class="text-sm font-semibold text-white">Audit Trail</div>
                                    <div class="text-[11px] text-slate-500 mt-0.5">Log every decision with full metadata for compliance</div>
                                </div>
                            </div>
                            <label class="toggle-switch">
                                <input type="checkbox" id="audit_enabled" checked onchange="scheduleOverrideUpdate()">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                    </div>
                </div>

                <!-- Live Policy State JSON -->
                <div class="bg-surface border border-border-subtle rounded-2xl p-6">
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-sm font-semibold text-white">Live Policy State</h2>
                        <div class="flex items-center space-x-2">
                            <span id="syncDot" class="h-2 w-2 rounded-full bg-emerald-400"></span>
                            <span id="syncLabel" class="text-[11px] font-mono text-emerald-400">Synced</span>
                        </div>
                    </div>
                    <pre id="policyJson" class="bg-obsidian border border-border-subtle rounded-xl p-4 text-xs font-mono text-slate-300 overflow-x-auto leading-relaxed">Loading...</pre>
                </div>

                <!-- Apply Button -->
                <button id="applyBtn" onclick="applyChanges()" class="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 font-bold text-white py-3.5 rounded-xl transition text-sm shadow-lg shadow-blue-900/30">
                    Apply Policy Changes
                </button>
                <div id="applyStatus" class="text-center text-xs font-mono text-slate-500 hidden"></div>
            </div>
        </div>
    </main>

    <footer class="border-t border-border-subtle bg-surface/40 py-4 px-6 text-xs text-slate-500 text-center">~PRATISHTHA & PARTH | CogniGuard ControlPlane</footer>

    <script>
        let currentProfile = 'customer_facing';
        let overrideTimer = null;

        const PROFILE_COLORS = {
            customer_facing: 'active',
            internal_copilot: 'active-amber',
            batch_processing: 'active-green'
        };

        async function loadPolicy() {
            try {
                const res = await fetch('/v1/policy');
                const data = await res.json();
                currentProfile = data.active_profile;
                updateProfileCards(data.active_profile);
                populateControls(data.policy);
                renderJson(data.policy);
                document.getElementById('headerStatus').innerText = 'Active: ' + data.policy.name;
                document.getElementById('headerStatus').className = 'text-xs font-mono px-2.5 py-1 rounded-full bg-emerald-950/60 border border-emerald-800/60 text-emerald-400';
            } catch(e) {
                document.getElementById('policyJson').innerText = 'Error loading policy.';
            }
        }

        function updateProfileCards(activeKey) {
            ['customer_facing', 'internal_copilot', 'batch_processing'].forEach(key => {
                const card = document.getElementById('card-' + key);
                const badge = document.getElementById('badge-' + key);
                card.classList.remove('active', 'active-green', 'active-amber');
                badge.classList.add('hidden');
                if (key === activeKey) {
                    card.classList.add(PROFILE_COLORS[key]);
                    badge.classList.remove('hidden');
                }
            });
        }

        function populateControls(policy) {
            setToggle('pii_enabled', policy.pii_detection !== false);
            setToggle('hallucination_enabled', policy.hallucination_check !== false);
            setToggle('bias_enabled', policy.bias_filter !== false);
            setToggle('audit_enabled', policy.audit_trail !== false);
            setSelect('pii_action', policy.on_pii || 'block');
            setSelect('hallucination_action', policy.on_hallucination || 'redact');
            setSelect('bias_action', policy.on_bias || 'escalate');
        }

        function setToggle(id, val) {
            const el = document.getElementById(id);
            if (el) el.checked = val;
        }
        function setSelect(id, val) {
            const el = document.getElementById(id);
            if (el) { for(let i=0; i<el.options.length; i++) { if(el.options[i].value===val) { el.selectedIndex=i; break; } } }
        }

        function renderJson(policy) {
            const el = document.getElementById('policyJson');
            el.classList.add('slide-in');
            el.innerText = JSON.stringify(policy, null, 2);
            setTimeout(() => el.classList.remove('slide-in'), 400);
        }

        function selectProfile(key) {
            currentProfile = key;
            updateProfileCards(key);
            // Apply immediately
            applyChanges();
        }

        function scheduleOverrideUpdate() {
            // Debounce — apply after 400ms of no more changes
            clearTimeout(overrideTimer);
            setSyncState('pending');
            overrideTimer = setTimeout(() => applyChanges(), 400);
        }

        function setSyncState(state) {
            const dot = document.getElementById('syncDot');
            const label = document.getElementById('syncLabel');
            if (state === 'pending') { dot.className = 'h-2 w-2 rounded-full bg-amber-400'; label.innerText = 'Pending...'; label.className = 'text-[11px] font-mono text-amber-400'; }
            else if (state === 'synced') { dot.className = 'h-2 w-2 rounded-full bg-emerald-400'; label.innerText = 'Synced'; label.className = 'text-[11px] font-mono text-emerald-400'; }
            else { dot.className = 'h-2 w-2 rounded-full bg-rose-400'; label.innerText = 'Error'; label.className = 'text-[11px] font-mono text-rose-400'; }
        }

        async function applyChanges() {
            const btn = document.getElementById('applyBtn');
            const status = document.getElementById('applyStatus');
            btn.disabled = true;
            btn.innerText = 'Applying...';
            setSyncState('pending');

            const overrides = {};
            if (!document.getElementById('pii_enabled').checked) overrides.pii_detection = false;
            if (!document.getElementById('hallucination_enabled').checked) overrides.hallucination_check = false;
            if (!document.getElementById('bias_enabled').checked) overrides.bias_filter = false;
            if (!document.getElementById('audit_enabled').checked) overrides.audit_trail = false;
            overrides.on_pii = document.getElementById('pii_action').value;
            overrides.on_hallucination = document.getElementById('hallucination_action').value;
            overrides.on_bias = document.getElementById('bias_action').value;

            try {
                const res = await fetch('/v1/policy', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ profile: currentProfile, overrides })
                });
                const data = await res.json();
                renderJson(data.policy);
                setSyncState('synced');
                document.getElementById('headerStatus').innerText = 'Active: ' + data.policy.name;
                status.innerText = '✓ Policy applied successfully — changes are live.';
                status.className = 'text-center text-xs font-mono text-emerald-400 slide-in';
                status.classList.remove('hidden');
                setTimeout(() => status.classList.add('hidden'), 3000);
            } catch(e) {
                setSyncState('error');
                status.innerText = '✗ Failed to apply policy.';
                status.className = 'text-center text-xs font-mono text-rose-400';
                status.classList.remove('hidden');
            } finally {
                btn.disabled = false;
                btn.innerText = 'Apply Policy Changes';
            }
        }

        // Boot
        loadPolicy();
    </script>
</body>
</html>
    """, status_code=200, headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})