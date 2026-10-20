# Cloud Run Deployment — Startup Kit App

This document covers deploying the Startup Kit app to Google Cloud Run in the real
`toptal-delivery-apps` project, building on the Firestore/Cloud Storage backend set up in
`docs/GCP_Firestore_CloudStorage_Setup.md`. That document covers the storage layer; this one
covers running the app itself in the cloud.

Every step below is written to be re-run from scratch by someone who has never done this
before — each check includes the actual command to run, not just a statement of what was found.

---

## 1. Prerequisites

- Real Firestore database and composite index live in `toptal-delivery-apps` (see the other doc)
- Real Cloud Storage bucket `toptal-startup-kit-outputs`, correctly bucket-scoped (not
  project-wide) IAM
- Service account `cloudrun-sa@toptal-delivery-apps.iam.gserviceaccount.com` already has:
  - `Cloud Datastore User` (Firestore read/write)
  - `Storage Object Admin`, scoped to `toptal-startup-kit-outputs` specifically
- `FirestoreReviewStorage` fully implemented, tested against local emulators, and confirmed
  working end-to-end through the real browser UI (`HTL-14`, `HTL-38`)
- A reviewed `Dockerfile` and `.dockerignore` in the repo root, using `python:3.14-slim` to match
  the real locally-tested interpreter, with no secrets or emulator host variables baked in

### Install and authenticate the `gcloud` CLI (one time, per machine)

1. Download and run the installer from `https://cloud.google.com/sdk/docs/install`
   (`GoogleCloudSDKInstaller.exe` on Windows).
2. Open a **brand new** terminal window after install finishes (PATH changes don't apply to
   already-open windows).
3. Confirm it installed:
   ```powershell
   gcloud --version
   ```
4. Authenticate as your real work account (not a personal Gmail — watch for this if the sign-in
   browser prompt defaults to an already-logged-in account):
   ```powershell
   gcloud auth login
   ```
5. Point it at the right project (it may default to an unrelated project from prior work):
   ```powershell
   gcloud config set project toptal-delivery-apps
   ```
6. Confirm both:
   ```powershell
   gcloud auth list
   gcloud config get-value project
   ```
   `gcloud auth list` should show your real work account marked active (`*`);
   `gcloud config get-value project` should print `toptal-delivery-apps`.

---

## 2. Required APIs

### Check what's currently enabled

```powershell
gcloud services list --enabled
```

### Required for this deployment

| API | Why |
|---|---|
| `firestore.googleapis.com` | Run storage backend |
| `storage.googleapis.com` | Generated file storage |
| `run.googleapis.com` | Cloud Run itself |
| `artifactregistry.googleapis.com` | Stores the built container image |
| `cloudbuild.googleapis.com` | Builds the container image from source |
| `secretmanager.googleapis.com` | Stores the LLM API key outside the image |

### If any are missing

Enabling an API requires `roles/serviceusage.serviceUsageAdmin` (or equivalent). If you hit:

```
Missing required permission
You are missing the required permission serviceusage.services.enable on project toptal-delivery-apps.
```

you do not have this role. Request IT enable the **specific missing API by name** (not a broad
admin role) — e.g.: *"Could you enable `secretmanager.googleapis.com` and
`cloudbuild.googleapis.com` on `toptal-delivery-apps`? I'm missing `serviceusage.services.enable`
to do it myself."* Re-run the `gcloud services list --enabled` check above once they confirm.

---

## 3. Required IAM roles

### For the account running `gcloud` (the person deploying)

