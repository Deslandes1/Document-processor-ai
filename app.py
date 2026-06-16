import streamlit as st
import supabase
import stripe
import PyPDF2
import docx
import tempfile
import os
from datetime import datetime
from gtts import gTTS
import google.generativeai as genai

# ========== PAGE CONFIG (MUST BE FIRST) ==========
st.set_page_config(
    page_title="Document Processor AI | GlobalInternet.py",
    page_icon="📄",
    layout="wide"
)

# ========== DIAGNOSTIC – REMOVE AFTER TESTING ==========
key = st.secrets.get("ANTHROPIC_API_KEY", "")
st.write("Gemini key exists:", bool(key))
st.write("Key prefix (first 15 chars):", key[:15] if key else "None")
st.markdown("---")

# ========== LIGHT BLUE THEME CSS ==========
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #e0f0ff 0%, #b8d9ff 100%);
        color: #1a2a3a;
    }
    [data-testid="stSidebar"] {
        background-color: #cce4ff !important;
    }
    .stButton>button {
        background-color: #2c7be5;
        color: white;
        border-radius: 30px;
        font-weight: bold;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #1a5bbf;
    }
    .big-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1e3c72;
        margin: 0;
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

# ========== LANGUAGE DICTIONARIES ==========
TEXTS = {
    "English": {
        "welcome": "🔐 Welcome to Document Processor AI",
        "sign_in_prompt": "Sign in or create an account to start processing your documents.",
        "email": "Email",
        "password": "Password",
        "action": "Action",
        "login": "Login",
        "sign_up": "Sign Up",
        "continue_btn": "Continue",
        "logout": "🚪 Logout",
        "premium_btn": "💎 Premium Features (Stripe)",
        "instructions_title": "📌 Instructions",
        "step1": "1. Upload a document (PDF, DOCX, TXT)",
        "step2": "2. Choose an operation (Summarize, Extract, QA)",
        "step3": "3. View AI results and save them to the cloud.",
        "step4": "4. Upgrade to premium for advanced features (coming soon).",
        "main_title": "📄 AI Document Processor",
        "main_subtitle": "Upload your document, let AI process it, and store the results securely.",
        "upload_label": "Choose a document",
        "operation_label": "What would you like to do?",
        "summarize": "Summarize",
        "extract": "Extract Key Information",
        "answer": "Answer a Question",
        "question_label": "Your question about the document:",
        "process_btn": "Process Document",
        "extracting": "Extracting text...",
        "sending_ai": "Sending to Google Gemini AI...",
        "success": "Processing complete!",
        "preview_title": "Document Preview",
        "ai_result_title": "AI Result",
        "save_success": "Document saved to cloud (Supabase).",
        "save_error": "Failed to save to Supabase. Check your credentials.",
        "view_docs_btn": "📂 View My Processed Documents",
        "no_docs": "No documents found.",
        "footer": "© 2026 Document Processor AI – Built with Streamlit, Google Gemini, Supabase, and Stripe",
        "explain_btn": "🎙️ AI Voice Explanation (Female)",
        "explain_text": "Hello, I am the AI assistant of Document Processor AI. This software allows you to upload documents (PDF, DOCX, TXT), then uses Google Gemini AI to summarize, extract key information, or answer questions based on the content. Results are stored in Supabase cloud database. You can also upgrade to premium features using Stripe. This tool was built by Gesner Deslandes, Engineer‑in‑Chief at GlobalInternet.py. Enjoy!"
    },
    "French": {
        "welcome": "🔐 Bienvenue dans Document Processor AI",
        "sign_in_prompt": "Connectez-vous ou créez un compte pour traiter vos documents.",
        "email": "Email",
        "password": "Mot de passe",
        "action": "Action",
        "login": "Connexion",
        "sign_up": "Inscription",
        "continue_btn": "Continuer",
        "logout": "🚪 Déconnexion",
        "premium_btn": "💎 Fonctionnalités Premium (Stripe)",
        "instructions_title": "📌 Instructions",
        "step1": "1. Téléchargez un document (PDF, DOCX, TXT)",
        "step2": "2. Choisissez une opération (Résumer, Extraire, Q/R)",
        "step3": "3. Visualisez les résultats IA et enregistrez-les dans le cloud.",
        "step4": "4. Passez à la version premium pour plus de fonctionnalités (bientôt).",
        "main_title": "📄 Processeur de documents IA",
        "main_subtitle": "Téléchargez votre document, laissez l'IA le traiter et stockez les résultats en toute sécurité.",
        "upload_label": "Choisissez un document",
        "operation_label": "Que souhaitez-vous faire ?",
        "summarize": "Résumer",
        "extract": "Extraire les informations clés",
        "answer": "Répondre à une question",
        "question_label": "Votre question sur le document :",
        "process_btn": "Traiter le document",
        "extracting": "Extraction du texte...",
        "sending_ai": "Envoi à l'IA Google Gemini...",
        "success": "Traitement terminé !",
        "preview_title": "Aperçu du document",
        "ai_result_title": "Résultat IA",
        "save_success": "Document enregistré dans le cloud (Supabase).",
        "save_error": "Échec de l'enregistrement dans Supabase. Vérifiez vos identifiants.",
        "view_docs_btn": "📂 Voir mes documents traités",
        "no_docs": "Aucun document trouvé.",
        "footer": "© 2026 Document Processor AI – Construit avec Streamlit, Google Gemini, Supabase et Stripe",
        "explain_btn": "🎙️ Explication vocale IA (femme)",
        "explain_text": "Bonjour, je suis l'assistant IA de Document Processor AI. Ce logiciel vous permet de télécharger des documents (PDF, DOCX, TXT), puis utilise l'IA Google Gemini pour résumer, extraire des informations clés ou répondre à des questions basées sur le contenu. Les résultats sont stockés dans la base de données cloud Supabase. Vous pouvez également passer à la version premium avec Stripe. Cet outil a été créé par Gesner Deslandes, ingénieur en chef chez GlobalInternet.py. Profitez-en !"
    },
    "Spanish": {
        "welcome": "🔐 Bienvenido a Document Processor AI",
        "sign_in_prompt": "Inicie sesión o cree una cuenta para procesar sus documentos.",
        "email": "Correo electrónico",
        "password": "Contraseña",
        "action": "Acción",
        "login": "Iniciar sesión",
        "sign_up": "Registrarse",
        "continue_btn": "Continuar",
        "logout": "🚪 Cerrar sesión",
        "premium_btn": "💎 Funcionalidades Premium (Stripe)",
        "instructions_title": "📌 Instrucciones",
        "step1": "1. Suba un documento (PDF, DOCX, TXT)",
        "step2": "2. Elija una operación (Resumir, Extraer, Preguntas)",
        "step3": "3. Vea los resultados de IA y guárdelos en la nube.",
        "step4": "4. Actualice a premium para funciones avanzadas (próximamente).",
        "main_title": "📄 Procesador de documentos IA",
        "main_subtitle": "Suba su documento, deje que la IA lo procese y almacene los resultados de forma segura.",
        "upload_label": "Elija un documento",
        "operation_label": "¿Qué desea hacer?",
        "summarize": "Resumir",
        "extract": "Extraer información clave",
        "answer": "Responder una pregunta",
        "question_label": "Su pregunta sobre el documento:",
        "process_btn": "Procesar documento",
        "extracting": "Extrayendo texto...",
        "sending_ai": "Enviando a IA Google Gemini...",
        "success": "¡Procesamiento completo!",
        "preview_title": "Vista previa del documento",
        "ai_result_title": "Resultado IA",
        "save_success": "Documento guardado en la nube (Supabase).",
        "save_error": "Error al guardar en Supabase. Verifique sus credenciales.",
        "view_docs_btn": "📂 Ver mis documentos procesados",
        "no_docs": "No se encontraron documentos.",
        "footer": "© 2026 Document Processor AI – Construido con Streamlit, Google Gemini, Supabase y Stripe",
        "explain_btn": "🎙️ Explicación por voz IA (mujer)",
        "explain_text": "Hola, soy el asistente IA de Document Processor AI. Este software le permite subir documentos (PDF, DOCX, TXT) y luego usa IA Google Gemini para resumir, extraer información clave o responder preguntas basadas en el contenido. Los resultados se almacenan en la base de datos en la nube Supabase. También puede actualizar a funciones premium usando Stripe. Esta herramienta fue construida por Gesner Deslandes, ingeniero jefe de GlobalInternet.py. ¡Disfrútela!"
    }
}

