#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zarkolia / Nutri-MX — Εβδομαδιαία αυτόματη γεννήτρια newsletter.

Καλεί το Claude API (με web_search) δίνοντας το unified prompt, ώστε το μοντέλο
να: (1) ψάξει την τρέχουσα επικαιρότητα & νέες μελέτες, (2) επιλέξει θέματα,
(3) γράψει το HTML newsletter, (4) τρέξει τον Έλεγχο Αξιοπιστίας (Βήμα 2.5).
Μετά, το script κάνει τεχνική επικύρωση (εικόνες HTTP 200, χωρίς «cite», subject)
και αποθηκεύει το αρχείο για ανθρώπινο έλεγχο πριν την αποστολή.

ΧΡΗΣΗ:
    export ANTHROPIC_API_KEY=sk-...
    python weekly_newsletter.py --audience pharmacists --product auto
    # ή σταθερό προϊόν:  --product 6     αναλύσεις:  --topics "Α3,10.1"

Απαιτεί: pip install anthropic  (βλ. requirements.txt)
"""

import argparse
import datetime as dt
import os
import re
import smtplib
import ssl
import sys
import urllib.request
from email.message import EmailMessage
from pathlib import Path

try:
    import anthropic
except ImportError:
    sys.exit("Λείπει το SDK. Τρέξε:  pip install -r requirements.txt")

# ── Ρυθμίσεις ───────────────────────────────────────────────────────────────
MODEL = os.environ.get("ZARKOLIA_MODEL", "claude-sonnet-5")   # ή claude-opus-4-8 για μέγιστη ακρίβεια
PROMPT_FILE = Path(__file__).parent / "Prompt_Weekly_Newsletter_UNIFIED.md"
OUT_DIR = Path(__file__).parent / "newsletters"
MAX_TOKENS = 16000

PRODUCTS = [
    "Zplast Total Repair", "Zplast Cream", "Revitacell+ Face Cream 50 ml",
    "Hydralia Face Cream 50 ml", "Revitacell Eyes", "Bruise Off Gel",
    "Alveolair Sir", "Z-Boost Caps", "Nutri-MX D3 4000 IU + K2 100 μg",
    "Nutri-MX Magnesium + B6", "Nutri-MX Omega-3 1000 mg",
    "Nutri-MX Probiotic Premium", "Nutri-MX Joint Support",
    "Nutri-MX A-Z Multivitamin & Minerals",
]

# Επιβεβαιωμένα raw image links (συμπλήρωσε όσα λείπουν όταν τα ανεβάσεις)
IMAGE_MAP = {
    2:  "https://raw.githubusercontent.com/pzaro/zarkolia-images/main/ZplastCream%20100gr.jpg",
    6:  "https://raw.githubusercontent.com/pzaro/zarkolia-images/main/Bruise%20Off%20%CE%BC%CE%B5%20%CF%86%CF%8C%CE%BD%CF%84%CE%BF.jpg",
    12: "https://raw.githubusercontent.com/pzaro/zarkolia-images/main/NUTRI%20MX%20PROBIOTIC%20PREMIUM.jpg",
}

DELIMS = ("<<<SUBJECT>>>", "<<<RELIABILITY>>>", "<<<HTML>>>", "<<<END>>>")


# ── Επιλογή προϊόντος (rotation ανά ISO week) ───────────────────────────────
def pick_product(arg: str) -> int:
    if arg == "auto":
        wk = dt.date.today().isocalendar()[1]
        return (wk % len(PRODUCTS)) + 1
    n = int(arg)
    if not 1 <= n <= len(PRODUCTS):
        sys.exit(f"Το προϊόν πρέπει να είναι 1–{len(PRODUCTS)}")
    return n


# ── Κατασκευή οδηγίας (μη-διαδραστική εκτέλεση του prompt) ───────────────────
def build_run_instruction(audience: str, product_n: int, topics: str) -> str:
    aud = "ΦΑΡΜΑΚΟΠΟΙΟΥΣ" if audience.startswith("pharm") else "ΙΑΤΡΟΥΣ"
    prod = f"{product_n}. {PRODUCTS[product_n - 1]}"
    img = IMAGE_MAP.get(product_n)
    img_line = (f"Χρησιμοποίησε ΑΥΤΟ το επιβεβαιωμένο image URL: {img}"
                if img else
                "Βρες/επιβεβαίωσε το σωστό raw image URL· αν δεν επιβεβαιώνεται (HTTP 200), "
                "άφησε placeholder και σημείωσέ το στον Έλεγχο Αξιοπιστίας.")
    topics_line = (f"Χρησιμοποίησε ΑΥΤΑ τα θέματα: {topics}." if topics else
                   "Επίλεξε μόνος σου τα 3–4 ΠΙΟ ΠΡΟΣΦΑΤΑ & σημαντικά θέματα της εβδομάδας "
                   "(νέες εγκρίσεις, PRAC, breakthrough/συνέδρια, οδηγίες), + 1 evergreen αν ταιριάζει.")
    today = dt.date.today().isoformat()
    return f"""ΕΚΤΕΛΕΣΗ ΜΗ-ΔΙΑΔΡΑΣΤΙΚΗ (μην κάνεις ερωτήσεις — αποφάσισε μόνος σου).

