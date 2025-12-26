import streamlit as st
import requests
import os

# Page configuration
st.set_page_config(
    page_title="AgroDiag — Діагностична система",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Enhanced CSS matching About Us page
st.markdown("""
<style>
    /* App background */
    .stApp {
        background-color: black;
    }

    /* Main title styling */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #2e7d32;
        text-align: center;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }

    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #4caf50 0%, #388e3c 100%);
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        border: none;
        font-weight: 600;
        transition: transform 0.2s ease;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #388e3c 0%, #2e7d32 100%);
        transform: translateY(-2px);
    }

    /* Feature card styling */
    .feature-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: black;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        margin: 0.5rem 0;
    }

    /* Info box styling */
    .info-box {
        background: black;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 4px solid #4caf50;
        margin: 1rem 0;
    }

    /* Recognition result box */
    .recognition-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }

    .recognition-item {
        display: flex;
        justify-content: space-between;
        padding: 0.5rem;
        border-bottom: 1px solid rgba(255,255,255,0.2);
    }

    .recognition-item:last-child {
        border-bottom: none;
    }
</style>
""", unsafe_allow_html=True)

# Main title
st.markdown('<h1 class="main-title">🌿 AgroDiag — Система попередньої діагностики</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Аналіз симптомів рослин з використанням ШІ та бази знань</p>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Налаштування системи")

    # Backend URL
    backend_url = st.text_input(
        "Backend URL",
        value="http://127.0.0.1:8000",
        help="🔗 Базова адреса FastAPI сервера (без /v1/diagnose в кінці)",
    )
    diag_endpoint = backend_url.rstrip("/") + "/v1/diagnose"

    st.divider()

    # Advanced features toggle section
    st.subheader("🚀 Додаткові можливості")

    use_rekognition = st.checkbox(
        "AWS Rekognition",
        value=True,
        help="🔬 Використовувати AWS Rekognition для аналізу зображень (потребує налаштувань AWS)"
    )

    use_bedrock = st.checkbox(
        "AWS Bedrock LLM",
        value=(os.getenv("AGRO_LLM_MODE", "stub") == "bedrock"),
        help="🧠 Використовувати AWS Bedrock для розширеного аналізу (замість стандартного LLM). Потребує налаштувань AWS"
    )

    st.divider()

    # Info section
    st.info(f"📍 Ендпойнт: `{diag_endpoint}`")

    with st.expander("ℹ️ Про систему"):
        st.markdown("""
        **AgroDiag** - система діагностики захворювань рослин.

        **Можливості:**
        - 🌱 Підтримка 10 культур
        - 🔍 Аналіз симптомів через текст
        - 📸 Аналіз зображень
        - 🤖 ШІ-асистент
        - 📊 Історія діагностик

        **Підтримувані культури:**
        томати, картопля, перець, огірки, цибуля, часник, капуста, морква, буряк, пшениця
        """)

# Main form
with st.form("diag_form", clear_on_submit=False):
    st.subheader("📋 Дані для діагностики")

    col1, col2 = st.columns([2, 1])

    with col1:
        crop = st.selectbox(
            "🌾 Культура *",
            ["tomato", "potato", "pepper", "cucumber", "onion", "garlic", "cabbage", "carrot", "beet", "wheat"],
            index=0,
            help="Виберіть культуру, яку потрібно діагностувати"
        )

    with col2:
        growth_stage = st.selectbox(
            "🌱 Стадія росту",
            ["", "seedling", "vegetative", "flowering", "fruiting", "tubering", "tuber_development"],
            index=0,
            help="Опціонально: виберіть поточну стадію росту рослини для більш точної діагностики"
        )

    st.divider()

    # Location
    col3, col4 = st.columns(2)
    with col3:
        lat = st.text_input(
            "🌍 Широта (Latitude)",
            value="",
            placeholder="наприклад: 50.4501",
            help="Опціонально: географічна широта для врахування кліматичних умов"
        )
    with col4:
        lon = st.text_input(
            "🌍 Довгота (Longitude)",
            value="",
            placeholder="наприклад: 30.5234",
            help="Опціонально: географічна довгота для врахування кліматичних умов"
        )

    st.divider()

    # Symptoms
    symptoms_text = st.text_area(
        "📝 Опис симптомів *",
        placeholder="Детально опишіть симптоми: колір та форма плям, наліт, в'янення, деформація листя, умови вирощування (температура, вологість, полив), тривалість прояву симптомів тощо...",
        height=150,
        help="🔍 Чим детальніше опис, тим точніша діагностика. Мінімум 5 символів."
    )

    # Images
    images = st.file_uploader(
        "📸 Зображення рослин",
        accept_multiple_files=True,
        type=["png", "jpg", "jpeg", "webp"],
        help="📤 Завантажте до 4 фотографій симптомів (PNG, JPG, WEBP). Краща якість фото = точніша діагностика"
    )

    if images:
        st.caption(f"✅ Завантажено файлів: {len(images)}")
        cols = st.columns(min(len(images), 4))
        for idx, img in enumerate(images[:4]):
            with cols[idx]:
                st.image(img, caption=img.name, use_container_width=True)

    # Submit button
    submitted = st.form_submit_button("🔬 Діагностувати", use_container_width=True)

# Handle form submission
if submitted:
    if not symptoms_text or len(symptoms_text.strip()) < 5:
        st.error("❌ Будь ласка, заповніть поле 'Опис симптомів' (мінімум 5 символів)")
    else:
        with st.spinner("⏳ Опрацьовуємо запит... Це може зайняти кілька секунд"):
            # Prepare request data
            data = {
                "crop": crop,
                "symptoms_text": symptoms_text,
                "growth_stage": growth_stage or "",
            }

            # Add location if provided
            if lat and lon:
                try:
                    data["lat"] = float(lat)
                    data["lon"] = float(lon)
                except ValueError:
                    st.warning("⚠️ Некоректні координати. Діагностика буде проведена без врахування локації.")

            # Prepare images
            files = []
            for img in images or []:
                files.append(
                    (
                        "images",
                        (img.name, img.getvalue(), img.type or "application/octet-stream"),
                    )
                )

            # Add feature flags as headers (optional backend implementation)
            headers = {}
            if use_rekognition:
                headers["X-Use-Rekognition"] = "true"
            if use_bedrock:
                headers["X-Use-Bedrock"] = "true"

            try:
                # Make request to backend
                res = requests.post(
                    diag_endpoint,
                    data=data,
                    files=files,
                    headers=headers,
                    timeout=60
                )

                if res.status_code != 200:
                    st.error(f"❌ Помилка {res.status_code}: {res.text[:500]}")
                else:
                    body = res.json()

                    # Success message
                    st.success("✅ Діагностика завершена успішно!")

                    # Case ID
                    st.code(f"🆔 Case ID: {body.get('case_id')}", language="text")

                    # Display visual features (Recognition results) if available
                    visual_feats = body.get("visual_features", {})
                    if visual_feats:
                        st.subheader("🔬 Результати аналізу зображень")

                        # Separate Rekognition disease detections from other features
                        rekognition_diseases = {}
                        rekognition_features = {}
                        other_features = {}

                        for key, value in visual_feats.items():
                            if key.startswith('_'):
                                continue  # Skip internal/debug features
                            elif key.endswith('_rek'):
                                # Rekognition standard label features
                                rekognition_features[key.replace('_rek', '')] = value
                            elif not any(x in key for x in ['img', 'white_like', 'very_dark', 'edges_mean']):
                                # Likely a disease name from Custom Labels
                                # Check if it looks like a disease (not a basic feature)
                                if key not in ['lesion_spots', 'white_powder', 'downy_mildew', 'wilting', 'yellowing', 'black_spots', 'water_soaked']:
                                    rekognition_diseases[key] = value
                                else:
                                    other_features[key] = value
                            else:
                                other_features[key] = value

                        # Display Rekognition Custom Labels (disease detections) prominently
                        if rekognition_diseases:
                            st.markdown("### 🎯 AWS Rekognition - Виявлені захворювання")
                            st.markdown("""
                            <div class="feature-card">
                                <p><strong>Результати Custom Labels моделі:</strong></p>
                            </div>
                            """, unsafe_allow_html=True)

                            # Sort by confidence (highest first)
                            sorted_diseases = sorted(rekognition_diseases.items(), key=lambda x: x[1], reverse=True)

                            cols_rek = st.columns(min(len(sorted_diseases), 3))
                            for idx, (disease, confidence) in enumerate(sorted_diseases):
                                with cols_rek[idx % 3]:
                                    st.metric(
                                        label=disease.replace('_', ' ').title(),
                                        value=f"{int(confidence * 100)}%",
                                        help="Впевненість AWS Rekognition Custom Labels"
                                    )

                        # Display Rekognition standard features
                        if rekognition_features:
                            st.markdown("### 📸 AWS Rekognition - Виявлені ознаки")
                            cols_feat = st.columns(min(len(rekognition_features), 4))
                            for idx, (feat, conf) in enumerate(sorted(rekognition_features.items(), key=lambda x: x[1], reverse=True)):
                                with cols_feat[idx % 4]:
                                    st.metric(
                                        label=feat.replace('_', ' ').title(),
                                        value=f"{int(conf * 100)}%",
                                        help="Впевненість виявлення"
                                    )

                        # Display other features in expander
                        if other_features:
                            with st.expander("🔍 Додаткові візуальні ознаки"):
                                for feat, val in sorted(other_features.items(), key=lambda x: x[1], reverse=True):
                                    if not feat.startswith('_'):
                                        st.write(f"**{feat.replace('_', ' ').title()}**: {val:.2f}")

                        st.divider()

                    # Display top candidate only
                    st.subheader("🔍 Діагноз")

                    candidates = body.get("candidates", [])
                    if candidates:
                        # Show only the top candidate
                        c = candidates[0]
                        with st.container(border=True):
                            col_a, col_b = st.columns([3, 1])
                            with col_a:
                                st.markdown(f"### {c['disease']}")
                            with col_b:
                                score_pct = int(c['score'] * 100)
                                st.metric("Точність", f"{score_pct}%")

                            st.markdown(f"**Обґрунтування:** {c.get('rationale', 'Немає обґрунтування')}")

                            kb = c.get("kb_refs") or []
                            if kb:
                                kb_titles = ", ".join([k.get("title", "") for k in kb])
                                st.caption(f"📚 База знань: {kb_titles}")
                    else:
                        st.warning("⚠️ Не знайдено можливих діагнозів")

                    # Display action plan
                    st.subheader("📋 План дій")
                    plan = body.get("plan", {}) or {}

                    col_plan1, col_plan2 = st.columns(2)

                    with col_plan1:
                        # Diagnostics
                        st.markdown("**🔬 Діагностичні заходи**")
                        diagnostics = plan.get("diagnostics", [])
                        if diagnostics:
                            for i, t in enumerate(diagnostics, 1):
                                st.write(f"{i}. {t}")
                        else:
                            st.caption("Немає рекомендацій")

                        st.divider()

                        # Agronomy
                        st.markdown("**🌾 Агротехнічні заходи**")
                        agronomy = plan.get("agronomy", [])
                        if agronomy:
                            for i, t in enumerate(agronomy, 1):
                                st.write(f"{i}. {t}")
                        else:
                            st.caption("Немає рекомендацій")

                    with col_plan2:
                        # Chemical
                        st.markdown("**⚗️ Хімічний захист**")
                        chemical = plan.get("chemical", [])
                        if chemical:
                            for i, t in enumerate(chemical, 1):
                                st.write(f"{i}. {t}")
                        else:
                            st.caption("Немає рекомендацій")

                        st.divider()

                        # Bio
                        st.markdown("**🌿 Біологічний захист**")
                        bio = plan.get("bio", [])
                        if bio:
                            for i, t in enumerate(bio, 1):
                                st.write(f"{i}. {t}")
                        else:
                            st.caption("Немає рекомендацій")

                    # Disclaimers
                    st.divider()
                    for d in body.get("disclaimers", []):
                        st.warning(d)

                    # Debug info (collapsible)
                    debug = body.get("debug") or {}
                    if debug:
                        with st.expander("🔧 Технічна інформація"):
                            col_d1, col_d2 = st.columns(2)

                            with col_d1:
                                st.json(debug.get("timings", {}))

                            with col_d2:
                                st.json(debug.get("components", {}))

                            if debug.get("workspace_path"):
                                st.caption(f"📁 Дані збережено: `{debug.get('workspace_path')}`")

            except requests.exceptions.Timeout:
                st.error("⏱️ Запит перевищив час очікування. Спробуйте ще раз.")
            except requests.exceptions.ConnectionError:
                st.error("🔌 Не вдалося підключитися до сервера. Переконайтеся, що Backend запущено.")
            except Exception as e:
                st.error(f"❌ Непередбачена помилка: {str(e)}")
                st.exception(e)

# Footer
st.divider()
st.caption("💡 Використовуйте бічну панель для навігації між сторінками")
