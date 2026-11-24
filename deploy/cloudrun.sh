#!/usr/bin/env bash
# Publie l'application sur Google Cloud Run.
#
# Prérequis (une seule fois) :
#   brew install --cask gcloud-cli
#   gcloud auth login
#   gcloud config set project <ID_DU_PROJET>     # projet avec facturation activée
#
# Usage (depuis la racine du projet) :
#   MISTRAL_API_KEY=... deploy/cloudrun.sh
# La clé n'est demandée qu'au premier lancement (elle est ensuite dans Secret Manager).
set -euo pipefail

SERVICE=rag-lois
REGION=europe-west1          # Belgique
SECRET=mistral-api-key

PROJET=$(gcloud config get-value project 2>/dev/null)
[ -n "$PROJET" ] || { echo "Aucun projet : gcloud config set project <ID_DU_PROJET>"; exit 1; }
[ -f chroma/chroma.sqlite3 ] || { echo "Index chroma/ absent : lancer python index.py d'abord."; exit 1; }
echo "Projet : $PROJET, région : $REGION"

echo "1/3 Activation des services Google nécessaires..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com

echo "2/3 Clé Mistral dans Secret Manager..."
if ! gcloud secrets describe "$SECRET" >/dev/null 2>&1; then
  [ -n "${MISTRAL_API_KEY:-}" ] || { echo "Premier lancement : définir MISTRAL_API_KEY."; exit 1; }
  printf '%s' "$MISTRAL_API_KEY" | gcloud secrets create "$SECRET" --data-file=- --replication-policy=automatic
fi
# le service Cloud Run (compte de service par défaut) doit pouvoir lire le secret
NUMERO=$(gcloud projects describe "$PROJET" --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding "$SECRET" --quiet \
  --member="serviceAccount:${NUMERO}-compute@developer.gserviceaccount.com" \
  --role=roles/secretmanager.secretAccessor >/dev/null

echo "3/3 Construction de l'image et déploiement (10 à 20 min la première fois)..."
# --memory 6Gi : les deux modèles + torch tiennent dans ~4,5 Go
# --min-instances 0 : éteint sans visiteur (gratuit), 1er appel lent ensuite
# --max-instances 1 : plafonne la facture et garde la limite par IP cohérente
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --memory 6Gi --cpu 2 --cpu-boost \
  --min-instances 0 --max-instances 1 \
  --concurrency 4 --timeout 120 \
  --set-secrets "MISTRAL_API_KEY=${SECRET}:latest" \
  --allow-unauthenticated \
  --quiet

echo "Adresse publique :"
gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)'
