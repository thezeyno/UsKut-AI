# -*- coding: utf-8 -*-
import streamlit as st
import ollama
from pypdf import PdfReader
import subprocess
import pandas as pd
import numpy as np
import sqlite3, uuid, os, datetime, traceback

# ===========================
# LOG DB
# ===========================
LOG_DB_PATH = os.path.join(os.path.dirname(__file__), "uskut_logs.db")

def _now_tr():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def init_log_db():
    conn = sqlite3.connect(LOG_DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        session_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        details TEXT
    )
    """)
    conn.commit()
    conn.close()

def log_event(session_id: str, event_type: str, details: str = ""):
    ts = _now_tr()
    print(f"[{ts}] [{session_id}] {event_type} | {details}", flush=True)
    try:
        conn = sqlite3.connect(LOG_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO events (ts, session_id, event_type, details) VALUES (?, ?, ?, ?)",
            (ts, session_id, event_type, (details or "")[:500])
        )
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}", flush=True)
    finally:
        try:
            conn.close()
        except Exception:
            pass

def format_error(e: Exception) -> str:
    tb = traceback.format_exc().splitlines()
    tb_short = " | ".join(tb[-6:])
    return f"{type(e).__name__}: {str(e)[:180]} | TB: {tb_short[:320]}"

# ===========================
# PAGE
# ===========================
st.set_page_config(page_title="UsKut AI", page_icon="🤖", layout="wide")

# ===========================
# I18N
# ===========================
T = {
    "Türkçe": {
        "welcome": "Merhaba! Ben UsKut. Nasıl yardımcı olayım?",
        "caption": "Kurum içi / Offline Yapay Zeka Asistanı (KVKK odaklı)",
        "settings": "Ayarlar",
        "ui_lang": "Arayüz dili",
        "model": "Model",
        "fast_mode": "Hızlı mod",
        "creativity": "Yaratıcılık (temperature)",
        "tab_chat": "💬 Genel Chat",
        "tab_pdf": "📄 PDF Soru–Cevap",
        "tab_excel": "📊 Excel Görselleştir",
        "tab_code": "🧩 Kod Düzelt",
        "type_msg": "Mesaj yaz...",
        "clear_chat": "🧹 Sohbeti temizle",
        "hint_fast": "İpucu: Hızlı mod açıkken cevaplar daha kısa gelir, gecikme azalır.",
        "upload_pdf": "PDF yükle",
        "pdf_info": "Devam etmek için bir PDF yükle.",
        "pdf_q": "PDF hakkında soru yaz",
        "ask": "Sor",
        "clear_pdf": "🧹 PDF geçmişini temizle",
        "pdf_read_ok": "PDF okundu ✅",
        "code_lang": "Kod dili",
        "code_input": "Hatalı kodu buraya yapıştır",
        "fix_code": "Kodu düzelt",
        "code_out_lang": "Çıktı dili",
        "error_model": "Model çağrılırken hata oluştu",
        "excel_help": "Excel dosyanı yükle → filtrele → tablo ve grafiklerle daha okunabilir hale getir.",
        "excel_upload": "Excel yükle (.xlsx / .xls)",
        "excel_need": "Devam etmek için bir Excel dosyası yükle.",
        "sheet_select": "Sayfa seç",
        "filters": "🔎 Filtreler",
        "filter_cols": "Filtrelemek istediğin sütunlar",
        "table": "### 📋 Filtrelenmiş Tablo",
        "charts": "### 📈 Grafikler",
        "download": "### ⬇️ Filtrelenmiş tabloyu indir",
        "csv_btn": "CSV indir",
    },
    "English": {
        "welcome": "Hello! I am UsKut. How can I help you?",
        "caption": "Internal / Offline AI Assistant (privacy-first)",
        "settings": "Settings",
        "ui_lang": "UI language",
        "model": "Model",
        "fast_mode": "Fast mode",
        "creativity": "Creativity (temperature)",
        "tab_chat": "💬 General Chat",
        "tab_pdf": "📄 PDF Q&A",
        "tab_excel": "📊 Excel Visualization",
        "tab_code": "🧩 Fix Code",
        "type_msg": "Type a message...",
        "clear_chat": "🧹 Clear chat",
        "hint_fast": "Tip: Fast mode gives shorter answers and lower latency.",
        "upload_pdf": "Upload PDF",
        "pdf_info": "Upload a PDF to continue.",
        "pdf_q": "Ask a question about the PDF",
        "ask": "Ask",
        "clear_pdf": "🧹 Clear PDF history",
        "pdf_read_ok": "PDF loaded ✅",
        "code_lang": "Code language",
        "code_input": "Paste the buggy code here",
        "fix_code": "Fix code",
        "code_out_lang": "Output language",
        "error_model": "Error while calling the model",
        "excel_help": "Upload Excel → filter → view table & charts.",
        "excel_upload": "Upload Excel (.xlsx / .xls)",
        "excel_need": "Upload an Excel file to continue.",
        "sheet_select": "Select sheet",
        "filters": "🔎 Filters",
        "filter_cols": "Columns to filter",
        "table": "### 📋 Filtered Table",
        "charts": "### 📈 Charts",
        "download": "### ⬇️ Download filtered table",
        "csv_btn": "Download CSV",
    }
}

# ===========================
# CSS
# ===========================
st.markdown("""
<style>
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1200px; }
[data-testid="stCaptionContainer"] { margin-top: -0.4rem; opacity: 0.85; }
section[data-testid="stSidebar"] .block-container { padding-top: 1.2rem; }
button[data-baseweb="tab"] { font-size: 16px; padding: 10px 14px; }
[data-testid="stChatInput"] textarea { min-height: 52px; }

