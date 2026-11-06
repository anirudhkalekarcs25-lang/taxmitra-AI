"""TaxMitra AI - Phase 1 mock data generator.

Creates (all FICTIONAL, for a hackathon demo):
  data/invoices.json      25 purchase invoices (ground truth of what is printed on each bill)
  data/gstr2b.json        simulated GSTR-2B-style supplier feed for the same month
  data/ground_truth.json  expected reconciliation result (matched / missing / mismatch / rate error)
  data/sales.json         15 outward sales (4 need an E-Way Bill)
  data/pincodes.csv       approximate city-centre coordinates for distance estimates
  data/bills/INV-xxx.*    one bill image per invoice (some look like crumpled phone photos)

Run:  python make_mock_data.py <output_dir>
Needs: pip install pillow numpy playwright && playwright install chromium
GST rates here are DEMO values. Verify them against the official GST rate table before relying on them.
"""
import json, math, os, random, sys
from datetime import date, timedelta

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
DATA = os.path.join(OUT, "data")
BILLS = os.path.join(DATA, "bills")
os.makedirs(BILLS, exist_ok=True)
random.seed(42)
np.random.seed(42)

# ---------------------------------------------------------------- GSTIN helper
ALPHA = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin(state, pan, n="1"):
    g = f"{state}{pan}{n}Z"
    s = 0
    for i, c in enumerate(g):
        p = ALPHA.index(c) * (1 if i % 2 == 0 else 2)
        s += p // 36 + p % 36
    return g + ALPHA[(36 - s % 36) % 36]


def inr(x):
    """Indian digit grouping, 2 decimals."""
    s = f"{abs(x):.2f}"
    whole, frac = s.split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return ("-" if x < 0 else "") + whole + "." + frac


# ---------------------------------------------------------------- master data
BUYER = dict(name="Sri Meenakshi Garments", state="29", state_name="Karnataka",
             address="12, Commercial Street, Bengaluru, Karnataka 560001", pincode="560001",
             gstin=gstin("29", "AKNPS4410R"))

SUPPLIERS = [
    dict(name="Kaveri Knit Mills Pvt Ltd", state="29", city="Bengaluru", pincode="560058", pan="AABCK4821M",
         address="Plot 41, Peenya Industrial Area, Bengaluru 560058", prefix="KKM"),
    dict(name="Mysore Cotton Traders", state="29", city="Mysuru", pincode="570001", pan="AAEFM7302D",
         address="88, Devaraja Mohalla, Mysuru 570001", prefix="MCT"),
    dict(name="Tiruppur Tex Exports", state="33", city="Tiruppur", pincode="641601", pan="AAUFT5519H",
         address="14/2, Kangeyam Road, Tiruppur 641601", prefix="TTX"),
    dict(name="Coimbatore Fabrics Co", state="33", city="Coimbatore", pincode="641001", pan="AAGFC2204Q",
         address="7, Oppanakara Street, Coimbatore 641001", prefix="CFC"),
    dict(name="Surat Weave Industries", state="24", city="Surat", pincode="395003", pan="AAHCS9017L",
         address="Block C, Ring Road Textile Market, Surat 395003", prefix="SWI"),
    dict(name="Ahmedabad Garment Hub", state="24", city="Ahmedabad", pincode="380001", pan="AAJFA6643R",
         address="22, Relief Road, Ahmedabad 380001", prefix="AGH"),
    dict(name="Pune Apparel House", state="27", city="Pune", pincode="411001", pan="AAMFP1180B",
         address="5, Laxmi Road, Pune 411001", prefix="PAH"),
    dict(name="Hubballi Textile Depot", state="29", city="Hubballi", pincode="580020", pan="AAIFH3957C",
         address="31, Station Road, Hubballi 580020", prefix="HTD"),
]
for s in SUPPLIERS:
    s["gstin"] = gstin(s["state"], s["pan"])

PRODUCTS = [  # description, hsn, unit, (min rate, max rate)
    ("Men's cotton round-neck T-shirt", "6109", "pcs", (180, 420)),
    ("Men's cotton formal shirt", "6205", "pcs", (350, 800)),
    ("Women's cotton kurti", "6204", "pcs", (300, 900)),
    ("Men's cotton trousers", "6203", "pcs", (450, 1100)),
    ("Cotton poplin fabric", "5208", "mtr", (90, 180)),
    ("Kids' knitted cotton set", "6111", "pcs", (150, 400)),
]
DEMO_GST_RATE = 5  # garments up to Rs 2,500 per piece and cotton fabric (demo value, verify officially)

