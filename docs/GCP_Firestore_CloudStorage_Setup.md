# GCP Firestore & Cloud Storage Setup — Local Dev Emulators + Real Cloud Resources

This document records how local Firestore and Cloud Storage emulators were set up for
development, how the matching real GCP resources were created in `toptal-delivery-apps`, and
how the app's storage layer was built on top of them. For deploying the app itself to Cloud
Run (secrets, the deploy command, IAM for the deploying user), see
`docs/Cloud_Run_Deployment.md` — that document picks up where this one leaves off.

Every step below includes the actual command to check or verify it, not just a statement of
what was found — so this can be rebuilt from scratch if needed.

---

## 1. Why this is needed

Cloud Run's local filesystem is ephemeral and not shared across instances — a file written
by one request may never be seen by a later request, or a different instance. The app's
original `review_queue/{run_id}/` folder-on-disk approach cannot work once deployed there.
Firestore replaces the run metadata (`baseline.json`, `validation_report.json`,
`status.json`) with a real, persistent, queryable document store. Cloud Storage replaces
the generated output files (`.docx`, `.xlsx`, `.pptx`) with a real, persistent file store,
since Firestore documents are capped at 1 MiB and aren't meant for large binary blobs.

---

## 2. Local prerequisites

The Firestore emulator (bundled with the Firebase CLI) requires Node.js/npm and a Java
runtime.

| Tool | Version used | Install source |
|---|---|---|
| Node.js | v24.x (Active LTS) | Official `.msi` from nodejs.org |
| Java (JDK) | Eclipse Temurin 25.x (LTS) | Official `.msi` from adoptium.net |
| Firebase CLI | 15.x | `npm install -g firebase-tools` |

Check what's actually installed on a given machine:
```powershell
node --version
npm --version
java -version
firebase --version
```

### Installation gotchas encountered (Windows)

- **"A DLL required for this install could not be run"** — a generic Windows Installer
  error. Fixed by re-downloading the `.msi` and running it elevated via `msiexec` instead
  of double-clicking:
  ```powershell
  cd $env:USERPROFILE\Downloads
  msiexec /i <installer-name>.msi
  ```
- **`node`/`npm`/`java` not recognized after install** — the installer updated PATH, but
  the current PowerShell session hadn't picked it up. Confirm the tool is actually installed
  (just not on PATH yet) via:
  ```powershell
  Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* |
    Where-Object { $_.DisplayName -like "*Node*" } | Select-Object DisplayName, DisplayVersion
  ```
  then make the PATH addition permanent (elevated PowerShell):
  ```powershell
  [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\nodejs", "Machine")
  ```
  (same pattern for Java's `...\Eclipse Adoptium\jdk-<version>-hotspot\bin` — check the exact
  folder name with `Get-ChildItem "C:\Program Files\Eclipse Adoptium"`), then open a **brand
  new** PowerShell window to pick up the change.
- **`npm` blocked: "running scripts is disabled on this system"** — a PowerShell execution
  policy default, unrelated to the install itself. Fix once, per machine:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
  ```
- **PyCharm's integrated terminal doesn't see a newly-installed tool** even though a
  standalone PowerShell window does — PyCharm's terminal inherits the environment from when
  PyCharm itself was launched. Fix: fully restart PyCharm (not just the terminal tab).

---

## 3. Firestore local emulator

### One-time setup

```powershell
cd C:\Users\james\PycharmProjects\PythonProject\Startup_Kit
firebase init firestore
```

Choices made during `firebase init`:
- **Project setup:** "Don't set up a default project" — this is a purely local emulator
  config, not linked to the real `toptal-delivery-apps` project.
- **Firestore Rules file / indexes file:** accept defaults (`firestore.rules`,
  `firestore.indexes.json`).
- **Agent Skills for Firebase:** Yes — installs Firebase-specific reference files useful to
  an AI coding assistant working on this code; purely additive local files.

This creates `firebase.json`, `.firebaserc`, `firestore.rules`, and `firestore.indexes.json`
in the project root.

### Starting it

```powershell
firebase emulators:start --only firestore
```

- Firestore emulator: `127.0.0.1:8080`
- Emulator UI (browsable dashboard): `http://127.0.0.1:4000`
- The "not authenticated" / metadata-lookup warnings on startup are expected and harmless —
  the emulator doesn't need real GCP credentials.
- **The emulator does not persist data between restarts by default** — closing the terminal
  window it's running in stops it and discards its data. It must be started fresh each dev
  session (or via the startup script in Section 5).

Check it's actually running:
```powershell
curl -UseBasicParsing http://127.0.0.1:8080
```
A refused connection means it isn't running.

---