/* Kart */
.uskut-card {
  background: rgba(15, 23, 42, 0.35);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 16px;
  padding: 16px;
  margin-top: 10px;
}

/* Chat balon */
[data-testid="stChatMessage"] { padding: 6px 0; }
[data-testid="stChatMessage"][data-testid*="assistant"] > div {
  background: rgba(59,130,246,0.10);
  border: 1px solid rgba(59,130,246,0.25);
  border-radius: 16px;
  padding: 12px 14px;
}
[data-testid="stChatMessage"][data-testid*="user"] > div {
  background: rgba(148,163,184,0.10);
  border: 1px solid rgba(148,163,184,0.25);
  border-radius: 16px;
  padding: 12px 14px;
}
</style>
""", unsafe_allow_html=True)

# ===========================
# TÜRK BAYRAĞI VE ATATÜRK İMZASI (CSS TEMA GARANTİLİ)
# ===========================
st.markdown("""
<style>
/* Varsayılan olarak KOYU mod (Beyaz Yazı) */
:root {
    --branding-color: #ffffff;
}

/* Eğer kullanıcı AÇIK mod kullanıyorsa (Siyah Yazı) */
@media (prefers-color-scheme: light) {
    :root {
        --branding-color: #000000;
    }
}

/* Streamlit'in kendi açık tema sınıfları için ek garanti */
[data-theme="light"] {
    --branding-color: #000000;
}

.tr-branding {
    position: fixed;
    bottom: 80px;
    right: 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    z-index: 9999;
    pointer-events: none;
}

.tr-flag-img {
    width: 40px;
    margin-bottom: 5px;
}

.ata-signature {
    font-family: 'Dancing Script', cursive;
    color: var(--branding-color); /* CSS değişkeni kullanıyoruz */
    font-size: 22px;
    opacity: 0.9;
    margin-bottom: 2px;
    transition: color 0.3s ease;
}

.made-in-text {
    font-size: 10px;
    font-weight: bold;
    color: var(--branding-color); /* CSS değişkeni kullanıyoruz */
    opacity: 0.6;
    letter-spacing: 1px;
    transition: color 0.3s ease;
}
</style>

