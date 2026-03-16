CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }

    .stApp { background: #f8fafc; }

    .main .block-container {
        background: #ffffff;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    }

    [data-testid="stSidebar"] { background: #f1f5f9; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] label { color: #334155 !important; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #1e293b !important;
        -webkit-text-fill-color: #1e293b !important;
    }

    .stButton>button {
        background: linear-gradient(90deg, #7c3aed 0%, #4f46e5 100%);
        color: white; border: none; border-radius: 8px;
        padding: 0.45rem 1rem; font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton>button:hover { opacity: 0.9; transform: translateY(-1px); }

    .stTabs [data-baseweb="tab-list"] {
        gap: 6px; background: #f1f5f9;
        padding: 0.4rem; border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px; padding: 0.45rem 1.25rem;
        font-weight: 600; color: #64748b;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #7c3aed 0%, #4f46e5 100%);
        color: white !important;
    }

    .flashcard {
        background: linear-gradient(135deg, #faf5ff, #ede9fe);
        border: 1px solid #c4b5fd;
        border-left: 4px solid #7c3aed;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
    }

    h1, h2, h3 { color: #1e293b !important; font-weight: 800; }
    p, span, label { color: #334155; }
    .stMarkdown p { color: #334155; }
</style>
"""