## 4. Cloud Storage local emulator (`fake-gcs-server`)

Docker was deliberately avoided (would require WSL2 + virtualization setup on Windows, a
heavier lift than needed for this). The standalone Windows binary is used instead.

### Download & extract

1. Download the **Windows + amd64** asset specifically (the release page also lists
   Linux/macOS and ARM64 builds) from
   `https://github.com/fsouza/fake-gcs-server/releases`.
2. Extract into its own folder:
   ```powershell
   cd $env:USERPROFILE\Downloads
   mkdir fake-gcs-server
   tar -xzf fake-gcs-server_<version>_Windows_amd64.tar.gz -C fake-gcs-server
   ```

### Starting it

```powershell
cd $env:USERPROFILE\Downloads\fake-gcs-server
.\fake-gcs-server.exe -scheme http -port 4443
```

- Runs on `http://localhost:4443`
- `-scheme http` avoids self-signed HTTPS certs for local dev (the real Cloud Storage API
  defaults to HTTPS, but the emulator supports either).

Check it's actually running and speaking the real API:
```powershell
curl -UseBasicParsing http://localhost:4443/storage/v1/b
```
Expect a real Cloud Storage-shaped JSON response, e.g. `{"kind":"storage#buckets"}`.

---

## 5. One-command dev startup script

`start-dev-servers.ps1`, in the project root, starts the Firestore emulator, the Cloud
Storage emulator, and the Streamlit app together:

```powershell
# start-dev-servers.ps1
$projectRoot = "C:\Users\james\PycharmProjects\PythonProject\Startup_Kit"
$gcsServerPath = "C:\Users\james\Downloads\fake-gcs-server"

Write-Host "Starting Firestore emulator..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; firebase emulators:start --only firestore"

Write-Host "Starting Cloud Storage emulator..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$gcsServerPath'; .\fake-gcs-server.exe -scheme http -port 4443"

Write-Host "Starting Streamlit app..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; streamlit run src/review_ui/app.py"
```

Run with:
```powershell
cd C:\Users\james\PycharmProjects\PythonProject\Startup_Kit
.\start-dev-servers.ps1
```

If PowerShell blocks the script, apply the execution-policy fix from Section 2.

**Note:** by default, the Streamlit instance this script launches uses the **local**
(`review_queue/`-file-based) storage backend, not Firestore/Cloud Storage. To test against the
real emulators instead, set `REVIEW_STORAGE_BACKEND=gcp`,
`FIRESTORE_EMULATOR_HOST=127.0.0.1:8080`, and `STORAGE_EMULATOR_HOST=http://localhost:4443`
as environment variables before starting Streamlit (either edit the script's Streamlit launch
line, or start Streamlit manually with those variables set).

---

## 6. Real GCP Firestore database (`toptal-delivery-apps`)

### Access required first

Viewing `https://console.cloud.google.com/firestore?project=toptal-delivery-apps` for the
first time failed with a missing-permission error (`datastore.databases.list`) — generic
project-level roles like `run.admin`/`storage.admin` do **not** include Firestore access,
which is a separate GCP service with its own IAM roles. This was requested from IT and
granted (`roles/datastore.owner`, for creating and managing the database).

### Database created with

| Setting | Value | Why |
|---|---|---|
| Edition | **Standard** | Simple query engine with automatic single-field indexing; Enterprise's MongoDB-compatibility layer is unneeded here |
| Mode | **Firestore in Native mode** | Implicit under Standard Edition; this is the mode `google-cloud-firestore` (the real Python client used) is built around. **This choice cannot be changed later.** |
| Location type | **Region** | Simpler/cheaper than Multi-region for an internal PMO tool |
| Region | **us-east1** | Matches the Cloud Storage bucket and the Cloud Run service, for co-location |
| Database ID | `(default)` | Standard convention |

Check the database exists and confirm these settings, in the browser:
```
https://console.cloud.google.com/firestore/databases?project=toptal-delivery-apps
```

**Unrelated permission gap encountered, does not block anything:** a `firebaserules.rulesets.create`
error appeared at one point. Security rules govern client-side web/mobile SDK access; this
app's Python backend uses the server-side client library authenticated via IAM/service-account
credentials, which security rules don't govern — safe to ignore for this app's architecture.

### Required IAM role for the deployed app's service account

The Cloud Run service account, `cloudrun-sa@toptal-delivery-apps.iam.gserviceaccount.com`,
needs `roles/datastore.user` (project-wide) to read/write Firestore at runtime. Check it has
this role:
```
https://console.cloud.google.com/iam-admin/iam?project=toptal-delivery-apps
```
Find `cloudrun-sa@...` in the list and confirm `Cloud Datastore User` is shown. If missing,
request it from IT by the service account's full email, not a broad project role.

