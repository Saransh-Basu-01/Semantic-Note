import streamlit as st
import requests
from datetime import datetime
import os

# --- Config ---
API_URL = os.getenv("API_URL", "http://localhost:8000")
NOTES_URL = f"{API_URL}/semantic/notes"
CREATE_URL = f"{API_URL}/semantic/create"
SEARCH_URL = f"{API_URL}/search/"

st.set_page_config(
    page_title="Semantic Notes",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Aesthetic CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
.stApp { font-family: 'Inter', sans-serif; background: #f8f8ff; }
.gradient-text {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800; font-size: 42px;
}
.note-card {
    background: white; border-radius: 20px; padding: 22px;
    box-shadow: 0 4px 24px rgba(102, 126, 234, 0.08);
    border: 1px solid #eef0ff; transition: 0.3s;
    height: 100%;
}
.note-card:hover { transform: translateY(-5px); box-shadow: 0 12px 32px rgba(102, 126, 234, 0.15); }
.search-card {
    background: white; border-radius: 16px; padding: 20px;
    border-left: 4px solid #667eea; margin-bottom: 12px;
}
.stButton>button { border-radius: 12px; font-weight: 600; }
div[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #eef0ff; }
</style>
""", unsafe_allow_html=True)

# --- API Helpers ---
def get_notes():
    try:
        r = requests.get(NOTES_URL)
        if r.status_code == 200:
            return r.json()
    except: pass
    return []

def create_note_api(title, content):
    r = requests.post(CREATE_URL, json={"title": title, "content": content})
    return r

def update_note_api(note_id, title, content):
    r = requests.patch(f"{NOTES_URL}/{note_id}", json={"title": title, "content": content})
    return r

def delete_note_api(note_id):
    r = requests.delete(f"{NOTES_URL}/{note_id}")
    return r

def search_api(query, limit=5):
    try:
        r = requests.get(SEARCH_URL, params={"query": query, "limit": limit})
        if r.status_code == 200:
            return r.json()
    except: pass
    return []

# --- Sidebar ---
with st.sidebar:
    st.markdown("## 🧠 Semantic Notes")
    st.caption("Powered by pgvector + FastAPI")
    st.divider()
    page = st.radio("Navigation", ["🏠 All Notes", "✨ Create Note", "🔍 Semantic Search"], label_visibility="collapsed")
    st.divider()
    st.markdown("**Backend:**")
    st.code(f"{API_URL}", language="text")
    if st.button("🔄 Refresh"):
        st.rerun()

# --- Header ---
st.markdown('<div class="gradient-text">Semantic Notes</div>', unsafe_allow_html=True)
st.caption("Aesthetic note-taking with AI-powered semantic search")

# --- Page: All Notes ---
if page == "🏠 All Notes":
    notes = get_notes()
    col1, col2, col3 = st.columns([2,1,1])
    col1.metric("Total Notes", len(notes))
    col2.metric("Embedding Dim", "384")
    col3.metric("Model", "MiniLM-L6-v2")

    st.divider()
    
    if not notes:
        st.info("No notes yet. Create your first note!")
    else:
        # Grid of cards
        cols = st.columns(2)
        for idx, note in enumerate(notes):
            with cols[idx % 2]:
                with st.container():
                    st.markdown(f"""
                    <div class="note-card">
                        <h4 style="margin:0 0 8px 0;">{note['title']}</h4>
                        <p style="color:#666; font-size:14px; min-height:60px;">{note['content'][:180]}...</p>
                        <small style="color:#999;">{note['created_at'][:10]}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    c1, c2, c3 = st.columns([1,1,1])
                    with c1:
                        if st.button("👁️ View", key=f"view_{note['id']}", use_container_width=True):
                            st.session_state.view_note = note
                    with c2:
                        if st.button("✏️ Edit", key=f"edit_{note['id']}", use_container_width=True):
                            st.session_state.edit_note = note
                    with c3:
                        if st.button("🗑️", key=f"del_{note['id']}", use_container_width=True):
                            delete_note_api(note['id'])
                            st.toast("Deleted!")
                            st.rerun()
                st.write("")

    # View Modal
    if "view_note" in st.session_state:
        note = st.session_state.view_note
        with st.expander(f"📖 {note['title']}", expanded=True):
            st.write(note['content'])
            st.caption(f"ID: {note['id']} | Created: {note['created_at']}")
            if st.button("Close"):
                del st.session_state.view_note
                st.rerun()

    # Edit Modal
    if "edit_note" in st.session_state:
        note = st.session_state.edit_note
        st.divider()
        st.subheader(f"✏️ Edit: {note['title']}")
        with st.form("edit_form"):
            new_title = st.text_input("Title", value=note['title'])
            new_content = st.text_area("Content", value=note['content'], height=150)
            save = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")
            if save:
                res = update_note_api(note['id'], new_title, new_content)
                if res.status_code == 200:
                    st.success("Updated with new embedding!")
                    del st.session_state.edit_note
                    st.rerun()
                else:
                    st.error(f"Failed: {res.text}")

# --- Page: Create Note ---
elif page == "✨ Create Note":
    st.subheader("Create a new semantic note")
    st.caption("Title + content will be converted to a 384-dim vector automatically.")
    with st.form("create_form", clear_on_submit=True):
        title = st.text_input("Title", placeholder="e.g. How to renew passport in Nepal")
        content = st.text_area("Content", placeholder="Write detailed content... This is what gets embedded for search.", height=200)
        submitted = st.form_submit_button("🚀 Create Note & Embed", use_container_width=True, type="primary")
        if submitted:
            if not title or not content:
                st.warning("Both fields required")
            else:
                with st.spinner("Generating embedding with MiniLM..."):
                    res = create_note_api(title, content)
                if res.status_code == 201:
                    st.success("Note created! Embedding stored in pgvector.")
                    st.balloons()
                else:
                    st.error(f"Error: {res.text}")

# --- Page: Semantic Search ---
elif page == "🔍 Semantic Search":
    st.subheader("Semantic Search")
    st.caption("Search by meaning, not keywords. Try 'travel documents' -> will find passport note.")

    q = st.text_input("Search query", placeholder="e.g. spicy dumplings, vector database, travel tips...")
    limit = st.slider("Results", 1, 20, 5)
    
    if q:
        with st.spinner("Embedding query & searching with cosine distance..."):
            results = search_api(q, limit)
        
        if not results:
            st.warning("No results. Try seeding DB first with scripts/seed.py")
        else:
            st.write(f"Found {len(results)} results for **'{q}'**")
            for r in results:
                # score is cosine distance - lower is better. Convert to similarity %
                dist = r.get('score', 0)
                similarity = max(0, (1 - dist) * 100)
                st.markdown(f"""
                <div class="search-card">
                    <div style="display:flex; justify-content:space-between;">
                        <h4 style="margin:0;">{r['title']}</h4>
                        <span style="background:#eef0ff; padding:4px 10px; border-radius:20px; font-size:12px; color:#667eea;">{similarity:.1f}% match</span>
                    </div>
                    <p style="color:#555; margin:10px 0;">{r['content'][:250]}...</p>
                    <small style="color:#999;">distance: {dist:.4f}</small>
                </div>
                """, unsafe_allow_html=True)