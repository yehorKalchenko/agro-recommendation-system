import streamlit as st
import requests

st.set_page_config(
    page_title="AgroDiag — Demo",
    page_icon="🌿",
    layout="centered",
)

st.title("🌿 AgroDiag — система попередньої діагностики")

with st.sidebar:
    st.header("Налаштування")
    backend_url = st.text_input(
        "Backend URL",
        value="http://127.0.0.1:8000",
        help="Базова адреса FastAPI (без /v1/diagnose в кінці)",
    )
    diag_endpoint = backend_url.rstrip("/") + "/v1/diagnose"
    st.write(f"Ендпойнт: `{diag_endpoint}`")

st.markdown("Опиши симптоми рослини, додай фото (за бажання) та отримай попередні гіпотези з планом дій.")

with st.form("diag_form"):
    crop = st.selectbox("Культура", ["potato", "onion", "garlic", "tomato", "cucumber"], index=3)
    growth_stage = st.text_input("Стадія росту (опц.)", value="vegetative")

    col1, col2 = st.columns(2)
    with col1:
        lat = st.text_input("Lat (опц.)", value="")
    with col2:
        lon = st.text_input("Lon (опц.)", value="")

    symptoms_text = st.text_area(
        "Симптоми (текст)",
        placeholder="Опиши симптоми: плями, наліт, в'янення, умови вирощування тощо",
        height=150,
    )

    images = st.file_uploader(
        "Зображення (опц.)",
        accept_multiple_files=True,
        type=["png", "jpg", "jpeg", "webp"],
    )

    submitted = st.form_submit_button("Діагностувати")

if submitted:
    if not symptoms_text or len(symptoms_text.strip()) < 5:
        st.error("Заповни поле 'Симптоми (текст)' (мінімум 5 символів).")
    else:
        with st.spinner("Опрацьовуємо запит..."):
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
                files.append(
                    (
                        "images",
                        (img.name, img.getvalue(), img.type or "application/octet-stream"),
                    )
                )

            try:
                res = requests.post(diag_endpoint, data=data, files=files, timeout=60)
                if res.status_code != 200:
                    st.error(f"Помилка {res.status_code}: {res.text[:500]}")
                else:
                    body = res.json()
                    st.success("Готово ✅")

                    st.code(f"case_id: {body.get('case_id')}", language="text")

                    # Кандидати
                    st.subheader("Кандидати")
                    for c in body.get("candidates", []):
                        with st.container(border=True):
                            st.markdown(f"**{c['disease']}** — score: `{c['score']}`")
                            st.write(c.get("rationale", ""))
                            kb = c.get("kb_refs") or []
                            if kb:
                                st.caption("KB: " + ", ".join([k.get("title", "") for k in kb]))

                    # План
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

                    debug = body.get("debug") or {}
                    if debug:
                        st.expander("Debug").json(debug)

            except Exception as e:
                st.exception(e)