<div class="tr-branding">
    <img src="https://flagcdn.com/w80/tr.png" class="tr-flag-img">
    <div class="ata-signature">K. Atatürk</div>
    <div class="made-in-text">MADE IN TÜRKİYE</div>
</div>

<link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# ===========================
# OLLAMA MODELS
# ===========================
def get_local_models():
    try:
        out = subprocess.check_output(["ollama", "list"], text=True, encoding="utf-8", errors="ignore")
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        models = []
        for ln in lines[1:]:
            name = ln.split()[0]
            if name:
                models.append(name)
        return models if models else ["llama3"]
    except Exception:
        return ["llama3"]

LOCAL_MODELS = get_local_models()

# ===========================
# INIT LOG ONCE
# ===========================
if "log_inited" not in st.session_state:
    init_log_db()
    st.session_state.log_inited = True

# ===========================
# LANGUAGE DEFAULT (IMPORTANT)
# ===========================
# L daha sidebar seçilmeden önce lazım olabiliyor -> default
L = st.session_state.get("ui_lang", "Türkçe")

# ===========================
# SESSION DEFAULTS
# ===========================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
    log_event(st.session_state.session_id, "APP_OPEN", "Uygulama oturumu başladı")

if "last_seen" not in st.session_state:
    st.session_state.last_seen = datetime.datetime.now().timestamp()

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [{"role": "assistant", "content": T[L]["welcome"]}]

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

if "pdf_history" not in st.session_state:
    st.session_state.pdf_history = []

# ===========================
# IDLE CONTROL (no "son loglar" UI yok)
# ===========================
IDLE_TIMEOUT_SEC = 120
now_ts = datetime.datetime.now().timestamp()
idle_sec = int(now_ts - st.session_state.last_seen)

if idle_sec > IDLE_TIMEOUT_SEC and not st.session_state.get("session_ended"):
    st.session_state.session_ended = True
    log_event(st.session_state.session_id, "APP_CLOSE", f"idle_sec={idle_sec}")

    # yeni session
    st.session_state.session_id = str(uuid.uuid4())[:8]
    st.session_state.last_seen = now_ts
    st.session_state.chat_messages = [{"role": "assistant", "content": T[L]["welcome"]}]
    st.session_state.pdf_text = ""
    st.session_state.pdf_history = []
    st.session_state.session_ended = False
    log_event(st.session_state.session_id, "APP_OPEN", "Yeni oturum başladı")

# ===========================
# ADAPTİF MODERN HEADER (RENK REVİZE)
# ===========================
st.markdown(f"""
<style>
/* Header Ana Kutusu */
.header-box {{
    padding: 25px;
    border-radius: 20px;
    margin-bottom: 20px;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}}

/* UsKut AI Yazısı - Varsayılan (Koyu Tema) */
.header-title {{
    margin: 0;
    font-size: 44px;
    font-weight: 800;
    /* Koyu temada daha ağırbaşlı, gümüşten koyu maviye geçiş */
    background: linear-gradient(90deg, #f8fafc, #334155);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.3));
}}

/* Açık Tema Ayarları */
@media (prefers-color-scheme: light) {{
    .header-box {{
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid rgba(0, 0, 0, 0.05);
    }}
    .header-title {{
        /* Açık temada o sevdiğin canlı mavi kalsın veya daha net dursun */
        background: linear-gradient(90deg, #1e40af, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .header-box p {{ color: #475569 !important; }}
}}

.header-caption {{
    margin-top: 10px;
    font-size: 16px;
    opacity: 0.85;
    font-weight: 500;
    color: #cbd5e1;
}}
</style>

<div class="header-box">
    <h1 class="header-title">🤖 UsKut AI</h1>
    <p class="header-caption">{T[L]["caption"]}</p>
</div>
""", unsafe_allow_html=True)

