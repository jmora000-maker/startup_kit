# Identity-Aware Proxy (IAP) Setup Plan — Startup Kit App

This document plans the work to put Identity-Aware Proxy in front of the deployed
`startup-kit-app` Cloud Run service, replacing today's per-person `run.invoker` + `gcloud`
access model with a normal Google sign-in redirect that works in any browser, no CLI needed.
It builds on `docs/Cloud_Run_Deployment.md` (the service that already exists) and
`docs/GCP_Firestore_CloudStorage_Setup.md` (the storage layer behind it).

---

## 0. Real outcome — DONE, confirmed working, same night this plan was written

**This was completed faster than planned, using a more layered, defense-in-depth setup than
Sections 1–4 below describe on their own.** The app is now live at
**`https://startup-kit.toptal.tech/`**,
protected by a genuine Google sign-in redirect — no `gcloud`, no proxy tunnel, no CLI needed on
the user's end at all.

**What actually happened, vs. what this plan assumed — corrected twice, the second time for
real, after checking the Console carefully:** Sections 1–4 below were written around the older,
more widely-documented IAP pattern — enabling IAP on an External HTTPS Load Balancer's *backend
service*. The real IAP Console
(`https://console.cloud.google.com/security/iap?project=toptal-delivery-apps`) lists two
IAP-eligible resources for `startup-kit-app` — a **Backend Services** entry (from the load
balancer IT built) and a **Cloud Run Services** entry (the Cloud Run service itself) — which
initially looked like both were deliberately enabled together. **That reading was wrong, and was
corrected after checking Google's own documentation directly**, which states a real, hard
limitation: *"You cannot configure IAP on both the load balancer and the Cloud Run service."*
Checking the actual per-resource toggle in the Console confirmed which one is genuinely real: the
**Cloud Run Services** entry shows IAP checked/enabled; the **Backend Services** entry does not —
it only appears in the list because it's associated via the load balancer's connection, not
because it's independently enforcing anything. This matches Google's newer native Cloud Run IAP
support (confirmed via Google's own IAP release notes: "Preview: You can now enable IAP directly
on your Cloud Run services without configuring load balancers") and matches Guilherme's own stated
intent: *"IAP should be set in your app deployment, not in the backend service (otherwise
`*.run.app` would allow access without auth)."*

**The one practical thing this means for managing access:** on that Console page, always select
the **"Cloud Run Services — `startup-kit-app`"** row specifically when granting or checking
someone's access — not the "Backend Services" row, which isn't the real gatekeeper and granting
access there would do nothing.

**Real division of labor, as it actually happened:**
- IT: built the load balancer, static IP, DNS record, and managed certificate for
  `startup-kit.toptal.tech`
- IT: enabled IAP directly on the `startup-kit-app` Cloud Run service, and set its ingress to
  `internal-and-cloud-load-balancing`
- This project: nothing further was needed — IT's setup already produced a fully working result

**Real, independent verification performed (not just trusting the UI):**
1. Opened `https://startup-kit.toptal.tech/` in a fresh private/incognito browser window (no
   existing Google session) — confirmed a genuine Google sign-in redirect appeared, and signing in
   as `james.mora@toptal.com` landed in the real app
2. Ran a complete real session through it: Generate → Fact Review → Approve → Generate documents
   (run `Pilot-Ready_Product_Implementation_20261021_221841`)
3. Independently confirmed via direct Firestore and Cloud Storage REST calls (not the app's own
   UI): the real Firestore document shows `status: "generated"`, and all five expected files
   (Startup Kit, Readiness Checklist, Workbook, Deck, trace manifest) exist in the real bucket
   with real sizes and checksums — the same standard of evidence used for every other
   verification in this project

**Resolved — granting future colleagues access is genuinely self-service, via the Console (not
`gcloud`), confirmed by IT:**

