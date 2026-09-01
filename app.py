#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit web app — ΔΥΟ ΣΤΑΔΙΑ, όπως το prompt:
  Στάδιο 1: live αναζήτηση → προτείνει ~10 επίκαιρα θέματα → διαλέγεις εσύ.
  Στάδιο 2: φτιάχνει το πλήρες newsletter ΜΟΝΟ για τα θέματα που επέλεξες + έλεγχος αξιοπιστίας.
Deploy: share.streamlit.io  ·  Secret: ANTHROPIC_API_KEY
"""
import os
import streamlit as st

if "ANTHROPIC_API_KEY" in st.secrets:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]

from weekly_newsletter import (
    PRODUCTS, discover_topics, generate, split_output, validate, IMAGE_MAP, MODEL,
)

st.set_page_config(page_title="Zarkolia Newsletter Generator", page_icon="📰", layout="wide")
st.title("📰 Zarkolia / Nutri-MX — Newsletter Generator")
st.caption("Ροή prompt: Βήμα 1 (πρότεινε θέματα από live αναζήτηση) → επιλογή → "
           "Βήμα 2 (σύνταξη + Έλεγχος Αξιοπιστίας). Πάντα ανθρώπινος έλεγχος πριν την αποστολή.")

if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error("Λείπει το ANTHROPIC_API_KEY (Settings → Secrets).")
    st.stop()

ss = st.session_state
ss.setdefault("topics", None)
ss.setdefault("ctx", None)
ss.setdefault("result", None)

st.subheader("1️⃣ Κοινό & Προϊόν")
c1, c2 = st.columns([1, 3])
with c1:
    audience = st.radio("Κοινό", ["doctors", "pharmacists"],
                        format_func=lambda x: "👨‍⚕️ Ιατροί" if x == "doctors" else "💊 Φαρμακοποιοί")
with c2:
    product_label = st.selectbox("Προϊόν", [f"{i+1}. {p}" for i, p in enumerate(PRODUCTS)])
    product_n = int(product_label.split(".")[0])
    img = IMAGE_MAP.get(product_n)
    st.caption(("🖼️ Εικόνα επιβεβαιωμένη ✅" if img else "🖼️ Εικόνα: placeholder ⚠️")
               + f"  ·  Μοντέλο `{MODEL}`")

st.subheader("2️⃣ Βήμα 1 — Πρότεινε επίκαιρα θέματα")
if st.button("🔎 Βρες τα θέματα της εβδομάδας (live)", use_container_width=True):
    with st.spinner("Live αναζήτηση πρόσφατων νέων & μελετών… (~40–70 δευτ.)"):
        try:
            ss.topics = discover_topics(audience, product_n)
            ss.ctx = (audience, product_n)
            ss.result = None
        except Exception as e:
            st.error(f"Σφάλμα αναζήτησης: {e}")

if ss.topics:
    aud_txt = "Ιατροί" if ss.ctx[0] == "doctors" else "Φαρμακοποιοί"
    st.info(f"Προτάσεις για: **{aud_txt} · {PRODUCTS[ss.ctx[1]-1]}** "
            f"(αν άλλαξες κοινό/προϊόν, ξανά-έψαξε).")
    chosen = st.multiselect("✅ Διάλεξε 1+ θέματα:", ss.topics, default=[])
    manual = st.text_input("➕ (προαιρετικά) evergreen κωδικοί", placeholder="π.χ. 7.4, 10.1")

    st.subheader("3️⃣ Βήμα 2 — Δημιούργησε το newsletter")
    if st.button("⚙️ Σύνταξη + Έλεγχος Αξιοπιστίας", type="primary",
                 use_container_width=True, disabled=not (chosen or manual)):
        picked = list(chosen) + ([manual] if manual.strip() else [])
        topics_str = " · ".join(picked)
        with st.spinner("Σύνταξη πλήρους newsletter + έλεγχος αξιοπιστίας… (~60–90 δευτ.)"):
            try:
                raw = generate(ss.ctx[0], ss.ctx[1], topics_str)
                subject, reliab, html = split_output(raw)
                issues = validate(subject, html)
                ss.result = (subject, reliab, html, issues, raw)
            except Exception as e:
                st.error(f"Σφάλμα δημιουργίας: {e}")
elif ss.topics is None:
    st.caption("Πάτα το κουμπί για να δεις τα προτεινόμενα θέματα της εβδομάδας.")

if ss.result:
    subject, reliab, html, issues, raw = ss.result
    st.divider()
    st.subheader("✉️ Subject line")
    st.code(subject or "—", language=None)
    verdict = "⚠️ ΧΡΕΙΑΖΕΤΑΙ ΕΛΕΓΧΟ" if issues else "✅ Καθαρό"
    st.subheader(f"🔍 Έλεγχος Αξιοπιστίας — {verdict}")
    st.text(reliab or "—")
    for i in issues:
        st.warning(i)
    if html:
        st.download_button("⬇️ Κατέβασε το HTML", data=html,
                           file_name=f"{ss.ctx[0]}_{PRODUCTS[ss.ctx[1]-1].split()[0]}.html",
                           mime="text/html", use_container_width=True)
        st.subheader("👁️ Προεπισκόπηση")
        st.components.v1.html(html, height=900, scrolling=True)
    else:
        st.error("Δεν παρήχθη έγκυρο HTML — δες το raw output.")
        with st.expander("Raw output"):
            st.text(raw)

st.divider()
st.caption("Το app παράγει υλικό για έλεγχο — δεν στέλνει σε παραλήπτες.")