# ===========================
# SIDEBAR
# ===========================
with st.sidebar:
    st.header(T[L]["settings"])

    ui_lang = st.selectbox(T[L]["ui_lang"], ["Türkçe", "English"], index=0, key="ui_lang")
    L = ui_lang

    if "last_lang" not in st.session_state:
        st.session_state.last_lang = L

    if st.session_state.last_lang != L:
        st.session_state.last_lang = L
        st.session_state.chat_messages = [{"role": "assistant", "content": T[L]["welcome"]}]
        st.session_state.pdf_text = ""
        st.session_state.pdf_history = []
        st.rerun()

    chat_model = st.selectbox(T[L]["model"], LOCAL_MODELS, index=0, key="chat_model")
    fast_mode = st.toggle(T[L]["fast_mode"], value=True, key="fast_mode")

    if fast_mode:
        num_predict = 180
        num_ctx = 1024
    else:
        num_predict = 350
        num_ctx = 2048

    temperature = st.slider(T[L]["creativity"], 0.0, 1.0, 0.3, 0.05, key="temperature")

# ===========================
# TABS
# ===========================
tab_chat, tab_pdf, tab_excel, tab_code = st.tabs(
    [T[L]["tab_chat"], T[L]["tab_pdf"], T[L]["tab_excel"], T[L]["tab_code"]]
)

# =========================================================
# TAB 1: CHAT
# =========================================================
with tab_chat:
    st.subheader(T[L]["tab_chat"].replace("💬 ", ""))

    for m in st.session_state.chat_messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_msg = st.chat_input(T[L]["type_msg"])

    if user_msg:
        st.session_state.last_seen = datetime.datetime.now().timestamp()
        log_event(st.session_state.session_id, "CHAT_ASK", f"len={len(user_msg)} model={chat_model} fast={fast_mode}")

        st.session_state.chat_messages.append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            acc = ""
            cursor = "▌"

            if L == "Türkçe":
                sys = "Sen UsKut'sun. KVKK/gizlilik odaklı, kısa ve net cevap ver. Sadece Türkçe konuş."
            else:
                sys = "You are UsKut. Privacy-first internal assistant. Keep answers short and clear. Speak English only."

            messages = [{"role": "system", "content": sys}] + st.session_state.chat_messages
            options = {"num_predict": num_predict, "num_ctx": num_ctx, "temperature": float(temperature)}

            try:
                stream = ollama.chat(
                    model=chat_model,
                    messages=messages,
                    options=options,
                    stream=True,
                )
                for chunk in stream:
                    part = chunk.get("message", {}).get("content", "")
                    if part:
                        acc += part
                        placeholder.markdown(acc + cursor)
                placeholder.markdown(acc)
            except Exception as e:
                log_event(st.session_state.session_id, "ERROR", f"WHERE=CHAT | {format_error(e)}")
                acc = f"{T[L]['error_model']}: {e}"
                placeholder.error(acc)

        st.session_state.chat_messages.append({"role": "assistant", "content": acc})

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button(T[L]["clear_chat"], key="clear_chat_btn"):
            st.session_state.chat_messages = [{"role": "assistant", "content": T[L]["welcome"]}]
            st.rerun()
    with col2:
        st.caption(T[L]["hint_fast"])

