#!/usr/bin/env bash
#
# Minions - Ollama Setup
# Sets up Ollama and required models for the minions plugin.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/felixmanojh/minions/main/install.sh | bash
#
# Environment variables:
#   MINIONS_PRESET - Set to nano/small/medium/large to skip interactive prompt
#
# This script only handles Ollama installation and model downloads.
# Install the plugin separately via: /plugin marketplace add felixmanojh/minions
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Helper functions
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_command() {
    command -v "$1" >/dev/null 2>&1
}

detect_os() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*)  echo "linux" ;;
        MINGW*|CYGWIN*|MSYS*) echo "windows" ;;
        *)       echo "unknown" ;;
    esac
}

# Get models for a preset (Bash 3 compatible)
# Each preset includes: implementer, reviewer, patcher (FIM specialist)
get_preset_models() {
    case "$1" in
        medium) echo "qwen2.5-coder:7b deepseek-coder:6.7b starcoder2:7b" ;;
        large)  echo "qwen2.5-coder:14b deepseek-coder:33b starcoder2:15b" ;;
        lite)   echo "qwen2.5-coder:7b" ;;  # Single model, minimal install
        *)      echo "" ;;
    esac
}

# Default preset - 7B models recommended for quality
PRESET="${MINIONS_PRESET:-medium}"

# Banner
echo -e "${BLUE}"
echo "  __  __ _       _                 "
echo " |  \/  (_)_ __ (_) ___  _ __  ___ "
echo " | |\/| | | '_ \| |/ _ \| '_ \/ __|"
echo " | |  | | | | | | | (_) | | | \__ \\"
echo " |_|  |_|_|_| |_|_|\___/|_| |_|___/"
echo -e "${NC}"
echo "Ollama Setup for Minions"
echo ""

# Detect OS early
OS=$(detect_os)

if [ "$OS" = "windows" ]; then
    echo ""
    warn "Windows detected. Please install Ollama manually:"
    echo "  1. Download from https://ollama.ai/download/windows"
    echo "  2. Run the installer"
    echo "  3. Open PowerShell and run:"
    echo "     ollama serve"
    echo "     ollama pull qwen2.5-coder:7b"
    echo "     ollama pull deepseek-coder:6.7b"
    echo "     ollama pull starcoder2:7b"
    echo ""
    echo "Then install the plugin: /plugin marketplace add felixmanojh/minions"
    exit 0
fi

# Show preset options if running interactively
if [ -t 0 ] && [ -z "$MINIONS_PRESET" ]; then
    echo "Choose a model preset based on your hardware:"
    echo ""
    echo "  medium - ~13GB download (recommended) [default]"
    echo "           Qwen2.5-Coder:7B + DeepSeek-Coder:6.7B + StarCoder2:7B"
    echo ""
    echo "  large  - ~35GB download (best quality, needs 32GB+ RAM)"
    echo "           Qwen2.5-Coder:14B + DeepSeek-Coder:33B + StarCoder2:15B"
    echo ""
    echo "  lite   - ~5GB download  (single model, basic features)"
    echo "           Qwen2.5-Coder:7B only"
    echo ""
    read -p "Preset [medium]: " user_preset
    PRESET="${user_preset:-medium}"
    echo ""
fi

# Validate preset
MODELS_STR=$(get_preset_models "$PRESET")
if [ -z "$MODELS_STR" ]; then
    error "Unknown preset: $PRESET"
    echo "Valid presets: nano, small, medium, large"
    exit 1
fi

info "Using preset: $PRESET"

# Step 1: Check/Install Ollama
echo ""
info "Checking Ollama installation..."

if check_command ollama; then
    success "Ollama is installed"
else
    warn "Ollama not found, installing..."

    if [ "$OS" = "macos" ]; then
        if check_command brew; then
            brew install ollama
        else
            error "Homebrew not found. Install Ollama manually: https://ollama.ai"
            exit 1
        fi
    elif [ "$OS" = "linux" ]; then
        curl -fsSL https://ollama.com/install.sh | sh
    fi

    success "Ollama installed"
fi

# Step 2: Check/Start Ollama daemon
info "Checking Ollama daemon..."

if curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    success "Ollama daemon is running"
else
    warn "Starting Ollama daemon..."

    if [ "$OS" = "macos" ]; then
        ollama serve > /tmp/ollama.log 2>&1 &
    else
        if check_command systemctl; then
            sudo systemctl start ollama 2>/dev/null || ollama serve > /tmp/ollama.log 2>&1 &
        else
            ollama serve > /tmp/ollama.log 2>&1 &
        fi
    fi

    echo -n "Waiting for Ollama"
    for i in {1..10}; do
        if curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
            echo ""
            success "Ollama daemon started"
            break
        fi
        echo -n "."
        sleep 1
    done

    if ! curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        echo ""
        error "Failed to start Ollama. Run manually: ollama serve"
        exit 1
    fi
fi

# Step 3: Pull models
info "Pulling models for '$PRESET' preset..."

for model in $MODELS_STR; do
    if ollama list 2>/dev/null | grep -q "$model"; then
        success "Model $model already available"
    else
        warn "Pulling $model (this may take a few minutes)..."
        ollama pull "$model"
        success "Model $model ready"
    fi
done

# Update config to use selected preset
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/llm_gc/config/models.yaml"

if [ -f "$CONFIG_FILE" ]; then
    # Update the preset line in the config file
    if grep -q "^preset:" "$CONFIG_FILE"; then
        sed -i.bak "s/^preset:.*/preset: $PRESET/" "$CONFIG_FILE" && rm -f "$CONFIG_FILE.bak"
        success "Config updated to use '$PRESET' preset"
    fi
fi

# Done
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Ollama setup complete! ($PRESET)${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Install the plugin in Claude Code:"
echo "     /plugin marketplace add felixmanojh/minions"
echo ""
echo "  2. Try your first minion command:"
echo "     /minion-huddle \"Review my code\""
echo ""
echo "To change models later, edit: llm_gc/config/models.yaml"
echo "Or re-run with: MINIONS_PRESET=medium ./install.sh"
echo ""

# Status check
echo "Status:"
check_command ollama && echo -e "  ${GREEN}✓${NC} Ollama installed" || echo -e "  ${RED}✗${NC} Ollama missing"
curl -s http://127.0.0.1:11434/api/tags >/dev/null && echo -e "  ${GREEN}✓${NC} Ollama running" || echo -e "  ${RED}✗${NC} Ollama not running"
for model in $MODELS_STR; do
    if ollama list 2>/dev/null | grep -q "$model"; then
        echo -e "  ${GREEN}✓${NC} $model"
    else
        echo -e "  ${RED}✗${NC} $model missing"
    fi
done
