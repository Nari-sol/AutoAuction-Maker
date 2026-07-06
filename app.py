import streamlit as st
import pandas as pd
from converter import process_csv
import io

st.set_page_config(page_title="AutoAuction Maker", layout="wide")

st.title("AutoAuction Maker 🚗")
st.markdown("YahooショッピングのCSVデータから、ヤフオクの一括出品用CSVを生成します。")

store_type = st.radio(
    "出力する店舗（形式）を選択してください：",
    ["競り1（1号店・送料別）", "競り3（3号店・送料込み）"],
    horizontal=True
)

st.write("---")
st.write("### 画像設定 (任意)")
st.markdown("各画像項目に一律で設定する値（ファイル名等）を入力してください。（空欄のままの場合は出力も空欄になります）")

image_settings = {}
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    image_settings["画像1"] = st.text_input("メイン", key="img_main")
    image_settings["画像6"] = st.text_input("サブ5", key="img_sub5")
with col2:
    image_settings["画像2"] = st.text_input("サブ1", key="img_sub1")
    image_settings["画像7"] = st.text_input("サブ6", key="img_sub6")
with col3:
    image_settings["画像3"] = st.text_input("サブ2", key="img_sub2")
    image_settings["画像8"] = st.text_input("サブ7", key="img_sub7")
with col4:
    image_settings["画像4"] = st.text_input("サブ3", key="img_sub3")
    image_settings["画像9"] = st.text_input("サブ9", key="img_sub9") # サブ8は意図的に除外
with col5:
    image_settings["画像5"] = st.text_input("サブ4", key="img_sub4")
    image_settings["画像10"] = st.text_input("notes", key="img_notes")

st.write("---")

uploaded_file = st.file_uploader("YahooショッピングのCSVファイルをアップロードしてください", type=["csv"])

if uploaded_file is not None:
    try:
        # CSVの読み込み（Shift-JISを優先、ダメならUTF-8）
        try:
            df = pd.read_csv(uploaded_file, encoding='cp932')
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding='utf-8')
            
        st.write("### アップロードされたデータ (先頭5件)")
        st.dataframe(df.head())

        if st.button("変換実行", type="primary"):
            with st.spinner("データを変換中..."):
                # 変換ロジックの呼び出し
                result_df, skipped_count = process_csv(df, store_type, image_settings)
                
                if skipped_count > 0:
                    st.warning(f"管理番号の文字数が20文字をオーバーするため、一部の商品（{skipped_count}件）を競り3の出力から除外しました。")
                
                st.success("変換が完了しました！")
                st.write("### 変換後のデータ (先頭5件)")
                st.dataframe(result_df.head())
                
                # CSV出力 (ヤフオク仕様に合わせShift-JIS)
                csv_buffer = io.BytesIO()
                result_df.to_csv(csv_buffer, index=False, encoding='cp932', errors='replace')
                csv_data = csv_buffer.getvalue()
                
                st.download_button(
                    label="📥 ヤフオク用CSVをダウンロード",
                    data=csv_data,
                    file_name="yahoo_auctions_listing.csv",
                    mime="text/csv",
                )
                
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
