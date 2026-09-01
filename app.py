#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit web app — διαδραστική δημιουργία newsletter «με το κουμπί».
Deploy δωρεάν στο Streamlit Community Cloud (share.streamlit.io) από το GitHub repo.

Απαιτεί secret: ANTHROPIC_API_KEY  (Streamlit → App → Settings → Secrets)
Τρέξε τοπικά:  streamlit run app.py
"""
import os
import streamlit as st

# Πέρνα το κλειδί από τα Streamlit secrets στο περιβάλλον, ΠΡΙΝ φορτωθεί το SDK
if "ANTHROPIC_API_KEY" in st.secrets:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]

from weekly_newsletter import (
    PRODUCTS, generate, split_output, validate, IMAGE_MAP, MODEL,
)

st.set_page_config(page_title="Zarkolia Newsletter Generator", page_icon="📰", layout="wide")

st.title("📰 Zarkolia / Nutri-MX — Newsletter Generator")
st.caption("Live επικαιρότητα + νέες μελέτες → πλήρες HTML + Έλεγχος Αξιοπιστίας. "
           "Πάντα ανθρώπινος έλεγχος πριν την αποστολή.")

if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error("Λείπει το ANTHROPIC_API_KEY. Πρόσθεσέ το στα Settings → Secrets της εφαρμογής.")
    st.stop()

# ── Επιλογές ────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([1, 2, 2])
with c1:
    audience = st.radio("Κοινό", ["doctors", "pharmacists"],
                        format_func=lambda x: "👨‍⚕️ Ιατροί" if x == "doctors" else "💊 Φαρμακοποιοί")
with c2:
    product_label = st.selectbox("Προϊόν", [f"{i+1}. {p}" for i, p in enumerate(PRODUCTS)])
    product_n = int(product_label.split(".")[0])
with c3:
    topics = st.text_input("Θέματα (προαιρετικά — αλλιώς αυτόματη επιλογή)",
                           placeholder="π.χ. Α3, 10.1   (κενό = live auto)")

img = IMAGE_MAP.get(product_n)
st.caption(("🖼️ Εικόνα: επιβεβαιωμένη ✅" if img
            else "🖼️ Εικόνα: δεν υπάρχει επιβεβαιωμένο link — θα μπει placeholder ⚠️")
           + f"  ·  Μοντέλο: `{MODEL}`")

# ── Δημιουργία ──────────────────────────────────────────────────────────────
if st.button("⚙️ Δημιουργία newsletter", type="primary", use_container_width=True):
    with st.spinner("Live αναζήτηση + σύνταξη + έλεγχος αξιοπιστίας… (~1–3 λεπτά)"):
        try:
            raw = generate(audience, product_n, topics.strip())
            subject, reliab, html = split_output(raw)
            issues = validate(subject, html)
        except Exception as e:
            st.error(f"Σφάλμα δημιουργίας: {e}")
            st.stop()

    st.success("Ολοκληρώθηκε.")
    st.subheader("✉️ Subject line")
    st.code(subject or "—", language=None)

    verdict = "⚠️ ΧΡΕΙΑΖΕΤΑΙ ΕΛΕΓΧΟ" if issues else "✅ Καθαρό"
    st.subheader(f"🔍 Έλεγχος Αξιοπιστίας — {verdict}")
    st.text(reliab or "—")
    if issues:
        for i in issues:
            st.warning(i)

    if html:
        st.download_button("⬇️ Κατέβασε το HTML", data=html,
                           file_name=f"{audience}_{PRODUCTS[product_n-1].split()[0]}.html",
                           mime="text/html", use_container_width=True)
        st.subheader("👁️ Προεπισκόπηση")
        st.components.v1.html(html, height=900, scrolling=True)
    else:
        st.error("Δεν παρήχθη έγκυρο HTML — δες το raw output παρακάτω.")
        with st.expander("Raw output"):
            st.text(raw)

st.divider()
st.caption("Το app παράγει υλικό για έλεγχο — δεν στέλνει σε παραλήπτες. "
           "Ο αυτόματος έλεγχος αξιοπιστίας βοηθά, δεν αντικαθιστά την κλινική κρίση.")
