import streamlit as st
import requests
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Історія діагностик — AgroDiag",
    page_icon="📊",
    layout="wide",
)

# Custom CSS for styling
st.markdown("""
<style>
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

    .case-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 5px solid #4caf50;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }

    .case-card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
        transform: translateX(5px);
    }

    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    .stat-number {
        font-size: 2.5rem;
        font-weight: 700;
    }

    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# Main title
st.markdown('<h1 class="main-title">📊 Історія діагностик</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Переглядайте всі попередні діагностики та їх результати</p>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Налаштування")

    backend_url = st.text_input(
        "Backend URL",
        value="http://127.0.0.1:8000",
        help="🔗 Базова адреса FastAPI сервера",
    )

    st.divider()

    # Filters
    st.subheader("🔍 Фільтри")

    date_filter = st.date_input(
        "Дата діагностики",
        value=None,
        help="Фільтрувати по даті (залиште порожнім для всіх)"
    )

    limit = st.slider(
        "Кількість записів",
        min_value=10,
        max_value=100,
        value=50,
        step=10,
        help="Максимальна кількість діагностик для відображення"
    )

    st.divider()

    with st.expander("ℹ️ Про історію"):
        st.markdown("""
        На цій сторінці ви можете:
        - 📋 Переглянути всі діагностики
        - 🔍 Фільтрувати по даті
        - 📊 Переглянути деталі кожної діагностики
        - 🔄 Порівняти результати
        """)

# Prepare API endpoint
cases_endpoint = backend_url.rstrip("/") + "/v1/cases"

# Fetch cases
with st.spinner("⏳ Завантажуємо історію діагностик..."):
    try:
        params = {"limit": limit}
        if date_filter:
            params["date"] = date_filter.isoformat()

        res = requests.get(cases_endpoint, params=params, timeout=30)

        if res.status_code != 200:
            st.error(f"❌ Помилка {res.status_code}: {res.text[:500]}")
        else:
            data = res.json()
            cases = data.get("cases", [])
            total = data.get("total", 0)

            # Display statistics
            st.markdown("### 📈 Статистика")

            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

            with col_stat1:
                st.metric("📊 Всього діагностик", total)

            with col_stat2:
                # Count unique crops
                unique_crops = len(set(c.get("crop", "") for c in cases))
                st.metric("🌾 Культур", unique_crops)

            with col_stat3:
                # Count cases with specific crop
                if cases:
                    most_common_crop = max(set(c.get("crop", "") for c in cases), key=lambda x: sum(1 for c in cases if c.get("crop") == x))
                    st.metric("🏆 Найчастіше", most_common_crop)
                else:
                    st.metric("🏆 Найчастіше", "N/A")

            with col_stat4:
                # Today's cases
                today_str = datetime.now().date().isoformat()
                today_cases = sum(1 for c in cases if c.get("date", "") == today_str)
                st.metric("📅 Сьогодні", today_cases)

            st.divider()

            # Display cases
            if not cases:
                st.info("📭 Історія діагностик порожня. Виконайте діагностику на головній сторінці!")
            else:
                st.markdown(f"### 📋 Діагностики ({len(cases)})")

                # Search box
                search_query = st.text_input("🔍 Пошук по симптомам", placeholder="Введіть ключові слова...")

                # Filter cases by search query
                filtered_cases = cases
                if search_query:
                    filtered_cases = [
                        c for c in cases
                        if search_query.lower() in c.get("symptoms_preview", "").lower()
                    ]

                st.caption(f"Знайдено: {len(filtered_cases)} з {len(cases)}")

                # Display each case
                for case in filtered_cases:
                    case_id = case.get("case_id", "unknown")
                    crop = case.get("crop", "unknown")
                    date = case.get("date", "unknown")
                    symptoms_preview = case.get("symptoms_preview", "")

                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 2, 1])

                        with col1:
                            st.markdown(f"**🆔 Case ID:** `{case_id[:8]}...`")
                            st.caption(f"**Симптоми:** {symptoms_preview}...")

                        with col2:
                            st.markdown(f"**🌾 Культура:** {crop}")
                            st.caption(f"**📅 Дата:** {date}")

                        with col3:
                            # View details button
                            if st.button("👁️ Деталі", key=f"view_{case_id}", use_container_width=True):
                                st.session_state[f"show_details_{case_id}"] = True

                        # Show details if button clicked
                        if st.session_state.get(f"show_details_{case_id}", False):
                            st.divider()

                            with st.spinner("Завантажуємо деталі..."):
                                try:
                                    detail_url = f"{backend_url.rstrip('/')}/v1/cases/{case_id}"
                                    detail_res = requests.get(detail_url, timeout=30)

                                    if detail_res.status_code == 200:
                                        detail_data = detail_res.json()

                                        # Display full diagnosis
                                        st.markdown("#### 🔍 Повна діагностика")

                                        # Candidates
                                        candidates = detail_data.get("candidates", [])
                                        if candidates:
                                            st.markdown("**Можливі діагнози:**")
                                            for idx, c in enumerate(candidates, 1):
                                                col_a, col_b = st.columns([3, 1])
                                                with col_a:
                                                    st.write(f"{idx}. **{c.get('disease', 'N/A')}**")
                                                    st.caption(c.get('rationale', ''))
                                                with col_b:
                                                    score_pct = int(c.get('score', 0) * 100)
                                                    st.metric("Точність", f"{score_pct}%")

                                        # Action plan
                                        plan = detail_data.get("plan", {})
                                        if plan:
                                            st.markdown("**📋 План дій:**")
                                            col_p1, col_p2 = st.columns(2)

                                            with col_p1:
                                                diagnostics = plan.get("diagnostics", [])
                                                if diagnostics:
                                                    st.markdown("*Діагностичні заходи:*")
                                                    for d in diagnostics:
                                                        st.write(f"- {d}")

                                                agronomy = plan.get("agronomy", [])
                                                if agronomy:
                                                    st.markdown("*Агротехнічні заходи:*")
                                                    for a in agronomy:
                                                        st.write(f"- {a}")

                                            with col_p2:
                                                chemical = plan.get("chemical", [])
                                                if chemical:
                                                    st.markdown("*Хімічний захист:*")
                                                    for ch in chemical:
                                                        st.write(f"- {ch}")

                                                bio = plan.get("bio", [])
                                                if bio:
                                                    st.markdown("*Біологічний захист:*")
                                                    for b in bio:
                                                        st.write(f"- {b}")

                                        # Close button
                                        if st.button("❌ Закрити", key=f"close_{case_id}"):
                                            st.session_state[f"show_details_{case_id}"] = False
                                            st.rerun()

                                    else:
                                        st.error(f"Не вдалося завантажити деталі: {detail_res.status_code}")

                                except Exception as e:
                                    st.error(f"Помилка: {str(e)}")

    except requests.exceptions.ConnectionError:
        st.error("🔌 Не вдалося підключитися до сервера. Переконайтеся, що Backend запущено.")
    except Exception as e:
        st.error(f"❌ Помилка: {str(e)}")
        st.exception(e)

# Footer
st.divider()
st.caption("💡 Підказка: Використовуйте фільтри в бічній панелі для пошуку діагностик")
