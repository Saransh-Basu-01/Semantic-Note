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
.stApp { background: #f8f8ff; }
.note-card { background: white; border-radius: 20px; padding: 22px; box-shadow: 0 4px 24px rgba(102,126,234,0.08); border: 1px solid #eef0ff; margin-bottom: 16px; }
.gradient-text { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; font-size: 40px; }
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