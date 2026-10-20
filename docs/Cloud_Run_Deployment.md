# Cloud Run Deployment — Startup Kit App

This document covers deploying the Startup Kit app to Google Cloud Run in the real
`toptal-delivery-apps` project, building on the Firestore/Cloud Storage backend set up in
`docs/GCP_Firestore_CloudStorage_Setup.md`. That document covers the storage layer; this one
covers running the app itself in the cloud.

---

## 1. Prerequisites confirmed so far

- Real Firestore database and composite index live in `toptal-delivery-apps` (see the other doc)
- Real Cloud Storage bucket `toptal-startup-kit-outputs`, correctly bucket-scoped (not project-wide) IAM
- Service account `cloudrun-sa@toptal-delivery-apps.iam.gserviceaccount.com` already has:
  - `Cloud Datastore User` (Firestore read/write)
  - `Storage Object Admin`, scoped to `toptal-startup-kit-outputs` specifically
- `FirestoreReviewStorage` fully implemented, tested against local emulators, and confirmed
  working end-to-end through the real browser UI (`HTL-14`, `HTL-38`)
- A reviewed `Dockerfile` and `.dockerignore` in the repo root, using `python:3.14-slim` to match
  the real locally-tested interpreter, with no secrets or emulator host variables baked in
- `gcloud` CLI installed locally, authenticated as `james.mora@toptal.com`, project set to
  `toptal-delivery-apps`

## 2. APIs required

Checked via `gcloud services list --enabled`. Already enabled (confirmed):
`firestore.googleapis.com`, `storage.googleapis.com`, `storage-api.googleapis.com`,
`run.googleapis.com`, `artifactregistry.googleapis.com`.

**Not yet enabled, requested from IT (pending as of this writing):**
- `secretmanager.googleapis.com` — needed to store `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` outside
  the container image
- `cloudbuild.googleapis.com` — needed for `gcloud run deploy --source .` to build the container
  image (this calls Cloud Build under the hood)

Enabling either of these requires `roles/serviceusage.services.enable` (or an equivalent admin
role), which this account does not have — same pattern as the Firestore and Service Usage API
gaps hit earlier in this project. Request IT enable the specific API rather than requesting a
broad admin role.

## 3. Secrets setup (Secret Manager)

Once `secretmanager.googleapis.com` is enabled:

1. Create the secret holding the real Anthropic API key:
   ```powershell
   echo "<the real key>" | gcloud secrets create anthropic-api-key --data-file=-
   ```
2. Grant `cloudrun-sa` permission to read it:
   ```powershell
   gcloud secrets add-iam-policy-binding anthropic-api-key `
     --member="serviceAccount:cloudrun-sa@toptal-delivery-apps.iam.gserviceaccount.com" `
     --role="roles/secretmanager.secretAccessor"
   ```
3. The deploy command (below) references this secret via `--set-secrets`, which injects it as the
   `ANTHROPIC_API_KEY` environment variable inside the running container — the app's existing
   `src/config.py` reads it exactly the same way it reads a local `.env` value, no code change
   needed.

**Never** put the real API key directly in the deploy command, a committed file, or a plain
`--set-env-vars` value — only ever via `--set-secrets`, which keeps the real value out of Cloud
Run's own revision metadata and logs.

## 4. Real deployment command

```powershell
gcloud run deploy startup-kit-app `
  --source . `
  --region us-east1 `
  --service-account cloudrun-sa@toptal-delivery-apps.iam.gserviceaccount.com `
  --set-env-vars REVIEW_STORAGE_BACKEND=gcp,GCS_BUCKET_NAME=toptal-startup-kit-outputs,GOOGLE_CLOUD_PROJECT=toptal-delivery-apps,LLM_PROVIDER=anthropic `
  --set-secrets ANTHROPIC_API_KEY=anthropic-api-key:latest `
  --no-allow-unauthenticated
```

### Why each piece is set the way it is

- **`--source .`** — builds the container from the repo's own `Dockerfile` via Cloud Build
  automatically, as part of this one command; no separate `gcloud builds submit` call needed.
- **`--region us-east1`** — matches Firestore and Cloud Storage's region, avoiding unnecessary
  cross-region latency/cost.
- **`--service-account cloudrun-sa@...`** — the identity the running container authenticates as;
  this is what makes `FIRESTORE_EMULATOR_HOST`/`STORAGE_EMULATOR_HOST` being *absent* meaningful —
  with no emulator host set, the real `google-cloud-firestore`/`google-cloud-storage` clients fall
  through to Application Default Credentials, i.e. this service account's real identity.
- **`REVIEW_STORAGE_BACKEND=gcp`** — selects `FirestoreReviewStorage` over the local-file backend.
- **`GCS_BUCKET_NAME` / `GOOGLE_CLOUD_PROJECT`** — read by `src/storage/firestore_client.py` and
  `src/storage/gcs_client.py` as their defaults; set explicitly here rather than relying on the
  code's own fallback values, for clarity.
- **`--set-secrets ANTHROPIC_API_KEY=anthropic-api-key:latest`** — injects the real key at
  container start from Secret Manager, `:latest` meaning "always use the most recently added
  version of this secret" without needing to redeploy when the key rotates.
- **`--no-allow-unauthenticated`** — deliberate choice, given this app handles real client SOW
  content: nobody can reach the deployed URL without being explicitly granted access (below).

### Explicitly NOT set

- `FIRESTORE_EMULATOR_HOST`, `STORAGE_EMULATOR_HOST` — their absence is what makes real cloud
  auth work; these exist only for local development against the emulators.

## 5. Granting access (since the service requires authentication)

After deployment, each person who needs to reach the app must be explicitly granted
`roles/run.invoker` on this specific service (this does not happen automatically, even for the
person who deployed it):

```powershell
gcloud run services add-iam-policy-binding startup-kit-app `
  --region us-east1 `
  --member="user:james.mora@toptal.com" `
  --role="roles/run.invoker"
```

Repeat with a different `--member` value for each additional person.

## 6. Post-deployment verification (not yet done)

Once deployed, confirm genuinely — the same hands-on standard used throughout this project,
not just "it deployed without erroring":

1. Open the deployed URL as an authenticated, granted user; confirm the app actually loads.
2. Run a real Generate against a real SOW, through Fact Review, approve, and Generate documents.
3. Confirm the run's data genuinely lands in the real Firestore database (check the Console) and
   the generated files genuinely land in the real `toptal-startup-kit-outputs` bucket — not a
   silent fallback to something broken.
4. Confirm download buttons work against the real deployed Cloud Storage data (this exact path
   was the subject of `HTL-38`'s fix; worth specifically re-confirming here against the real
   cloud deployment, not just the local emulators).

## 7. Still open / not yet done

- [ ] `secretmanager.googleapis.com` and `cloudbuild.googleapis.com` enablement — requested from
      IT, pending
- [ ] Create the real `anthropic-api-key` secret and grant `cloudrun-sa` access to it
- [ ] Run the actual `gcloud run deploy` command for the first time
- [ ] Grant `roles/run.invoker` to everyone who needs access
- [ ] Complete the post-deployment verification checklist above
