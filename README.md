# TaxMitra AI

**Autonomous GST Copilot & ITC Guardian for MSMEs, on WhatsApp.**

> Hackathon problem statement 3.1: *Micro enterprises lose time and profit to compliance paperwork.*

TaxMitra AI turns messy paper bills and voice notes into extracted invoice data, Input Tax Credit (ITC) alerts, E-Way Bill drafts and GST return JSON files. The owner does everything inside WhatsApp, with no new app to install, and approves every draft before any file is produced.

> **Note:** All government data (GSTR-2B, GSTN endpoints) is **simulated** for this hackathon. TaxMitra AI does not connect to the real GST portal and never files anything on its own.

---

## The problem

Micro and small businesses in India struggle with GST paperwork:

- **15-20 hours a month** go into sorting paper bills and WhatsApp receipts.
- **8-12% of profit** can leak through missed Input Tax Credit.
- **₹1,500-₹3,000 a month** goes to professional fees for basic manual sorting.
- Shipments above **₹50,000** risk detention and fines when E-Way Bills are missing or delayed.

Existing GST tools are desktop- or web-heavy and built for accountants, not shop owners.

## The solution

The owner sends a bill photo or voice note on WhatsApp. Four coordinated AI agents do the rest:

| Agent | What it does |
| --- | --- |
| **Perception Agent** | Reads invoice photos and voice notes; extracts supplier, GSTIN, HSN, tax and line items |
| **Reconciliation Sentinel** | Matches purchases against a simulated GSTR-2B feed, flags missing or mismatched invoices and drafts a supplier follow-up |
| **Logistics Agent** | Checks the ₹50,000 rule and drafts the E-Way Bill payload |
| **Tax Compliance Agent** | Validates HSN rates against a GST rulebook and prepares GSTR-1 and GSTR-3B JSON drafts for owner sign-off |

## Owner journey

**Send -> Extract -> Reconcile -> Prepare -> Approve**

1. Send a bill photo or voice note on WhatsApp.
2. TaxMitra extracts supplier, GSTIN, HSN, tax and line-item details.
3. ITC Sentinel flags missing or mismatched invoices and drafts a follow-up.
4. The Logistics Agent prepares an E-Way Bill when a shipment crosses the threshold.
5. The owner reviews, approves and receives a return-ready JSON file.

## Tech stack

- **Interface:** WhatsApp (Twilio)
- **Backend:** Python, FastAPI
- **Orchestration:** LangGraph
- **Vision and voice:** GPT-4o-mini Vision, Whisper
- **Knowledge base:** FAISS over GST / CBIC rulebook text
- **Storage:** SQLite (state and audit trail)

## Trust and safety

- The human stays in control: nothing is exported until the owner approves.
- Every extraction, correction, approval and export is logged in an audit trail.
- All outputs are labelled as drafts that need owner approval.

## Business model (proposed)

- **Freemium SaaS:** free up to 25 invoices a month; ₹299/month for unlimited AI E-Way Bills and ITC alerts.
- **CA / practitioner portal:** helps accountants manage more clients using pre-sorted JSON returns.

## Status

Work in progress for the hackathon. Setup instructions and code will be added as each part is built.

## Team

- Anirudh Kalekar
- Ananya Ravi Hanchinamane
- Disha Naik
- Ankitha

---

*Making GST compliance feel as easy as sending a message.*