- Go to `https://console.cloud.google.com/security/iap?project=toptal-delivery-apps`
- Find the **"Cloud Run Services — `startup-kit-app`"** row specifically (not the "Backend
  Services" row, which also appears in the list but isn't the one actually enforcing IAP — see the
  confirmed explanation in Section 0 above), grant the person access, and set **Role → Cloud IAP →
  IAP-secured Web App User**
- **Good news, confirmed:** everyone in the `core@toptal.com` Google Group already has access,
  granted at the project level by IT — most colleagues likely need no individual grant at all.
  Only grant someone individually if they're not already a member of that group. Ping IT
  (Guilherme) if `core@toptal.com`'s own membership needs to change.
- Access changes take effect within a minute or two. If someone still sees "access denied" right
  after being granted, have them sign out and back in, or try a private/incognito window — this
  is a normal propagation delay, not a sign anything is actually wrong.

**Sections 1–4 below are kept as reference** for the alternative, classic load-balancer-centric
IAP pattern — useful if a future need arises where the native Cloud Run IAP path doesn't fit
(e.g., needing Cloud Armor, CDN, or other load-balancer-specific features alongside IAP), but they
describe a path that was not, in the end, the one actually used.

---

## 1. Why this is needed (background on the original plan)

Confirmed during the real Cloud Run deployment work: this org's effective
`constraints/iam.allowedPolicyMemberDomains` policy makes `--allow-unauthenticated` permanently
unusable (it only permits specific Workspace customer IDs, and `allUsers` can never satisfy a
domain restriction — see `docs/Cloud_Run_Deployment.md` Section 9 for the full story of how this
was discovered). That leaves today's real, working access model as the only option: per-person
`roles/run.invoker` grants, which require the person to have `gcloud` installed, authenticated,
and running `gcloud run services proxy` to reach the app at all. That's a reasonable bar for one
technical person; it is not a reasonable bar for a PMO team of colleagues who just want to open a
link in their browser.

IAP solves this properly: a real Google sign-in redirect in front of the app, the same familiar
experience as signing into Gmail or Drive, restricted to specific people or a Google Group —
no CLI, no proxy tunnel, no technical setup on the colleague's end.

---

## 2. What this actually requires (confirmed from Google's current documentation)

IAP for Cloud Run is not a flag on the existing service — it requires a new piece of
infrastructure sitting in front of it:

```
Browser --> External HTTPS Load Balancer --> IAP --> Serverless NEG --> Cloud Run (startup-kit-app)
```

| Component | What it is | Exists today? |
|---|---|---|
| External HTTPS Load Balancer | A new, separate billed resource | No — needs to be created |
| Serverless NEG | Connects the load balancer to the existing Cloud Run service | No — needs to be created |
| Backend service (with IAP enabled) | The load balancer's backend configuration; IAP is enabled here, not on Cloud Run itself | No — needs to be created |
| OAuth consent screen | A one-time, project-level prerequisite for IAP | Not yet configured for this project |
| `startup-kit-app`'s ingress setting | Must change from the default (all traffic) to `internal-and-cloud-load-balancing`, or the existing direct Cloud Run URL stays reachable and bypasses IAP entirely | Still default; needs to change |
| `roles/iap.httpsResourceAccessor` grants | The actual access-control layer going forward, replacing `run.invoker` for this purpose | Not yet used |

**A real, honest cost note:** a load balancer is a continuously-billed resource, unlike Cloud
Run's pay-per-request model. This is an ongoing cost the current setup does not have. Confirm
the real current pricing before proceeding (check `https://cloud.google.com/vpc/network-pricing`
and the Cloud Load Balancing pricing page directly, since pricing pages change — don't rely on
a remembered figure).

