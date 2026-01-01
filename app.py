import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="米国株 短期売買 完全版", layout="wide")
st.title("📉 米国株 短期売買スクリーナー（完全版）")

# ----------------------
# セッション初期化
# ----------------------
if "ranking" not in st.session_state:
    st.session_state.ranking = None
if "data_cache" not in st.session_state:
    st.session_state.data_cache = {}

# ----------------------
# セクター日本語
# ----------------------
SECTOR_JP = {
    "Technology": "情報技術",
    "Consumer Cyclical": "一般消費財",
    "Consumer Defensive": "生活必需品",
    "Healthcare": "ヘルスケア",
    "Financial Services": "金融",
    "Communication Services": "通信サービス",
    "Industrials": "資本財",
    "Energy": "エネルギー",
    "Utilities": "公益事業",
    "Real Estate": "不動産",
    "Basic Materials": "素材"
}

# ----------------------
# 対象銘柄
# ----------------------
TICKERS = [
    "PLTR","SOFI","COIN","RBLX","SNOW",
    "SHOP","UBER","ABNB","DASH",
    "AMD","NVDA","INTC","TSM",
    "TSLA","LCID","RIVN",
    "PYPL","SQ",
    "META","NFLX"
]

# ----------------------
# 関数
# ----------------------
def get_sector_jp(ticker):
    try:
        sector = yf.Ticker(ticker).info.get("sector")
        if not sector:
            return "不明"
        return SECTOR_JP.get(sector, sector)
    except:
        return "不明"

def calc_indicators(df):
    df["SMA5"] = df["Close"].rolling(5).mean()
    df["SMA20"] = df["Close"].rolling(20).mean()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean().replace(0,1e-6)
    df["RSI"] = 100 - (100 / (1 + rs))
    df["Volume_MA5"] = df["Volume"].rolling(5).mean()
    df["Volume_MA20"] = df["Volume"].rolling(20).mean()
    df["Return_5d"] = df["Close"].pct_change(5)*100
    return df

def score_stock(df):
    score = 0
    if df.empty or len(df)<20: return score
    rsi = df["RSI"].iloc[-1]
    ret5 = df["Return_5d"].iloc[-1]
    if rsi<25: score+=5
    elif rsi<35: score+=4
    elif rsi<45: score+=2
    if ret5<=-8: score+=3
    elif ret5<=-4: score+=2
    elif ret5<=-2: score+=1
    if df["Volume_MA5"].iloc[-1] > df["Volume_MA20"].iloc[-1]: score+=2
    if len(df)>=3 and df["SMA20"].iloc[-1]>=df["SMA20"].iloc[-3]: score+=1
    return score

def score_to_color(score):
    if score>=9: return "darkgreen"
    elif score>=6: return "green"
    return "gray"

# ----------------------
# 高速分析ボタン
# ----------------------
if st.button("🔍 高速分析開始"):
    results=[]
    with st.spinner("分析中..."):
        # 一括ダウンロード
        all_data = yf.download(TICKERS, period="3mo", group_by='ticker', progress=False)
        for ticker in TICKERS:
            df = all_data[ticker].copy() if ticker in all_data else pd.DataFrame()
            if df.empty or len(df)<30: continue
            df = calc_indicators(df)
            score = score_stock(df)
            st.session_state.data_cache[ticker] = df
            if score>=4:
                results.append({
                    "銘柄": ticker,
                    "セクター": get_sector_jp(ticker),
                    "スコア": score,
                    "RSI": round(df["RSI"].iloc[-1],1),
                    "5日騰落率(%)": round(df["Return_5d"].iloc[-1],1)
                })
    st.session_state.ranking = pd.DataFrame(results).sort_values("スコア", ascending=False)

# ----------------------
# 結果表示
# ----------------------
if st.session_state.ranking is not None and not st.session_state.ranking.empty:
    ranking = st.session_state.ranking
    st.subheader("📊 リバウンド候補ランキング")
    st.dataframe(ranking, use_container_width=True)

    selected = st.selectbox("📌 銘柄を選択", ranking["銘柄"])
    current_score = ranking.loc[ranking["銘柄"]==selected,"スコア"].values[0]

    df = st.session_state.data_cache.get(selected)
    if df is not None:
        entry = df["Close"].iloc[-1]
        take_profit = entry*1.05
        stop_loss = entry*0.95
        color = score_to_color(current_score)

        fig,(ax1,ax2)=plt.subplots(2,1,figsize=(10,6),sharex=True,gridspec_kw={"height_ratios":[3,1]})
        ax1.plot(df["Close"],color=color,linewidth=2,label=f"終値（スコア {current_score}）")
        ax1.plot(df["SMA5"],label="SMA5")
        ax1.plot(df["SMA20"],label="SMA20")
        ax1.axhline(entry,linestyle="--",label="エントリー")
        ax1.axhline(take_profit,linestyle="--",label="利確 +5%")
        ax1.axhline(stop_loss,linestyle="--",label="損切り -5%")
        ax1.legend()
        ax2.plot(df["RSI"],label="RSI")
        ax2.axhline(70,linestyle="--")
        ax2.axhline(30,linestyle="--")
        ax2.set_ylim(0,100)
        ax2.legend()
        st.pyplot(fig, clear_figure=True)

        if current_score>=7:
            st.success("🟢 リバウンド有力候補")
        else:
            st.info("⚪ 様子見")
else:
    st.info("🔍『高速分析開始』を押してください")
