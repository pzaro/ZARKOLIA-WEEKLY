# Zarkolia / Nutri-MX — Εβδομαδιαία Γεννήτρια Newsletter

Αυτόματη παραγωγή evidence-based newsletter κάθε εβδομάδα, με βάση την **τρέχουσα
επικαιρότητα & νέες μελέτες**. Το «έξυπνο» μέρος το κάνει το **Claude API** (με
live web search) χρησιμοποιώντας το ενιαίο prompt· το script προσθέτει
χρονοπρογραμματισμό, τεχνική επικύρωση και αποθήκευση για ανθρώπινο έλεγχο.

## Πώς δουλεύει
1. `weekly_newsletter.py` καλεί το Claude API με το `Prompt_Weekly_Newsletter_UNIFIED.md`.
2. Το Claude ψάχνει live την εβδομαδιαία επικαιρότητα, επιλέγει θέματα, γράφει το
   HTML και τρέχει τον **Έλεγχο Αξιοπιστίας (Βήμα 2.5)**.
3. Το script επικυρώνει τεχνικά (εικόνες HTTP 200, χωρίς «cite», subject, blob→raw)
   και αποθηκεύει `.html` + `.report.md` στον φάκελο `newsletters/`.

## Τοπική εκτέλεση
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...
python weekly_newsletter.py --audience doctors --product auto
# σταθερό προϊόν + θέματα:
python weekly_newsletter.py --audience pharmacists --product 6 --topics "Α3,10.1"
```
Επιλογές: `--audience doctors|pharmacists` · `--product auto|1..14` · `--topics "…"`.
Μοντέλο: `export ZARKOLIA_MODEL=claude-opus-4-8` για μέγιστη ακρίβεια (default `claude-sonnet-5`).

## Αυτόματα κάθε εβδομάδα (GitHub Actions — δωρεάν)
1. Ανέβασε τον φάκελο σε GitHub repo.
2. Settings → Secrets → Actions → πρόσθεσε `ANTHROPIC_API_KEY`.
3. Το `.github/workflows/weekly.yml` τρέχει κάθε **Δευτέρα 06:00 UTC** (ή χειροκίνητα
   από την καρτέλα Actions → Run workflow). Το αποτέλεσμα ανεβαίνει ως artifact.

## Χρονοπρογραμματισμός σε δικό σου server (εναλλακτικά)
```cron
0 6 * * 1  cd /path/zarkolia-weekly && ANTHROPIC_API_KEY=sk-... /usr/bin/python3 weekly_newsletter.py --audience doctors --product auto
```

## Αποστολή (Mailchimp) — προαιρετικό & OFF by default
Για ασφάλεια, το πρόγραμμα **δεν στέλνει** αυτόματα — παράγει το HTML για έλεγχο.
Όταν θελήσεις auto-draft στο Mailchimp, δες `mailchimp_draft.py` (template) και
πρόσθεσε `MAILCHIMP_API_KEY` + `MAILCHIMP_AUDIENCE_ID`.

## ⚠️ Σημαντικά
- **Κόστος:** κάθε εκτέλεση καταναλώνει API tokens (χρέωση Anthropic).
- **Ιατρικό περιεχόμενο:** ο Έλεγχος Αξιοπιστίας μειώνει —δεν εξαλείφει— το ρίσκο.
  Κράτα **ανθρώπινο έλεγχο πριν την αποστολή** (human-in-the-loop).
- Συμπλήρωσε τα υπόλοιπα `IMAGE_MAP` links στο `weekly_newsletter.py` όταν
  επιβεβαιωθούν (HTTP 200), για να μη μένουν placeholders.

## ✉️ Εβδομαδιαίο email ελέγχου (στο δικό σου inbox)
Το πρόγραμμα στέλνει το έτοιμο newsletter στο mail σου **για έγκριση** (ποτέ στους
τελικούς παραλήπτες). Το subject προθεματίζεται με `[ΕΛΕΓΧΟΣ · ✓/⚠]`, και το body
έχει τον Πίνακα Αξιοπιστίας — το ίδιο το newsletter είναι το HTML μέρος του email.

Όρισε τα εξής env / GitHub Secrets:
- `REVIEW_TO` — πού θα φτάνει (π.χ. `zarkolia.gr@gmail.com`)
- `SMTP_USER` — το Gmail σου
- `SMTP_PASS` — **Gmail App Password** (Google Account → Security → 2-Step →
  App passwords· ΟΧΙ ο κανονικός κωδικός)
- `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587` (default)

Τοπικά:
```bash
export REVIEW_TO=zarkolia.gr@gmail.com
export SMTP_USER=zarkolia.gr@gmail.com
export SMTP_PASS=xxxx-xxxx-xxxx-xxxx        # App Password
python weekly_newsletter.py --audience doctors --product auto
```
Αν δεν οριστεί `REVIEW_TO`, το βήμα email παραλείπεται σιωπηλά.