# =========================================================
# TAB 2: PDF Q&A
# =========================================================
with tab_pdf:
    st.subheader(T[L]["tab_pdf"].replace("📄 ", ""))
    st.markdown('<div class="uskut-card">', unsafe_allow_html=True)

    uploaded = st.file_uploader(T[L]["upload_pdf"], type=["pdf"], key="pdf_uploader")
    if uploaded:
        try:
            reader = PdfReader(uploaded)
            parts = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
            text = "\n".join(parts).encode("utf-8", "ignore").decode("utf-8")
            st.session_state.pdf_text = text
            st.success(T[L]["pdf_read_ok"])
        except Exception as e:
            log_event(st.session_state.session_id, "ERROR", f"WHERE=PDF_READ | {format_error(e)}")
            st.error(f"PDF okunurken hata oluştu: {e}")

    if not st.session_state.pdf_text.strip():
        st.info(T[L]["pdf_info"])
    else:
        question = st.text_input(T[L]["pdf_q"], key="pdf_question")
        ask = st.button(T[L]["ask"], key="ask_pdf_btn")

        if ask:
            st.session_state.last_seen = datetime.datetime.now().timestamp()
            log_event(st.session_state.session_id, "PDF_ASK", f"len={len(question)} model={chat_model}")

            if not question.strip():
                st.warning("Lütfen bir soru yaz." if L == "Türkçe" else "Please write a question.")
            else:
                with st.spinner("UsKut düşünüyor..." if L == "Türkçe" else "UsKut is thinking..."):
                    if L == "Türkçe":
                        sys = (
                            "Sadece Türkçe cevap ver. "
                            "Sadece verilen PDF metnine dayan. Metinde yoksa aynen: 'Bu bilgi PDF'te geçmiyor.' de. "
                            "Kısa ve net cevap ver."
                        )
                    else:
                        sys = (
                            "Answer only in English. Use only the provided PDF text. "
                            "If not found, say: 'This is not mentioned in the PDF.' Keep it short and clear."
                        )

                    prompt = f"{sys}\n\nPDF TEXT:\n{st.session_state.pdf_text[:12000]}\n\nQUESTION:\n{question}\n\nANSWER:"
                    try:
                        resp = ollama.generate(
                            model=chat_model,
                            prompt=prompt,
                            options={"num_predict": num_predict, "num_ctx": num_ctx, "temperature": float(temperature)},
                        )
                        answer = (resp.get("response") or "").strip()
                    except Exception as e:
                        log_event(st.session_state.session_id, "ERROR", f"WHERE=PDF_GEN | {format_error(e)}")
                        answer = f"Hata: {e}" if L == "Türkçe" else f"Error: {e}"

                    st.session_state.pdf_history.append((question, answer))
                    st.markdown("### " + ("Cevap" if L == "Türkçe" else "Answer"))
                    st.write(answer)

        st.divider()
        st.markdown("### PDF Geçmişi" if L == "Türkçe" else "### PDF History")
        if st.session_state.pdf_history:
            for q, a in reversed(st.session_state.pdf_history):
                st.markdown(f"**Sen:** {q}" if L == "Türkçe" else f"**You:** {q}")
                st.markdown(f"**UsKut:** {a}")
                st.markdown("---")
        else:
            st.caption("Henüz soru sorulmadı." if L == "Türkçe" else "No questions yet.")

        if st.button(T[L]["clear_pdf"], key="clear_pdf_btn"):
            st.session_state.pdf_history = []
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# TAB 3: EXCEL VIS
# =========================================================
with tab_excel:
    st.subheader(T[L]["tab_excel"].replace("📊 ", ""))
    st.caption(T[L]["excel_help"])

    excel_file = st.file_uploader(T[L]["excel_upload"], type=["xlsx", "xls"], key="excel_uploader")

    if not excel_file:
        st.info(T[L]["excel_need"])
    else:
        st.session_state.last_seen = datetime.datetime.now().timestamp()
        log_event(st.session_state.session_id, "EXCEL_UPLOAD", f"name={excel_file.name} size={excel_file.size}")

        try:
            xls = pd.ExcelFile(excel_file)
            sheet = st.selectbox(T[L]["sheet_select"], xls.sheet_names, index=0, key="sheet_select")
            df = xls.parse(sheet)

            df.columns = [str(c).strip() if str(c).strip() else f"Kolon_{i}" for i, c in enumerate(df.columns)]
            st.success(f"Excel okundu ✅ | Satır: {len(df)} | Sütun: {len(df.columns)}" if L == "Türkçe"
                       else f"Excel loaded ✅ | Rows: {len(df)} | Cols: {len(df.columns)}")

            with st.expander(T[L]["filters"], expanded=True):
                filter_cols = st.multiselect(T[L]["filter_cols"], df.columns.tolist(), key="filter_cols")
                filtered = df.copy()

                for col in filter_cols:
                    if pd.api.types.is_numeric_dtype(filtered[col]):
                        s = pd.to_numeric(filtered[col], errors="coerce")
                        s_nonnull = s.dropna()
                        mn = float(s_nonnull.min()) if len(s_nonnull) else 0.0
                        mx = float(s_nonnull.max()) if len(s_nonnull) else 0.0
                        r = st.slider(f"{col} aralığı" if L == "Türkçe" else f"{col} range", mn, mx, (mn, mx), key=f"rng_{col}")
                        filtered = filtered[(pd.to_numeric(filtered[col], errors="coerce") >= r[0]) &
                                            (pd.to_numeric(filtered[col], errors="coerce") <= r[1])]
                    else:
                        uniq = filtered[col].dropna().astype(str).unique().tolist()[:300]
                        chosen = st.multiselect(f"{col} değerleri" if L == "Türkçe" else f"{col} values",
                                                uniq, default=uniq, key=f"cat_{col}")
                        filtered = filtered[filtered[col].astype(str).isin(chosen)]

            st.markdown(T[L]["table"])
            st.dataframe(filtered, use_container_width=True, height=380)

            c1, c2, c3 = st.columns(3)
            c1.metric("Satır" if L == "Türkçe" else "Rows", f"{len(filtered)}")
            c2.metric("Sütun" if L == "Türkçe" else "Cols", f"{len(filtered.columns)}")
            c3.metric("Boş Hücre" if L == "Türkçe" else "Empty Cells", f"{int(filtered.isna().sum().sum())}")

            st.divider()
            st.markdown(T[L]["charts"])

            numeric_cols = [c for c in filtered.columns if pd.api.types.is_numeric_dtype(pd.to_numeric(filtered[c], errors="coerce"))]
            non_numeric_cols = [c for c in filtered.columns if c not in numeric_cols]

            if len(numeric_cols) == 0:
                st.warning("Grafik için sayısal sütun bulunamadı." if L == "Türkçe" else "No numeric column found for charts.")
            else:
                chart_type = st.selectbox(
                    "Grafik tipi" if L == "Türkçe" else "Chart type",
                    ["Bar (Kategori→Toplam)", "Line (Zaman/Index)", "Histogram (Dağılım)"],
                    key="chart_type"
                )

                if chart_type == "Bar (Kategori→Toplam)":
                    if len(non_numeric_cols) == 0:
                        st.warning("Bar grafik için en az 1 kategori/metin sütunu lazım." if L == "Türkçe"
                                   else "Need at least 1 category/text column for bar chart.")
                    else:
                        cat = st.selectbox("Kategori sütunu" if L == "Türkçe" else "Category column", non_numeric_cols, key="bar_cat")
                        val = st.selectbox("Değer (sayısal) sütunu" if L == "Türkçe" else "Value (numeric) column", numeric_cols, key="bar_val")
                        agg = filtered.groupby(cat, dropna=False)[val].sum(numeric_only=True).reset_index()
                        agg = agg.sort_values(val, ascending=False).head(25)
                        st.caption("Not: En yüksek 25 kategori gösterilir." if L == "Türkçe" else "Top 25 categories shown.")
                        st.bar_chart(agg, x=cat, y=val)

                elif chart_type == "Line (Zaman/Index)":
                    val = st.selectbox("Değer (sayısal) sütunu" if L == "Türkçe" else "Value (numeric) column",
                                       numeric_cols, key="line_val")
                    xcol = st.selectbox("X ekseni (opsiyonel)" if L == "Türkçe" else "X axis (optional)",
                                        ["(Index)"] + filtered.columns.tolist(), key="line_x")

                    if xcol == "(Index)":
                        tmp = filtered[[val]].reset_index(drop=True)
                        st.line_chart(tmp, y=val)
                    else:
                        tmp = filtered[[xcol, val]].dropna()
                        st.line_chart(tmp, x=xcol, y=val)

                else:
                    val = st.selectbox("Histogram sütunu" if L == "Türkçe" else "Histogram column", numeric_cols, key="hist_val")
                    bins = st.slider("Bin sayısı" if L == "Türkçe" else "Bins", 5, 60, 20, key="hist_bins")
                    s = pd.to_numeric(filtered[val], errors="coerce").dropna()
                    cut = pd.cut(s, bins=bins)
                    hist = cut.value_counts().sort_index()
                    hist_df = hist.reset_index()
                    hist_df.columns = ["Aralık", "Adet"] if L == "Türkçe" else ["Range", "Count"]
                    hist_df[hist_df.columns[0]] = hist_df[hist_df.columns[0]].astype(str)
                    st.bar_chart(hist_df, x=hist_df.columns[0], y=hist_df.columns[1])

            st.divider()
            st.markdown(T[L]["download"])
            csv = filtered.to_csv(index=False).encode("utf-8")
            st.download_button(T[L]["csv_btn"], data=csv, file_name="filtered.csv", mime="text/csv", key="dl_csv")

        except Exception as e:
            log_event(st.session_state.session_id, "ERROR", f"WHERE=EXCEL | {format_error(e)}")
            st.error(f"Excel okunurken hata oluştu: {e}" if L == "Türkçe" else f"Error while reading Excel: {e}")
            st.stop()