Σημερινή ημερομηνία: {today}.
Κοινό (Βήμα 0): {aud}.
Προϊόν (Βήμα 1): {prod}.
{img_line}

Βήμα 1: Κάνε ΠΡΑΓΜΑΤΙΚΟ web search για την τρέχουσα επικαιρότητα ΑΥΤΗΣ της εβδομάδας
(FDA/EMA εγκρίσεις, PRAC σήματα, ESC/ACC/ADA/ASCO late-breaking, νέες μελέτες).
{topics_line}

Βήμα 2: Γράψε το ΠΛΗΡΕΣ HTML newsletter σύμφωνα με το prompt (inline CSS, ένα style block
μόνο για stat-tooltips, hover-tooltips στους στατιστικούς δείκτες, χωρίς «cite»).

Βήμα 2.5: Τρέξε τον Έλεγχο Αξιοπιστίας (επαλήθευση PMID, όχι επινοημένα στατιστικά,
embargo→preview, EU-safe). 

ΜΟΡΦΗ ΕΞΟΔΟΥ — ακριβώς έτσι, με τους διαχωριστές:
{DELIMS[0]}
(μία γραμμή: το subject line)
{DELIMS[1]}
(ο Πίνακας Ελέγχου Αξιοπιστίας με ✓/⚠/✗ + ετυμηγορία)
{DELIMS[2]}
(ΟΛΟΚΛΗΡΟ το HTML, από <!DOCTYPE html> έως </html>)
{DELIMS[3]}
"""


# ── Βήμα 1 μόνο: live πρόταση επίκαιρων θεμάτων (για επιλογή από τον χρήστη) ──
def discover_topics(audience: str, product_n: int, n: int = 10) -> list:
    """Τρέχει ΜΟΝΟ το Βήμα 1: live web search → ~n επίκαιρα θέματα προς επιλογή."""
    client = anthropic.Anthropic()
    system_prompt = PROMPT_FILE.read_text(encoding="utf-8")
    aud = "ΦΑΡΜΑΚΟΠΟΙΟΥΣ" if audience.startswith("pharm") else "ΙΑΤΡΟΥΣ"
    prod = f"{product_n}. {PRODUCTS[product_n - 1]}"
    today = dt.date.today().isoformat()
    msg = f"""Εκτέλεσε ΜΟΝΟ το Βήμα 1 (θεματολογία) — μη-διαδραστικά, χωρίς ερωτήσεις.
