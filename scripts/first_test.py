import os, sys, json, time, mimetypes
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

PROMPT = """You read Indian GST bills and receipts. Return ONLY JSON with these keys:
document_type (one of: tax_invoice, bill_of_supply, advance_receipt, estimate, other),
supplier, gstin, invoice_no (the invoice, bill or order number), date (YYYY-MM-DD),
line_items (list of {description, hsn, qty, rate, discount, amount}),
gross_total, total_discount, taxable_value, cgst, sgst, igst,
total (the final net amount payable).
All money and quantity fields must be plain numbers with no currency symbols or commas.
Discounts are positive numbers. Copy values exactly as printed.
Use null for anything not printed. Do not guess or calculate."""

def main(path):
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    with open(path, "rb") as f:
        data = f.read()
    client = genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options=types.HttpOptions(timeout=60000),
    )
    for attempt in range(1, 6):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=[types.Part.from_bytes(data=data, mime_type=mime), PROMPT],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            print(json.dumps(json.loads(resp.text), indent=2, ensure_ascii=False))
            return
        except Exception as e:
            print(f"attempt {attempt} failed: {type(e).__name__}: {str(e)[:150]}")
            time.sleep(10 * attempt)
    print("All attempts failed.")

if __name__ == "__main__":
    main(sys.argv[1])