# =========================================================
# TAB 4: CODE FIXER
# =========================================================
with tab_code:
    st.subheader(T[L]["tab_code"].replace("🧩 ", ""))
    st.markdown('<div class="uskut-card">', unsafe_allow_html=True)

    lang_cf = st.selectbox(T[L]["code_out_lang"], ["Türkçe", "English"], key="cf_lang")
    target_lang = "Türkçe" if lang_cf == "Türkçe" else "English"

    code_lang = st.selectbox(T[L]["code_lang"], ["Python", "JavaScript", "Java", "C#", "SQL", "Diğer"], key="code_lang")
    code_input = st.text_area(T[L]["code_input"], height=220, key="code_input_area", placeholder='Örn: prin("Selam")')

    if st.button(T[L]["fix_code"], key="fix_code_btn"):
        st.session_state.last_seen = datetime.datetime.now().timestamp()
        log_event(st.session_state.session_id, "CODE_FIX", f"lang={code_lang} len={len(code_input)} model={chat_model}")

        if not code_input.strip():
            st.warning("Lütfen bir kod yapıştır." if L == "Türkçe" else "Please paste some code.")
        else:
            with st.spinner("UsKut kodu analiz ediyor..." if L == "Türkçe" else "UsKut is analyzing code..."):
                prompt = f"""
Rule: Use ONLY {target_lang}.
Do NOT introduce yourself. Do NOT say "I am UsKut AI".
Language: {code_lang}

Task:
1) Find and fix bugs with minimal changes.
2) Output ONLY the corrected code inside ONE Markdown code block.
3) Then write 3-6 bullet points explanation in {target_lang}.

CODE:
{code_input}
"""
                try:
                    resp = ollama.generate(
                        model=chat_model,
                        prompt=prompt,
                        options={"num_predict": num_predict, "num_ctx": num_ctx, "temperature": float(temperature)},
                    )
                    output = (resp.get("response") or "").strip()
                    st.markdown("### " + ("Düzeltilmiş Kod ve Açıklama" if L == "Türkçe" else "Fixed Code & Explanation"))
                    st.write(output)
                except Exception as e:
                    log_event(st.session_state.session_id, "ERROR", f"WHERE=CODEFIX | {format_error(e)}")
                    st.error(f"Hata: {e}" if L == "Türkçe" else f"Error: {e}")

    st.markdown('</div>', unsafe_allow_html=True)