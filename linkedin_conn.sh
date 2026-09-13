#!/usr/bin/env bash
# Wrapper de execucao diaria do bot.
#
# Garante no maximo 1 execucao por dia NESTA maquina, mesmo que o
# systemd timer (Persistent=true) dispare atrasado por causa do PC
# ter ficado desligado no horario agendado. Cada maquina (notebook e
# desktop) guarda seu proprio controle localmente; nao ha coordenacao
# entre elas, entao evite ligar as duas no mesmo dia se quiser garantir
# que o bot rode uma unica vez no total.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/linkedin-connections"
LAST_RUN_FILE="$STATE_DIR/last_run_date"
TODAY="$(date +%Y-%m-%d)"

mkdir -p "$STATE_DIR"

if [[ -f "$LAST_RUN_FILE" && "$(cat "$LAST_RUN_FILE")" == "$TODAY" ]]; then
    echo "[$TODAY] $(hostname): ja rodou hoje nesta maquina, pulando execucao (provavelmente um catch-up atrasado)."
    exit 0
fi

cd "$PROJECT_DIR"
# shellcheck source=/dev/null
source .venv/bin/activate

set +e
python main.py
status=$?
set -e

# Marca o dia como "rodado" mesmo se main.py falhar, para nao ficar
# tentando de novo no mesmo dia (o timer so dispara de novo amanha).
echo "$TODAY" > "$LAST_RUN_FILE"

exit "$status"
