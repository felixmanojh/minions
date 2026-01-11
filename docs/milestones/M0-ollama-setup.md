# Milestone M0 – Local Ollama Models

Goal: have at least two local coding models running through Ollama with a reachable HTTP API so later agents can call them.

## 1. Install prerequisites

1. **macOS/Linux**: make sure you have a recent CPU/GPU driver. For Apple Silicon, no extra drivers are needed.
2. **Install Ollama**:
   ```bash
   # macOS (Homebrew)
   brew install ollama

   # Linux (official install script)
   curl -fsSL https://ollama.com/install.sh | sh
   ```
3. Verify installation:
   ```bash
   ollama --version
   ```

## 2. Start the Ollama service

Run the daemon once per machine boot (launchctl/systemd can keep it alive later):
```bash
ollama serve > ~/.ollama/log 2>&1 &
```
Default API: `http://127.0.0.1:11434`.

Quick health check:
```bash
curl http://127.0.0.1:11434/api/tags
```
You should see a JSON list (possibly empty) of pulled models.

## 3. Pull baseline coding models

Pull at least two complementary models so we can test multi-agent orchestration. Suggested mix (adjust to your GPU/VRAM budget):

```bash
ollama pull qwen2.5-coder:1.5b
ollama pull deepseek-coder:1.3b
ollama pull codellama:7b-code
```

List what you have:
```bash
ollama list
```

## 4. Smoke-test each model

Interactive CLI run:
```bash
ollama run qwen2.5-coder:1.5b "Summarize the repo layout"
```

HTTP request (what the orchestrator will do later):
```bash
curl http://127.0.0.1:11434/api/generate \
  -d '{
        "model": "qwen2.5-coder:1.5b",
        "prompt": "Write a docstring for a Python function that adds two numbers."
      }'
```
Make sure responses arrive within your latency budget.

## 5. Optional: define logical model aliases

Create `models.yaml` (future CLI will consume it) so we can refer to models by role-friendly names:

```yaml
implementer:
  model: qwen2.5-coder:1.5b
  temperature: 0.2
reviewer:
  model: deepseek-coder:1.3b
  temperature: 0.1
bughunter:
  model: codellama:7b-code
  temperature: 0.3
```

## 6. Capture results

* Save `ollama list` output so we know which weights are available.
* Note average response latency for a 200-token prompt for each model (helps size future turn budgets).

Once these steps succeed, Milestone M0 is complete and we can move to orchestrator work (M1).

NAME                   ID              SIZE      MODIFIED           
codellama:7b-code      8df0a30bb1e6    3.8 GB    About a minute ago    
deepseek-coder:1.3b    3ddd2d3fc8d2    776 MB    5 minutes ago         
qwen2.5-coder:1.5b     d7372fd82851    986 MB    6 minutes ago 