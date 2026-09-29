import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

# --- CORRECT URLS AS PER YOUR ROUTER ---
LIST_URL = f"{API_URL}/notes/read_notes"
CREATE_URL = f"{API_URL}/notes/create"
READ_ONE_URL = f"{API_URL}/notes/read_note"
UPDATE_URL = f"{API_URL}/notes/update_note"
DELETE_URL = f"{API_URL}/notes/delete_note"
SEARCH_URL = f"{API_URL}/search/"

st.set_page_config(page_title="Semantic Notes", page_icon="🧠", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');

html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif; }

/* Background */
.stApp {
    background:
        radial-gradient(circle at 15% 10%, rgba(102,126,234,0.14) 0%, transparent 40%),
        radial-gradient(circle at 85% 20%, rgba(118,75,162,0.12) 0%, transparent 40%),
        #f7f7fd;
}
.block-container { padding-top: 2rem; max-width: 1200px; }

/* Title */
.gradient-text {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 60%, #f093fb 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 44px;
    letter-spacing: -1px;
    margin-bottom: 8px;
}

/* Note cards */
.note-card {
    background: rgba(255,255,255,0.85);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    padding: 22px 24px;
    border: 1px solid rgba(102,126,234,0.15);
    box-shadow: 0 4px 24px rgba(102,126,234,0.08);
    margin-bottom: 10px;
    transition: transform .2s ease, box-shadow .2s ease;
}
.note-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(102,126,234,0.18);
}
.note-card h4 { margin: 0 0 8px 0; color: #2d2d4a; font-weight: 700; }
.note-card p  { line-height: 1.6; margin: 0 0 10px 0; }
.note-card small { color: #9a9ab5; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #f0f0ff 100%);
    border-right: 1px solid #eef0ff;
}

/* Buttons */
.stButton > button, .stFormSubmitButton > button {
    border-radius: 12px;
    border: 1px solid #e3e6ff;
    font-weight: 600;
    transition: all .2s ease;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    border-color: #667eea;
    color: #667eea;
    transform: translateY(-1px);
}
.stFormSubmitButton > button[kind="primary"], .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border: none;
    box-shadow: 0 6px 18px rgba(102,126,234,0.35);
}

/* Inputs */
.stTextInput input, .stTextArea textarea {
    border-radius: 12px !important;
    border: 1px solid #e3e6ff !important;
    background: white !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #667eea !important;
    box-shadow: 0 0 0 3px rgba(102,126,234,0.15) !important;
}

/* Metric */
[data-testid="stMetric"] {
    background: white;
    border-radius: 16px;
    padding: 14px 20px;
    border: 1px solid #eef0ff;
    box-shadow: 0 4px 16px rgba(102,126,234,0.06);
    width: fit-content;
}
</style>
""", unsafe_allow_html=True)
def get_notes():
    try:
        r = requests.get(LIST_URL)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        st.error(f"Backend error: {e}")
    return []

def create_note_api(title, content):
    return requests.post(CREATE_URL, json={"title": title, "content": content})

def update_note_api(note_id, title, content):
    return requests.patch(f"{UPDATE_URL}/{note_id}", json={"title": title, "content": content})

def delete_note_api(note_id):
    return requests.delete(f"{DELETE_URL}/{note_id}")

def search_api(query, limit=5):
    return requests.get(SEARCH_URL, params={"query": query, "limit": limit}).json()

# --- Sidebar ---
with st.sidebar:
    st.markdown("## 🧠 Semantic Notes")
    page = st.radio("Go to", ["🏠 All Notes", "✨ Create Note", "🔍 Semantic Search"])

st.markdown('<div class="gradient-text">Semantic Notes</div>', unsafe_allow_html=True)

if page == "🏠 All Notes":
    notes = get_notes()
    st.metric("Total Notes", len(notes))
    st.divider()
    if not notes:
        st.info("No notes found. Create some or run scripts/seed.py")
    else:
        cols = st.columns(2)
        for i, note in enumerate(notes):
            with cols[i % 2]:
                st.markdown(f"<div class='note-card'><h4>{note['title']}</h4><p style='color:#666'>{note['content'][:180]}...</p><small>{note['created_at'][:10]}</small></div>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("✏️ Edit", key=f"e_{note['id']}", use_container_width=True):
                    st.session_state.edit = note
                if c2.button("🗑️ Delete", key=f"d_{note['id']}", use_container_width=True):
                    delete_note_api(note['id'])
                    st.rerun()
    
    if "edit" in st.session_state:
        n = st.session_state.edit
        st.divider()
        st.subheader(f"Editing {n['title']}")
        with st.form("edit_form"):
            nt = st.text_input("Title", value=n['title'])
            nc = st.text_area("Content", value=n['content'], height=150)
            if st.form_submit_button("Save", type="primary"):
                res = update_note_api(n['id'], nt, nc)
                if res.status_code == 200:
                    del st.session_state.edit
                    st.success("Updated with new embedding!")
                    st.rerun()
                else:
                    st.error(res.text)

elif page == "✨ Create Note":
    with st.form("create"):
        title = st.text_input("Title")
        content = st.text_area("Content", height=200)
        if st.form_submit_button("Create & Embed", type="primary", use_container_width=True):
            with st.spinner("Embedding..."):
                r = create_note_api(title, content)
            if r.status_code == 201:
                st.success("Created!")
                st.balloons()
            else:
                st.error(r.text)

elif page == "🔍 Semantic Search":
    q = st.text_input("Search by meaning", placeholder="e.g. travel documents, spicy dumplings, vector index")
    limit = st.slider("Results", 1, 20, 5)
    if q:
        with st.spinner("Searching..."):
            try:
                results = search_api(q, limit)
                for r in results:
                    dist = r.get('score', 0)
                    sim = max(0, (1-dist)*100)
                    st.markdown(f"<div class='note-card' style='border-left:4px solid #667eea'><b>{r['title']}</b> <span style='float:right; background:#eef0ff; padding:2px 10px; border-radius:20px; color:#667eea'>{sim:.1f}%</span><p style='color:#555'>{r['content'][:250]}...</p><small>distance: {dist:.4f}</small></div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Search failed: {e}")