| Role | Why | How to request if missing |
|---|---|---|
| `roles/artifactregistry.writer` | Required for `gcloud run deploy --source` to create/push to an Artifact Registry repo, **and** required to pull a pre-built image back out for deployment (confirmed: `gcr.io` pushes are backed by Artifact Registry under the hood as of this writing, so this role is needed regardless of which deploy path is used — see Section 5's deviation log) | *"I need `roles/artifactregistry.writer` on `toptal-delivery-apps` to deploy to Cloud Run — both `gcloud run deploy --source` and deploying a pre-built image need it."* |
| `roles/storage.admin` | Creating the Cloud Build staging bucket if it doesn't already exist (Section 5) | Already granted project-wide as of this writing |

### For `cloudrun-sa` (the identity the deployed service runs as)

| Role | Scope | Why |
|---|---|---|
| `roles/datastore.user` | Project-wide | Already granted |
| `roles/storage.objectAdmin` | `toptal-startup-kit-outputs` bucket only | Already granted |
| `roles/secretmanager.secretAccessor` | The `anthropic-api-key` secret only | Granted in Section 4 below |

### How to check your own current roles

Open in a browser:
```
https://console.cloud.google.com/iam-admin/iam?project=toptal-delivery-apps
```
Find your own email in the list and read the roles shown next to it. (If this page itself denies
you with a `resourcemanager.projects.getIamPolicy` error, you don't have permission to view IAM
on this project at all — request `roles/iam.roleViewer` from IT, or just ask them to confirm your
current roles directly.)

---

## 4. Create the Secret Manager secret

Run this **once**, from the repo root, with your real local Anthropic API key:

```powershell
cd C:\Users\james\PycharmProjects\PythonProject\Startup_Kit
echo "<your real Anthropic API key>" | gcloud secrets create anthropic-api-key --data-file=-
```

Confirm it was created:

```powershell
gcloud secrets describe anthropic-api-key
```

Grant `cloudrun-sa` permission to read it:

```powershell
gcloud secrets add-iam-policy-binding anthropic-api-key `
  --member="serviceAccount:cloudrun-sa@toptal-delivery-apps.iam.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"
```

Confirm the binding:

```powershell
gcloud secrets get-iam-policy anthropic-api-key
```
You should see `cloudrun-sa@...` listed under `roles/secretmanager.secretAccessor`.

**Never** put the real key value directly in a deploy command, a committed file, or a plain
`--set-env-vars` value — only ever via `--set-secrets`, which keeps the real value out of Cloud
Run's own revision metadata and logs.

---

## 5. Build the container image

### Preferred path: let `gcloud run deploy --source` build it automatically

```powershell
gcloud run deploy startup-kit-app `
  --source . `
  --region us-east1 `
  --service-account cloudrun-sa@toptal-delivery-apps.iam.gserviceaccount.com `
  --set-env-vars REVIEW_STORAGE_BACKEND=gcp,GCS_BUCKET_NAME=toptal-startup-kit-outputs,GOOGLE_CLOUD_PROJECT=toptal-delivery-apps,LLM_PROVIDER=anthropic `
  --set-secrets ANTHROPIC_API_KEY=anthropic-api-key:latest `
  --no-allow-unauthenticated
```

This single command builds the image via Cloud Build **and** deploys it — skip the manual build
steps below entirely if this works. It requires `roles/artifactregistry.writer` (Section 3).

### If you hit the Cloud Build staging-bucket soft-delete error

```
ERROR: (gcloud.builds.submit) HTTPError 412: '604800' violates constraint 'constraints/storage.softDeletePolicySeconds'
```

This org has a policy rejecting the default 7-day soft-delete duration on new buckets. Cloud
Build auto-creates a staging bucket named `<PROJECT_ID>_cloudbuild` the first time it's used in a
project, and that auto-creation uses the rejected default. Fix by pre-creating it yourself with
soft delete disabled, **before** running the build:

```powershell
gcloud storage buckets create gs://toptal-delivery-apps_cloudbuild `
  --location=us-east1 `
  --soft-delete-duration=0
```

Confirm it exists with the right settings:

```powershell
gcloud storage buckets describe gs://toptal-delivery-apps_cloudbuild
```
Check `retentionDurationSeconds: '0'` in the output. Then retry the build/deploy command above.

### Manual two-step build (only if `--source` genuinely can't be used)

**Deviation log, confirmed real on this project:** a manual two-step build (build separately, then
deploy from the built image) was tried here as an attempted workaround for a missing
`artifactregistry.writer` grant, on the theory that pushing to the legacy `gcr.io` Container
Registry name might avoid needing Artifact Registry access. **This did not work** — `gcr.io`
pushes are backed by Artifact Registry storage under the hood as of this writing, so the build
step succeeded, but the subsequent deploy step failed pulling the image back out with the same
underlying permission error (`artifactregistry.repositories.downloadArtifacts`). **Conclusion:
`roles/artifactregistry.writer` is required regardless of which path is used — don't spend time on
this workaround again.** The two-step commands are recorded here only for reference:

```powershell
gcloud builds submit --tag gcr.io/toptal-delivery-apps/startup-kit-app
# Check real build status directly if log streaming is denied (see note below):
gcloud builds describe <BUILD_ID> --format="value(status)"

gcloud run deploy startup-kit-app `
  --image gcr.io/toptal-delivery-apps/startup-kit-app `
  --region us-east1 `
  --service-account cloudrun-sa@toptal-delivery-apps.iam.gserviceaccount.com `
  --set-env-vars REVIEW_STORAGE_BACKEND=gcp,GCS_BUCKET_NAME=toptal-startup-kit-outputs,GOOGLE_CLOUD_PROJECT=toptal-delivery-apps,LLM_PROVIDER=anthropic `
  --set-secrets ANTHROPIC_API_KEY=anthropic-api-key:latest `
  --no-allow-unauthenticated
```

**Note on log streaming:** `gcloud builds submit` may return
`This tool can only stream logs if you are Viewer/Owner of the project` even when the build itself
succeeds. This is a separate, narrower permission (live log streaming) from what's needed for the
build to actually complete. Don't treat this message alone as a failure — check the real status
directly via `gcloud builds describe <BUILD_ID> --format="value(status)"` or the Console link
printed alongside the error.

---

## 6. Real deployment command (once `artifactregistry.writer` is granted)

```powershell
gcloud run deploy startup-kit-app `
  --source . `
  --region us-east1 `
  --service-account cloudrun-sa@toptal-delivery-apps.iam.gserviceaccount.com `
  --set-env-vars REVIEW_STORAGE_BACKEND=gcp,GCS_BUCKET_NAME=toptal-startup-kit-outputs,GOOGLE_CLOUD_PROJECT=toptal-delivery-apps,LLM_PROVIDER=anthropic `
  --set-secrets ANTHROPIC_API_KEY=anthropic-api-key:latest `
  --no-allow-unauthenticated
```

### Why each flag is set the way it is

- **`--source .`** — builds the container from the repo's own `Dockerfile` via Cloud Build
  automatically, as part of this one command.
- **`--region us-east1`** — matches Firestore and Cloud Storage's region.
- **`--service-account cloudrun-sa@...`** — the identity the running container authenticates as.
  With no `FIRESTORE_EMULATOR_HOST`/`STORAGE_EMULATOR_HOST` set, the real client libraries fall
  through to Application Default Credentials — i.e. this service account's real identity.
- **`REVIEW_STORAGE_BACKEND=gcp`** — selects `FirestoreReviewStorage` over the local-file backend.
- **`GCS_BUCKET_NAME` / `GOOGLE_CLOUD_PROJECT`** — read by `src/storage/firestore_client.py` and
  `src/storage/gcs_client.py` as their defaults; set explicitly for clarity.
- **`--set-secrets ANTHROPIC_API_KEY=anthropic-api-key:latest`** — injects the real key at
  container start from Secret Manager; `:latest` means "always use the most recent version"
  without needing to redeploy when the key rotates.
- **`--no-allow-unauthenticated`** — deliberate choice given this app handles real client SOW
  content: nobody can reach the deployed URL without being explicitly granted access (Section 7).

### Explicitly NOT set

`FIRESTORE_EMULATOR_HOST`, `STORAGE_EMULATOR_HOST` — their absence is what makes real cloud auth
work; these exist only for local development against the emulators.

---

## 7. Grant access (required, since the service rejects unauthenticated requests)

Confirm the service exists and check who currently has access:

```powershell
gcloud run services describe startup-kit-app --region us-east1 --format="value(status.url)"
gcloud run services get-iam-policy startup-kit-app --region us-east1
```

Grant each person who needs access:

```powershell
gcloud run services add-iam-policy-binding startup-kit-app `
  --region us-east1 `
  --member="user:james.mora@toptal.com" `
  --role="roles/run.invoker"
```

Repeat with a different `--member` value (e.g. `user:colleague@toptal.com`) for each additional
person.

---

## 8. Post-deployment verification (do this for real, every time — don't assume success)

1. Get the real service URL:
   ```powershell
   gcloud run services describe startup-kit-app --region us-east1 --format="value(status.url)"
   ```
2. Open it in a browser as a granted, authenticated user; confirm the app actually loads (not a
   403 or a blank page).
3. Run a real Generate against a real SOW, through Fact Review, approve, and Generate documents.
4. Confirm the run's data genuinely lands in the real Firestore database:
   `https://console.cloud.google.com/firestore/databases/-default-/data/panel?project=toptal-delivery-apps`
5. Confirm the generated files genuinely land in the real bucket:
   `https://console.cloud.google.com/storage/browser/toptal-startup-kit-outputs`
6. Confirm download buttons work against the real deployed Cloud Storage data (this exact path
   was the subject of `HTL-38`'s fix — re-confirm it specifically against the real cloud
   deployment, not just the local emulators).

---

## 9. Status as of this writing

- [x] `gcloud` installed, authenticated as `james.mora@toptal.com`, project set correctly
- [x] `secretmanager.googleapis.com` and `cloudbuild.googleapis.com` enabled
- [x] `anthropic-api-key` secret created; `cloudrun-sa` granted `secretmanager.secretAccessor`
- [x] Cloud Build staging bucket soft-delete issue hit and fixed
- [x] A real container image build completed successfully (confirmed via
      `gcloud builds describe <BUILD_ID>`, status `SUCCESS`)
- [ ] `roles/artifactregistry.writer` — requested from IT, pending as of this writing. **Blocks
      the actual deploy step** — both the `--source` path and the pre-built-image path fail
      without it (see Section 5's deviation log)
- [ ] Run the actual `gcloud run deploy` command successfully
- [ ] Grant `roles/run.invoker` to everyone who needs access
- [ ] Complete the post-deployment verification checklist (Section 8)
