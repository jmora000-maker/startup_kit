# GCP Firestore & Cloud Storage Setup — Local Dev Emulators + Real Cloud Resources

This document records how local Firestore and Cloud Storage emulators were set up for
development, how the matching real GCP resources were created in `toptal-delivery-apps`,
and how to start the local dev environment going forward. This is groundwork for migrating
the Startup Kit app's storage layer off local disk (`review_queue/`) onto Firestore
(run metadata) and Cloud Storage (generated document files) ahead of a Cloud Run deployment.

---

## 1. Why this is needed

Cloud Run's local filesystem is ephemeral and not shared across instances — a file written
by one request may never be seen by a later request, or a different instance. The app's
current `review_queue/{run_id}/` folder-on-disk approach cannot work once deployed there.
Firestore replaces the run metadata (`baseline.json`, `validation_report.json`,
`status.json`) with a real, persistent, queryable document store. Cloud Storage replaces
the generated output files (`.docx`, `.xlsx`, `.pptx`) with a real, persistent file store,
since Firestore documents are capped at 1 MiB and aren't meant for large binary blobs.

---

## 2. Local prerequisites installed

The Firestore emulator (bundled with the Firebase CLI) requires Node.js/npm and a Java
runtime. These were installed fresh:

| Tool | Version installed | Notes |
|---|---|---|
| Node.js | v24.22.0 (Active LTS "Krypton") | Installed via the official `.msi` from nodejs.org |
| npm | 11.19.1 | Bundled with Node |
| Java (JDK) | Eclipse Temurin 25.0.4.1 (LTS) | Installed via the official `.msi` from adoptium.net |
| Firebase CLI | 15.34.0 | `npm install -g firebase-tools` |

### Installation gotchas encountered (Windows)

- **"A DLL required for this install could not be run"** — a generic Windows Installer
  error. Fixed by re-downloading the `.msi` and running it elevated via `msiexec` instead
  of double-clicking:
  ```powershell
  cd $env:USERPROFILE\Downloads
  msiexec /i <installer-name>.msi
  ```
