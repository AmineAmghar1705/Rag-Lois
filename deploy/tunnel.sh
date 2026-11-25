#!/usr/bin/env bash
# Met l'application en ligne depuis ce Mac, gratuitement, via Tailscale Funnel.
# Adresse fixe : https://<nom-du-mac>.<tailnet>.ts.net (la même à chaque lancement).
# Toute la qualité est gardée (Ollama + reclasseur). Le site n'est accessible que
# tant que ce script tourne et que le Mac est allumé. Ctrl+C pour tout arrêter.
#
# Prérequis (une seule fois) :
#   - application Tailscale installée et connectée
#   - HTTPS et Funnel activés : https://login.tailscale.com/admin/dns (HTTPS Certificates)
#     et la règle « funnel » dans https://login.tailscale.com/admin/acls
#     (le premier lancement de « tailscale funnel » affiche le lien direct)
# Usage (depuis la racine du projet) : deploy/tunnel.sh
set -euo pipefail

PORT=5001

command -v tailscale >/dev/null || { echo "Commande tailscale absente : installer l'application Tailscale."; exit 1; }
tailscale status >/dev/null 2>&1 || { echo "Tailscale n'est pas connecté : ouvrir l'application Tailscale."; exit 1; }
curl -s -o /dev/null localhost:11434/api/tags || { echo "Ollama ne répond pas : lancer l'application Ollama."; exit 1; }
[ -f chroma/chroma.sqlite3 ] || { echo "Index chroma/ absent : lancer python index.py d'abord."; exit 1; }

arreter() {
  echo; echo "Arrêt du site..."
  kill "${TUNNEL:-}" "${APP:-}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap arreter EXIT INT TERM

echo "1/2 Démarrage de l'application (chargement des modèles, ~30 s)..."
# n'écoute que sur 127.0.0.1 : seul Funnel y accède, pas le réseau local
.venv/bin/gunicorn --bind 127.0.0.1:$PORT --workers 1 --threads 4 --timeout 180 app:app &
APP=$!
until curl -s -o /dev/null localhost:$PORT/; do
  kill -0 $APP 2>/dev/null || { echo "L'application n'a pas démarré."; exit 1; }
  sleep 2
done

echo "2/2 Ouverture de Tailscale Funnel..."
# au premier lancement, Tailscale peut afficher un lien pour activer Funnel : l'ouvrir,
# valider, puis relancer ce script
tailscale funnel $PORT &
TUNNEL=$!

NOM=$(tailscale status --json | python3 -c "import json, sys; print(json.load(sys.stdin)['Self']['DNSName'].rstrip('.'))")
sleep 3
kill -0 $TUNNEL 2>/dev/null || { echo "Funnel n'a pas démarré (voir le message ci-dessus)."; exit 1; }

echo
echo "Site en ligne : https://$NOM"
echo "(adresse fixe - Ctrl+C pour arrêter)"
wait $APP