Σημερινή ημερομηνία: {today}. Κοινό: {aud}. Προϊόν: {prod}.
Κάνε ΠΡΑΓΜΑΤΙΚΟ web search για τα ΠΙΟ ΠΡΟΣΦΑΤΑ ιατρικά νέα ΑΥΤΗΣ της εβδομάδας
(FDA/EMA εγκρίσεις, PRAC σήματα, ESC/ACC/ADA/ASCO late-breaking, νέες μελέτες).
Πρότεινε {n} επίκαιρα θέματα «Ανάλυσης της Εβδομάδας».
Επίστρεψε ΜΟΝΟ λίστα — μία γραμμή ανά θέμα, ΑΚΡΙΒΩΣ στη μορφή:
ΚΩΔΙΚΟΣ|Τίτλος — μία σύντομη γραμμή περιγραφή
(π.χ.  Α3|STAREE — στατίνες σε ≥70, −30% MACE, ESC 2026)
Χωρίς εισαγωγικά, χωρίς αρίθμηση, χωρίς άλλο κείμενο πριν/μετά."""
    resp = client.messages.create(
        model=MODEL, max_tokens=2000, system=system_prompt,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}],
        messages=[{"role": "user", "content": msg}],
    )
    text = "\n".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    topics = []
    for line in text.splitlines():
        line = line.strip().lstrip("-•* ").strip()
        if "|" in line:
            code, desc = line.split("|", 1)
            topics.append(f"{code.strip()} — {desc.strip()}")
        elif line and len(topics) and len(line) > 8:
            topics.append(line)
    return topics[:n] if topics else ["(δεν επιστράφηκαν θέματα — δοκίμασε ξανά)"]


# ── Κλήση Claude API με web_search ──────────────────────────────────────────
def generate(audience: str, product_n: int, topics: str) -> str:
    client = anthropic.Anthropic()  # διαβάζει ANTHROPIC_API_KEY από env
    system_prompt = PROMPT_FILE.read_text(encoding="utf-8")
    user_msg = build_run_instruction(audience, product_n, topics)

    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}],
        messages=[{"role": "user", "content": user_msg}],
    )
    # Ένωσε όλα τα text blocks (αγνόησε tool_use/tool_result)
    return "\n".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


# ── Parsing εξόδου ──────────────────────────────────────────────────────────
def split_output(text: str):
    def between(a, b):
        m = re.search(re.escape(a) + r"(.*?)" + re.escape(b), text, re.S)
        return m.group(1).strip() if m else ""
    subject = between(DELIMS[0], DELIMS[1])
    reliab = between(DELIMS[1], DELIMS[2])
    html = between(DELIMS[2], DELIMS[3]) or text[text.find("<!DOCTYPE"):] if "<!DOCTYPE" in text else ""
    return subject, reliab, html


# ── Τεχνική επικύρωση ───────────────────────────────────────────────────────
def http_ok(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "zarkolia-check"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception:
        try:  # μερικά CDNs δεν δέχονται HEAD
            with urllib.request.urlopen(url, timeout=15) as r:
                return r.status == 200
        except Exception:
            return False


def validate(subject: str, html: str) -> list:
    issues = []
    if not subject:
        issues.append("✗ Λείπει subject line.")
    if not html or "<!DOCTYPE" not in html:
        issues.append("✗ Λείπει/ελλιπές HTML.")
        return issues
    if re.search(r"\bcite\b", html, re.I):
        issues.append("⚠ Βρέθηκε η λέξη «cite» — αφαίρεσέ την.")
    if "github.com" in html and "/blob/" in html:
        issues.append("⚠ Υπάρχει blob image URL — μετέτρεψε σε raw.githubusercontent.")
    imgs = re.findall(r'<img[^>]+src="([^"]+)"', html)
    for u in imgs:
        if u.startswith("http") and not http_ok(u):
            issues.append(f"✗ Εικόνα δεν φορτώνει (≠200): {u}")
    # πολλαπλά style blocks (επιτρέπεται 1 για tooltips)
    if len(re.findall(r"<style", html, re.I)) > 1:
        issues.append("⚠ Πάνω από ένα <style> block.")
    return issues


# ── Αποθήκευση ──────────────────────────────────────────────────────────────
def save(product_n: int, audience: str, subject: str, reliab: str,
         html: str, issues: list) -> Path:
    OUT_DIR.mkdir(exist_ok=True)
    stamp = dt.date.today().isoformat()
    slug = PRODUCTS[product_n - 1].split()[0].lower().replace("+", "")
    base = OUT_DIR / f"{stamp}_{audience}_{slug}"
    base.with_suffix(".html").write_text(html, encoding="utf-8")
    report = (f"# Newsletter {stamp} — {PRODUCTS[product_n-1]} ({audience})\n\n"
              f"## Subject\n{subject}\n\n"
              f"## Έλεγχος Αξιοπιστίας (Claude)\n{reliab}\n\n"
              f"## Τεχνική επικύρωση (script)\n" +
              ("\n".join(issues) if issues else "✓ Καθαρό — καμία ένσταση.") + "\n")
    base.with_suffix(".report.md").write_text(report, encoding="utf-8")
    return base.with_suffix(".html")


# ── Εβδομαδιαίο email ελέγχου (στον εαυτό σου — ΔΕΝ στέλνει σε παραλήπτες) ────
def send_review_email(subject: str, html: str, report: str, issues: list) -> str:
    """Στέλνει το newsletter στο REVIEW_TO για ανθρώπινη έγκριση.
    Env: REVIEW_TO, SMTP_USER, SMTP_PASS (Gmail App Password),
         SMTP_HOST=smtp.gmail.com, SMTP_PORT=587, REVIEW_FROM (προαιρ.)."""
    to_addr = os.environ.get("REVIEW_TO")
    if not to_addr:
        return "skip"
    user = os.environ.get("SMTP_USER")
    pw = os.environ.get("SMTP_PASS")
    if not (user and pw):
        return "⚠ REVIEW_TO ορίστηκε αλλά λείπουν SMTP_USER/SMTP_PASS — παραλείφθηκε."
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    verdict = "⚠ ΧΡΕΙΑΖΕΤΑΙ ΕΛΕΓΧΟ" if issues else "✓ καθαρό"

    msg = EmailMessage()
    msg["Subject"] = f"[ΕΛΕΓΧΟΣ · {verdict}] {subject}"
    msg["From"] = os.environ.get("REVIEW_FROM", user)
    msg["To"] = to_addr
    # Το plain-text body = ο Πίνακας Αξιοπιστίας + τεχνικές ενστάσεις (για γρήγορη έγκριση)
    body = ("Προεπισκόπηση εβδομαδιαίου newsletter — για έλεγχο πριν την αποστολή.\n\n"
            "ΕΛΕΓΧΟΣ ΑΞΙΟΠΙΣΤΙΑΣ (Claude):\n" + (report or "-") + "\n\n"
            "ΤΕΧΝΙΚΗ ΕΠΙΚΥΡΩΣΗ (script):\n" +
            ("\n".join(issues) if issues else "✓ Καθαρό.") +
            "\n\nΤο ίδιο το newsletter είναι το HTML μέρος αυτού του email.\n")
    msg.set_content(body)
    msg.add_alternative(html, subtype="html")  # το HTML rendered στο inbox

    ctx = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls(context=ctx)
        s.login(user, pw)
        s.send_message(msg)
    return f"✓ Στάλθηκε email ελέγχου στο {to_addr}"


# ── main ────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Εβδομαδιαία γεννήτρια newsletter Zarkolia/Nutri-MX")
    ap.add_argument("--audience", default="doctors",
                    choices=["doctors", "pharmacists"], help="κοινό")
    ap.add_argument("--product", default="auto",
                    help="'auto' (rotation) ή αριθμός 1–14")
    ap.add_argument("--topics", default="",
                    help="προαιρετικά σταθερά θέματα, π.χ. 'Α3,10.1'")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Όρισε ANTHROPIC_API_KEY στο περιβάλλον.")
    if not PROMPT_FILE.exists():
        sys.exit(f"Δεν βρέθηκε το prompt: {PROMPT_FILE}")

    product_n = pick_product(args.product)
    print(f"▶ Δημιουργία: {PRODUCTS[product_n-1]} · κοινό={args.audience} · μοντέλο={MODEL}")

    text = generate(args.audience, product_n, args.topics)
    subject, reliab, html = split_output(text)
    issues = validate(subject, html)
    path = save(product_n, args.audience, subject, reliab, html, issues)
    print(f"✔ Αποθηκεύτηκε: {path}")
    print(f"  Report:      {path.with_suffix('.report.md')}")

    # Εβδομαδιαίο email ελέγχου στον εαυτό σου (αν έχει οριστεί REVIEW_TO)
    try:
        print("✉ " + send_review_email(subject, html, reliab, issues))
    except Exception as e:
        print(f"⚠ Απέτυχε η αποστολή email ελέγχου: {e}")

    if issues:
        print("⚠ Εκκρεμότητες επικύρωσης:")
        for i in issues:
            print("   " + i)
        # exit code 2 ώστε το CI να «κοκκινίσει» αν κάτι χρειάζεται χειρωνακτικό έλεγχο
        sys.exit(2)
    print("✓ Έτοιμο για ανθρώπινο έλεγχο πριν την αποστολή.")


if __name__ == "__main__":
    main()
