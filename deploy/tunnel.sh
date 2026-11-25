#!/usr/bin/env bash
# Met l'application en ligne depuis ce Mac, gratuitement, via un tunnel Cloudflare.
# Toute la qualité est gardée (Ollama + reclasseur). Le site n'est accessible que
# tant que ce script tourne et que le Mac est allumé. Ctrl+C pour tout arrêter.
#
# Prérequis (une seule fois) : brew install cloudflared
# Usage (depuis la racine du projet) : deploy/tunnel.sh
set -euo pipefail

PORT=5001

command -v cloudflared >/dev/null || { echo "cloudflared absent : brew install cloudflared"; exit 1; }
curl -s -o /dev/null localhost:11434/api/tags || { echo "Ollama ne répond pas : lancer l'application Ollama."; exit 1; }
[ -f chroma/chroma.sqlite3 ] || { echo "Index chroma/ absent : lancer python index.py d'abord."; exit 1; }

arreter() {
  echo; echo "Arrêt du site..."
  kill "${APP:-}" "${TUNNEL:-}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap arreter EXIT INT TERM

echo "1/2 Démarrage de l'application (chargement des modèles, ~30 s)..."
# n'écoute que sur 127.0.0.1 : seul le tunnel y accède, pas le réseau local
.venv/bin/gunicorn --bind 127.0.0.1:$PORT --workers 1 --threads 4 --timeout 180 app:app &
APP=$!
until curl -s -o /dev/null localhost:$PORT/; do
  kill -0 $APP 2>/dev/null || { echo "L'application n'a pas démarré."; exit 1; }
  sleep 2
done

echo "2/2 Ouverture du tunnel Cloudflare..."
JOURNAL=$(mktemp)
cloudflared tunnel --no-autoupdate --url http://localhost:$PORT >"$JOURNAL" 2>&1 &
TUNNEL=$!
until URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$JOURNAL" | head -1) && [ -n "$URL" ]; do
  kill -0 $TUNNEL 2>/dev/null || { echo "Le tunnel n'a pas démarré :"; cat "$JOURNAL"; exit 1; }
  sleep 1
done

echo
echo "Site en ligne : $URL"
echo "(nouvelle adresse à chaque lancement - Ctrl+C pour arrêter)"
wait $APP