**Good fit with the existing org policy, not a conflict:** `roles/iap.httpsResourceAccessor`
grants are ordinary IAM bindings, so they are governed by the same
`constraints/iam.allowedPolicyMemberDomains` policy already discovered — meaning only real
`@toptal.com` (or whichever Workspace org the policy's customer IDs correspond to) accounts can
ever be granted access this way. This is exactly the right fit for an internal PMO tool, not a
new restriction to work around.

---

## 3. Prerequisites to confirm before starting

- [ ] Real current pricing for an External HTTPS Load Balancer, confirmed directly against
      Google's current pricing page, so the ongoing cost is a known, deliberate decision
- [x] `roles/oauthconfig.editor` granted by IT. Check
      `https://console.cloud.google.com/apis/credentials/consent?project=toptal-delivery-apps`
      directly to see whether an OAuth consent screen already exists for any other purpose and, if
      so, whether it's suitable for internal use; if not, create one, scoped to internal
      (Google Workspace organization only, not "External").
- [x] **Domain and load balancer ownership resolved — a real, favorable change to the plan.**
      IT's response: use `toptal.tech` (the organization's standard domain for new services, not
      `toptal.com`), and IT offered to build and own the load balancer and certificate directly,
      given the real Cloud Run service name. Real values to give IT: service `startup-kit-app`,
      region `us-east1`, project `toptal-delivery-apps`, proposed subdomain
      `startup-kit.toptal.tech`. (Note: this is deliberately a different domain than people's own
      `@toptal.com` email addresses used elsewhere in this plan for IAM grants — `toptal.tech` is
      specifically the org's domain for new service URLs, not a typo or inconsistency.)
      **Real division of ownership, confirmed with IT:** IT builds the networking/TLS layer
      (static IP, DNS record, managed certificate, NEG, backend service, URL map, proxy,
      forwarding rule — Section 4 Steps 2–7, 12, and 14 below). IT's own words: "IAP will still be
      managed at the service" — meaning enabling IAP itself (Step 8), locking Cloud Run's ingress
      to the load balancer (Step 10), granting IAP's own service agent permission to invoke the
      service (Step 9), and granting real people access via `roles/iap.httpsResourceAccessor`
      (Step 11) all stay this project's own responsibility, not IT's. Once IT confirms the backend
      service name/ID they create, Step 8 onward can proceed on that real resource.
- [ ] Decide the real list of people (or a Google Group, if one exists/can be created) who should
      be granted `roles/iap.httpsResourceAccessor` — this replaces today's `run.invoker` list

---

## 4. Planned steps (to execute in a future session, in order)

**Note on a point worth confirming at execution time, not assumed here either way:** Google
now supports a Google-managed OAuth client for IAP by default, meaning `--iap=enabled` alone may
work without supplying an explicit `oauth2-client-id`/`oauth2-client-secret` at all. Supplying
your own (Step 5 below shows both forms) is for a *custom* OAuth client — useful for specific
consent-screen branding or reusing an existing client, but not a universal requirement. Try the
plain `--iap=enabled` form first; only create and supply explicit credentials if that doesn't
give the result wanted.

1. **Confirm/create the OAuth consent screen** for `toptal-delivery-apps`, scoped to internal
   use (Google Workspace organization only, not "External").
2. **Reserve a global static external IP** and note its address:
   ```powershell
   gcloud compute addresses create startup-kit-ip --global
   gcloud compute addresses describe startup-kit-ip --global --format="value(address)"
   ```
3. **Point the chosen custom domain's DNS `A` record** at that static IP (requires DNS access
   confirmed in Section 3 — a Google-managed SSL certificate cannot attach to a bare IP address
   with no domain, so a real, resolvable domain is required, not optional).
4. **Create a Google-managed SSL certificate** for that domain:
   ```powershell
   gcloud compute ssl-certificates create startup-kit-cert `
     --domains="startup-kit.toptal.tech" `
     --global
   ```
