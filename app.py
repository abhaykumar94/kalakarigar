# app.py
import streamlit as st
from PIL import Image
from utils.ai_utils import get_gemini_response
from utils.firebase_utils import (
    init_firebase,
    upload_image_to_storage,
    save_artisan_data,
)
from utils.image_utils import generate_enhanced_image
from utils.gcp_ai_utils import transcribe_audio, translate_text, get_image_labels
from st_audiorec import st_audiorec
from io import BytesIO
from utils.gdrive_utils import (
    get_gdrive_flow,
    get_gdrive_service_from_session,
    get_user_info,
    export_marketing_pack,
)
import time
import base64
import json
from datetime import datetime, timedelta


def encode_session_data(data):
    """Encode session data for URL storage"""
    json_str = json.dumps(data)
    encoded = base64.urlsafe_b64encode(json_str.encode()).decode()
    return encoded


def decode_session_data(encoded_data):
    """Decode session data from URL storage"""
    try:
        json_str = base64.urlsafe_b64decode(encoded_data.encode()).decode()
        return json.loads(json_str)
    except:
        return None


def save_credentials_to_url():
    """Save credentials to URL for persistence"""
    if st.session_state.get("gdrive_credentials") and st.session_state.get(
        "user_profile"
    ):
        session_data = {
            "creds": st.session_state.gdrive_credentials,
            "user": st.session_state.user_profile,
            "timestamp": datetime.now().isoformat(),
        }
        encoded = encode_session_data(session_data)
        st.query_params["auth_session"] = encoded


def restore_credentials_from_url():
    """Restore credentials from URL"""
    auth_session = st.query_params.get("auth_session")
    if auth_session:
        session_data = decode_session_data(auth_session)
        if session_data:
            # Check if session is not older than 24 hours
            try:
                timestamp = datetime.fromisoformat(session_data["timestamp"])
                if datetime.now() - timestamp < timedelta(hours=24):
                    st.session_state.gdrive_credentials = session_data["creds"]
                    st.session_state.user_profile = session_data["user"]
                    return True
            except:
                pass
    return False


def scroll_to_top():
    """Force scroll to top using JavaScript"""
    js_code = """
    <script>
    setTimeout(function() {
        window.parent.document.querySelector('.main').scrollTop = 0;
        window.parent.document.documentElement.scrollTop = 0;
        window.parent.document.body.scrollTop = 0;
    }, 100);
    </script>
    """
    st.components.v1.html(js_code, height=0)


def render_scroll_to_top_button():
    """Render fixed scroll to top button"""
    st.markdown(
        """
        <div id="scroll-to-top-container">
            <button class="scroll-to-top-btn" id="scrollToTopBtn" onclick="scrollToTop()">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="18,15 12,9 6,15"></polyline>
                </svg>
            </button>
        </div>

        <script>
        function scrollToTop() {
            const mainElement = window.parent.document.querySelector('.main');
            if (mainElement) {
                mainElement.scrollTo({ top: 0, behavior: 'smooth' });
            }
            window.parent.document.documentElement.scrollTo({ top: 0, behavior: 'smooth' });
            window.parent.document.body.scrollTo({ top: 0, behavior: 'smooth' });
        }

        function toggleScrollButton() {
            const scrollBtn = document.getElementById('scrollToTopBtn');
            if (!scrollBtn) return;
            
            const mainElement = window.parent.document.querySelector('.main');
            const scrollTop = mainElement ? mainElement.scrollTop : 
                             (window.parent.document.documentElement.scrollTop || window.parent.document.body.scrollTop);
            
            if (scrollTop > 300) {
                scrollBtn.classList.add('visible');
            } else {
                scrollBtn.classList.remove('visible');
            }
        }

        // Set up scroll listener
        setTimeout(function() {
            const mainElement = window.parent.document.querySelector('.main');
            if (mainElement) {
                mainElement.addEventListener('scroll', toggleScrollButton);
            }
            window.parent.addEventListener('scroll', toggleScrollButton);
            toggleScrollButton(); // Initial check
        }, 500);
        </script>
        """,
        unsafe_allow_html=True,
    )


# ==================== CONFIGURATION ====================
FAVICON_PATH = "assets/favicon.png"