---

## 7. Real GCP Cloud Storage bucket (`toptal-delivery-apps`)

### Bucket created with

| Setting | Value | Why |
|---|---|---|
| Name | `toptal-startup-kit-outputs` | Bucket names are globally unique across all of GCP |
| Location type | **Region** | Matches Firestore |
| Region | **us-east1** | Matches Firestore and Cloud Run, for co-location |
| Storage class | **Standard** | Actively-used generated documents, not archival data |
| Hierarchical namespace | **Disabled** | Permanent, one-way choice meant for filesystem-heavy workloads; not needed here |
| Rapid Cache | **Disabled** | Meant for very frequent repeated reads; doesn't match this app's occasional single-user-download pattern |
| Cross-bucket replication | **Not enabled** | Firestore's `baseline` document is the real source of truth; a lost generated file can be regenerated, so a redundant copy adds cost with no real benefit |
| Public access prevention | **On** | Internal PMO deliverables, never meant to be publicly reachable |
| Access control | **Uniform** | Modern recommended default over the older per-object ACL model |
| Soft delete policy | **Disabled** (`0` retention) | The org's policy rejects the default 7-day duration (`'604800' violates constraint 'constraints/storage.softDeletePolicySeconds'`) — this exact constraint recurs elsewhere too, see `docs/Cloud_Run_Deployment.md` Section 5 for the Cloud Build staging-bucket version of the same issue |
| Object versioning | **Disabled** | Firestore's `baseline` is the real source of truth; recovering a specific old file version has low value relative to the ongoing storage cost |
| Bucket/Object retention | **Disabled** | No compliance requirement applies |
| Encryption | **Google-managed** | No requirement for customer-managed (Cloud KMS) keys |

Check the bucket exists and confirm these settings:
```powershell
gcloud storage buckets describe gs://toptal-startup-kit-outputs
```

### Required IAM role for the deployed app's service account

`cloudrun-sa@toptal-delivery-apps.iam.gserviceaccount.com` needs **bucket-scoped**
`roles/storage.objectAdmin` on `toptal-startup-kit-outputs` specifically — not a project-wide
Storage role, which would grant it access to every bucket in the project. This is a real
distinction worth being precise about when requesting it from IT: a project-wide grant by
mistake went to the wrong principal once during this setup (the requesting user's own
account, rather than the service account) because the request wasn't explicit enough about
*which* identity needed *which* scope. When asking IT for this, name both the exact service
account email and the exact bucket name.

Check the current binding:
```powershell
gcloud storage buckets get-iam-policy gs://toptal-startup-kit-outputs
```
Confirm `cloudrun-sa@...` appears with `roles/storage.objectAdmin`.

### Naming convention for objects in this bucket

Cloud Storage has a flat namespace (no real directories), but `/` in an object name displays
as a folder path in the console:

```
runs/{run_id}/<document_name>
```
e.g. `runs/ARC_Application_Implementation_20261010_160224/Startup_Kit.docx`

---

## 8. Composite index for cross-run milestone queries