# which invoices get which test condition (1-based)
MISSING = [4, 11, 18]
MISMATCH = [7, 14]
WRONG_RATE = 22
PHOTO = [3, 8, 12, 17, 23]


def r2(x):
    return round(x + 1e-9, 2)


def make_taxes(taxable, rate, intra):
    if intra:
        half = r2(taxable * rate / 200)
        return half, half, 0.0
    return 0.0, 0.0, r2(taxable * rate / 100)


# ---------------------------------------------------------------- purchase invoices
invoices = []
for i in range(1, 26):
    sup = SUPPLIERS[(i - 1) % 8]
    d = date(2026, 10, 1) + timedelta(days=round((i - 1) * 27 / 24))
    n_lines = random.choice([1, 2, 2, 3])
    prods = random.sample(PRODUCTS, n_lines)
    if i == WRONG_RATE:
        prods = [PRODUCTS[1]] + [p for p in prods if p[1] != "6205"][: n_lines - 1]
    lines = []
    for desc, hsn, unit, (lo, hi) in prods:
        rate = int(random.randint(lo, hi) // 5 * 5)
        qty = random.choice([20, 25, 30, 40, 50, 60, 75, 80, 100, 120])
        lines.append(dict(description=desc, hsn=hsn, qty=qty, unit=unit, rate=float(rate), amount=float(qty * rate)))
    taxable = float(sum(l["amount"] for l in lines))
    gst_rate = 18 if i == WRONG_RATE else DEMO_GST_RATE
    intra = sup["state"] == BUYER["state"]
    cgst, sgst, igst = make_taxes(taxable, gst_rate, intra)
    total = r2(taxable + cgst + sgst + igst)
    inv_no = f"{sup['prefix']}/26-27/{random.randint(100, 999):04d}"
    invoices.append(dict(
        id=f"INV-{i:03d}", image="", document_type="tax_invoice",
        supplier_name=sup["name"], supplier_gstin=sup["gstin"], supplier_address=sup["address"],
        invoice_no=inv_no, date=d.isoformat(), buyer_name=BUYER["name"], buyer_gstin=BUYER["gstin"],
        place_of_supply=f"{BUYER['state_name']} ({BUYER['state']})", line_items=lines,
        taxable_value=taxable, gst_rate=gst_rate, cgst=cgst, sgst=sgst, igst=igst, total=total))
    ext = "jpg" if i in PHOTO else "png"
    invoices[-1]["image"] = f"bills/INV-{i:03d}.{ext}"

# ---------------------------------------------------------------- simulated GSTR-2B + ground truth
gt_rows, feed = [], {}
for i, inv in enumerate(invoices, 1):
    itc_books = r2(inv["cgst"] + inv["sgst"] + inv["igst"])
    status, itc_2b = "matched", itc_books
    if i in MISSING:
        status, itc_2b = "missing_in_2b", 0.0
    else:
        rec = dict(invoice_no=inv["invoice_no"], date=inv["date"], taxable_value=inv["taxable_value"],
                   cgst=inv["cgst"], sgst=inv["sgst"], igst=inv["igst"], total=inv["total"])
        if i in MISMATCH:  # supplier under-reported the taxable value by 10%
            tv = r2(inv["taxable_value"] * 0.9)
            c, s_, g = make_taxes(tv, inv["gst_rate"], inv["igst"] == 0)
            rec.update(taxable_value=tv, cgst=c, sgst=s_, igst=g, total=r2(tv + c + s_ + g))
            status, itc_2b = "amount_mismatch", r2(c + s_ + g)
        feed.setdefault(inv["supplier_gstin"], dict(supplier_gstin=inv["supplier_gstin"],
                                                    supplier_name=inv["supplier_name"], invoices=[])
                        )["invoices"].append(rec)
    gt_rows.append(dict(id=inv["id"], invoice_no=inv["invoice_no"], supplier_gstin=inv["supplier_gstin"],
                        status=status, itc_in_books=itc_books, itc_in_2b=itc_2b,
                        itc_at_risk=r2(max(0.0, itc_books - itc_2b)),
                        rate_error=(i == WRONG_RATE), expected_gst_rate=DEMO_GST_RATE if i == WRONG_RATE else None))

# one invoice the supplier filed that is NOT in the owner's books
extra_sup = SUPPLIERS[3]
extra = dict(invoice_no="CFC/26-27/0777", date="2026-10-20", taxable_value=18000.0, cgst=0.0, sgst=0.0,
             igst=900.0, total=18900.0)
feed.setdefault(extra_sup["gstin"], dict(supplier_gstin=extra_sup["gstin"], supplier_name=extra_sup["name"],
                                         invoices=[]))["invoices"].append(extra)

gstr2b = dict(
    note="SIMULATED GSTR-2B style feed for the hackathon demo. Not real GST portal data.",
    return_period="102026", recipient_gstin=BUYER["gstin"], recipient_name=BUYER["name"],
    b2b=list(feed.values()))

counts = {k: sum(1 for r in gt_rows if r["status"] == k) for k in ("matched", "missing_in_2b", "amount_mismatch")}
ground_truth = dict(
    period="2026-10", recipient_gstin=BUYER["gstin"],
    summary=dict(**counts, in_2b_not_in_books=1, rate_errors=1,
                 itc_in_books_total=r2(sum(r["itc_in_books"] for r in gt_rows)),
                 itc_at_risk_total=r2(sum(r["itc_at_risk"] for r in gt_rows)),
                 itc_at_risk_invoice_ids=[r["id"] for r in gt_rows if r["itc_at_risk"] > 0]),
    purchases=gt_rows,
    in_2b_not_in_books=[dict(supplier_gstin=extra_sup["gstin"], **extra)])

# ---------------------------------------------------------------- sales + pincodes
BUYERS = [
    ("Urban Threads Boutique", "29", "Bengaluru", "560034", "AAFPU2231K"),
    ("Koramangala Kids Corner", "29", "Bengaluru", "560095", "AAKFK8820P"),
    ("City Fashion Mart", "29", "Bengaluru", "560068", "AABFC4417T"),
    ("Mysuru Style Bazaar", "29", "Mysuru", "570001", "AAHFM1096N"),
    ("Chennai Trendz", "33", "Chennai", "600001", "AATCC5538G"),
    ("Pune Fashion Point", "27", "Pune", "411001", "AAPFP7745E"),
    ("Hubballi Garment Mart", "29", "Hubballi", "580020", "AAJFH3380D"),
]
BUYERS = [dict(name=n, state=s, city=c, pincode=p, gstin=gstin(s, pan)) for n, s, c, p, pan in BUYERS]
B = {b["city"] + b["name"][:2]: b for b in BUYERS}
local = BUYERS[:3]
SALE_PLAN = [  # taxable, qty, product index, buyer
    (8000, 20, 0, local[0]), (12500, 25, 1, local[1]), (18000, 45, 0, local[2]), (22500, 45, 2, local[0]),
    (9500, 20, 5, local[1]), (30000, 60, 3, local[2]), (15000, 30, 1, local[0]), (27500, 50, 2, local[1]),
    (6000, 15, 0, local[2]), (40000, 80, 3, local[0]),
    (47000, 100, 1, local[2]),        # total 49,350  -> below threshold
    (48000, 120, 0, BUYERS[3]),       # total 50,400  -> E-Way Bill (intra-state)
    (60000, 150, 2, BUYERS[4]),       # total 63,000  -> E-Way Bill (inter-state)
    (80000, 200, 3, BUYERS[5]),       # total 84,000  -> E-Way Bill (inter-state)
    (120000, 300, 1, BUYERS[6]),      # total 126,000 -> E-Way Bill (intra-state)
]
sales = []
for k, (taxable, qty, pi, b) in enumerate(SALE_PLAN, 1):
    desc, hsn, unit, _ = PRODUCTS[pi]
    intra = b["state"] == BUYER["state"]
    cgst, sgst, igst = make_taxes(float(taxable), DEMO_GST_RATE, intra)
    total = r2(taxable + cgst + sgst + igst)
    sales.append(dict(
        id=f"SALE-{k:03d}", date=(date(2026, 10, 2) + timedelta(days=(k - 1) * 2)).isoformat(),
        invoice_no=f"SMG/26-27/{k:04d}", buyer_name=b["name"], buyer_gstin=b["gstin"], buyer_city=b["city"],
        from_pincode=BUYER["pincode"], to_pincode=b["pincode"],
        line_items=[dict(description=desc, hsn=hsn, qty=qty, unit=unit, rate=round(taxable / qty, 2),
                         amount=float(taxable))],
        taxable_value=float(taxable), gst_rate=DEMO_GST_RATE, cgst=cgst, sgst=sgst, igst=igst, total=total,
        eway_bill_required=total > 50000))

PINCODES = [  # approximate city-centre coordinates, for demo distance estimates only
    ("560001", "Bengaluru", "Karnataka", 12.9763, 77.6033), ("560034", "Bengaluru", "Karnataka", 12.9352, 77.6245),
    ("560095", "Bengaluru", "Karnataka", 12.9279, 77.6271), ("560068", "Bengaluru", "Karnataka", 12.9081, 77.6376),
    ("560058", "Bengaluru", "Karnataka", 13.0286, 77.5197), ("570001", "Mysuru", "Karnataka", 12.2958, 76.6394),
    ("580020", "Hubballi", "Karnataka", 15.3647, 75.1240), ("600001", "Chennai", "Tamil Nadu", 13.0827, 80.2707),
    ("641001", "Coimbatore", "Tamil Nadu", 11.0168, 76.9558), ("641601", "Tiruppur", "Tamil Nadu", 11.1085, 77.3411),
    ("411001", "Pune", "Maharashtra", 18.5204, 73.8567), ("400001", "Mumbai", "Maharashtra", 18.9388, 72.8354),
    ("395003", "Surat", "Gujarat", 21.1702, 72.8311), ("380001", "Ahmedabad", "Gujarat", 23.0225, 72.5714),
]
with open(os.path.join(DATA, "pincodes.csv"), "w") as f:
    f.write("pincode,city,state,lat,lng\n")
    for row in PINCODES:
        f.write(",".join(map(str, row)) + "\n")

# ---------------------------------------------------------------- bill HTML (3 layouts)


def tax_lines(inv):
    r = inv["gst_rate"]
    if inv["igst"] > 0:
        return [(f"IGST @ {r:g}%", inv["igst"])]
    return [(f"CGST @ {r / 2:g}%", inv["cgst"]), (f"SGST @ {r / 2:g}%", inv["sgst"])]


def layout_a(inv):
    rows = "".join(
        f"<tr><td>{n}</td><td>{l['description']}</td><td>{l['hsn']}</td><td class='r'>{l['qty']} {l['unit']}</td>"
        f"<td class='r'>{inr(l['rate'])}</td><td class='r'>{inr(l['amount'])}</td></tr>"
        for n, l in enumerate(inv["line_items"], 1))
    tx = "".join(f"<tr><td colspan='5' class='r'>{n}</td><td class='r'>{inr(v)}</td></tr>" for n, v in tax_lines(inv))
    css = ("body{margin:0;background:#fff;font-family:Arial,Helvetica,sans-serif;color:#111}"
           "#sheet{width:794px;padding:36px 40px;box-sizing:border-box;background:#fff}"
           "h1{margin:0;font-size:22px;letter-spacing:2px;text-align:center}"
           ".top{display:flex;justify-content:space-between;margin-top:18px;font-size:13px;line-height:1.5}"
           "table{width:100%;border-collapse:collapse;margin-top:16px;font-size:13px}"
           "th,td{border:1px solid #222;padding:7px 8px;text-align:left}th{background:#eee}.r{text-align:right}"
           ".tot td{font-weight:bold;font-size:15px}.foot{margin-top:28px;font-size:11px;color:#444}")
    return (f"<style>{css}</style><div id='sheet'><h1>TAX INVOICE</h1><div class='top'>"
            f"<div><b style='font-size:16px'>{inv['supplier_name']}</b><br>{inv['supplier_address']}<br>"
            f"GSTIN: {inv['supplier_gstin']}</div>"
            f"<div style='text-align:right'>Invoice No: <b>{inv['invoice_no']}</b><br>Date: {inv['date'][8:]}-{inv['date'][5:7]}-{inv['date'][:4]}"
            f"<br>Place of supply: {inv['place_of_supply']}</div></div>"
            f"<div class='top'><div><b>Bill to:</b><br>{inv['buyer_name']}<br>GSTIN: {inv['buyer_gstin']}</div></div>"
            f"<table><tr><th>#</th><th>Description of goods</th><th>HSN</th><th class='r'>Qty</th><th class='r'>Rate</th>"
            f"<th class='r'>Amount</th></tr>{rows}"
            f"<tr><td colspan='5' class='r'>Taxable value</td><td class='r'>{inr(inv['taxable_value'])}</td></tr>{tx}"
            f"<tr class='tot'><td colspan='5' class='r'>Grand total (Rs)</td><td class='r'>{inr(inv['total'])}</td></tr></table>"
            f"<div class='foot'>Subject to local jurisdiction. This is a computer generated invoice.</div></div>")


def layout_b(inv):
    rows = "".join(
        f"<div class='it'>{l['description']}<br>HSN {l['hsn']} &nbsp; {l['qty']} {l['unit']} x {inr(l['rate'])}"
        f"<span>{inr(l['amount'])}</span></div>" for l in inv["line_items"])
    tx = "".join(f"<div class='row'>{n}<span>{inr(v)}</span></div>" for n, v in tax_lines(inv))
    css = ("body{margin:0;background:#fff}#sheet{width:380px;padding:22px 20px;box-sizing:border-box;background:#fbfbfb;"
           "font-family:'Courier New',monospace;font-size:13px;color:#000}"
           ".c{text-align:center}.it{border-bottom:1px dashed #000;padding:8px 0;position:relative}"
           ".it span,.row span{float:right}.row{padding:3px 0}.big{font-size:16px;font-weight:bold;"
           "border-top:2px solid #000;margin-top:6px;padding-top:6px}")
    return (f"<style>{css}</style><div id='sheet'><div class='c'><b style='font-size:16px'>{inv['supplier_name']}</b><br>"
            f"{inv['supplier_address']}<br>GSTIN {inv['supplier_gstin']}<br>--------------------------------<br>"
            f"<b>TAX INVOICE</b></div>Inv: {inv['invoice_no']}<br>Date: {inv['date'][8:]}/{inv['date'][5:7]}/{inv['date'][:4]}<br>"
            f"To: {inv['buyer_name']}<br>GSTIN {inv['buyer_gstin']}<br>--------------------------------{rows}"
            f"<div class='row'>Taxable<span>{inr(inv['taxable_value'])}</span></div>{tx}"
            f"<div class='row big'>TOTAL Rs<span>{inr(inv['total'])}</span></div>"
            f"<div class='c' style='margin-top:12px'>Thank you. Visit again.</div></div>")


COLORS = ["#0b6e4f", "#1d4e89", "#8a2be2", "#b5473a", "#2b7a78", "#6b4e16", "#c2410c", "#334155"]


def layout_c(inv):
    col = COLORS[int(inv["supplier_gstin"][-3:].encode().hex(), 16) % len(COLORS)]
    rows = "".join(
        f"<tr><td>{l['description']}<div class='s'>HSN {l['hsn']}</div></td><td class='r'>{l['qty']} {l['unit']}</td>"
        f"<td class='r'>{inr(l['rate'])}</td><td class='r'>{inr(l['amount'])}</td></tr>" for l in inv["line_items"])
    tx = "".join(f"<div class='kv'><span>{n}</span><b>{inr(v)}</b></div>" for n, v in tax_lines(inv))
    css = ("body{margin:0;background:#fff;font-family:'Helvetica Neue',Arial,sans-serif;color:#1a1a1a}"
           f"#sheet{{width:794px;box-sizing:border-box;background:#fff}}.hd{{background:{col};color:#fff;padding:26px 40px}}"
           ".hd h2{margin:0;font-size:24px}.hd div{font-size:12.5px;opacity:.92;margin-top:4px}"
           ".bd{padding:24px 40px}.meta{display:flex;justify-content:space-between;font-size:13px;line-height:1.6}"
           "table{width:100%;border-collapse:collapse;margin-top:20px;font-size:13px}"
           f"th{{text-align:left;border-bottom:2px solid {col};padding:8px 4px;color:{col}}}td{{padding:9px 4px;border-bottom:1px solid #ddd}}"
           ".r{text-align:right}.s{font-size:11px;color:#666}.sum{width:300px;margin-left:auto;margin-top:18px;font-size:13px}"
           ".kv{display:flex;justify-content:space-between;padding:4px 0}"
           f".gt{{border-top:2px solid {col};margin-top:6px;padding-top:8px;font-size:17px}}")
    return (f"<style>{css}</style><div id='sheet'><div class='hd'><h2>{inv['supplier_name']}</h2>"
            f"<div>{inv['supplier_address']} &nbsp;|&nbsp; GSTIN {inv['supplier_gstin']}</div></div><div class='bd'>"
            f"<div class='meta'><div><b>INVOICE</b><br>No. {inv['invoice_no']}<br>Date {inv['date']}</div>"
            f"<div><b>Billed to</b><br>{inv['buyer_name']}<br>GSTIN {inv['buyer_gstin']}</div></div>"
            f"<table><tr><th>Item</th><th class='r'>Qty</th><th class='r'>Rate</th><th class='r'>Amount</th></tr>{rows}</table>"
            f"<div class='sum'><div class='kv'><span>Subtotal</span><b>{inr(inv['taxable_value'])}</b></div>{tx}"
            f"<div class='kv gt'><span>Total</span><b>Rs {inr(inv['total'])}</b></div></div></div></div>")


LAYOUTS = [layout_a, layout_b, layout_c]

# ---------------------------------------------------------------- phone-photo augmentation


def coeffs(dst, src):
    m = []
    for (x, y), (u, v) in zip(dst, src):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        m.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    return np.linalg.solve(np.array(m, dtype=float), np.array(src, dtype=float).reshape(8))


def phone_photo(img, seed):
    rng = random.Random(seed)
    w, h = img.size
    pad = 90
    W, H = w + 2 * pad, h + 2 * pad
    desk = Image.new("RGB", (W, H), (62 + rng.randint(-8, 8), 56, 50))
    dd = ImageDraw.Draw(desk)
    for _ in range(40):  # desk texture
        y = rng.randint(0, H)
        dd.line([(0, y), (W, y + rng.randint(-6, 6))], fill=(70 + rng.randint(-10, 10), 62, 54), width=rng.randint(1, 3))
    paper = img.convert("RGB").rotate(rng.uniform(-3.5, 3.5), expand=True, fillcolor=(0, 0, 0, 0) if False else (62, 56, 50),
                                      resample=Image.BICUBIC)
    desk.paste(paper, ((W - paper.width) // 2, (H - paper.height) // 2))
    # fold creases
    cr = Image.new("L", (W, H), 0)
    cd = ImageDraw.Draw(cr)
    for _ in range(rng.randint(2, 3)):
        if rng.random() < 0.5:
            y = rng.randint(pad + 100, H - pad - 100)
            cd.line([(pad, y), (W - pad, y + rng.randint(-25, 25))], fill=120, width=3)
        else:
            x = rng.randint(pad + 100, W - pad - 100)
            cd.line([(x, pad), (x + rng.randint(-25, 25), H - pad)], fill=120, width=3)
    cr = cr.filter(ImageFilter.GaussianBlur(2.2))
    arr = np.array(desk).astype(float)
    arr -= np.array(cr)[..., None] * 0.55
    # lighting gradient (one side darker) + shadow
    g = np.linspace(rng.uniform(0.78, 0.92), 1.08, W)[None, :, None]
    if rng.random() < 0.5:
        g = g[:, ::-1]
    arr *= g
    arr += np.random.normal(0, 5.5, arr.shape)
    out = Image.fromarray(np.clip(arr, 0, 255).astype("uint8"))
    j = lambda: rng.randint(10, 38)
    dst = [(j(), j()), (W - j(), j()), (W - j(), H - j()), (j(), H - j())]
    src = [(0, 0), (W, 0), (W, H), (0, H)]
    out = out.transform((W, H), Image.PERSPECTIVE, coeffs(dst, src), Image.BICUBIC, fillcolor=(30, 28, 26))
    out = out.filter(ImageFilter.GaussianBlur(rng.uniform(0.7, 1.3)))
    return out


# ---------------------------------------------------------------- render
def render_all():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(device_scale_factor=1.5, viewport={"width": 900, "height": 1000})
        page = ctx.new_page()
        for i, inv in enumerate(invoices, 1):
            page.set_content("<html><body>" + LAYOUTS[i % 3](inv) + "</body></html>")
            png = os.path.join(BILLS, f"INV-{i:03d}.png")
            page.locator("#sheet").screenshot(path=png)
            if i in PHOTO:
                img = Image.open(png)
                phone_photo(img, seed=i).save(os.path.join(BILLS, f"INV-{i:03d}.jpg"), quality=72)
                os.remove(png)
        browser.close()


render_all()

for name, obj in (("invoices.json", invoices), ("gstr2b.json", gstr2b), ("ground_truth.json", ground_truth),
                  ("sales.json", sales)):
    with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
print("done:", counts, "sales needing E-Way Bill:", sum(s["eway_bill_required"] for s in sales))
