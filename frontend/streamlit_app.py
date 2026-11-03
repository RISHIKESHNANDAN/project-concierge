"""Run: streamlit run frontend/streamlit_app.py"""
import httpx
import streamlit as st

st.title("ShopEase Support (Project Concierge, synthetic demo)")
email = st.sidebar.selectbox("Signed in as", ["alice@example.com", "bob@example.com", "mallory@example.com"])
if "chat" not in st.session_state:
    st.session_state.chat = []
for role, text in st.session_state.chat:
    st.chat_message(role).write(text)
if q := st.chat_input("Ask about orders, returns, shipping, accounts..."):
    st.session_state.chat.append(("user", q))
    st.chat_message("user").write(q)
    try:
        r = httpx.post("http://localhost:8000/chat", json={"message": q, "customer_email": email}, timeout=60).json()
        cites = ", ".join(f"{c['title']} ({c['section']})" if c.get("section") else c["title"] for c in r["citations"])
        text = r["answer"] + (f"\n\n*Sources: {cites}*" if cites else "") + f"\n\n`{r['outcome']} | {r['latency_s']}s`"
    except Exception as e:
        text = f"Backend error: {e}"
    st.session_state.chat.append(("assistant", text))
    st.chat_message("assistant").write(text)