5. **Create the serverless NEG**, pointing at the existing `startup-kit-app` service:
   ```powershell
   gcloud compute network-endpoint-groups create startup-kit-app-neg `
     --region=us-east1 `
     --network-endpoint-type=serverless `
     --cloud-run-service=startup-kit-app
   ```
6. **Create a backend service** and attach the NEG to it. **Critical, confirmed directly against
   Google's own `gcloud` CLI reference:** `backend-services create`'s `--timeout` flag defaults to
   **30 seconds** — far shorter than Cloud Run's own request timeout. Left at the default, the
   load balancer itself would silently kill a long-running session at 30 seconds, reintroducing
   the exact class of failure `HTL-39` diagnosed and fixed, just sooner. Set `--timeout` to match
   the already-researched and justified Cloud Run value (`1800`, see
   `docs/Cloud_Run_Deployment.md` Section 6) — not a new, separately-chosen number:
   ```powershell
   gcloud compute backend-services create startup-kit-app-backend `
     --global `
     --load-balancing-scheme=EXTERNAL_MANAGED `
     --timeout=1800

   gcloud compute backend-services add-backend startup-kit-app-backend `
     --global `
     --network-endpoint-group=startup-kit-app-neg `
     --network-endpoint-group-region=us-east1
   ```
   **Worth investigating, not yet confirmed either way:** whether `--session-affinity` is actually
   needed for Streamlit's persistent WebSocket connection. A single already-established WebSocket
   connection stays bound to one backend instance for its own lifetime by the nature of the
   protocol — session affinity typically matters for routing *separate, repeated* requests to the
   same backend, not one continuous open stream — so it may be unnecessary here. Also unconfirmed:
   whether `GENERATED_COOKIE` session affinity is even supported for a serverless NEG backend at
   all. Don't add `--session-affinity` speculatively; only investigate and add it if real testing
   in Step 12 actually shows session-continuity problems.
7. **Create the URL map, target HTTPS proxy, and forwarding rule**:
   ```powershell
   gcloud compute url-maps create startup-kit-url-map `
     --default-service=startup-kit-app-backend `
     --global

   gcloud compute target-https-proxies create startup-kit-https-proxy `
     --url-map=startup-kit-url-map `
     --ssl-certificates=startup-kit-cert `
     --global

   gcloud compute forwarding-rules create startup-kit-fwd-rule `
     --load-balancing-scheme=EXTERNAL_MANAGED `
     --network-tier=PREMIUM `
     --address=startup-kit-ip `
     --target-https-proxy=startup-kit-https-proxy `
     --ports=443 `
     --global
   ```
8. **Enable IAP on the backend service** — try the plain form first (see the note above this
   list); fall back to the explicit-credentials form only if needed:
   ```powershell
   gcloud compute backend-services update startup-kit-app-backend --global --iap=enabled

   # Only if a custom OAuth client is genuinely needed:
   gcloud compute backend-services update startup-kit-app-backend `
     --global `
     --iap=enabled,oauth2-client-id="<CLIENT_ID>",oauth2-client-secret="<CLIENT_SECRET>"
   ```
