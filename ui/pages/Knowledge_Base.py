import streamlit as st
import os
import yaml
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="База знань — AgroDiag",
    page_icon="📚",
    layout="wide",
)

# Custom CSS for styling
st.markdown("""
<style>
    .stApp {
        background-color: black;
    }

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

    .disease-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 5px solid #ff9800;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }

    .disease-card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
        transform: translateY(-3px);
    }

    .crop-badge {
        display: inline-block;
        background: linear-gradient(90deg, #4caf50 0%, #8bc34a 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        margin: 0.25rem;
        font-weight: 600;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Main title
st.markdown('<h1 class="main-title">📚 База знань про захворювання рослин</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Інформація про підтримувані захворювання та культури</p>', unsafe_allow_html=True)

# Function to load knowledge base
@st.cache_data
def load_knowledge_base(kb_path):
    """Load all YAML knowledge base files"""
    diseases = []

    kb_root = Path(kb_path)

    # Try to resolve path if it's relative
    if not kb_root.exists():
        # Try relative to current file location
        current_dir = Path(__file__).parent.parent
        kb_root = (current_dir / ".." / kb_path).resolve()

    if not kb_root.exists():
        st.warning(f"❌ Шлях не знайдено: {kb_root}")
        return diseases

    # Iterate through crop directories
    for crop_dir in kb_root.iterdir():
        if crop_dir.is_dir():
            crop_name = crop_dir.name

            # Load each disease YAML file
            for yaml_file in crop_dir.glob("*.yaml"):
                try:
                    with open(yaml_file, 'r', encoding='utf-8') as f:
                        disease_data = yaml.safe_load(f)
                        if disease_data:
                            disease_data['crop'] = crop_name
                            disease_data['file_id'] = yaml_file.stem
                            diseases.append(disease_data)
                except Exception as e:
                    st.warning(f"Could not load {yaml_file}: {e}")

    return diseases

# Sidebar
with st.sidebar:
    st.header("⚙️ Налаштування")

    # KB path configuration
    kb_path = st.text_input(
        "Шлях до бази знань",
        value="app/data/kb",
        help="Відносний або абсолютний шлях до каталогу з базою знань"
    )

    st.divider()

    # Filters
    st.subheader("🔍 Фільтри")

    selected_crop = st.selectbox(
        "Культура",
        ["Всі", "tomato", "potato", "pepper", "cucumber", "onion", "garlic", "cabbage", "carrot", "beet", "wheat"],
        help="Фільтрувати захворювання по культурі"
    )

    search_query = st.text_input(
        "🔎 Пошук",
        placeholder="Назва захворювання або симптом",
        help="Пошук по назві захворювання або симптомах"
    )

    st.divider()

    with st.expander("ℹ️ Про базу знань"):
        st.markdown("""
        База знань містить інформацію про:
        - 📖 Назва захворювання
        - 🔬 Симптоми та візуальні ознаки
        - 🌱 Підтримувані культури
        - 📅 Стадії росту (вікно уразливості)
        - 💊 Методи боротьби (агротехніка, хімія, біо)
        """)

# Load knowledge base
with st.spinner("📚 Завантажуємо базу знань..."):
    diseases = load_knowledge_base(kb_path)

if not diseases:
    st.warning(f"📭 База знань порожня або не знайдена за шляхом: `{kb_path}`")
    st.info("""
    💡 **Можливі рішення:**
    1. Переконайтеся, що backend запущено з правильної директорії
    2. Спробуйте абсолютний шлях: `C:/Users/.../agro-project/app/data/kb`
    3. Перевірте, що YAML файли існують в підкаталогах (tomato/, potato/, тощо)
    """)
else:
    # Filter by crop
    if selected_crop != "Всі":
        diseases = [d for d in diseases if d.get("crop") == selected_crop]

    # Filter by search query
    if search_query:
        diseases = [
            d for d in diseases
            if search_query.lower() in d.get("name", "").lower()
            or search_query.lower() in str(d.get("symptoms", [])).lower()
            or search_query.lower() in str(d.get("visual_patterns", [])).lower()
        ]

    # Statistics
    st.markdown("### 📊 Статистика бази знань")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📚 Всього захворювань", len(diseases))

    with col2:
        unique_crops = len(set(d.get("crop", "") for d in diseases))
        st.metric("🌾 Культур", unique_crops)

    with col3:
        # Count diseases with symptoms
        with_symptoms = sum(1 for d in diseases if d.get("symptoms"))
        st.metric("🔬 З симптомами", with_symptoms)

    with col4:
        # Count diseases with actions
        with_actions = sum(1 for d in diseases if d.get("actions"))
        st.metric("💊 З планами дій", with_actions)

    st.divider()

    # Display diseases
    st.markdown(f"### 📋 Захворювання ({len(diseases)})")

    if not diseases:
        st.info("🔍 Не знайдено захворювань за вказаними фільтрами")
    else:
        # Group by crop for better organization
        diseases_by_crop = {}
        for disease in diseases:
            crop = disease.get("crop", "unknown")
            if crop not in diseases_by_crop:
                diseases_by_crop[crop] = []
            diseases_by_crop[crop].append(disease)

        # Display each crop section
        for crop, crop_diseases in sorted(diseases_by_crop.items()):
            with st.expander(f"🌾 {crop.capitalize()} ({len(crop_diseases)} захворювань)", expanded=(selected_crop == crop)):
                for disease in crop_diseases:
                    name = disease.get("name", "Unknown")
                    symptoms = disease.get("symptoms", [])
                    visual_patterns = disease.get("visual_patterns", [])
                    crops_supported = disease.get("crops_supported", [])
                    stage_window = disease.get("stage_window", [])
                    actions = disease.get("actions", {})

                    with st.container(border=True):
                        # Disease name and metadata
                        col_title, col_meta = st.columns([3, 1])

                        with col_title:
                            st.markdown(f"### {name}")

                        with col_meta:
                            # Crops badges
                            st.caption("**Культури:**")
                            for crop_name in crops_supported:
                                st.markdown(f'<span class="crop-badge">{crop_name}</span>', unsafe_allow_html=True)

                        # Stage window
                        if stage_window:
                            st.markdown("**📅 Стадії росту (вікно уразливості):**")
                            stage_names = {
                                "seedling": "Сходи",
                                "vegetative": "Вегетація",
                                "flowering": "Цвітіння",
                                "fruiting": "Плодоношення",
                                "tubering": "Бульбоутворення",
                                "tuber_development": "Розвиток бульб"
                            }
                            stages_translated = [stage_names.get(s, s) for s in stage_window]
                            st.write(f"🌱 {', '.join(stages_translated)}")

                        st.divider()

                        # Symptoms
                        if symptoms:
                            st.markdown("**🔬 Симптоми:**")
                            for symptom in symptoms:
                                st.write(f"- {symptom}")

                        # Visual patterns
                        if visual_patterns:
                            st.markdown("**👁️ Візуальні ознаки:**")
                            for pattern in visual_patterns:
                                st.write(f"- {pattern}")

                        # Actions (plan)
                        if actions:
                            st.markdown("**📋 План дій:**")

                            col_a1, col_a2 = st.columns(2)

                            with col_a1:
                                # Diagnostics
                                diagnostics = actions.get("diagnostics", [])
                                if diagnostics:
                                    st.markdown("**🔬 Діагностичні заходи:**")
                                    for diag in diagnostics:
                                        st.write(f"- {diag}")

                                # Agronomy
                                agronomy = actions.get("agronomy", [])
                                if agronomy:
                                    st.markdown("**🌾 Агротехнічні заходи:**")
                                    for agr in agronomy:
                                        st.write(f"- {agr}")

                            with col_a2:
                                # Chemical control
                                chemical = actions.get("chemical", [])
                                if chemical:
                                    st.markdown("**⚗️ Хімічний захист:**")
                                    for chem in chemical:
                                        st.write(f"- {chem}")

                                # Biological control
                                bio = actions.get("bio", [])
                                if bio:
                                    st.markdown("**🌿 Біологічний захист:**")
                                    for b in bio:
                                        st.write(f"- {b}")

                        # File info
                        st.caption(f"📄 Файл: `{disease.get('file_id', 'unknown')}.yaml`")

# Footer
st.divider()
st.caption("💡 Підказка: Використовуйте фільтри в бічній панелі для пошуку конкретних захворювань")
