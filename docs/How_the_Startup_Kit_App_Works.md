# How the Startup Kit App Works

Oct 21, 2026 · @James

The Startup Kit app reads a Statement of Work and supporting kickoff materials uploaded by a PMO, uses AI to extract key structured facts (dates, deliverables, milestones, risks, and governance terms), enables human review and editing of those facts, and then assembles everything into four ready-to-use project delivery documents:
- a **Startup Kit** (`.docx`),
- a **Project Delivery Workbook** (`.xlsx`),
- a **Talent Team Onboarding Deck** (`.pptx`), and
- a **Client Kickoff Deck** (`.pptx`) with companion audit-trail trace manifests (`.trace.json`).

## Architecture

&#91;embedded content: deployment architecture · browser to Cloud Run to three Google Cloud services\]

The app runs as one Streamlit service on Google Cloud Run, in a project called toptal-delivery-apps. A colleague reaches it at a real web address; Identity-Aware Proxy checks their Google sign-in before any request is allowed through — there is no separate login inside the app itself. Past that check, the running app talks to three Google Cloud services: Firestore holds each run's status and extracted facts, Cloud Storage holds the generated files, and Secret Manager holds the API key and admin passphrase. The one service outside Google Cloud entirely is Anthropic's API, which does the actual AI reading of the uploaded documents.

## Internal flow

&#91;embedded content: internal flow · five stages from upload to generated documents\]

Upload starts the run on the Generate page via two dedicated upload slots: a required primary Statement of Work (SOW) slot and an optional supporting documents slot (accepting `.pdf`, `.docx`, `.pptx`, `.txt`, and `.md` notes). Extraction applies strict SOW-first precedence — the SOW is the definitive source of truth, while supporting notes fill missing context (such as concrete pain points for the problem statement). To prevent unauthorized API consumption, SOW uploads and document generation are protected by a generation passphrase.

AI extraction reads the ingested documents and produces structured domain baselines, including customer-outcome narratives for the problem statement, solution overview, and success criteria. Validation runs deterministic business-rule checks against the extracted facts (e.g., verifying 1:1 structural counts of acceptance criteria, checking parent deliverable references, and repairing gate numbering).

Human review is where a reviewer inspects the extracted baseline across collapsed fact categories on the Fact Review page, applies any necessary corrections, and clicks Approve — nothing is generated without explicit approval. Once approved, Generate executes, assembling the verified facts into the four polished deliverables.

## How it uses AI

&#91;embedded content: AI extraction · several focused readings combine into one structured baseline\]

The AI work is not one giant call — several smaller, focused readings run against the same document text, each covering one domain (milestones, risks and stakeholders, governance terms, and more), and the results combine into a single structured baseline. Each reading is asked for structured output against a defined schema, not free text, which is a big part of why the validation step afterward can check the results so precisely. Claude is the primary model doing this reading; a fallback to OpenAI exists in the code but is not currently active in the deployed app. The same input can come back phrased slightly differently from one run to the next, since that is inherent to how AI models work — which is exactly why the validation step exists: it is taught to recognize many different valid phrasings of the same real fact, rather than breaking on anything unfamiliar. The AI's role ends at producing structured facts; turning those facts into the final Word, Excel, and PowerPoint files is ordinary, deterministic code, not another AI call.

## In short

In short: it runs as a secure web app on Google's cloud. A person uploads a contract document, several focused AI readings pull out the key facts, a layer of automated checks and then a human reviewer confirm those facts are right, and only then does the system assemble them into four polished, ready-to-use project documents.
