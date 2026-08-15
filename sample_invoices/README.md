# Sample Invoice PDFs for PayCrew Testing

10 realistic invoice PDFs in this folder. Upload them on the **AP Dashboard** to test each risk scenario.

## How to use

1. Log in as AP with code `AP2024`
2. Upload any PDF from this folder
3. Watch the 6 agents process it live
4. Check the result risk badge and status

## Invoice catalog

| File | Vendor | Amount | Expected Risk | Expected Outcome |
|------|--------|--------|---------------|------------------|
| `01-low-officesupply.pdf` | OfficeSupplyCo | $800 | LOW | Auto Approved |
| `02-low-cleanvendor.pdf` | CleanVendor Inc | $475 | LOW | Auto Approved |
| `03-low-paperworks.pdf` | PaperWorks Ltd | $375 | LOW | Auto Approved |
| `04-low-techsoftware.pdf` | TechSoftware Inc | $3,500 | LOW | Auto Approved |
| `05-high-duplicate.pdf` | TechSoftware Inc | $1,200 | HIGH | Pending CFO (duplicate payment) |
| `06-medium-no-po.pdf` | PaperWorks Ltd | $325 | MEDIUM | Flagged for AP (invalid PO) |
| `07-critical-fraud.pdf` | FastConsult LLC | $45,000 | CRITICAL | Escalated / Blocked (fraud vendor) |
| `08-critical-unknown-vendor.pdf` | ApexShell Corp | $3,200 | CRITICAL | Escalated / Blocked (unknown vendor) |
| `09-critical-large-no-po.pdf` | OfficeSupplyCo | $18,500 | CRITICAL | Escalated / Blocked (large amount, no PO) |
| `10-medium-bank-mismatch.pdf` | CleanVendor Inc | $480 | MEDIUM | Flagged for AP (wrong bank account) |

## CFO dashboard

Upload **05**, **07**, **08**, or **09** — then log in as CFO (`CFO2024`) to see them in **Pending Approvals**.

## Regenerate / re-test

```bash
cd backend
source .venv/bin/activate
python scripts/generate_sample_pdfs.py
python scripts/test_sample_pdfs.py
```

All 10 should pass before you test manually.
