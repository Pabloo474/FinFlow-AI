# FinFlow AI — Agentic Financial Intelligence Pipeline

An enterprise-grade financial analysis system built with **LangGraph**, **Pydantic contracts**, and **Agentic RAG**. Analyzes any public stock ticker and generates professional financial reports with built-in quality control.

## Architecture Overview

```
                    ┌─────────────────────────────────────────────────────────┐
                    │              LangGraph State Graph                       │
                    │                                                          │
  Ticker Input ───▶ ───▶ Market Research ───▶ Financial Analyst ───▶ Report Writer
                    │        (Tavily API)        (yfinance)                    │
                    │                            │                             │
                    │                            ▼                             │
                    │                    Quality Controller ──────────────────┘
                    │                    (LLM-based validation)                   │
                    │                         │                                 │
                    │                    ┌────┴────┐                            │
                    │                    │         │                            │
                    │               Passed      Retry (max 3)                   │
                    │                    │         │                            │
                    │                    ▼         ▼                            │
                    │              Final Report   (feedback → Report Writer)     │
                    └─────────────────────────────────────────────────────────┘
```

### Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Contracts First (SDD)** | All inter-agent communication uses Pydantic models (`FinancialMetricsModel`, `NewsItemModel`, `QAResult`) |
| **Determinism** | Each node has a single responsibility, explicit error handling, and cached LLM calls |
| **Observability** | Structured logging to files + LangGraph checkpointing via SQLite |
| **Resilience** | Exponential backoff retries, error fallbacks, and a Quality Controller agent that validates outputs |
| **Agentic RAG** | Real-time retrieval (Tavily + yfinance) + LLM generation in a loop with QA feedback |

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository>
cd FinFlow-AI
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your API keys
```

Required variables:
| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (or skip for local mode) |
| `TAVILY_API_KEY` | Tavily search API key |
| `OPENAI_MODEL` | (Optional) Model name, e.g. `gpt-4o-mini` |
| `LOCAL_LLM_ENABLED` | Set to `true` to use local inference |
| `LOCAL_LLM_MODEL` | Path to `.gguf` model file (e.g. `models/gemma-4-26B-A4B-it-Q4_K_M.gguf`) |
| `LLAMA_N_CTX` | Context window size (default: `32768`) |

### 3. Run Analysis

```bash
python main.py AAPL
python main.py TSLA "Compare Q3 earnings with Q2"
python main.py MSFT "Investment outlook and risks"
```

Output format:
```
======================================================================
FINANCIAL ANALYSIS REPORT
======================================================================
[Professional markdown report here...]
======================================================================
Company: AAPL
QA Passed: True
Iterations: 1
======================================================================
```

## Project Structure

```
FinFlow-AI/
├── main.py                          # CLI entry point
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variable template
│
├── src/
├── │   ├── __init__.py
├── │   ├── state.py                     # Pydantic contracts + LangGraph state definition
├── │   ├── graph.py                     # LangGraph workflow assembly
├── │   │
├── │   ├── agents/
├── │   │   ├── researcher.py            # Market research agent (Tavily)
├── │   │   ├── analyst.py               # Financial analyst agent (yfinance)
├── │   │   ├── report_writer.py         # Report synthesis agent (LLM)
├── │   │   └── quality_controller.py    # QA/auditing agent (LLM)
├── │   │
├── │   └── tools/
├── │   │       ├── research_tool.py         # Tavily API wrapper with retry
├── │   │       ├── finance_tool.py          # yfinance wrapper with retry
├── │   │       └── llm_tool.py              # Unified LLM interface (OpenAI + llama.cpp)
├── │
├── docs/
├── │   ├── requirements.md              # Functional & non-functional requirements
├── │   └── specs/
├── │       ├── 01-architecture.md       # Architecture specification
├── │       ├── 02-state-schema.md       # State schema specification
├── │       └── 03-evaluation-plan.md    # QA evaluation criteria
├── │
├── checkpoints/
├── │   └── finflow_checkpoints.db      # SQLite checkpoint database
├── │
└── logs/
    └── app_*.log                    # Application logs
