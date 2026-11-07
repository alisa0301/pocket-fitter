#!/usr/bin/env bash
# One-time Google Cloud setup for deploying Pocket Fitter from GitHub Actions to Cloud Run.
# Usage: ./scripts/gcp-setup.sh <PROJECT_ID> [REGION] [GITHUB_REPO]
# Requires: gcloud logged in as a project Owner (gcloud auth login).
set -euo pipefail

PROJECT_ID="${1:?Usage: $0 <PROJECT_ID> [REGION] [GITHUB_REPO]}"
REGION="${2:-europe-north1}"
GITHUB_REPO="${3:-alisa0301/pocket-fitter}"
SERVICE=pocket-fitter
AR_REPO=pocket-fitter
POOL=github
PROVIDER=github
DEPLOY_SA="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
RUNTIME_SA="pocket-fitter-run@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud config set project "$PROJECT_ID" >/dev/null
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

echo "==> Enabling APIs"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com iamcredentials.googleapis.com sts.googleapis.com

echo "==> Artifact Registry repo"
gcloud artifacts repositories describe "$AR_REPO" --location "$REGION" >/dev/null 2>&1 ||
  gcloud artifacts repositories create "$AR_REPO" --repository-format docker --location "$REGION"

echo "==> Service accounts"
for sa in github-deployer pocket-fitter-run; do
  gcloud iam service-accounts describe "${sa}@${PROJECT_ID}.iam.gserviceaccount.com" >/dev/null 2>&1 ||
    gcloud iam service-accounts create "$sa"
done
for role in roles/run.admin roles/artifactregistry.writer; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:$DEPLOY_SA" \
    --role "$role" --condition None >/dev/null
done
# Deployer may deploy services that run as the runtime SA.
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" \
  --member "serviceAccount:$DEPLOY_SA" --role roles/iam.serviceAccountUser >/dev/null

echo "==> Gemini API key secret"
if ! gcloud secrets describe gemini-api-key >/dev/null 2>&1; then
  read -rsp "Paste your Gemini API key (input hidden): " KEY; echo
  printf '%s' "$KEY" | gcloud secrets create gemini-api-key --data-file=-
fi
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member "serviceAccount:$RUNTIME_SA" --role roles/secretmanager.secretAccessor >/dev/null

echo "==> Workload Identity Federation for $GITHUB_REPO"
gcloud iam workload-identity-pools describe "$POOL" --location global >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools create "$POOL" --location global --display-name "GitHub Actions"
gcloud iam workload-identity-pools providers describe "$PROVIDER" --location global \
  --workload-identity-pool "$POOL" >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" --location global \
    --workload-identity-pool "$POOL" --display-name "GitHub" \
    --issuer-uri "https://token.actions.githubusercontent.com" \
    --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition "assertion.repository == '${GITHUB_REPO}'"
gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/attribute.repository/${GITHUB_REPO}" >/dev/null

WIF_PROVIDER="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/providers/${PROVIDER}"

cat <<OUT

Done. Add these as GitHub repository *variables*
(Settings -> Secrets and variables -> Actions -> Variables):

  GCP_PROJECT_ID    = ${PROJECT_ID}
  GCP_REGION        = ${REGION}
  GCP_WIF_PROVIDER  = ${WIF_PROVIDER}
  GCP_DEPLOY_SA     = ${DEPLOY_SA}
  GCP_RUNTIME_SA    = ${RUNTIME_SA}

Or with the GitHub CLI:
  gh variable set GCP_PROJECT_ID   -R ${GITHUB_REPO} -b ${PROJECT_ID}
  gh variable set GCP_REGION       -R ${GITHUB_REPO} -b ${REGION}
  gh variable set GCP_WIF_PROVIDER -R ${GITHUB_REPO} -b ${WIF_PROVIDER}
  gh variable set GCP_DEPLOY_SA    -R ${GITHUB_REPO} -b ${DEPLOY_SA}
  gh variable set GCP_RUNTIME_SA   -R ${GITHUB_REPO} -b ${RUNTIME_SA}
OUT