- **`node`/`npm`/`java` not recognized after install** — the installer updated PATH, but
  the current PowerShell session hadn't picked it up. Confirmed the tool was actually
  installed (it was, just not on PATH yet) via:
  ```powershell
  Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* |
    Where-Object { $_.DisplayName -like "*Node*" } | Select-Object DisplayName, DisplayVersion
  ```
  then made the PATH addition permanent (elevated PowerShell):
  ```powershell
  [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\nodejs", "Machine")
  ```
  (same pattern used for Java's `...\Eclipse Adoptium\jdk-25.0.4.101-hotspot\bin`), then
  opened a **brand new** PowerShell window to pick up the change.
- **`npm` blocked: "running scripts is disabled on this system"** — a PowerShell execution
  policy default, unrelated to the install itself. Fixed once, per user, with:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
  ```
- **PyCharm's integrated terminal didn't see `firebase`** even though a standalone
  PowerShell window did — PyCharm's terminal inherits the environment from when PyCharm
  itself was launched. Fixed by fully restarting PyCharm (not just the terminal tab).

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
- **Firestore Rules file:** accepted default (`firestore.rules`)
- **Firestore indexes file:** accepted default (`firestore.indexes.json`)
- **Agent Skills for Firebase:** Yes — installs Firebase-specific reference files useful to
  an AI coding assistant working on the Firestore integration code; purely additive local
  files, no effect on the emulator itself.

This created `firebase.json`, `.firebaserc`, `firestore.rules`, and
`firestore.indexes.json` in the project root.

### Starting it

```powershell
firebase emulators:start --only firestore
```

- Firestore emulator: `127.0.0.1:8080`
- Emulator UI (browsable dashboard): `http://127.0.0.1:4000`
- The "not authenticated" / metadata-lookup warnings on startup are expected and harmless
  — the emulator doesn't need real GCP credentials.
- **The emulator does not persist data between restarts by default** — closing the
  terminal window it's running in stops it and discards its data.

Verified working via:
```powershell
curl -UseBasicParsing http://127.0.0.1:8080
```
(a refused connection means the emulator isn't currently running — it must be started
fresh each dev session).

---

## 4. Cloud Storage local emulator (`fake-gcs-server`)

Docker was deliberately avoided (would require WSL2 + virtualization setup on Windows,
a heavier lift than needed). Used the standalone Windows binary instead.

### Download & extract

1. Downloaded `fake-gcs-server_1.56.1_Windows_amd64.tar.gz` from
   `https://github.com/fsouza/fake-gcs-server/releases`
   (confirm the **Windows** + **amd64** asset specifically — the release page also lists
   Linux/macOS and ARM64 builds).
2. Extracted into its own folder to avoid confusion with any pre-existing copy:
   ```powershell
   cd $env:USERPROFILE\Downloads
   mkdir fake-gcs-server
   tar -xzf fake-gcs-server_1.56.1_Windows_amd64.tar.gz -C fake-gcs-server
   ```

### Starting it

```powershell
cd $env:USERPROFILE\Downloads\fake-gcs-server
.\fake-gcs-server.exe -scheme http -port 4443
```

- Runs on `http://localhost:4443`
- `-scheme http` avoids dealing with self-signed HTTPS certs for local dev (the real
  Cloud Storage API defaults to HTTPS, but the emulator supports either).

Verified working via:
```powershell
curl -UseBasicParsing http://localhost:4443/storage/v1/b
```
Expected a real Cloud Storage-shaped JSON response, e.g. `{"kind":"storage#buckets"}`,
confirming the emulator correctly speaks the real Cloud Storage API.

---

## 5. One-command dev startup script

To avoid manually starting three separate processes (Firestore emulator, Cloud Storage
emulator, the Streamlit app) every session, `start-dev-servers.ps1` was created in the
project root:

```powershell
# start-dev-servers.ps1
# Launches Firestore emulator, Cloud Storage emulator, and the Streamlit app
# each in their own window, for local development.

$projectRoot = "C:\Users\james\PycharmProjects\PythonProject\Startup_Kit"
$gcsServerPath = "C:\Users\james\Downloads\fake-gcs-server"

Write-Host "Starting Firestore emulator..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; firebase emulators:start --only firestore"

Write-Host "Starting Cloud Storage emulator..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$gcsServerPath'; .\fake-gcs-server.exe -scheme http -port 4443"

Write-Host "Starting Streamlit app..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; streamlit run src/review_ui/app.py"

Write-Host "All three dev servers launching in separate windows."
```

Run with:
```powershell
cd C:\Users\james\PycharmProjects\PythonProject\Startup_Kit
.\start-dev-servers.ps1
```

If PowerShell blocks the script from running, the same execution-policy fix from Section 2
applies:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

---

## 6. Real GCP Firestore database (`toptal-delivery-apps`)

### Access required first

Initial attempt to view `https://console.cloud.google.com/firestore?project=toptal-delivery-apps`
failed with a missing-permission error (`datastore.databases.list`) — the existing
`run.admin` and `storage.admin` roles do **not** include Firestore/Datastore access, which
is a separate GCP service with its own IAM roles. Access was requested from IT/the GCP
admin (`roles/datastore.owner` for setup, plus confirmation of the Cloud Run service
account for later `roles/datastore.user` runtime access) and subsequently granted.

### Database created with

| Setting | Value | Why |
|---|---|---|
| Edition | **Standard** | Simple query engine with automatic single-field indexing; Enterprise's MongoDB-compatibility/advanced query engine is unneeded for this app |
| Mode | **Firestore in Native mode** | Implicit under Standard Edition (the only mode it supports); this is the mode the `google-cloud-firestore` Python client is built around. Datastore mode / MongoDB-compatible mode were explicitly avoided. **This choice cannot be changed later.** |
| Location type | **Region** (not Multi-region) | No Cloud Run service existed yet to match a region to; a single region is simpler/cheaper and sufficient for an internal PMO tool |
| Region | **us-east1** (South Carolina) | Chosen as the general "US East" region; will also be used for the Cloud Storage bucket and the eventual Cloud Run service, to keep everything co-located |
| Database ID | `(default)` | Standard convention absent a reason for multiple databases |

**Note:** a separate, unrelated permission gap (`firebaserules.rulesets.create`, needed to
create *security rules*) also appeared during setup. This does not block anything — security
rules govern client-side web/mobile SDK access; this app's Python backend uses the
server-side client library authenticated via IAM/service-account credentials, which security
rules don't govern.

---

## 7. Real GCP Cloud Storage bucket (`toptal-delivery-apps`)

### Bucket created with

| Setting | Value | Why |
|---|---|---|
| Name | `toptal-startup-kit-outputs` | Bucket names are globally unique across all of GCP, not just this project |
| Location type | **Region** | Matches Firestore's choice; lowest latency / simplest / cheapest for this app's needs |
| Region | **us-east1** | Matches Firestore, for co-location |
| Storage class | **Standard** | Actively-used generated documents, not archival data |
| Hierarchical namespace | **Disabled** | A permanent, one-way choice meant for filesystem-heavy workloads (ML training, analytics); not needed for this app's simple write-once/read-occasionally pattern |
| Rapid Cache | **Disabled** | Meant for data read very frequently/repeatedly (e.g. ML inference); doesn't match this app's occasional single-user-download pattern |
| Cross-bucket replication | **Not enabled** | The real source of truth is the Firestore `baseline` document, not the generated files — if a file were lost it could be regenerated, so a redundant replicated copy adds cost with no real benefit here |
| Public access prevention | **On** | These are internal PMO deliverables, never meant to be publicly reachable |
| Access control | **Uniform** | The modern recommended default over the older per-object ACL model |
| Soft delete policy | **Disabled** (`0` retention) | The org's Org Policy constraint rejected the default 7-day duration (`'604800' violates constraint 'constraints/storage.softDeletePolicySeconds'`); disabling was the pragmatic path forward given these files are regenerable from Firestore anyway |
| Object versioning | **Disabled** | Protects against overwritten versions, not accidental deletion; Firestore's `baseline` is the real source of truth, so recovering a specific prior version of a generated file is low-value relative to the ongoing storage cost of keeping every version |
| Bucket/Object retention | **Disabled** | No compliance-driven "cannot delete for N years" requirement applies here |
| Encryption | **Google-managed** | No specific requirement for customer-managed (Cloud KMS) keys |

### Naming convention for objects in this bucket

Cloud Storage has a flat namespace (no real directories), but `/` in an object name
displays as a folder path in the console. Agreed convention:

```
runs/{run_id}/startup_kit.docx
runs/{run_id}/readiness_checklist.docx
runs/{run_id}/delivery_workbook.xlsx
runs/{run_id}/onboarding_deck.pptx
```

---

## 8. Firestore schema design (for the Python client code, not yet implemented)

**Collection:** `runs`
**Document ID:** the existing `run_id` string (e.g. `ARC_Application_Implementation_20261010_160224`)
— this makes fetch-by-ID a direct document lookup, no query needed.

**Top-level fields** (chosen for direct queryability — confirmed real filtering needs:
status, project, contract type, delivery manager, talent PM, award date, and milestone
dates both within and across runs):

| Field | Type | Source today |
|---|---|---|
| `status` | string | app-managed (`pending_review` / `approved` / `generated`) |
| `project_name` | string | `baseline.project_name` |
| `contract_type` | string | `baseline.contract_type` |
| `delivery_manager` | string | `baseline.charter.delivery_manager` |
| `talent_pm` | string | `baseline.charter.talent_pm` |
| `sow_awarded_date` | date | `baseline.sow_awarded_date` |
| `created_at` / `updated_at` | timestamp | app-managed |
| `baseline` | map | full `baseline.json` contents, **including milestones** (kept in one place — see below) |
| `validation_report` | map | full `validation_report.json` contents |

**Subcollection:** `runs/{run_id}/milestones/{milestone_id}` — a denormalized, queryable
*mirror* of the milestones already inside `baseline.milestones`, needed specifically to
support **cross-run** milestone queries (e.g. "every milestone across every project due in
the next two weeks") via Firestore's collection group query feature, which a single
document's nested array cannot support. Milestones remain the full source of truth inside
`baseline` (no rewiring of existing code paths that read `baseline.milestones` directly);
the subcollection is a derived copy kept in sync whenever a run's `baseline` is written.

**Design decision explicitly accepted:** milestone data lives in two places (full detail in
`baseline.milestones`, a queryable slice in the subcollection) as a deliberate, bounded
sync cost — the alternative (milestones living *only* in the subcollection) was rejected
because it would require rewiring every existing read path (Workbook builder, Deck
generator, Fact Review, validation logic) that currently reads `baseline.milestones`
directly, for an unverified amount of real risk.

---

## 9. Still to do (not yet implemented)

- Write the real Python client code: `write_run()`, `get_run()`,
  `query_runs_by_status()`, and the milestone-subcollection sync, using
  `google-cloud-firestore` and `google-cloud-storage` — developed and tested against the
  two local emulators above via `FIRESTORE_EMULATOR_HOST=127.0.0.1:8080` and
  `STORAGE_EMULATOR_HOST=http://localhost:4443` (no code branching needed between
  emulator and real-cloud paths — same client libraries, different target endpoint).
- Swap the app's storage layer from `review_queue/` local files to this new backend.
- Real GCP credentials setup for when the app is deployed to Cloud Run (a separate,
  final verification step — nearly all of the storage-layer code above can be built and
  fully tested locally against the emulators before this is needed).