```

## Agent Descriptions

### 1. Market Researcher (`researcher.py`)
**Purpose:** Retrieves real-time market news and macroeconomic context.
**Tool:** Tavily Search API (`research_tool.py`)
**Output:** List of `NewsItemModel` objects (title, content, URL, date)
**Retry:** 3 attempts with exponential backoff

### 2. Financial Analyst (`analyst.py`)
**Purpose:** Fetches quantitative financial metrics.
**Tool:** yfinance API (`finance_tool.py`)
**Output:** `FinancialMetricsModel` (revenue, net income, P/E ratio, debt-to-equity)
**Fallback:** Returns error-flagged metrics if yfinance fails

### 3. Report Writer (`report_writer.py`)
**Purpose:** Synthesizes qualitative (news) and quantitative (metrics) data into a professional report.
**LLM:** OpenAI GPT or local model (via `llm_tool.py`)
**Context:** Structured JSON with metrics, news snippets, and data quality flags
**Cache:** Memoizes outputs by ticker + news count + revenue hash

### 4. Quality Controller (`quality_controller.py`)
**Purpose:** Validates report accuracy against source data.
**Checks:**
- Metric consistency (numbers match source data exactly)
- Numerical accuracy (no fabricated calculations)
- Data honesty (no claims beyond provided data)
- Logical coherence (trends supported by data)
- Completeness (all key metrics addressed)

**Loop:** Retries report generation up to 3 times if QA fails, feeding feedback to Report Writer.

## Configuration

### Local Inference Mode

To bypass OpenAI API and use a local model:

```bash
export LOCAL_LLM_ENABLED=true
export LOCAL_LLM_MODEL=/path/to/your/model.gguf
export LLAMA_N_CTX=32768
```

The system uses `llama-cpp-python` for local inference with:
- GPU offloading (Metal on Mac, CUDA on Linux)
- Configurable context window (default 32K tokens)
- Thread pool control (`LLAMA_N_THREADS=12`)

### Token Management

To prevent context window overflow:
- News content is truncated: 120 chars for titles, 150 for content
- Maximum 3 news items per analysis
- Research search depth set to `basic` with 3 results max
- QA draft truncation at 8000 characters

## Logging

Logs are written to `./logs/` with timestamp-based filenames:
```
logs/app_20261111_142813.log
```

Log levels: `INFO`, `WARNING`, `ERROR`
Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

## Checkpointing

LangGraph checkpointing is enabled via SQLite (`./checkpoints/finflow_checkpoints.db`).
This enables:
- Conversation history persistence
- Fault recovery from interruption
- Debugging via checkpoint inspection

## Development

### Adding a New Agent

1. Define Pydantic input/output contracts in `src/state.py`
2. Create agent file in `src/agents/`
3. Add node to `src/graph.py` workflow
4. Define routing edges (conditional or fixed)

### Adding a New Tool

1. Create Pydantic `Input` and `Output` models
2. Implement `run()` and `arun()` methods with retry logic
3. Register in the appropriate agent

## Troubleshooting

### Context Window Overflow
- Reduce news items or increase `n_ctx` in `llm_tool.py`
- Set `LOCAL_LLM_MODEL` to a smaller model (e.g., Q4 quantized)
- Check logs for `context window` errors

### QA Loop Not Breaking
- The system caps retries at 3 iterations
- After 3 failures, the draft is returned regardless of QA status
- Check `qa_feedback` in the output for detailed reasons

### API Key Issues
- Verify `.env` file is loaded (`python-dotenv` runs at startup)
- Check key validity on Tavily/OpenAI dashboards
- Ensure `TAVILY_API_KEY` and `OPENAI_API_KEY` are set

## License

Private project — All rights reserved.
