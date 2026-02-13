import streamlit as st
import pandas as pd
import plotly.express as px
from google_play_scraper import app, search, reviews, Sort
try:
    from google_play_scraper import suggestions
except ImportError:
    suggestions = None
from textblob import TextBlob
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import re
import io
import nltk
from nltk.util import ngrams
from collections import Counter

# --- Page Config ---
st.set_page_config(page_title="App Scout - Pencari Peluang Blue Ocean", layout="wide")

# --- Custom Styling ---
st.markdown("""
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0" />
    <style>
    .main {
        background-color: #f8f9fa;
        font-family: 'Inter', sans-serif;
    }
    h1, h2, h3 {
        color: #2c3e50;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .material-symbols-rounded {
        font-size: 24px;
        color: #444;
        vertical-align: middle;
    }
    .hero-icon {
        font-size: 32px !important;
        color: #1565c0;
    }
    /* Card-like styling for containers */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
    }
    /* Metric styling */
    [data-testid="stMetric"] {
        background-color: #ffffff !important;
        padding: 15px !important;
        border-radius: 8px !important;
        border: 1px solid #e0e0e0 !important;
        box-shadow: none !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        color: #666 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        color: #333 !important;
    }
    /* Opportunity Card */
    .opportunity-card {
        background-color: #ffffff;
        border-left: 5px solid #ff4b4b;
        padding: 15px;
        margin-bottom: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        color: #333 !important;
    }
    .opportunity-card h4 { margin: 0 0 10px 0; color: #ff4b4b !important; }
    .opportunity-card p { margin: 5px 0; color: #555 !important; font-size: 0.95rem; }
    .badge-tier {
        background-color: #e3f2fd;
        color: #1565c0;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- Utilities ---
def parse_installs(installs_str):
    if not installs_str: return 0
    clean = re.sub(r'[^\d]', '', installs_str)
    return int(clean) if clean else 0

def get_aso_score(app_detail):
    score = 100
    if len(app_detail.get('title', '')) < 10: score -= 20
    if len(app_detail.get('description', '')) < 500: score -= 20
    if len(app_detail.get('screenshots', [])) < 3: score -= 20
    if not app_detail.get('video'): score -= 10
    return max(0, score)

def clean_size(size_str):
    if not size_str or 'Varies' in size_str or 'Bervariasi' in size_str:
        return 0
    try:
        num = re.search(r'(\d+[.,]?\d*)', size_str)
        if not num: return 0
        val = float(num.group(1).replace(',', '.'))
        if 'G' in size_str.upper(): val *= 1024
        if 'k' in size_str.lower(): val /= 1024
        return val
    except:
        return 0

@st.cache_data(ttl=3600)
def fetch_keyword_data(keywords, country, lang):
    all_data = []
    base_keywords = [k.strip() for k in keywords.split(",")]
    expanded_keywords = set(base_keywords)
    
    with st.spinner("Mengembangkan kata kunci (Pro Feature)..."):
        if suggestions:
            for k in base_keywords:
                try:
                    suggs = suggestions(k, lang=lang, country=country)
                    for s in suggs[:3]:
                        expanded_keywords.add(s)
                except:
                    continue
    
    for kw in list(expanded_keywords):
        with st.spinner(f"Mencari data untuk '{kw}'..."):
            results = search(kw, lang=lang, country=country, n_hits=20)
            for r in results:
                try:
                    detail = app(r['appId'], lang=lang, country=country)
                    
                    installs = parse_installs(detail.get('installs', '0'))
                    rev_count = detail.get('reviews', 1)
                    engagement = installs / rev_count if rev_count > 0 else 0
                    
                    last_updated = detail.get('updated')
                    if last_updated:
                        last_updated_date = datetime.fromtimestamp(last_updated)
                        is_zombie = (datetime.now() - last_updated_date).days > 730
                    else:
                        is_zombie = False
                        last_updated_date = None

                    tier = "Pendatang Baru"
                    if installs > 1000000: tier = "Raksasa (Hindari)"
                    elif installs > 100000: tier = "Pemain Stabil"
                    elif installs > 10000: tier = "Sedang Naik Daun"
                    
                    price = detail.get('price', 0)
                    currency = detail.get('currency', 'USD')
                    est_revenue = f"{currency} {installs * price:,.0f}" if price > 0 else "Gratis / Iklan"

                    all_data.append({
                        'Kata Kunci': kw,
                        'Judul': detail.get('title'),
                        'App ID': detail.get('appId'),
                        'Rating': detail.get('score'),
                        'Instalasi': installs,
                        'Review': rev_count,
                        'Engagement': engagement,
                        'Ukuran (MB)': detail.get('size', 'Bervariasi').replace('M', '').replace('k', '/1024'),
                        'Zombie App': is_zombie,
                        'Update Terakhir': last_updated_date,
                        'Ada Iklan': detail.get('adSupported', False),
                        'IAP': detail.get('offersIAP', False),
                        'Teks IAP': "Ya" if detail.get('offersIAP', False) else "Tidak",
                        'Skor ASO': get_aso_score(detail),
                        'Link': detail.get('url'),
                        'Tier Kompetitor': tier,
                        'Estimasi Omzet': est_revenue
                    })
                except Exception as e:
                    continue
    return pd.DataFrame(all_data)

# --- UI Layout ---

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2586/2586144.png", width=50)
    st.title("App Scout")
    st.caption("Intelligence Blue Ocean Tool")
    st.divider()
    
    st.subheader("Konfigurasi")
    country = st.text_input("Negara (Kode)", value="id", help="Contoh: id, us, sg")
    lang = st.text_input("Bahasa (Kode)", value="id", help="Contoh: id, en")
    st.divider()
    st.info("Tips: Gunakan kata kunci spesifik untuk hasil yang lebih baik.")

# Main Tabs
tab1, tab2 = st.tabs(["Market Gap Hunter", "Competitor Spy"])

# ... (Previous code remains)

# --- Helper: Decision Logic ---
def get_market_decision(df):
    avg_rating = df['Rating'].mean()
    avg_installs = df['Instalasi'].mean()
    opportunities = len(df[df['Rating'] < 4.0])
    
    if opportunities >= 3 and avg_installs > 10000:
        return "POTENSI TINGGI (High Potential)", "green", \
               f"Ditemukan {opportunities} aplikasi dengan permintaan tinggi tapi kualitas buruk (Rating < 4.0). Pasar ini 'haus' akan aplikasi yang lebih baik.", "check_circle"
    elif avg_installs > 500000 and avg_rating > 4.2:
        return "PERSAINGAN KETAT (Saturated)", "orange", \
               "Pasar sudah dikuasai aplikasi raksasa dengan kualitas bagus. Kecuali Anda punya fitur revolusioner, akan sulit bersaing.", "warning"
    elif avg_installs < 5000:
        return "PASAR SEPI (Niche/Low Demand)", "red", \
               "Volume pencarian/instalasi terlalu kecil. Mungkin kata kunci terlalu spesifik atau memang tidak ada peminat.", "cancel"
    else:
        return "NETRAL / MODERAT", "blue", \
               "Ada peluang, tapi tidak terlalu mencolok. Perlu riset lebih dalam pada fitur spesifik.", "info"

def get_competitor_decision(detail, rv_df):
    score = detail.get('score', 0)
    installs = parse_installs(detail.get('installs', '0'))
    
    # Calculate Velocity if available
    velocity = 0
    if not rv_df.empty:
        last_30 = rv_df[rv_df['at'] > datetime.now() - timedelta(days=30)]
        velocity = len(last_30)
    
    if score < 3.8 and installs > 50000:
        return "SERANG SEKARANG (Vulnerable)", "success", \
               f"Musuh sedang lemah! Rating {score:.1f} dengan banyak user ({installs}) artinya user kecewa tapi tidak ada pilihan lain. Masuk dan tawarkan solusi yang lebih stabil.", "gavel"
    elif velocity > 100:
        return "TUNGGANGI OMBAK (Viral)", "warning", \
               f"Kompetitor sedang viral ({velocity} review/bulan). Jangan langsung *head-to-head*, tapi buat versi 'alternatif' atau 'lite' untuk mengambil tumpahan user mereka.", "trending_up"
    elif score > 4.5 and installs > 1000000:
        return "HINDARI (Dominant Leader)", "error", \
               "Raja pasar yang sangat kuat. User puas (Rating 4.5+). Sangat mahal untuk merebut user mereka kecuali Anda punya budget marketing besar.", "shield"
    else:
        return "AMATI (Monitor)", "info", \
               "Kompetitor standar. Cari celah spesifik di fitur yang tidak mereka miliki (lihat tab 'Kelemahan').", "visibility"

with tab1:
    st.title("Pemburu Celah Pasar")
    st.markdown("Temukan *keyword* dengan permintaan tinggi namun persaingan rendah.")
    
    if 'market_data' not in st.session_state: st.session_state.market_data = None

    with st.container(border=True):
        col_in1, col_in2 = st.columns([3, 1])
        with col_in1:
            kw_input = st.text_input("Kata Kunci (pisahkan koma)", "meditasi, jadwal sholat, resep masakan")
        with col_in2:
            st.write("") 
            st.write("") 
            analyze_btn = st.button("Analisis Pasar", use_container_width=True)

    if analyze_btn:
        df = fetch_keyword_data(kw_input, country, lang)
        st.session_state.market_data = df

    if st.session_state.market_data is not None:
        df = st.session_state.market_data
        if not df.empty:
            st.divider()
            
            # --- NEW: DECISION BLOCK ---
            dec_title, dec_color, dec_reason, dec_icon = get_market_decision(df)
            
            # Map simple colors to hex for inline style
            bg_map = {'green': '#e8f5e9', 'orange': '#fff3e0', 'red': '#ffebee', 'blue': '#e3f2fd'}
            color_map = {'green': '#2e7d32', 'orange': '#ef6c00', 'red': '#c62828', 'blue': '#1565c0'}
            
            st.markdown(f"""
            <div style="padding:15px; border-radius:10px; background-color:{bg_map.get(dec_color, '#f5f5f5')}; border: 1px solid {color_map.get(dec_color, '#999')}; margin-bottom:20px;">
                <h3 style="margin:0; color:{color_map.get(dec_color, '#333')}; display:flex; align-items:center; gap:10px;">
                    <span class="material-symbols-rounded">{dec_icon}</span> {dec_title}
                </h3>
                <p style="margin-top:5px; margin-bottom:0; color:#333;"><b>Analisis AI:</b> {dec_reason}</p>
            </div>
            """, unsafe_allow_html=True)
            # ---------------------------

            # Summary Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Aplikasi", len(df), help="Total aplikasi yang ditemukan.")
            m2.metric("Rating Rata-rata", f"{df['Rating'].mean():.1f}", help="Kepuasan rata-rata.")
            m3.metric("Install Rata-rata", f"{df['Instalasi'].mean():,.0f}", help="Besar pasar.")
            m4.metric("Kompetitor Lemah", len(df[df['Rating'] < 4.0]), help="Target empuk!")

            st.write("")
            
            with st.expander("📚 Panduan Membaca Data"):
                st.markdown("""
                **Tips Cepat:**
                1.  **Kompetitor Lemah**: Rating < 4.0. Target empuk.
                2.  **Tambang Emas**: Install Jutaan + Rating Rendah.
                3.  **Zombie App**: Tidak update > 2 tahun.
                """)

            # Content Tabs
            res_tab1, res_tab2, res_tab3 = st.tabs(["Visualisasi", "Peluang Emas", "Data Lengkap"])
            
            with res_tab1:
                c1, c2 = st.columns(2)
                with c1:
                    with st.container(border=True):
                        st.subheader("Peta Persaingan")
                        fig = px.scatter(df, x="Instalasi", y="Rating", color="Skor ASO", 
                                         size="Review", hover_name="Judul", 
                                         color_continuous_scale="RdYlGn", height=400)
                        st.plotly_chart(fig, use_container_width=True)
                
                with c2:
                    with st.container(border=True):
                        st.subheader("Peluang 'Lite'")
                        df['Size_Numeric'] = df['Ukuran (MB)'].apply(clean_size)
                        fig_lite = px.scatter(df, x="Size_Numeric", y="Instalasi", color="Rating", hover_name="Judul", height=400)
                        st.plotly_chart(fig_lite, use_container_width=True)
            
            with res_tab2:
                # Opportunities Logic (Relaxed Criteria)
                opp_df = df[(df['Rating'] < 4.2) & (df['Instalasi'] > 10000)].copy()
                opp_df['Tipe_Peluang'] = "Kualitas Rendah, Demand Cukup"
                
                zombie_df = df[df['Zombie App']].copy()
                zombie_df['Tipe_Peluang'] = "Zombie App (Lama Tidak Update)"
                
                low_aso = df[df['Skor ASO'] < 50].copy()
                low_aso['Tipe_Peluang'] = "ASO Lemah (Mudah Disalip)"
                
                final_opp = pd.concat([opp_df, zombie_df, low_aso]).drop_duplicates(subset=['App ID'])
                
                if not final_opp.empty:
                    st.success(f"Ditemukan {len(final_opp)} aplikasi target!")
                    for _, row in final_opp.iterrows():
                        st.markdown(f"""
                            <div class="opportunity-card">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <h4 style="margin:0;"><span class="material-symbols-rounded" style="font-size:18px; vertical-align:middle;">target</span> {row['Judul']}</h4>
                                    <span class="badge-tier">{row.get('Tier Kompetitor', 'N/A')}</span>
                                </div>
                                <p style="margin-bottom:10px; font-size:0.8em; color:#777;"><i>{row['App ID']}</i></p>
                                <p><b>Celah:</b> {row['Tipe_Peluang']}</p>
                                <hr style="margin:8px 0; border-top:1px solid #eee;">
                                <div style="display:flex; gap:15px; font-size:0.9rem; align-items:center;">
                                    <span title="Rating"><span class="material-symbols-rounded" style="font-size:16px;">star</span> {row['Rating']:.1f}</span>
                                    <span title="Installs"><span class="material-symbols-rounded" style="font-size:16px;">download</span> {row['Instalasi']:,}</span>
                                    <span title="ASO Score"><span class="material-symbols-rounded" style="font-size:16px;">build</span> {row['Skor ASO']}</span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button(f"Mata-matai {row['Judul'][:15]}...", key=f"btn_{row['App ID']}", help="Analisis detail aplikasi ini"):
                            st.session_state.current_app_id = row['App ID']
                            st.session_state.analyze_active = True
                            st.toast(f"Siap! Pindah ke tab Competitor Spy untuk analisis {row['Judul']}.")
                else:
                    st.info("Belum ada peluang yang sangat menonjol.")

            with res_tab3:
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Unduh CSV", csv, "market_gap.csv", "text/csv")
        else:
            st.warning("Tidak ada data ditemukan.")

with tab2:
    st.markdown('<h1>Mata-mata Kompetitor</h1>', unsafe_allow_html=True)
    st.markdown("Analisis mendalam kelemahan dan strategi lawan.")
    
    if 'current_app_id' not in st.session_state: st.session_state.current_app_id = "com.whatsapp"
    if 'analyze_active' not in st.session_state: st.session_state.analyze_active = False

    with st.container(border=True):
        c_in1, c_in2 = st.columns([3, 1])
        with c_in1:
            app_id_input = st.text_input("App ID Kompetitor", value=st.session_state.current_app_id)
        with c_in2:
            st.write("")
            st.write("")
            spy_btn = st.button("Mulai Mata-matai", use_container_width=True) # Removed emoji

    if spy_btn:
        st.session_state.current_app_id = app_id_input
        st.session_state.analyze_active = True

    if st.session_state.analyze_active:
        try:
            with st.spinner("Sedang membedah aplikasi lawan..."):
                detail = app(st.session_state.current_app_id, lang=lang, country=country)
                
                # --- Get Reviews & calc Trend (Pro Feature) ---
                rv_data_trend, _ = reviews(st.session_state.current_app_id, lang=lang, country=country, count=300, sort=Sort.NEWEST)
                rv_df_trend = pd.DataFrame(rv_data_trend)
                
                # --- DECISION LOGIC FOR TAB 2 ---
                dec_title, dec_color, dec_reason, dec_icon = get_competitor_decision(detail, rv_df_trend)
                
                # Map simple colors to hex
                bg_map = {'green': '#e8f5e9', 'orange': '#fff3e0', 'red': '#ffebee', 'blue': '#e3f2fd'} # Note: tab 2 used diff logic names, let's align
                # get_competitor_decision returns success/warning/error/info
                # Mapping Streamlit status to colors: success->green, warning->orange, error->red, info->blue
                status_map = {'success': 'green', 'warning': 'orange', 'error': 'red', 'info': 'blue'}
                final_color = status_map.get(dec_color, 'blue')
                
                bg_map = {'green': '#e8f5e9', 'orange': '#fff3e0', 'red': '#ffebee', 'blue': '#e3f2fd'}
                color_map = {'green': '#2e7d32', 'orange': '#ef6c00', 'red': '#c62828', 'blue': '#1565c0'}

                st.markdown(f"""
                <div style="padding:15px; border-radius:10px; background-color:{bg_map.get(final_color)}; border: 1px solid {color_map.get(final_color)}; margin-bottom:20px;">
                    <h3 style="margin:0; color:{color_map.get(final_color)}; display:flex; align-items:center; gap:10px;">
                        <span class="material-symbols-rounded">{dec_icon}</span> {dec_title}
                    </h3>
                    <p style="margin-top:5px; margin-bottom:0; color:#333;"><b>Analisis AI:</b> {dec_reason}</p>
                </div>
                """, unsafe_allow_html=True)
                # -------------------------------

                # --- Top Section: Profile ---
                with st.container(border=True):
                    head1, head2, head3 = st.columns([1, 4, 2])
                    with head1:
                        st.image(detail['icon'], width=100)
                    with head2:
                        st.subheader(detail['title'])
                        st.caption(detail['developer'])
                        st.write(detail['summary'])
                    with head3:
                        st.metric("Instalasi", detail['installs'])
                        st.metric("Rating", f"{detail['score']:.1f} ⭐")

                with st.expander("📚 Panduan: Apa yang harus saya pelajari dari musuh?"):
                    st.markdown("""
                    - **Cek 'Traction' (Tab Kelemahan)**: Jika "🔥 VIRAL", hati-hati, mereka sedang naik daun. Jika "💀 Sepi", mereka mungkin sudah ditinggalkan user.
                    - **Tren Sentimen**: Lihat grafiknya. Jika menurun 📉, berarti update terakhir mereka bermasalah. Ini celah masuk!
                    - **Strategi AI (Tab 2)**: AI akan membacakan ribuan review untuk Anda dan menyimpulkan: *Apa yang paling dibenci user dari aplikasi ini?* (Misal: Iklan kebanyakan, Login susah). **JANGAN ULANGI KESALAHAN ITU.**
                    """)

                # --- Analysis Tabs ---
                spy_tab1, spy_tab2, spy_tab3 = st.tabs(["📉 Kelemahan & Review", "🔮 Strategi AI", "⚙️ Teknis"])
                
                monthly_velocity = 0
                hype_status = "Tidak Diketahui"
                
                if not rv_df_trend.empty:
                    rv_df_trend['at'] = pd.to_datetime(rv_df_trend['at'])
                    rv_df_trend['date'] = rv_df_trend['at'].dt.date
                    
                    last_30_days = rv_df_trend[rv_df_trend['at'] > datetime.now() - timedelta(days=30)]
                    monthly_velocity = len(last_30_days)
                    hype_status = "🔥 VIRAL" if monthly_velocity > 50 else "Stabil" if monthly_velocity > 10 else "💀 Sepi"

                with spy_tab1:
                     col_s1, col_s2 = st.columns([1, 2])
                     with col_s1:
                         with st.container(border=True):
                             st.metric("Traction (30 Hari)", f"{monthly_velocity} Ulasan", hype_status)
                             st.caption("Indikator seberapa aktif user baru.")
                     
                     with col_s2:
                         if not rv_df_trend.empty:
                            daily_sentiment = rv_df_trend.groupby('date')['score'].mean().reset_index()
                            fig_trend = px.line(daily_sentiment, x='date', y='score', 
                                                title="Tren Sentimen (Memburuk/Membaik?)", markers=True, height=250)
                            fig_trend.update_layout(margin=dict(l=20, r=20, t=30, b=20))
                            st.plotly_chart(fig_trend, use_container_width=True)

                     st.divider()
                     
                     if not rv_df_trend.empty:
                        neg_reviews = rv_df_trend[rv_df_trend['score'] <= 2]
                        
                        c_pie, c_cloud = st.columns([1, 1])
                        with c_pie:
                            fig_sent = px.pie(rv_df_trend, names='score', title="Komposisi Rating", height=450, hole=0.5)
                            fig_sent.update_layout(legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center", yanchor="top"))
                            st.plotly_chart(fig_sent, use_container_width=True)
                        
                        with c_cloud:
                             if not neg_reviews.empty:
                                all_text = " ".join(neg_reviews['content'].astype(str))
                                wc = WordCloud(width=400, height=300, background_color='white', colormap='Reds').generate(all_text)
                                fig_wc, ax = plt.subplots()
                                ax.imshow(wc, interpolation='bilinear')
                                ax.axis("off")
                                plt.title("Keluhan Utama")
                                st.pyplot(fig_wc)
                             else:
                                 st.info("Belum ada review negatif signifikan.")

                        # Review Search
                        with st.expander("🔍 Cari Review Spesifik"):
                            search_rv = st.text_input("Ketik kata kunci (misal: 'login', 'mahal')", "")
                            if search_rv:
                                results = rv_df_trend[rv_df_trend['content'].str.contains(search_rv, case=False, na=False)]
                                st.dataframe(results[['userName', 'score', 'content', 'at']], use_container_width=True)

                with spy_tab2:
                    if not rv_df_trend.empty and not neg_reviews.empty:
                        # Logic for clusters
                        clusters = {
                            "Performa": ["lambat", "lag", "macet", "lemot", "slow", "crash", "freeze"],
                            "Iklan": ["iklan", "ads", "ganggu", "annoying", "pop up"],
                            "UX/UI": ["bingung", "jelek", "sulit", "complex", "ugly", "difficult", "hard", "bad ui"],
                            "Koneksi": ["internet", "koneksi", "sinyal", "login", "masuk", "daftar"],
                            "Harga/IAP": ["mahal", "bayar", "uang", "money", "price", "pay", "purchase"]
                        }
                        top_pain_point = ""
                        max_count = 0
                        
                        # Clustering Display
                        with st.container(border=True):
                            st.subheader("⚠️ Top Keluhan User")
                            cols_pain = st.columns(len(clusters))
                            idx = 0
                            for cat, keywords in clusters.items():
                                count = sum(any(k in txt.lower() for k in keywords) for txt in neg_reviews['content'])
                                if count > 0:
                                    cols_pain[idx % 5].metric(cat, f"{count} Keluhan")
                                    if count > max_count:
                                        max_count = count
                                        top_pain_point = cat
                                    idx += 1

                        # AI Strategy Box
                        wishlist_regex = r"(wish|please|add|could you|want|hope|missing|tolong|tambah|harap|kurang|kapan)"
                        wishlist = neg_reviews[neg_reviews['content'].str.contains(wishlist_regex, case=False, na=False)]
                        top_wish = wishlist['content'].iloc[0][:50] if not wishlist.empty else "Fitur simpel & tanpa iklan"

                        st.markdown(f"""
                        <div class="opportunity-card" style="border-left-color: #4CAF50;">
                            <h4 style="color: #4CAF50 !important;">🏆 Strategi Menang (AI Recommendation)</h4>
                            <ol>
                                <li><b>Serang Kelemahan:</b> Fokus perbaiki masalah <b>{top_pain_point if top_pain_point else "UX/UI"}</b> yang banyak dikeluhkan.</li>
                                <li><b>Kabulkan Permintaan:</b> User meminta: <i>"{top_wish}..."</i>. Wujudkan ini!</li>
                                <li><b>Branding:</b> { 'Tonjolkan fitur Privasi & Keamanan.' if detail.get('permissions') else 'Tonjolkan aplikasi Ringan & Cepat.' }</li>
                            </ol>
                        </div>
                        """, unsafe_allow_html=True)

                        # N-Grams
                        st.subheader("Analisis Konteks (Bigrams)")
                        words = re.findall(r'\w+', all_text.lower())
                        bigrams = ngrams(words, 2)
                        top_bigrams = Counter(bigrams).most_common(5)
                        cols_gram = st.columns(5)
                        for i, (bg, count) in enumerate(top_bigrams):
                            cols_gram[i].markdown(f"**{bg[0]} {bg[1]}** ({count}x)")
                    else:
                        st.info("Data review tidak cukup untuk analisis AI.")

                with spy_tab3:
                    st.subheader("🛡️ Audit Izin (Permissions)")
                    perms = detail.get('permissions', [])
                    critical_keywords = ['location', 'contacts', 'sms', 'calendar', 'camera', 'microphone']
                    raised = [p['permission'] for p in perms if any(k in p['permission'].lower() for k in critical_keywords)]
                    
                    if raised:
                        st.error(f"⚠️ Ditemukan {len(raised)} Izin Sensitif:")
                        for p in raised:
                            st.code(p, language="text")
                    else:
                        st.success("✅ Aplikasi ini relatif aman (minim izin sensitif).")
                    
                    with st.expander("Lihat Semua Data Teknis"):
                        st.json(detail)

        except Exception as e:
            st.error(f"Gagal mengambil data: {e}")
