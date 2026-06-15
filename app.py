import streamlit as st
import anthropic
import supabase
import stripe
import PyPDF2
import docx
import io
import tempfile
import os
from datetime import datetime
from typing import Optional

# ========== CONFIGURATION ==========
# Replace these with your own keys (use Streamlit secrets in production)
ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "your-key-here")
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "your-anon-key")
STRIPE_SECRET_KEY = st.secrets.get("STRIPE_SECRET_KEY", "sk_test_...")
STRIPE_PUBLISHABLE_KEY = st.secrets.get("STRIPE_PUBLISHABLE_KEY", "pk_test_...")

# Initialize clients
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
stripe.api_key = STRIPE_SECRET_KEY

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="Document Processor AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== SESSION STATE ==========
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "processed_docs" not in st.session_state:
    st.session_state.processed_docs = []
if "payment_success" not in st.session_state:
    st.session_state.payment_success = False

# ========== HELPER FUNCTIONS ==========
def extract_text_from_file(uploaded_file):
    """Extract text from PDF, DOCX, or TXT file."""
    file_type = uploaded_file.type
    if file_type == "text/plain":
        return uploaded_file.read().decode("utf-8")
    elif file_type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        return ""

def process_with_anthropic(text: str, operation: str) -> str:
    """Send text to Anthropic Claude for processing."""
    prompts = {
        "summarize": "Please summarize the following document in a few concise paragraphs:\n\n",
        "extract_key_info": "Extract the most important information from this document (key facts, dates, names, decisions):\n\n",
        "answer_question": "Answer the question based on the document.\n\nDocument:\n"
    }
    prompt = prompts.get(operation, "Please process this document:\n\n") + text
    try:
        response = anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"AI error: {str(e)}"

def save_to_supabase(user_id: str, filename: str, original_text: str, processed_summary: str, extracted_info: str):
    """Store document and AI results in Supabase."""
    try:
        data = {
            "user_id": user_id,
            "filename": filename,
            "original_text": original_text[:5000],  # limit to avoid row size issues
            "summary": processed_summary,
            "extracted_info": extracted_info,
            "created_at": datetime.now().isoformat()
        }
        supabase_client.table("documents").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Supabase error: {e}")
        return False

def create_stripe_checkout():
    """Create a Stripe Checkout session for premium features."""
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Premium Document Processing"},
                    "unit_amount": 999,  # $9.99
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=st.secrets.get("APP_URL", "http://localhost:8501") + "?payment=success",
            cancel_url=st.secrets.get("APP_URL", "http://localhost:8501") + "?payment=cancel",
        )
        return session.url
    except Exception as e:
        st.error(f"Stripe error: {e}")
        return None

# ========== LOGIN / SIGNUP (Mock) ==========
def login_ui():
    st.title("🔐 Welcome to Document Processor AI")
    st.markdown("Sign in or create an account to start processing your documents.")
    with st.form("auth_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        action = st.selectbox("Action", ["Login", "Sign Up"])
        submitted = st.form_submit_button("Continue")
        if submitted:
            if action == "Sign Up":
                # In production, you would use Supabase Auth.
                # For demo, we create a mock user ID.
                st.session_state.user_id = email
                st.success("Account created! You are now logged in.")
                st.rerun()
            else:
                # Mock login – accept any email/password
                st.session_state.user_id = email
                st.success("Logged in successfully!")
                st.rerun()
    st.stop()

# ========== MAIN APP ==========
if st.session_state.user_id is None:
    login_ui()

# Sidebar user info
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/null/document.png", width=80)
    st.markdown(f"**User:** {st.session_state.user_id}")
    if st.button("🚪 Logout"):
        st.session_state.user_id = None
        st.rerun()
    st.markdown("---")
    if st.button("💎 Premium Features (Stripe)", use_container_width=True):
        url = create_stripe_checkout()
        if url:
            st.markdown(f"[Click to pay $9.99]({url})")
        else:
            st.error("Could not create checkout session.")
    st.markdown("---")
    st.markdown("### 📌 Instructions")
    st.markdown("1. Upload a document (PDF, DOCX, TXT)")
    st.markdown("2. Choose an operation (Summarize, Extract, QA)")
    st.markdown("3. View AI results and save them to the cloud.")
    st.markdown("4. Upgrade to premium for advanced features (coming soon).")

st.title("📄 AI Document Processor")
st.markdown("Upload your document, let AI process it, and store the results securely.")

# Document upload
uploaded_file = st.file_uploader("Choose a document", type=["pdf", "docx", "txt"])
operation = st.selectbox("What would you like to do?", ["Summarize", "Extract Key Information", "Answer a Question"])
question = None
if operation == "Answer a Question":
    question = st.text_input("Your question about the document:")

if uploaded_file is not None and st.button("Process Document", type="primary"):
    with st.spinner("Extracting text..."):
        text = extract_text_from_file(uploaded_file)
        if not text:
            st.error("Could not extract text from the file.")
        else:
            with st.spinner("Sending to Anthropic AI..."):
                if operation == "Summarize":
                    result = process_with_anthropic(text, "summarize")
                    summary = result
                    extracted_info = ""
                elif operation == "Extract Key Information":
                    result = process_with_anthropic(text, "extract_key_info")
                    summary = ""
                    extracted_info = result
                else:  # Answer question
                    if not question:
                        st.warning("Please enter a question.")
                        st.stop()
                    prompt = f"Answer the question based on the document.\n\nDocument:\n{text}\n\nQuestion: {question}"
                    result = process_with_anthropic(prompt, "answer_question")
                    summary = ""
                    extracted_info = result
                
                # Display results
                st.success("Processing complete!")
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Document Preview")
                    st.text_area("First 1000 characters:", text[:1000], height=200)
                with col2:
                    st.subheader("AI Result")
                    st.markdown(result)
                
                # Save to Supabase
                if save_to_supabase(st.session_state.user_id, uploaded_file.name, text[:5000], summary, extracted_info):
                    st.success("Document saved to cloud (Supabase).")
                else:
                    st.error("Failed to save to Supabase. Check your credentials.")

# Show previously processed documents (optional)
if st.button("📂 View My Processed Documents"):
    try:
        response = supabase_client.table("documents").select("*").eq("user_id", st.session_state.user_id).order("created_at", desc=True).execute()
        docs = response.data
        if docs:
            for doc in docs[:5]:
                with st.expander(f"{doc['filename']} - {doc['created_at'][:10]}"):
                    st.write(f"**Summary:** {doc['summary'][:300] if doc['summary'] else 'N/A'}")
                    st.write(f"**Extracted Info:** {doc['extracted_info'][:300] if doc['extracted_info'] else 'N/A'}")
        else:
            st.info("No documents found.")
    except Exception as e:
        st.error(f"Could not fetch documents: {e}")

st.markdown("---")
st.caption("© 2026 Document Processor AI – Built with Streamlit, Anthropic Claude, Supabase, and Stripe")
