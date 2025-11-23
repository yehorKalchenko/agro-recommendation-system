import streamlit as st
import requests
import os

st.set_page_config(page_title="AgroDiag — Streamlit UI", page_icon="🌿", layout="centered")

st.title("🌿 AgroDiag — MVP (Streamlit)")
st.caption("Локальний клієнт до FastAPI /v1/diagnose")

with st.form("diag_form"):
    crop = st.selectbox("Культура", ["potato", "onion", "garlic", "tomato", "cucumber"], index=3)
    growth_stage = st.text_input("Стадія росту", value="vegetative")
    col1, col2 = st.columns(2)
    with col1:
        lat = st.text_input("Lat (опц.)", value="")
    with col2:
        lon = st.text_input("Lon (опц.)", value="")

    symptoms_text = st.text_area("Симптоми (текст)", placeholder="Опиши симптоми: плями, наліт, в'янення, тощо", height=120)

    images = st.file_uploader("Зображення (опц.)", accept_multiple_files=True, type=["png", "jpg", "jpeg", "webp"])

    submitted = st.form_submit_button("Діагностувати")

if submitted:
    if not symptoms_text or len(symptoms_text) < 5:
        st.error("Заповни поле 'Симптоми (текст)' (мінімум 5 символів).")
    else:
        with st.spinner("Опрацьовуємо запит..."):
            backend_url_default = os.getenv("BACKEND_URL", "http://127.0.0.1:8000/v1/diagnose")
            try:
                if "BACKEND_URL" in st.secrets:
                    backend_url_default = st.secrets["BACKEND_URL"]
            except Exception:
                pass
            with st.sidebar:
                backend_url = st.text_input("Backend URL", value=backend_url_default)
            # url = st.secrets.get("BACKEND_URL", "http://127.0.0.1:8000/v1/diagnose")
            data = {
                "crop": crop,
                "symptoms_text": symptoms_text,
                "growth_stage": growth_stage or "",
            }
            if lat and lon:
                data["lat"] = lat
                data["lon"] = lon

            files = []
            for img in images or []:
                files.append(("images", (img.name, img.getvalue(), img.type or "application/octet-stream")))

            try:
                res = requests.post(backend_url_default, data=data, files=files, timeout=30)
                if res.status_code != 200:
                    st.error(f"Помилка {res.status_code}: {res.text[:500]}")
                else:
                    body = res.json()
                    st.success("Готово ✅")

                    st.code(f"case_id: {body.get('case_id')}", language="text")

                    st.subheader("Кандидати")
                    for c in body.get("candidates", []):
                        with st.container(border=True):
                            st.markdown(f"**{c['disease']}** — score: `{c['score']}`")
                            st.write(c.get("rationale", ""))
                            kb = c.get("kb_refs") or []
                            if kb:
                                st.caption("KB: " + ", ".join([k.get("title","") for k in kb]))

                    plan = body.get("plan", {}) or {}
                    cols = st.columns(2)
                    with cols[0]:
                        st.markdown("**Diagnostics**")
                        for i, t in enumerate(plan.get("diagnostics", []), 1):
                            st.write(f"{i}. {t}")
                        st.markdown("**Agronomy**")
                        for i, t in enumerate(plan.get("agronomy", []), 1):
                            st.write(f"{i}. {t}")
                    with cols[1]:
                        st.markdown("**Chemical**")
                        for i, t in enumerate(plan.get("chemical", []), 1):
                            st.write(f"{i}. {t}")
                        st.markdown("**Bio**")
                        for i, t in enumerate(plan.get("bio", []), 1):
                            st.write(f"{i}. {t}")

                    for d in body.get("disclaimers", []):
                        st.caption(d)
            except Exception as e:
                st.exception(e)
