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
- [ ] Confirm whether `toptal-delivery-apps` already has an OAuth consent screen configured for
      any other purpose (check `https://console.cloud.google.com/apis/credentials/consent?project=toptal-delivery-apps`)
      — if one exists, confirm it's suitable for internal use; if not, one must be created
- [ ] Decide: use a custom domain for the load balancer (e.g. `startup-kit.toptal.com`, requiring
      DNS access and a managed SSL certificate), or use the load balancer's own default IP with a
      Google-managed certificate against no custom domain. A custom domain is cleaner for
      colleagues to remember and type, but needs DNS access this plan doesn't yet confirm is
      available
- [ ] Decide the real list of people (or a Google Group, if one exists/can be created) who should
      be granted `roles/iap.httpsResourceAccessor` — this replaces today's `run.invoker` list

---

## 4. Planned steps (to execute in a future session, in order)

1. **Confirm/create the OAuth consent screen** for `toptal-delivery-apps`, scoped to internal
   use (Google Workspace organization only, not "External").
2. **Create the serverless NEG**, pointing at the existing `startup-kit-app` service:
   ```powershell
   gcloud compute network-endpoint-groups create startup-kit-app-neg `
     --region=us-east1 `
     --network-endpoint-type=serverless `
     --cloud-run-service=startup-kit-app
   ```
3. **Create a backend service** and attach the NEG to it:
   ```powershell
   gcloud compute backend-services create startup-kit-app-backend `
     --global `
     --load-balancing-scheme=EXTERNAL_MANAGED

   gcloud compute backend-services add-backend startup-kit-app-backend `
     --global `
     --network-endpoint-group=startup-kit-app-neg `
     --network-endpoint-group-region=us-east1
   ```
4. **Create the load balancer's remaining components** (URL map, target HTTPS proxy, forwarding
   rule, and either a Google-managed SSL certificate for a custom domain or one for the load
   balancer's own IP) — the exact commands depend on the custom-domain decision from Section 3
   and should be confirmed against Google's current documentation at execution time, not copied
   from this plan verbatim, since load balancer setup commands are detailed and
   environment-specific.
5. **Enable IAP on the backend service**:
   ```powershell
   gcloud compute backend-services update startup-kit-app-backend `
     --global `
     --iap=enabled
   ```
6. **Grant IAP's own service agent permission to invoke the Cloud Run service** (a separate,
   required identity from `cloudrun-sa` — IAP calls Cloud Run on the authenticated user's behalf):
   ```powershell
   gcloud beta services identity create --service=iap.googleapis.com --project=toptal-delivery-apps
   # then grant the resulting service agent roles/run.invoker on startup-kit-app
   ```
7. **Change `startup-kit-app`'s ingress** to prevent the direct Cloud Run URL from bypassing IAP:
   ```powershell
   gcloud run services update startup-kit-app `
     --region us-east1 `
     --ingress internal-and-cloud-load-balancing
   ```
8. **Grant real people access**:
   ```powershell
   gcloud iap web add-iam-policy-binding `
     --resource-type=backend-services `
     --service=startup-kit-app-backend `
     --member="user:james.mora@toptal.com" `
     --role="roles/iap.httpsResourceAccessor"
   ```
   Repeat per person, or use a `group:` member if a Google Group is set up for this instead.
9. **Verify end-to-end**: open the load balancer's URL (or custom domain) in a browser as a
   granted user with no `gcloud` running at all, confirm the real Google sign-in redirect appears,
   and confirm a real Generate → Fact Review → Approve → Generate documents cycle works through
   it — the same hands-on verification standard used for every other piece of this project.
10. **Update `docs/Cloud_Run_Deployment.md`** once this is live: replace Section 7's
    `run.invoker`-based access instructions with the new IAP-based flow, and update this plan's
    own checklist to reflect what's actually been done versus what's still open — the same way
    the Cloud Run and Firestore/Storage docs were kept honest and current throughout tonight's
    work.

---

## 5. Explicitly out of scope for this plan

- Migrating away from the existing Cloud Run service itself — this plan only adds a load balancer
  and IAP in front of what already exists; `startup-kit-app`'s own configuration, environment
  variables, secrets, and service account stay as documented in `docs/Cloud_Run_Deployment.md`.
- Removing today's `run.invoker`-based access entirely until IAP is confirmed working — both can
  coexist during setup and testing; `run.invoker` access should only be retired once IAP is
  genuinely verified end-to-end.
