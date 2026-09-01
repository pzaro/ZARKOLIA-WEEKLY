#!/usr/bin/env python3
"""ΠΡΟΑΙΡΕΤΙΚΟ template: δημιουργία DRAFT campaign στο Mailchimp (δεν στέλνει).
Χρήση: python mailchimp_draft.py newsletters/αρχείο.html "Subject line"
Env: MAILCHIMP_API_KEY (μορφή key-usXX), MAILCHIMP_AUDIENCE_ID, MAILCHIMP_FROM, MAILCHIMP_FROM_NAME
"""
import os, sys, json, urllib.request

def dc(key): return key.split("-")[-1]  # data center από το api key

def main():
    if len(sys.argv) < 3: sys.exit("usage: mailchimp_draft.py file.html \"subject\"")
    html = open(sys.argv[1], encoding="utf-8").read(); subject = sys.argv[2]
    key = os.environ["MAILCHIMP_API_KEY"]; aud = os.environ["MAILCHIMP_AUDIENCE_ID"]
    base = f"https://{dc(key)}.api.mailchimp.com/3.0"
    def call(path, payload):
        req = urllib.request.Request(base+path, data=json.dumps(payload).encode(),
              headers={"Authorization": "apikey "+key, "Content-Type":"application/json"})
        return json.load(urllib.request.urlopen(req))
    camp = call("/campaigns", {"type":"regular","recipients":{"list_id":aud},
        "settings":{"subject_line":subject,"title":subject,
        "from_name":os.environ.get("MAILCHIMP_FROM_NAME","Zarkolia Health"),
        "reply_to":os.environ.get("MAILCHIMP_FROM","zarkolia.gr@gmail.com")}})
    call(f"/campaigns/{camp['id']}/content", {"html": html})
    print("✓ Draft δημιουργήθηκε (δεν στάλθηκε):", camp["id"])

if __name__ == "__main__": main()