# ========== VOICE GENERATION WITH gTTS ==========
def generate_audio(text, lang):
    lang_map = {
        "English": "en",
        "French": "fr",
        "Spanish": "es"
    }
    lang_code = lang_map.get(lang, "en")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp_path = tmp.name
    tts = gTTS(text=text, lang=lang_code, slow=False)
    tts.save(tmp_path)
    with open(tmp_path, "rb") as f:
        audio_bytes = f.read()
    os.unlink(tmp_path)
    return audio_bytes

# ========== CONFIGURATION (from secrets) ==========
GEMINI_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")  # reuse the same secret name
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "your-anon-key")
STRIPE_SECRET_KEY = st.secrets.get("STRIPE_SECRET_KEY", "sk_test_...")
STRIPE_PUBLISHABLE_KEY = st.secrets.get("STRIPE_PUBLISHABLE_KEY", "pk_test_...")

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Initialize Supabase and Stripe if configured
if SUPABASE_URL != "https://your-project.supabase.co":
    supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase_client = None
if STRIPE_SECRET_KEY != "sk_test_...":
    stripe.api_key = STRIPE_SECRET_KEY

# ========== SESSION STATE ==========
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "processed_docs" not in st.session_state:
    st.session_state.processed_docs = []
if "payment_success" not in st.session_state:
    st.session_state.payment_success = False
