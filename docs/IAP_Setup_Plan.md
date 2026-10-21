# Identity-Aware Proxy (IAP) Setup Plan — Startup Kit App

This document plans the work to put Identity-Aware Proxy in front of the deployed
`startup-kit-app` Cloud Run service, replacing today's per-person `run.invoker` + `gcloud`
access model with a normal Google sign-in redirect that works in any browser, no CLI needed.
It builds on `docs/Cloud_Run_Deployment.md` (the service that already exists) and
`docs/GCP_Firestore_CloudStorage_Setup.md` (the storage layer behind it). This is a plan to
execute in a future session, not yet started.

---

## 1. Why this is needed

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
- [ ] **In progress:** checking `https://console.cloud.google.com/apis/credentials/consent?project=toptal-delivery-apps`
      hit a real, confirmed permission gap: `clientauthconfig.clients.get`,
      `clientauthconfig.clients.list`, `oauthconfig.verification.get`,
      `resourcemanager.projects.get`, and `serviceusage.quotas.get` are all missing. The real role
      that covers the first three (confirmed directly against Google's own OAuthConfig roles
      documentation) is `roles/oauthconfig.editor`. The other two are more basic permissions that
      may already be covered by existing project roles — worth confirming either way. Requested
      from IT; pending as of this writing. Once granted, check this page directly to see whether an
      OAuth consent screen already exists for any other purpose and, if so, whether it's suitable
      for internal use; if not, one must be created.
- [ ] **In progress:** DNS access for a custom domain (e.g. `startup-kit.toptal.com`) is not
      confirmed either way — asked IT directly who manages `toptal.com`'s DNS and whether access
      is available; pending as of this writing. A custom domain is cleaner for colleagues to
      remember and type, but isn't required — the load balancer's own IP with a Google-managed
      certificate against no custom domain is a fully workable fallback if DNS access isn't
      available or would take too long to arrange.
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
     --domains="startup-kit.toptal.com" `
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