st.set_page_config(
    page_title="KalaKarigar.ai - Empower Your Craft",
    page_icon=FAVICON_PATH,
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ==================== CUSTOM CSS STYLING ====================
def load_custom_css():
    st.markdown(
        """
    <style>
    /* Import Google Fonts for better typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Theme Variables */
    :root {
        --primary: #667eea;
        --primary-dark: #5a67d8;
        --primary-light: #7c8ff0;
        --secondary: #764ba2;
        --accent: #f59e0b;
        --success: #10b981;
        --success-dark: #059669;
        --danger: #ef4444;
        --bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --bg-gradient-hover: linear-gradient(135deg, #7c8ff0 0%, #8b5bb8 100%);
        --neon-glow: 0 0 20px rgba(102, 126, 234, 0.5);
        --neon-glow-strong: 0 0 30px rgba(102, 126, 234, 0.7);
        --text-primary: #1e293b;
        --text-secondary: #475569;
        --text-muted: #94a3b8;
        --bg-primary: #ffffff;
        --bg-secondary: #f8fafc;
        --bg-tertiary: #f1f5f9;
        --card-bg: #ffffff;
        --border-color: #e2e8f0;
        --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* Dark mode */
    @media (prefers-color-scheme: dark) {
        :root {
            --text-primary: #f1f5f9;
            --text-secondary: #cbd5e1;
            --text-muted: #64748b;
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-tertiary: #334155;
            --card-bg: #1e293b;
            --border-color: #334155;
            --neon-glow: 0 0 25px rgba(102, 126, 234, 0.6);
            --neon-glow-strong: 0 0 40px rgba(102, 126, 234, 0.8);
        }
    }
    
    /* Global Styles */
    * {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    .stApp {
        background: var(--bg-primary);
        color: var(--text-primary);
    }
    
    /* Fix header z-index */
    .stApp > header {
        z-index: 1000 !important;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: ;}
    footer {visibility: hidden;}
    
    /* Main container with proper padding */
    .main > div {
        padding-top: 1rem;
    }
    
    /* Enhanced Container */
    .main-container {
        background: var(--card-bg);
        border-radius: 16px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: var(--shadow-lg);
        border: 1px solid var(--border-color);
        transition: var(--transition);
        animation: fadeInUp 0.5s ease;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Progress Container - Always Horizontal */
    .progress-container {
        background: var(--bg-gradient);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1.5rem 0 2rem 0;
        box-shadow: var(--neon-glow);
        overflow-x: auto;
        animation: pulseGlow 3s ease-in-out infinite;
    }
    
    @keyframes pulseGlow {
        0%, 100% { box-shadow: var(--neon-glow); }
        50% { box-shadow: var(--neon-glow-strong); }
    }
    
    .progress-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        min-width: 400px;
        padding: 0.5rem;
    }
    
    .progress-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;
        z-index: 2;
    }
    
    .progress-step {
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        backdrop-filter: blur(10px);
        color: rgba(255, 255, 255, 0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 1.2rem;
        transition: var(--transition);
        border: 2px solid rgba(255, 255, 255, 0.3);
    }
    
    .progress-step.active {
        background: white;
        color: var(--primary);
        transform: scale(1.2);
        box-shadow: 0 0 0 8px rgba(255, 255, 255, 0.2),
                    0 0 20px rgba(255, 255, 255, 0.5);
    }
    
    .progress-step.completed {
        background: var(--success);
        color: white;
        border-color: var(--success-dark);
    }
    
    .progress-label {
        margin-top: 0.75rem;
        font-size: 0.85rem;
        font-weight: 500;
        color: white;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    .progress-connector {
        width: 80px;
        height: 3px;
        background: rgba(255, 255, 255, 0.3);
        position: relative;
        margin: 0 -15px;
        z-index: 1;
    }
    
    .progress-connector.completed {
        background: var(--success);
        box-shadow: 0 0 10px rgba(16, 185, 129, 0.5);
    }
    
    /* Scroll to Top Button */
    #scroll-to-top-container {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 1001;
    }
    
    .scroll-to-top-btn {
        width: 50px;
        height: 50px;
        background: var(--bg-gradient);
        border: none;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: var(--shadow-lg);
        color: white;
        font-size: 1.2rem;
        font-weight: bold;
        transition: var(--transition);
        opacity: 0;
        visibility: hidden;
        transform: translateY(20px);
    }
    
    .scroll-to-top-btn.visible {
        opacity: 1;
        visibility: visible;
        transform: translateY(0);
    }
    
    .scroll-to-top-btn:hover {
        transform: translateY(-3px) scale(1.1);
        box-shadow: var(--neon-glow);
        background: var(--bg-gradient-hover);
    }
    
    .scroll-to-top-btn:active {
        transform: translateY(-1px) scale(1.05);
    }
    
    .scroll-to-top-btn svg {
        width: 20px;
        height: 20px;
    }
    
    /* User Profile Card */
    .user-profile-card {
        background: var(--bg-gradient);
        border-radius: 12px;
        padding: 1rem;
        box-shadow: var(--shadow-lg);
        transition: var(--transition);
        animation: slideInDown 0.5s ease;
    }
    
    @keyframes slideInDown {
        from {
            opacity: 0;
            transform: translateY(-20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .user-profile-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--neon-glow);
    }
    
    .user-avatar {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: white;
        color: var(--primary);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        font-weight: 600;
        margin: 0 auto 0.5rem;
        box-shadow: var(--shadow);
    }
    
    .user-name {
        color: white;
        font-weight: 500;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    /* Enhanced Logout Button */
    .logout-btn {
        background: rgba(255, 255, 255, 0.2);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.3);
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: var(--transition);
        width: 100%;
        text-align: center;
    }
    
    .logout-btn:hover {
        background: rgba(255, 255, 255, 0.3);
        transform: translateY(-1px);
    }
    
    /* Feature Cards with Animation */
    .feature-card {
        background: var(--card-bg);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid var(--border-color);
        box-shadow: var(--shadow);
        transition: var(--transition);
        animation: fadeIn 0.5s ease;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    .feature-card:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-xl);
        border-color: var(--primary-light);
    }
    
    .feature-card.neon {
        border: 1px solid var(--primary);
        box-shadow: var(--neon-glow);
    }
    
    /* Enhanced Buttons */
    .stButton > button {
        background: var(--bg-gradient);
        color: white;
        border: none;
        padding: 0.875rem 2rem;
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.95rem;
        transition: var(--transition);
        box-shadow: var(--shadow);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button:before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.6s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: var(--neon-glow);
        background: var(--bg-gradient-hover);
    }
    
    .stButton > button:hover:before {
        left: 100%;
    }
    
    /* Success Message with Animation */
    .success-message {
        background: linear-gradient(135deg, var(--success), var(--success-dark));
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1.5rem 0;
        text-align: center;
        box-shadow: 0 0 30px rgba(16, 185, 129, 0.4);
        animation: bounceIn 0.6s ease;
    }
    
    @keyframes bounceIn {
        0% { transform: scale(0); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    /* Logo Container */
    .logo-container {
        text-align: center;
        margin: 1rem 0;
        animation: fadeIn 0.8s ease;
    }
    
    .logo-image {
        max-width: 120px;
        height: auto;
        filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1));
    }
    
    /* Text Areas Enhancement */
    .stTextArea textarea {
        min-height: 150px !important;
        border-radius: 10px;
        border: 1px solid var(--border-color);
        transition: var(--transition);
    }
    
    .stTextArea textarea:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Tab Content */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        background: var(--bg-tertiary);
        transition: var(--transition);
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: var(--primary-light);
        color: white;
    }
    
    /* Sidebar Enhancement */
    section[data-testid="stSidebar"] {
        background: var(--bg-secondary);
        z-index: 999;
    }
    
    section[data-testid="stSidebar"] .stButton > button {
        background: var(--bg-tertiary);
        color: var(--text-primary);
        box-shadow: none;
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: var(--primary);
        color: white;
    }
    
    /* File Uploader Enhancement */
    .stFileUploader > div {
        border-radius: 10px;
        border: 2px dashed var(--primary);
        padding: 1rem;
        transition: var(--transition);
    }
    
    .stFileUploader > div:hover {
        border-color: var(--primary-dark);
        background: var(--bg-tertiary);
    }
    
    /* Info Messages */
    .stAlert {
        border-radius: 10px;
        border-left: 4px solid var(--primary);
        animation: slideInLeft 0.4s ease;
    }
    
    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .main-container {
            padding: 1.25rem;
            border-radius: 12px;
        }
        
        .progress-container {
            padding: 1rem;
        }
        
        .progress-step {
            width: 40px;
            height: 40px;
            font-size: 1rem;
        }
        
        .progress-connector {
            width: 60px;
        }
        
        .logo-image {
            max-width: 140px;
        }
        
        .scroll-to-top-btn {
            bottom: 20px;
            right: 20px;
            width: 45px;
            height: 45px;
        }
        
        .scroll-to-top-btn svg {
            width: 20px;
            height: 20px;
        }
    }
    
    /* Smooth Scrolling */
    html {
        scroll-behavior: smooth;
    }
    
    /* Loading States */
    .stSpinner > div {
        border-color: var(--primary) !important;
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-secondary);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--primary);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary-dark);
    }

    /* Scroll Reset Helper */
    .scroll-to-top {
        scroll-behavior: smooth;
    }

    /* Ensure main content starts at top */
    section.main > .block-container {
        scroll-margin-top: 0;
    }
    
    /* Force scroll to top on page changes */
    .main .block-container {
        animation: scrollToTop 0.1s ease-out;
    }

    @keyframes scrollToTop {
        0% {
            transform: translateY(0);
        }
        1% {
            transform: translateY(-10px);
        }
        100% {
            transform: translateY(0);
        }
    }

    /* Ensure content starts from top */
    .stApp > .main {
        scroll-behavior: auto;
    }

    </style>
    """,
        unsafe_allow_html=True,
    )


def render_logo():
    """Render the responsive logo"""
    try:
        with open("assets/logo_desktop.png", "rb") as f:
            logo_desktop_data = base64.b64encode(f.read()).decode()

        with open("assets/logo_mobile.png", "rb") as f:
            logo_mobile_data = base64.b64encode(f.read()).decode()

        st.markdown(
            f"""
            <style>
            .desktop-logo {{ display: block; margin: 0 auto; }}
            .mobile-logo {{ display: none; }}
            @media (max-width: 768px) {{
                .desktop-logo {{ display: none; }}
                .mobile-logo {{ display: block; margin: 0 auto; }}
            }}
            </style>
            <div class="logo-container" style="width: 55%; margin: 0 auto;">
                <img src="data:image/png;base64,{logo_desktop_data}" class="desktop-logo logo-image" alt="KalaKarigar.ai">
                <img src="data:image/png;base64,{logo_mobile_data}" class="mobile-logo logo-image" alt="KalaKarigar.ai">
            </div>
            """,
            unsafe_allow_html=True,
        )
    except:
        st.markdown(
            """
            <div class="logo-container">
                <h2 style="background: var(--bg-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;">
                    🎨 KalaKarigar.ai
                </h2>
                <p style="color: var(--text-secondary); margin: 0.5rem 0 0 0; font-size: 0.9rem;">
                    Empower Your Craft with AI
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ==================== INITIALIZATION ====================
@st.cache_resource
def initialize_services():
    """Initialize Firebase and other services"""
    try:
        init_firebase()
        return True
    except Exception as e:
        st.error(f"⚠️ Failed to initialize services: {e}")
        return False


# ==================== SESSION STATE MANAGEMENT ====================
class SessionState:
    @staticmethod
    def init():
        """Initialize all session state variables"""
        defaults = {
            "gdrive_credentials": None,
            "user_profile": None,
            "page": "Onboarding",
            "artisan_data": {
                "craft_type": "",
                "description": "",
                "materials": "",
                "dimensions": "",
                "tags": [],
            },
            "product_image": None,
            "uploaded_file_name": "",
            "generated_content": None,
            "enhanced_image": None,
            "transcribed_text": None,
            "suggested_tags": None,
            "current_step": 1,
            "steps_completed": [],
        }

        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value


# ==================== HELPER FUNCTIONS ====================
def change_page(page_name, step_number):
    """Change page with step tracking and scroll to top"""
    st.session_state.page = page_name
    st.session_state.current_step = step_number
    # Mark previous steps as completed when moving forward
    if step_number > 1:
        for i in range(1, step_number):
            if i not in st.session_state.steps_completed:
                st.session_state.steps_completed.append(i)

    # Set a flag to trigger scroll after rerun
    st.session_state.should_scroll_to_top = True


def render_progress_indicator():
    """Render horizontal progress indicator"""
    steps = [
        ("1", "Details", 1),
        ("2", "Content", 2),
        ("3", "Enhance", 3),
        ("4", "Export", 4),
    ]

    html = '<div class="progress-container"><div class="progress-wrapper">'

    for i, (num, label, step) in enumerate(steps):
        is_active = st.session_state.current_step == step
        is_completed = step in st.session_state.steps_completed

        step_class = "active" if is_active else "completed" if is_completed else ""

        html += f"""
        <div class="progress-item">
            <div class="progress-step {step_class}">{num}</div>
            <div class="progress-label">{label}</div>
        </div>
        """

        if i < len(steps) - 1:
            # Connector is completed if the current step is completed
            connector_class = "completed" if is_completed else ""
            html += f'<div class="progress-connector {connector_class}"></div>'

    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)


def render_header():
    """Render application header with enhanced user info"""
    col1, col3 = st.columns([3, 1])

    with col1:
        render_logo()

    with col3:
        if st.session_state.user_profile:
            name = st.session_state.user_profile["name"].split()[0]
            initial = name[0].upper()
            st.markdown(
                f"""
                <div class="user-profile-card">
                    <div class="user-avatar">{initial}</div>
                    <div class="user-name">{name}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                "🚪 Logout",
                key="logout_btn",
                type="secondary",
                use_container_width=True,
            ):
                # Clear all query params
                for key in list(st.query_params.keys()):
                    st.query_params.pop(key, None)

                # Clear all session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]

                st.rerun()


# ==================== PAGE RENDERERS ====================
def render_onboarding_page():
    """Render the onboarding/details page with all form fields inside main-container"""

    # Product Information Section
    st.markdown("### 📋 Product Information")

    data = st.session_state.artisan_data

    # Craft Type
    data["craft_type"] = st.text_input(
        "🏺 **Craft Name**",
        value=data["craft_type"],
        placeholder="e.g., Bandhani Saree, Pottery, Jewelry",
        help="Enter the name of your craft or product",
    )

    # Voice Recording Section
    with st.expander("🎤 **Record Product Description** (Optional)", expanded=False):
        lang_options = {
            "English": "en-US",
            "हिन्दी (Hindi)": "hi-IN",
            "ગુજરાતી (Gujarati)": "gu-IN",
        }

        col_a, col_b = st.columns([1, 2])
        with col_a:
            selected_lang = st.selectbox("Language:", options=list(lang_options.keys()))
        with col_b:
            st.info("Record in your preferred language")

        # Improved audio recorder UI with instructions and loading indicator
        st.markdown(
            """
            <div style="margin-bottom: 0.5rem; color: var(--text-secondary); font-size: 0.95rem;">
                <ul style="margin: 0; padding-left: 1.2rem;">
                    <li>Click <b>Start Recording</b> and speak clearly.</li>
                    <li>Click <b>Stop</b> when done.</li>
                    <li>Transcribe or translate below.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Show spinner while audio controls are loading
        with st.spinner("Loading audio recorder..."):
            audio = st_audiorec()

        if audio:
            col_1, col_2 = st.columns(2)
            with col_1:
                if st.button(
                    "📝 Transcribe Audio",
                    type="secondary",
                    use_container_width=True,
                ):
                    with st.spinner("Transcribing..."):
                        transcribed = transcribe_audio(
                            audio, lang_options[selected_lang]
                        )
                        if transcribed:
                            st.session_state.transcribed_text = transcribed
                            st.success("✅ Transcription complete!")
                            if not data["description"]:
                                data["description"] = transcribed

            with col_2:
                if st.session_state.transcribed_text and selected_lang != "English":
                    if st.button(
                        "🌍 Translate to English",
                        type="secondary",
                        use_container_width=True,
                    ):
                        with st.spinner("Translating..."):
                            translated = translate_text(
                                st.session_state.transcribed_text, "en"
                            )
                            if translated:
                                data["description"] = translated
                                st.success("✅ Translation added!")

    # Text Fields
    data["description"] = st.text_area(
        "📋 **Product Description**",
        height=120,
        value=data["description"],
        placeholder="Describe your product in detail...",
        help="Provide a detailed description",
    )

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        data["materials"] = st.text_input(
            "🧵 **Materials Used**",
            value=data["materials"],
            placeholder="e.g., Cotton, Silk, Clay",
            help="Materials used in your craft",
        )
    with col_m2:
        data["dimensions"] = st.text_input(
            "📏 **Dimensions** (Optional)",
            value=data["dimensions"],
            placeholder="e.g., 6x9 feet",
            help="Size/dimensions of product",
        )

    # Product Image Section (Below other fields)
    st.markdown("---")
    st.markdown("### 🖼️ Product Image")

    col_img1, col_img2 = st.columns([1, 1])

    with col_img1:
        uploaded_file = st.file_uploader(
            "Upload a clear photo of your product",
            type=["jpg", "png", "jpeg"],
            help="Best results with well-lit, clear images",
        )

        if uploaded_file:
            if (
                st.session_state.product_image is None
                or uploaded_file.name != st.session_state.uploaded_file_name
            ):
                # Read the bytes of the uploaded file first
                image_bytes = uploaded_file.getvalue()

                # Open the image from bytes for display and other non-cached uses
                st.session_state.product_image = Image.open(BytesIO(image_bytes))
                st.session_state.uploaded_file_name = uploaded_file.name

                with st.spinner("🔍 Analyzing image with AI..."):
                    # ✅ Pass the HASHABLE raw bytes to the cached function
                    st.session_state.suggested_tags = get_image_labels(image_bytes)
                    time.sleep(0.5)

    with col_img2:
        if st.session_state.product_image:
            st.image(
                st.session_state.product_image,
                use_container_width=True,
                caption="Your Product",
            )

            if st.session_state.suggested_tags:
                st.markdown("#### 🏷️ AI-Suggested Tags")
                data["tags"] = st.multiselect(
                    "Select relevant tags for better marketing:",
                    options=st.session_state.suggested_tags,
                    default=st.session_state.suggested_tags[:5],
                    help="These tags help with searchability",
                )
        else:
            st.info("👈 Upload an image to see preview and get AI-suggested tags")

    # Action Button
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        if st.button(
            "💾 Save & Continue to Content →",
            type="primary",
            use_container_width=True,
            disabled=not (data["craft_type"] and st.session_state.product_image),
        ):
            if validate_onboarding_data():
                with st.spinner("Saving your information..."):
                    save_onboarding_data()
                    st.success("✅ Information saved successfully!")
                    time.sleep(1)
                    change_page("Content", 2)
                    st.rerun()


def render_content_page():
    """Render the AI content generation page"""

    # Product Details Card
    st.markdown("### 📋 Product Overview")
    col_detail1, col_detail2 = st.columns([1, 2])

    with col_detail1:
        if st.session_state.product_image:
            st.image(
                st.session_state.product_image,
                use_container_width=True,
                caption="Your Product",
            )

    with col_detail2:
        st.markdown(
            f"""
            <div class="feature-card neon">
                <h4 style="margin-top: 0;">🏺 {st.session_state.artisan_data['craft_type']}</h4>
                <p><strong>📝 Description:</strong> {st.session_state.artisan_data['description'][:150]}...</p>
                <p><strong>🧵 Materials:</strong> {st.session_state.artisan_data['materials']}</p>
                <p><strong>📏 Dimensions:</strong> {st.session_state.artisan_data.get('dimensions', 'Not specified')}</p>
                <p><strong>🏷️ Tags:</strong> {', '.join(st.session_state.artisan_data.get('tags', [])[:5])}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Generate Content Button
    col_gen1, col_gen2, col_gen3 = st.columns([1, 2, 1])
    with col_gen2:
        if st.button(
            "✨ Generate Marketing Content with AI",
            type="primary",
            use_container_width=True,
        ):
            with st.spinner("🤖 AI is creating compelling content..."):
                progress_bar = st.progress(0)
                for i in range(100):
                    time.sleep(0.02)
                    progress_bar.progress(i + 1)

                # ✅ Convert the PIL image to bytes before passing to the cached function
                buffered = BytesIO()
                st.session_state.product_image.save(buffered, format="PNG")
                image_bytes = buffered.getvalue()

                st.session_state.generated_content = get_gemini_response(
                    image_bytes, st.session_state.artisan_data
                )

                if st.session_state.generated_content:
                    st.balloons()
                    st.success("🎉 Content generated successfully!")
                    time.sleep(0.5)
                    st.rerun()

    # Generated Content Display
    if st.session_state.generated_content:
        st.markdown("### 📱 Generated Marketing Content")

        content = st.session_state.generated_content

        # Enhanced Product Description
        st.markdown("#### 📝 Enhanced Product Description")
        st.markdown(
            f"""
            <div class="feature-card" style="background: var(--bg-tertiary);">
                {content.get('product_description', 'Not available.')}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Social Media Captions with increased height
        st.markdown("#### 💬 Social Media Captions")
        captions = content.get("social_media_captions", [])
        if captions:
            tabs = st.tabs([f"📱 Caption {i+1}" for i in range(len(captions))])
            for i, (tab, caption) in enumerate(zip(tabs, captions)):
                with tab:
                    st.text_area(
                        "Ready to copy and paste:",
                        caption,
                        height=180,  # Increased height
                        key=f"caption_{i}",
                        help="Click to select all text, then copy",
                    )

        # Hashtags
        hashtags = content.get("hashtags", [])
        if hashtags:
            st.markdown("#### #️⃣ Trending Hashtags")
            hashtag_text = " ".join(f"{tag}" for tag in hashtags)
            st.code(hashtag_text, language=None)

        # Continue Button
        st.markdown("---")
        col_cont1, col_cont2, col_cont3 = st.columns([1, 2, 1])
        with col_cont2:
            if st.button(
                "🎨 Continue to Image Enhancement →",
                type="primary",
                use_container_width=True,
            ):
                change_page("Image", 3)
                st.rerun()
    else:
        st.info(
            "👆 Click the button above to generate AI-powered marketing content for your product"
        )


def render_image_page():
    """Render the AI image enhancement page"""

    st.markdown("### 🎨 AI-Powered Image Enhancement")
    st.info("✨ Choose a style to transform your product image with AI magic")

    # Style Selection with better cards
    cols = st.columns(3)
    styles = [
        (
            "🎨",
            "Vibrant",
            "Enhanced colors and contrast for eye-catching appeal",
            "Vibrant",
        ),
        (
            "📸",
            "Studio",
            "Professional studio lighting with clean background",
            "Studio",
        ),
        (
            "✨",
            "Festive",
            "Warm, celebratory atmosphere perfect for occasions",
            "Festive",
        ),
    ]

    for col, (icon, title, desc, style_name) in zip(cols, styles):
        with col:
            st.markdown(
                f"""
                <div class="feature-card" style="text-align: center; min-height: 180px; cursor: pointer;">
                    <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">{icon}</div>
                    <h4 style="color: var(--primary); margin: 0.5rem 0;">{title}</h4>
                    <p style="font-size: 0.85rem; color: var(--text-secondary); margin: 0.5rem 0;">{desc}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                f"Apply {title} Style",
                use_container_width=True,
                key=style_name.lower(),
            ):
                enhance_image(style_name)

    # Image Comparison
    st.markdown("---")
    st.markdown("### 🖼️ Image Comparison")

    col_img1, col_img2 = st.columns(2)

    with col_img1:
        st.markdown("#### 📷 Original Image")
        if st.session_state.product_image:
            st.image(st.session_state.product_image, use_container_width=True)
        else:
            st.info("No image uploaded")

    with col_img2:
        st.markdown("#### ✨ Enhanced Image")
        if st.session_state.enhanced_image:
            st.image(st.session_state.enhanced_image, use_container_width=True)

            # Download and Continue
            st.markdown("---")
            buffered = BytesIO()
            st.session_state.enhanced_image.save(buffered, format="PNG")

            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button(
                    label="⬇️ Download Enhanced",
                    data=buffered.getvalue(),
                    file_name=f"enhanced_{st.session_state.artisan_data['craft_type'].replace(' ', '_')}.png",
                    mime="image/png",
                    use_container_width=True,
                )
            with col_d2:
                if st.button(
                    "📤 Continue to Export →",
                    type="primary",
                    use_container_width=True,
                ):
                    change_page("Export", 4)
                    st.rerun()
        else:
            st.info("👆 Select a style above to enhance your image")


def render_export_page():
    """Render the final export page"""

    # Success Message
    st.markdown(
        """
        <div class="success-message">
            <h2 style="margin: 0;">🎉 Congratulations!</h2>
            <p style="font-size: 1.1rem; margin-top: 0.5rem;">Your Marketing Pack is Ready for Export</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Package Overview
    st.markdown("### 📦 Your Complete Marketing Package")

    col1, col2 = st.columns([1, 1])

    with col1:
        # Package Contents
        st.markdown(
            """
            <div class="feature-card neon">
                <h4 style="margin-top: 0;">✅ Package Includes:</h4>
                <ul style="list-style: none; padding-left: 0;">
                    <li>✨ AI-Enhanced product image</li>
                    <li>📝 Professional product description</li>
                    <li>💬 Ready-to-use social media captions</li>
                    <li>🏷️ Trending hashtags for visibility</li>
                    <li>📊 Complete product details</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Quick Stats
        if st.session_state.generated_content:
            content = st.session_state.generated_content
            st.markdown(
                f"""
                <div class="feature-card">
                    <h4 style="margin-top: 0;">📊 Content Stats</h4>
                    <p><strong>Product:</strong> {st.session_state.artisan_data['craft_type']}</p>
                    <p><strong>Captions Generated:</strong> {len(content.get('social_media_captions', []))}</p>
                    <p><strong>Hashtags Created:</strong> {len(content.get('hashtags', []))}</p>
                    <p><strong>Enhancement:</strong> AI-Powered</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col2:
        # Final Image Preview
        if st.session_state.enhanced_image:
            st.markdown("#### 🖼️ Your Enhanced Product Image")
            st.image(st.session_state.enhanced_image, use_container_width=True)

    # Export Section
    st.markdown("---")
    st.markdown("### 📤 Export Your Marketing Pack")

    col_exp1, col_exp2, col_exp3 = st.columns([1, 2, 1])
    with col_exp2:
        st.markdown(
            """
            <div class="feature-card" style="text-align: center; background: var(--bg-tertiary);">
                <h4>📁 Google Drive Export</h4>
                <p>Save your complete marketing package to Google Drive for easy access, sharing, and future use.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "🚀 Export to Google Drive Now",
            type="primary",
            use_container_width=True,
        ):
            export_to_drive()

    # New Project
    st.markdown("---")
    col_new1, col_new2, col_new3 = st.columns([1, 2, 1])
    with col_new2:
        if st.button("🔄 Start New Project", use_container_width=True):
            reset_project_state()
            change_page("Onboarding", 1)
            st.rerun()


# ==================== UTILITY FUNCTIONS ====================
def validate_onboarding_data():
    """Validate onboarding form data"""
    data = st.session_state.artisan_data
    if not data["craft_type"]:
        st.error("❌ Please enter your craft type")
        return False
    if not st.session_state.product_image:
        st.error("❌ Please upload a product image")
        return False
    return True


def save_onboarding_data():
    """Save onboarding data to Firebase"""
    data = st.session_state.artisan_data.copy()
    data["name"] = st.session_state.user_profile["name"]
    data["user_email"] = st.session_state.user_profile["email"]

    buffered = BytesIO()
    st.session_state.product_image.save(buffered, format="JPEG")
    image_url = upload_image_to_storage(
        buffered.getvalue(), st.session_state.uploaded_file_name
    )
    data["product_image_url"] = image_url

    save_artisan_data(data)


def enhance_image(style):
    """Enhance image with selected style"""
    with st.spinner(f"🎨 Applying {style} style with AI magic..."):
        progress_bar = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i + 1)

        # ✅ Convert the PIL image to bytes before passing to the cached function
        buffered = BytesIO()
        st.session_state.product_image.save(buffered, format="PNG")
        image_bytes = buffered.getvalue()

        st.session_state.enhanced_image = generate_enhanced_image(image_bytes, style)
        if st.session_state.enhanced_image:
            st.success(f"✨ {style} style applied successfully!")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("❌ Failed to enhance image. Please try again.")


def export_to_drive():
    """Export marketing pack to Google Drive"""
    if not st.session_state.enhanced_image or not st.session_state.generated_content:
        st.error("❌ Please complete all steps before exporting")
        return

    with st.spinner("☁️ Uploading to Google Drive..."):
        progress_bar = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i + 1)

        service = get_gdrive_service_from_session()
        content = st.session_state.generated_content

        export_text = f"""
# KalaKarigar.ai Marketing Pack
Generated for: {st.session_state.user_profile['name']}
Product: {st.session_state.artisan_data['craft_type']}
Date: {time.strftime('%Y-%m-%d %H:%M')}

---

## Enhanced Product Description
{content.get('product_description', 'N/A')}

## Social Media Captions
### Caption 1:
{content.get('social_media_captions', ['N/A'])[0]}

### Caption 2:
{content.get('social_media_captions', ['N/A', 'N/A'])[1] if len(content.get('social_media_captions', [])) > 1 else 'N/A'}

## Hashtags
{' '.join('#' + tag for tag in content.get('hashtags', []))}

## Product Details
- Materials: {st.session_state.artisan_data.get('materials', 'N/A')}
- Dimensions: {st.session_state.artisan_data.get('dimensions', 'N/A')}
- Tags: {', '.join(st.session_state.artisan_data.get('tags', []))}
"""

        folder_name = f"KalaKarigar_{st.session_state.artisan_data['craft_type']}_{time.strftime('%Y%m%d_%H%M%S')}"

        folder_link = export_marketing_pack(
            service, st.session_state.enhanced_image, export_text, folder_name
        )

        # ✅ Check if the folder_link is valid before showing success
        if folder_link:
            st.balloons()
            st.success("🎉 Successfully exported to Google Drive!")
            st.markdown(
                f"""
                <div class="success-message">
                    <p style="margin: 0;">Your marketing pack has been saved!</p>
                    <a href="{folder_link}" target="_blank" style="color: white; text-decoration: underline;">
                        📁 Open in Google Drive
                    </a>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            # This 'else' block is optional but good practice
            st.error("❌ Export failed. Please check the logs or try again.")


def reset_project_state():
    """Reset project-specific state for new project"""
    st.session_state.artisan_data = {
        "craft_type": "",
        "description": "",
        "materials": "",
        "dimensions": "",
        "tags": [],
    }
    st.session_state.product_image = None
    st.session_state.uploaded_file_name = ""
    st.session_state.generated_content = None
    st.session_state.enhanced_image = None
    st.session_state.transcribed_text = None
    st.session_state.suggested_tags = None
    st.session_state.current_step = 1
    st.session_state.steps_completed = []


# ==================== MAIN APPLICATION ====================
def main():
    """Main application entry point"""
    load_custom_css()
    SessionState.init()

    # First, try to restore session from URL
    session_restored = restore_credentials_from_url()

    if not initialize_services():
        st.stop()

    flow = get_gdrive_flow()
    auth_code = st.query_params.get("code")

    # Handle OAuth callback
    if auth_code and not st.session_state.gdrive_credentials:
        try:
            with st.spinner("🔐 Authenticating..."):
                flow.fetch_token(code=auth_code)
                creds = flow.credentials
                st.session_state.gdrive_credentials = {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": creds.scopes,
                }
                # Get user profile
                st.session_state.user_profile = get_user_info()

                # Save to URL for persistence
                save_credentials_to_url()

                # Clear the auth code but keep session
                st.query_params.pop("code", None)
                st.rerun()
        except Exception as e:
            st.error(f"Authentication failed: {e}")
            st.stop()

    # Show appropriate interface
    if not st.session_state.gdrive_credentials:
        render_login_page(flow)
    else:
        # Ensure user profile is loaded
        if not st.session_state.user_profile:
            with st.spinner("Loading your profile..."):
                st.session_state.user_profile = get_user_info()
                save_credentials_to_url()  # Update URL with profile
                st.rerun()

        render_main_app()


def render_login_page(flow):
    """Render the login page"""
    load_custom_css()

    render_logo()

    st.markdown(
        """
        <div style="max-width: 600px; margin: 2rem auto; text-align: center;">
            <h3 style="color: var(--text-primary); margin-bottom: 2rem;">
                Empower Your Craft with AI
            </h3>
            <div class="feature-card neon" style="text-align: left; margin: 2rem 0;">
                <h4>Welcome, Artisan! 👋</h4>
                <p>Transform your handmade products into professional marketing materials:</p>
                <ul style="text-align: left; margin-top: 1rem;">
                    <li>📸 AI-enhanced product photography</li>
                    <li>✏️ Professional product descriptions</li>
                    <li>📱 Social media ready content</li>
                    <li>🏷️ Smart hashtag generation</li>
                    <li>☁️ Google Drive integration</li>
                </ul>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if flow:
            auth_url, _ = flow.authorization_url(prompt="consent")
            if st.button(
                "🔐 Login with Google",
                type="primary",
                use_container_width=True,
                key="google_login_btn",
            ):
                st.markdown(
                    f'<meta http-equiv="refresh" content="0; url={auth_url}">',
                    unsafe_allow_html=True,
                )
                st.rerun()


def render_main_app():
    """Render the main application interface"""
    # Check if we need to scroll to top after page change
    if st.session_state.get("should_scroll_to_top", False):
        scroll_to_top()
        st.session_state.should_scroll_to_top = False

    render_header()
    render_progress_indicator()

    # Enhanced Sidebar Navigation
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; padding: 1rem; background: var(--bg-gradient); 
                        border-radius: 10px; margin-bottom: 1rem;">
                <h3 style="color: white; margin: 0;">🧭 Navigation</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        nav_buttons = [
            ("📋 Step 1: Details", "Onboarding", 1, True),
            (
                "✏️ Step 2: Content",
                "Content",
                2,
                st.session_state.product_image is not None,
            ),
            (
                "🎨 Step 3: Enhance",
                "Image",
                3,
                st.session_state.generated_content is not None,
            ),
            (
                "📤 Step 4: Export",
                "Export",
                4,
                st.session_state.enhanced_image is not None,
            ),
        ]

        for label, page, step, enabled in nav_buttons:
            # Determine button state and styling
            is_current = st.session_state.page == page
            is_completed = step in st.session_state.steps_completed

            # Custom styling based on state
            if is_current:
                # Current step - highlighted
                st.markdown(
                    f"""
                <style>
                .stButton > button[key="nav_{page}_{step}"] {{
                    background: var(--primary) !important;
                    color: white !important;
                    border: 2px solid var(--primary-light) !important;
                    box-shadow: var(--neon-glow) !important;
                    transform: translateX(5px) !important;
                }}
                </style>
                """,
                    unsafe_allow_html=True,
                )
            elif is_completed:
                # Completed step - success styling
                st.markdown(
                    f"""
                <style>
                .stButton > button[key="nav_{page}_{step}"] {{
                    background: var(--success) !important;
                    color: white !important;
                    border: 1px solid var(--success-dark) !important;
                }}
                </style>
                """,
                    unsafe_allow_html=True,
                )

            # Add completion indicator to label
            if is_completed and not is_current:
                label = f"✅ {label}"
            elif is_current:
                label = f"▶️ {label}"

            button_type = "primary" if is_current else "secondary"

            if st.button(
                label,
                use_container_width=True,
                disabled=not enabled,
                type=button_type,
                key=f"nav_{page}_{step}",
            ):
                change_page(page, step)
                time.sleep(0.05)
                st.rerun()

    # Page Content Rendering
    if st.session_state.page == "Onboarding":
        render_onboarding_page()
    elif st.session_state.page == "Content":
        render_content_page()
    elif st.session_state.page == "Image":
        render_image_page()
    elif st.session_state.page == "Export":
        render_export_page()

    # Add the scroll to top button at the end of the main app
    render_scroll_to_top_button()


# ==================== RUN APPLICATION ====================
if __name__ == "__main__":
    main()