if "lang" not in st.session_state:
    st.session_state.lang = "English"

# ========== HELPER FUNCTIONS ==========
def extract_text_from_file(uploaded_file):
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

def process_with_gemini(text: str, operation: str, question: str = None) -> str:
    """Process document using Google Gemini API."""
    if not GEMINI_API_KEY:
        return f"[Mock AI – Valid Gemini API key not found]\n\nYour document starts with: {text[:400]}...\n\nTo enable real AI, add your Gemini API key (from Google AI Studio) to Streamlit secrets."
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')  # free tier model
        if operation == "summarize":
            prompt = f"Please summarize the following document in a few concise paragraphs:\n\n{text}"
        elif operation == "extract":
            prompt = f"Extract the most important information from this document (key facts, dates, names, decisions):\n\n{text}"
        elif operation == "answer_question":
            if not question:
                return "Please enter a question."
            prompt = f"Answer the question based on the document.\n\nDocument:\n{text}\n\nQuestion: {question}"
        else:
            return "Invalid operation selected."
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini API error: {str(e)}"

def save_to_supabase(user_id: str, filename: str, original_text: str, processed_summary: str, extracted_info: str):
    if supabase_client is None:
        st.warning("Supabase not configured. Document not saved.")
        return False
    try:
        data = {
            "user_id": user_id,
            "filename": filename,
            "original_text": original_text[:5000],
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
    if STRIPE_SECRET_KEY == "sk_test_...":
        st.warning("Stripe not configured.")
        return None
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Premium Document Processing"},
                    "unit_amount": 999,
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

# ========== LOGIN UI ==========
def login_ui(texts):
    st.title(texts["welcome"])
    st.markdown(texts["sign_in_prompt"])
    with st.form("auth_form"):
        email = st.text_input(texts["email"])
        password = st.text_input(texts["password"], type="password")
        action = st.selectbox(texts["action"], [texts["login"], texts["sign_up"]])
        submitted = st.form_submit_button(texts["continue_btn"])
        if submitted:
            if action == texts["sign_up"]:
                st.session_state.user_id = email
                st.success("Account created! You are now logged in.")
                st.rerun()
            else:
                st.session_state.user_id = email
                st.success("Logged in successfully!")
                st.rerun()
    st.stop()

# ========== SIDEBAR ==========
lang = st.sidebar.selectbox("🌐 Language", ["English", "French", "Spanish"], index=["English","French","Spanish"].index(st.session_state.lang))
if lang != st.session_state.lang:
    st.session_state.lang = lang
    st.rerun()
texts = TEXTS[st.session_state.lang]

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/null/document.png", width=80)
    if st.session_state.user_id:
        st.markdown(f"**User:** {st.session_state.user_id}")
        if st.button(texts["logout"], use_container_width=True):
            st.session_state.user_id = None
            st.rerun()
        st.markdown("---")
        if st.button(texts["premium_btn"], use_container_width=True):
            url = create_stripe_checkout()
            if url:
                st.markdown(f"[Click to pay $9.99]({url})")
            else:
                st.error("Could not create checkout session.")
    st.markdown("---")
    st.markdown(f"### {texts['instructions_title']}")
    st.markdown(texts["step1"])
    st.markdown(texts["step2"])
    st.markdown(texts["step3"])
    st.markdown(texts["step4"])
    st.markdown("---")
    if st.button(texts["explain_btn"], use_container_width=True):
        with st.spinner("Generating voice explanation..."):
            audio_bytes = generate_audio(texts["explain_text"], st.session_state.lang)
            st.audio(audio_bytes, format="audio/mp3")
            st.success("Explanation played. Click again to repeat.")

# ========== MAIN CONTENT ==========
col_title, col_pic = st.columns([4, 1])
with col_title:
    st.markdown('<div class="big-title">DOCUMENT PROCESSOR AI</div>', unsafe_allow_html=True)
    st.markdown(f"*{texts['main_subtitle']}*")
with col_pic:
    try:
        st.image("https://raw.githubusercontent.com/Deslandes1/Document-processor-ai/main/Gesner%20Deslandes.png", width=100)
        st.caption("Gesner Deslandes")
    except:
        pass
st.markdown("---")

if st.session_state.user_id is None:
    login_ui(texts)

st.markdown(f"## {texts['main_title']}")
st.markdown(texts["main_subtitle"])

uploaded_file = st.file_uploader(texts["upload_label"], type=["pdf", "docx", "txt"])
operation = st.selectbox(texts["operation_label"], [texts["summarize"], texts["extract"], texts["answer"]])
question = None
if operation == texts["answer"]:
    question = st.text_input(texts["question_label"])

if uploaded_file is not None and st.button(texts["process_btn"], type="primary"):
    with st.spinner(texts["extracting"]):
        text = extract_text_from_file(uploaded_file)
        if not text:
            st.error("Could not extract text from the file.")
        else:
            with st.spinner(texts["sending_ai"]):
                if operation == texts["summarize"]:
                    result = process_with_gemini(text, "summarize")
                    summary = result
                    extracted_info = ""
                elif operation == texts["extract"]:
                    result = process_with_gemini(text, "extract")
                    summary = ""
                    extracted_info = result
                else:
                    if not question:
                        st.warning("Please enter a question.")
                        st.stop()
                    result = process_with_gemini(text, "answer_question", question=question)
                    summary = ""
                    extracted_info = result
                st.success(texts["success"])
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader(texts["preview_title"])
                    st.text_area("", text[:1000], height=200)
                with col2:
                    st.subheader(texts["ai_result_title"])
                    st.markdown(result)
                if save_to_supabase(st.session_state.user_id, uploaded_file.name, text[:5000], summary, extracted_info):
                    st.success(texts["save_success"])
                else:
                    st.error(texts["save_error"])

if st.button(texts["view_docs_btn"]):
    if supabase_client is None:
        st.info("Supabase not configured. Cannot fetch documents.")
    else:
        try:
            response = supabase_client.table("documents").select("*").eq("user_id", st.session_state.user_id).order("created_at", desc=True).execute()
            docs = response.data
            if docs:
                for doc in docs[:5]:
                    with st.expander(f"{doc['filename']} - {doc['created_at'][:10]}"):
                        st.write(f"**Summary:** {doc['summary'][:300] if doc['summary'] else 'N/A'}")
                        st.write(f"**Extracted Info:** {doc['extracted_info'][:300] if doc['extracted_info'] else 'N/A'}")
            else:
                st.info(texts["no_docs"])
        except Exception as e:
            st.error(f"Could not fetch documents: {e}")

st.markdown("---")
st.caption(texts["footer"])