9. **Grant IAP's own service agent permission to invoke the Cloud Run service** (a separate
   identity from `cloudrun-sa` — IAP calls Cloud Run on the authenticated user's behalf, using the
   real numeric project number, not the project ID):
   ```powershell
   $PROJECT_NUM = (gcloud projects describe toptal-delivery-apps --format="value(projectNumber)")

   gcloud beta services identity create --service=iap.googleapis.com --project=toptal-delivery-apps

   gcloud run services add-iam-policy-binding startup-kit-app `
     --region=us-east1 `
     --member="serviceAccount:service-$PROJECT_NUM@gcp-sa-iap.iam.gserviceaccount.com" `
     --role="roles/run.invoker"
   ```
10. **Change `startup-kit-app`'s ingress** to prevent the direct Cloud Run URL from bypassing IAP:
    ```powershell
    gcloud run services update startup-kit-app `
      --region us-east1 `
      --ingress internal-and-cloud-load-balancing
    ```
11. **Grant real people access**:
   ```powershell
   gcloud iap web add-iam-policy-binding `
     --resource-type=backend-services `
     --service=startup-kit-app-backend `
     --member="user:james.mora@toptal.com" `
     --role="roles/iap.httpsResourceAccessor"
   ```
   Repeat per person, or use a `group:` member if a Google Group is set up for this instead.
12. **Before testing in a browser, confirm the SSL certificate has actually finished
    provisioning.** A Google-managed certificate typically takes 15–60 minutes to provision after
    the forwarding rule is active and DNS has propagated; testing too early produces a confusing
    `ERR_SSL_VERSION_OR_CIPHER_MISMATCH` or privacy error that looks like a setup mistake but is
    actually just a timing issue. Check status directly rather than guessing:
    ```powershell
    gcloud compute ssl-certificates describe startup-kit-cert `
      --global `
      --format="value(managed.status, managed.domainStatus)"
    ```
    Wait for `ACTIVE` before proceeding.
13. **Verify end-to-end**: open the load balancer's URL (or custom domain) in a browser as a
    granted user with no `gcloud` running at all, confirm the real Google sign-in redirect
    appears, and confirm a real Generate → Fact Review → Approve → Generate documents cycle works
    through it — the same hands-on verification standard used for every other piece of this
    project.
14. **Optional polish: redirect plain HTTP to HTTPS.** As planned, only port 443 is bound to the
    forwarding rule — a colleague typing the bare domain without `https://` would fail to connect
    on port 80. A standard redirect setup:
    ```powershell
    gcloud compute url-maps import startup-kit-http-redirect --global --source=- <<EOF
    name: startup-kit-http-redirect
    defaultUrlRedirect:
      redirectResponseCode: MOVED_PERMANENTLY_DEFAULT
      httpsRedirect: true
      stripQuery: false
    EOF

    gcloud compute target-http-proxies create startup-kit-http-proxy `
      --url-map=startup-kit-http-redirect `
      --global

    gcloud compute forwarding-rules create startup-kit-http-fwd-rule `
      --load-balancing-scheme=EXTERNAL_MANAGED `
      --network-tier=PREMIUM `
      --address=startup-kit-ip `
      --target-http-proxy=startup-kit-http-proxy `
      --ports=80 `
      --global
    ```
    Genuinely optional — skip if typing the full `https://` URL is an acceptable ask of
    colleagues; include if a more forgiving, typical-browser experience matters.
15. **Update `docs/Cloud_Run_Deployment.md`** once this is live: replace Section 7's
    `run.invoker`-based access instructions with the new IAP-based flow, and update this plan's
    own checklist to reflect what's actually been done versus what's still open — the same way
    the Cloud Run and Firestore/Storage docs were kept honest and current throughout tonight's
    work.

---

## 5. For later: per-user identity inside the app (not needed for this plan's goal)

IAP only governs perimeter access (who can reach the app at all) — it does not, by itself, give
the Streamlit app any way to know *which* authenticated person is making a given request. If a
future need arises for per-user logic inside the app (e.g., auditing who approved or generated a
given run), IAP injects identity headers into every proxied request that the app could read:
`X-Goog-Authenticated-User-Email`, `X-Goog-Authenticated-User-Id`, and a signed
`X-Goog-IAP-JWT-Assertion` for verifying the other two haven't been spoofed. Not needed for this
plan's actual goal (replacing `run.invoker`/`gcloud` with a normal browser sign-in) — noted here
only so it doesn't need re-researching if a real need for it comes up later.

## 6. Explicitly out of scope for this plan

- Migrating away from the existing Cloud Run service itself — this plan only adds a load balancer
  and IAP in front of what already exists; `startup-kit-app`'s own configuration, environment
  variables, secrets, and service account stay as documented in `docs/Cloud_Run_Deployment.md`.
- Removing today's `run.invoker`-based access entirely until IAP is confirmed working — both can
  coexist during setup and testing; `run.invoker` access should only be retired once IAP is
  genuinely verified end-to-end.