The schema (Section 9) includes a `runs/{run_id}/milestones` subcollection, queried across
**all** runs at once via a Firestore collection group query (e.g. "every milestone across
every project due in the next two weeks"). This kind of query requires an explicitly
provisioned composite index — the local emulator evaluates it without one (permissive by
design), but **real Cloud Firestore does not** and will fail at runtime with
`FAILED_PRECONDITION: The query requires an index` until this exists.

### Real index definition

```json
{
  "indexes": [
    {
      "collectionGroup": "milestones",
      "queryScope": "COLLECTION_GROUP",
      "fields": [
        { "fieldPath": "external_date", "order": "ASCENDING" },
        { "fieldPath": "milestone_id", "order": "ASCENDING" }
      ]
    }
  ],
  "fieldOverrides": []
}
```
This lives in `firestore.indexes.json` in the repo root.

### How this was actually created (Console, not CLI)

Deploying it via the Firebase CLI (`firebase deploy --only firestore:indexes --project
toptal-delivery-apps`) requires `roles/firebaserules.*` permissions as part of the same
deploy command's rules-validation step, which were not available — the same
`firebaserules.rulesets.create` gap noted in Section 6. Rather than request that role for a
one-time index creation, the index was created directly through the Console instead:

1. Go to
   `https://console.cloud.google.com/firestore/databases/-default-/indexes?project=toptal-delivery-apps`
2. Composite tab → **Create Index**
3. **Collection ID:** `milestones`
4. **Query scope:** **Collection group** (not the default "Collection" — this is the setting
   that actually enables cross-run querying; easy to miss since "Collection" is pre-selected)
5. **Field path 1:** `external_date`, Ascending
6. **Field path 2:** the Console's composite-index form requires at least two fields and will
   reject a single-field submission with "two are required," even though the real query only
   filters/sorts on `external_date`. Add `milestone_id`, Ascending, as the second field purely
   to satisfy this form requirement — it doesn't change what the real query does.
7. Click Create. Index creation is asynchronous — it shows a "Building" status before becoming
   "Enabled," which can take anywhere from a few minutes to longer depending on data volume.

Check its current status:
```
https://console.cloud.google.com/firestore/databases/-default-/indexes?project=toptal-delivery-apps
```
Confirm the `milestones` row shows **Collection group** scope and an **Enabled** status before
relying on `query_milestones_by_date_range()` against real Cloud Firestore.

---

## 9. Firestore schema design

**Collection:** `runs`
**Document ID:** the existing `run_id` string (e.g. `ARC_Application_Implementation_20261010_160224`)
— this makes fetch-by-ID a direct document lookup, no query needed.

**Top-level fields:**

| Field | Type | Source |
|---|---|---|
| `status` | string | app-managed (`pending_review` / `approved` / `generated`) |
| `project_name` | string | `baseline.project_name` |
| `contract_type` | string | `baseline.contract_type` |
| `delivery_manager` | string | `baseline.charter.delivery_manager` |
| `talent_pm` | string | `baseline.charter.talent_pm` |
| `sow_awarded_date` | date | `baseline.sow_awarded_date` |
| `created_at` / `updated_at` | timestamp | app-managed |
| `outputs` | map | which document types were requested (`HTL-36`) |
| `review_audit` | map | Fact Review correction history, when present |
| `baseline` | map | full baseline contents, **including milestones** (kept in one place, see below) |
| `validation_report` | map | full validation report contents |

**Subcollection:** `runs/{run_id}/milestones/{milestone_id}` — a denormalized, queryable
*mirror* of the milestones already inside `baseline.milestones`, needed specifically for
**cross-run** milestone queries (Section 8), which a single document's nested array cannot
support. Milestones remain the full source of truth inside `baseline`; the subcollection is a
derived copy kept in sync whenever a run's baseline is written.

**Design decision explicitly accepted:** milestone data lives in two places (full detail in
`baseline.milestones`, a queryable slice in the subcollection) as a deliberate, bounded sync
cost — the alternative (milestones living *only* in the subcollection) was rejected because it
would require rewiring every existing read path (Workbook builder, Deck generator, Fact
Review, validation logic) that reads `baseline.milestones` directly.

---

## 10. Real implementation status

The storage layer described above is fully built and verified, not just designed:

| Piece | Real location | Status |
|---|---|---|
| Firestore client functions (`write_run`, `get_run`, `query_runs_by_status`, `sync_milestones`, `query_milestones_by_date_range`) | `src/storage/firestore_client.py` | Done, tested against the local emulator |
| Cloud Storage client functions (`upload_file`, `download_file`, `download_file_bytes`, `list_run_files`, `delete_run_files`) | `src/storage/gcs_client.py` | Done, tested against the local emulator |
| `FirestoreReviewStorage` (implements the app's `ReviewStorage` interface) | `src/review_storage/firestore.py` | Done — `create_run`, `get_run`, `list_runs`, `list_pending_runs`, `update_status` (via a real Firestore transaction), `save_corrected_baseline`, `put_generated_files`, `get_file_bytes`, `list_generated_files` all implemented |
| Backend selection | `src/review_storage/__init__.py`, `get_review_storage()` | Done — `REVIEW_STORAGE_BACKEND=local` (default) or `gcp`/`firestore` selects which backend is used; the rest of the app never needs to know which is active |
| Generated-file download buttons working against the GCS backend | `src/review_ui/app.py` | Done (`HTL-38`) — the UI previously assumed a local filesystem path when checking whether a file exists, which silently broke downloads under the GCP backend; now uses `storage.get_file_bytes()`/`list_generated_files()`, backend-agnostic |

**Confirmed end-to-end, live, through the real browser UI** (not just unit tests): a full
Generate → Fact Review correction → Approve → Generate documents cycle, run with
`REVIEW_STORAGE_BACKEND=gcp` against the **local emulators**, including clicking real download
buttons and confirming the downloaded files are genuinely correct.

**Not yet done:** the same end-to-end confirmation against the **real** cloud Firestore/Storage
(as opposed to the local emulators) — this happens naturally as part of the first real Cloud
Run deployment's verification step. See `docs/Cloud_Run_Deployment.md` Section 8 for that
checklist.
