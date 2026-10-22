# How the Startup Kit App Works

Oct 21, 2026 · @James

The Startup Kit app reads a Statement of Work and other project documents a PMO uploads, uses AI to pull out the key facts (dates, deliverables, risks, contract terms), has a person confirm those facts are right, and then assembles everything into four ready-to-use project documents — a Startup Kit, a Readiness Checklist, a Delivery Workbook, and an Onboarding Deck.

## Architecture

&#91;embedded content: deployment architecture · browser to Cloud Run to three Google Cloud services\]

The app runs as one Streamlit service on Google Cloud Run, in a project called toptal-delivery-apps. A colleague reaches it at a real web address; Identity-Aware Proxy checks their Google sign-in before any request is allowed through — there is no separate login inside the app itself. Past that check, the running app talks to three Google Cloud services: Firestore holds each run's status and extracted facts, Cloud Storage holds the generated files, and Secret Manager holds the API key and admin passphrase. The one service outside Google Cloud entirely is Anthropic's API, which does the actual AI reading of the uploaded documents.

## Internal flow

&#91;embedded content: internal flow · five stages from upload to generated documents\]

Upload starts the run: a Statement of Work and any supporting documents go in together. AI extraction reads them and pulls out structured facts — dates, deliverables, risks, contract terms. Validation is deterministic code, not AI: dozens of real business-rule checks run against the extracted facts, catching things like a deliverable with no real reference back to the source document, and automatically repairing some issues on their own. Human review is where a person actually reads the extracted facts, corrects anything wrong, and clicks Approve — nothing is generated without that explicit action. Only after approval does Generate run, assembling the approved facts into the four real documents.

## How it uses AI

&#91;embedded content: AI extraction · several focused readings combine into one structured baseline\]

The AI work is not one giant call — several smaller, focused readings run against the same document text, each covering one domain (milestones, risks and stakeholders, governance terms, and more), and the results combine into a single structured baseline. Each reading is asked for structured output against a defined schema, not free text, which is a big part of why the validation step afterward can check the results so precisely. Claude is the primary model doing this reading; a fallback to OpenAI exists in the code but is not currently active in the deployed app. The same input can come back phrased slightly differently from one run to the next, since that is inherent to how AI models work — which is exactly why the validation step exists: it is taught to recognize many different valid phrasings of the same real fact, rather than breaking on anything unfamiliar. The AI's role ends at producing structured facts; turning those facts into the final Word, Excel, and PowerPoint files is ordinary, deterministic code, not another AI call.

## In short

In short: it runs as a secure web app on Google's cloud. A person uploads a contract document, several focused AI readings pull out the key facts, a layer of automated checks and then a human reviewer confirm those facts are right, and only then does the system assemble them into four polished, ready-to-use project documents.
