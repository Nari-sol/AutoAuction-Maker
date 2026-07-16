import pandas as pd
import re
import unicodedata

def get_width(text):
    return sum(0.5 if unicodedata.east_asian_width(c) in ['H', 'Na'] else 1.0 for c in text)

def truncate_text(text, limit):
    count = 0.0
    res = []
    for c in text:
        w = 0.5 if unicodedata.east_asian_width(c) in ['H', 'Na'] else 1.0
        if count + w > limit:
            break
        count += w
        res.append(c)
    return "".join(res)

MAKER_LIST = [
    "ダイハツ", "BMW", "UDトラックス", "いすゞ", "アウディ", "アストンマーティン", "アバルト", 
    "アプリリア", "アルファ ロメオ", "オペル", "カワサキ", "クライスラー", "サーブ", "シトロエン", 
    "シボレー", "ジャガー", "スズキ", "スバル", "テスラ", "トモス", "トヨタ", "トライアンフ", 
    "ドゥカティ", "ハーレーダビッドソン", "ヒュンダイ", "フィアット", "フェラーリ", "フォルクスワーゲン", 
    "フォード", "プジョー", "ベスパ", "ベントレー", "ホンダ", "ボルボ", "ポルシェ", "マセラティ", 
    "マツダ", "メルセデス・ベンツ", "メルセデスベンツ", "ヤマハ", "ランチア", "ランドローバー", 
    "ランボルギーニ", "ルノー", "レクサス", "ロータス", "ローバー", "三菱ふそう", "三菱", 
    "日産", "日野自動車", "汎用タイプ", "スマート", "MINI", "コマツ", "DAIHATSU", "ベンツ"
]

def process_csv(df: pd.DataFrame, store_type: str = "競り1（1号店・送料別）", image_settings: dict = None) -> tuple[pd.DataFrame, int]:
    """
    Yahooショッピングのデータフレームを受け取り、ヤフオクの一括出品用データフレームに変換する。
    戻り値は (変換後のデータフレーム, スキップされた件数) のタプル。
    """
    result_df = df.copy()
    
    price_col = pd.to_numeric(result_df.get('price', pd.Series([0]*len(result_df))), errors='coerce').fillna(0)
    ship_weight_col = pd.to_numeric(result_df.get('ship-weight', pd.Series([0]*len(result_df))), errors='coerce').fillna(0)
    postage_set_col = pd.to_numeric(result_df.get('postage-set', pd.Series([0]*len(result_df))), errors='coerce').fillna(0)
    name_col = result_df.get('name', pd.Series(['']*len(result_df))).astype(str)
    code_col = result_df.get('code', pd.Series(['']*len(result_df))).astype(str)
    
    code_split = code_col.str.split('-', n=1, expand=True)
    result_df['親品番'] = code_split[0].fillna('')
    if code_split.shape[1] > 1:
        result_df['子品番'] = code_split[1].fillna('')
    else:
        result_df['子品番'] = ''
        
    result_df['重量設定'] = ship_weight_col
    result_df['タイトル'] = name_col
    result_df['カテゴリ'] = result_df.get('auc-category', '')
    result_df['ストア内商品検索用キーワード'] = result_df.get('auc-store-keyword', '')

    if store_type == "競り3（3号店・送料込み）":
        def calculate_shipping(weight):
            if weight == 0: return 770
            elif weight == 100: return 1100
            elif weight == 1: return 1650
            elif weight == 1000: return 3850
            else: return 0
        shipping_cost = ship_weight_col.apply(calculate_shipping)
        result_df['開始価格'] = (price_col + shipping_cost).astype(int)
        
        is_clickpost = (postage_set_col == 6)
        result_df.loc[is_clickpost, '重量設定'] = 6
        result_df.loc[is_clickpost, '開始価格'] = (price_col[is_clickpost] + 185).astype(int)
        
        def get_shipping_suffix(cost):
            if cost == 770: return "VVV"
            elif cost == 1100: return "WWW"
            elif cost == 1650: return "XXX"
            elif cost == 3850: return "YYY"
            elif cost == 185: return "SSS"
            else: return ""
        actual_shipping = shipping_cost.copy()
        actual_shipping[is_clickpost] = 185
        result_df['suffix'] = actual_shipping.apply(get_shipping_suffix)
    else:
        result_df['開始価格'] = price_col.astype(int)
        is_clickpost = (postage_set_col == 6)
        result_df.loc[is_clickpost, '重量設定'] = 6
        result_df.loc[is_clickpost, 'タイトル'] = "送料185円 " + name_col[is_clickpost]
        result_df['suffix'] = ""

    result_df['即決価格'] = result_df['開始価格']
    result_df['開始価格'] = result_df['即決価格'] - 10
    result_df['個数'] = 10
    result_df['期間'] = 7
    result_df['終了時間'] = 0
    result_df['商品発送元の都道府県'] = '千葉県'
    result_df['商品発送元の市区町村'] = '木更津市'
    result_df['送料負担'] = '落札者'
    result_df['代金先払い、後払い'] = '代金先払い'
    result_df['商品の状態'] = '未使用'
    
    html_template = '<CENTER><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/960.jpg"></CENTER><BR><TABLE BORDER="1" WIDTH="100%" CELLPADDING="8" CELLSPACING="0" BORDERCOLOR="#D4AF37"><TR><TD COLSPAN="2" BGCOLOR="#B40000" ALIGN="LEFT"><FONT COLOR="#FFFFFF" ><B>適合情報</B></FONT></TD></TR><TR><TD WIDTH="25%" BGCOLOR="#FFF4D6" ALIGN="LEFT"><B>メーカー</B></TD><TD ALIGN="LEFT">【メーカー】<BR></TD></TR><TR><TD BGCOLOR="#FFF4D6" ALIGN="LEFT"><B>車種</B></TD><TD ALIGN="LEFT">【適合車種】<BR></TD></TR><TR ><TD BGCOLOR="#FFF4D6" ALIGN="LEFT"><B>対応純正品番</B></TD><TD ALIGN="LEFT">【純正品番】<BR></TD></TR></TABLE><FONT SIZE=2 COLOR=#666666>※上記車種にグレードや型式記載されている場合でも、年式・仕様等により適合しない場合がございます。<BR>※必ず実車に取付されている純正品番をご確認ください。<BR>★ブランド情報や商品詳細など、下記【商品説明】をご確認ください★</FONT><CENTER><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/6month.jpg"><BR><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/tekigou.jpg"><BR><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/iso.jpg"></CENTER>'
    
    output_rows = []
    skipped_count = 0
    
    for p_code, group in result_df.groupby('親品番', sort=False, dropna=False):
        group_len = len(group)
        is_title_over_50 = group_len > 50
        
        if not is_title_over_50:
            for seq, (idx, row) in enumerate(group.iterrows(), start=1):
                out_row = row.copy()
                p_str = str(p_code) if pd.notna(p_code) else ''
                
                if store_type == "競り3（3号店・送料込み）":
                    suf = out_row.get('suffix', '')
                    base_code = f"{p_str}{suf}"
                    L = len(base_code)
                    if p_str == '':
                        out_row['管理番号'] = ""
                    elif L + 4 <= 20:
                        out_row['管理番号'] = f"{base_code}-Y{seq:02d}"
                    elif L + 2 <= 20:
                        alpha = chr(64 + seq) if seq <= 26 and seq > 0 else chr(64 + ((seq - 1) % 26 + 1))
                        out_row['管理番号'] = f"{base_code}-{alpha}"
                    else:
                        skipped_count += 1
                        continue
                else:
                    if p_str != '':
                        out_row['管理番号'] = f"{p_str}-Y{seq:02d}"
                    else:
                        out_row['管理番号'] = ""
                        
                add1 = str(out_row.get('additional1', ''))
                target_block_start = ""
                if "【商品詳細】" in add1:
                    after_detail = add1.split("【商品詳細】", 1)[1]
                    find_idx = after_detail.find("●適合車種")
                    if find_idx != -1:
                        target_block_start = after_detail[find_idx:]
                else:
                    find_idx = add1.rfind("●適合車種")
                    if find_idx != -1:
                        target_block_start = add1[find_idx:]
                        
                extracted_lines = []
                maker_name_ext = ""
                if target_block_start:
                    import re
                    end_pattern = re.compile(r'(※|<A\b)', flags=re.IGNORECASE)
                    end_match = end_pattern.search(target_block_start)
                    block_content = target_block_start[:end_match.start()] if end_match else target_block_start
                    lines_arr = re.split(r'<\s*br\s*[^>]*>', block_content, flags=re.IGNORECASE)
                    
                    if len(lines_arr) >= 3:
                        maker_name_ext = re.sub(r'<[^>]+>', '', lines_arr[1]).strip()
                        for line_str in lines_arr[2:]:
                            line_clean = re.sub(r'<[^>]+>', '', line_str).strip()
                            if line_clean:
                                extracted_lines.append(line_clean)
                                
                compressed_str = "\n".join(extracted_lines)
                
                html = html_template
                
                is_clickpost_row = False
                try:
                    if int(float(out_row.get('postage-set', 0))) == 6:
                        is_clickpost_row = True
                except (ValueError, TypeError):
                    pass
                    
                if "14週間" in add1:
                    html = html.replace('<CENTER><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/6month.jpg">', '<CENTER><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/14day.jpg">')
                
                current_tekigou = '<BR><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/tekigou.jpg">'
                if "parts010.gif" in add1 or "supplies" in add1:
                    new_tekigou = '<BR><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/tekigou2.jpg">'
                    html = html.replace(current_tekigou, new_tekigou)
                    current_tekigou = new_tekigou
                    
                if is_clickpost_row:
                    html = html.replace(current_tekigou, current_tekigou + '<BR><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/YO-post.jpg">')
                    
                import re
                
                match_center = re.search(r"<\s*center\s*>(.*?)<\s*/center\s*>", add1, flags=re.IGNORECASE | re.DOTALL)
                if match_center:
                    center_inner = match_center.group(1)
                    img_matches = list(re.finditer(r"<\s*img\b[^>]*>", center_inner, flags=re.IGNORECASE))
                    if len(img_matches) >= 3:
                        second_img_end = img_matches[1].end()
                        extracted_images = center_inner[second_img_end:]
                        extracted_images = re.sub(r"(?i)(?:<\s*br\s*[^>]*>|\s)+$", "", extracted_images)
                        
                        match_last_center = list(re.finditer(r"<\s*/center\s*>", html, flags=re.IGNORECASE))
                        if match_last_center:
                            last_center_idx = match_last_center[-1].start()
                            html = html[:last_center_idx] + extracted_images + html[last_center_idx:]

                match_parts = re.search(r"●純正品番.*?<\s*br\s*[^>]*>([\x00-\x7F\xA1-\xDF]*)", add1, flags=re.IGNORECASE | re.DOTALL)
                parts_exists = False
                if match_parts:
                    ext_parts = match_parts.group(1)
                    ext_parts = re.sub(r"(?i)^(?:<\s*br\s*[^>]*>|\s)+", "", ext_parts)
                    ext_parts = re.sub(r"(?i)(?:<\s*br\s*[^>]*>|\s)+$", "", ext_parts)
                    if ext_parts and ext_parts not in ["-", "－"]:
                        parts_exists = True
                        html = html.replace('【純正品番】', ext_parts)
                if not parts_exists:
                    html = re.sub(r"<\s*tr[^>]*>(?:(?!<\s*/?tr[^>]*>).)*?【純正品番】.*?<\s*/tr\s*>", "", html, flags=re.IGNORECASE | re.DOTALL)
                    
                clean_maker = ""
                for m in MAKER_LIST:
                    if m in add1:
                        clean_maker = "ダイハツ" if m == "DAIHATSU" else "メルセデス・ベンツ" if m == "メルセデスベンツ" else m
                        break
                        
                html_cars = compressed_str.replace('\n', '<BR>') if compressed_str else ""
                
                match_desc = re.search(r"(【商品詳細】.*)", add1, flags=re.IGNORECASE | re.DOTALL)
                if match_desc:
                    extracted_detail = match_desc.group(1)
                else:
                    if "●適合車種" in add1:
                        idx = add1.rfind("●適合車種")
                        extracted_detail = add1[idx:]
                    else:
                        extracted_detail = ""
                        
                search_link_block = f'<A HREF=https://auctions.yahoo.co.jp/seller/CYWC2j57DBqjcNEscUthj1EQCzRbG?p={clean_maker}&b=1&n=50&select=23 TARGET=new>その他{clean_maker}対応パーツはこちら</A><BR><BR><A HREF=https://auctions.yahoo.co.jp/seller/CYWC2j57DBqjcNEscUthj1EQCzRbG?b=1&is_postage_mode=1&n=50&select=23 TARGET=new>【当店ストアページ】</A>より、お探しの車種や純正品番からも検索いただけます！<BR><BR> <BR>'
                
                html_display_maker = maker_name_ext if maker_name_ext else clean_maker
                new_block_full = (
                    f"<B>●適合車種</B><BR>"
                    f"{html_display_maker}<BR>"
                    f"{html_cars}<BR>"
                    f"※上記車種にグレードや型式記載されている場合でも、年式・仕様等により適合しない場合が御座います。必ず実車に取付されている純正品番をご確認の上ご注文お願いします。<BR><BR>"
                    f"{search_link_block}"
                )
                
                extracted_detail = re.sub(
                    r"(?:<\s*b\s*>\s*)?●適合車種.*?ご注文お願いします。(?:<\s*br\s*[^>]*>\s*)*",
                    new_block_full,
                    extracted_detail,
                    flags=re.IGNORECASE | re.DOTALL
                )
                    
                html = html + extracted_detail
                
                if clean_maker:
                    html = html.replace('【メーカー】', html_display_maker)
                    
                html_cars = compressed_str.replace('\n', '<BR>') if compressed_str else ""
                html = html.replace('【適合車種】', html_cars)
                html = re.sub(r"(?i)(?:<\s*br\s*[^>]*>\s*){4}", "<BR><BR>", html)
                
                # 保証案内の追加
                if store_type == "競り3（3号店・送料込み）":
                    guarantee_url = "https://store.shopping.yahoo.co.jp/solltd3/solpage01.html"
                else:
                    guarantee_url = "https://store.shopping.yahoo.co.jp/solltd/solpage01.html"
                html = html + f"<B>●保証について</B><BR>保証内容はご購入頂いた商品のみとなります。<BR>当社では初期不良、商品保証期間で対応が異なります。<BR><B><A HREF={guarantee_url} TARGET=new>コチラ</A></B>をご一読ください。 <BR> <BR>"
                
                html = html.replace('\n', '').replace('\r', '')
                out_row['説明'] = html
                
                prod_match = re.search(r"●商品説明.*?<\s*br\s*[^>]*>(.*?)(?:<\s*br\s*[^>]*>|$)", add1, flags=re.IGNORECASE)
                product_name = ""
                if prod_match:
                    product_name = prod_match.group(1).strip()
                    product_name = re.sub(r"<[^>]+>", "", product_name)
                    product_name = re.sub(r"リビルト|新品|[【】\[\]「」『』]", "", product_name).strip()
                    product_name = re.sub(r"\s+", " ", product_name).strip()
                    
                img_car_str = compressed_str.replace('\n', ' ') if compressed_str else ""
                img_car_str = re.sub(r"\s+", " ", img_car_str).strip()
                maker_prod_parts = [p for p in [clean_maker, product_name] if p]
                maker_prod_str = " ".join(maker_prod_parts)
                
                final_comment = ""
                if get_width(maker_prod_str) > 20.0:
                    final_comment = truncate_text(maker_prod_str, 20.0)
                else:
                    if img_car_str:
                        car_blocks = img_car_str.split(" ")
                        while len(car_blocks) > 0:
                            current_car = " ".join(car_blocks)
                            parts = [p for p in [clean_maker, current_car, product_name] if p]
                            test_comment = " ".join(parts)
                            if get_width(test_comment) <= 20.0:
                                final_comment = test_comment
                                break
                            car_blocks.pop()
                        if not final_comment:
                            final_comment = maker_prod_str
                    else:
                        final_comment = maker_prod_str
                        
                for i in range(1, 11):
                    out_row[f'画像{i}コメント'] = final_comment
                    
                out_row['最低評価'] = 0
                out_row['悪評割合制限'] = 'はい'
                out_row['入札者認証制限'] = 'いいえ'
                out_row['自動延長'] = 'いいえ'
                out_row['商品の自動再出品'] = 3
                out_row['注目のオークション'] = 0
                out_row['消費税設定'] = 10
                out_row['税込みフラグ'] = 'はい'
                out_row['商品保存先フォルダパス'] = '新規作成中'
                out_row['配送グループ'] = 1
                out_row['発送までの日数'] = 4
                
                output_rows.append(out_row)

        else:
            extracted_lines_all = []
            
            for _, row in group.iterrows():
                add1 = str(row.get('additional1', ''))
                target_block_start = ""
                if "【商品詳細】" in add1:
                    after_detail = add1.split("【商品詳細】", 1)[1]
                    idx = after_detail.find("●適合車種")
                    if idx != -1:
                        target_block_start = after_detail[idx:]
                else:
                    idx = add1.rfind("●適合車種")
                    if idx != -1:
                        target_block_start = add1[idx:]
                        
                if target_block_start:
                    import re
                    end_pattern = re.compile(r'(※|<A\b)', flags=re.IGNORECASE)
                    end_match = end_pattern.search(target_block_start)
                    block_content = target_block_start[:end_match.start()] if end_match else target_block_start
                        
                    lines_arr = re.split(r'<\s*br\s*[^>]*>', block_content, flags=re.IGNORECASE)
                    
                    if len(lines_arr) >= 3:
                        raw_maker = re.sub(r'<[^>]+>', '', lines_arr[1]).strip()
                        html_maker_ext = raw_maker
                        for line_str in lines_arr[2:]:
                            line_clean = re.sub(r'<[^>]+>', '', line_str).strip()
                            if line_clean:
                                if "ベンツ" in html_maker_ext or "メルセデス" in html_maker_ext:
                                    match_code = re.search(r'[A-Za-z]\d{3}', line_clean)
                                    if match_code:
                                        line_clean = match_code.group(0).upper()
                                extracted_lines_all.append((html_maker_ext, line_clean))
            
            grouped_for_merge = {}
            for maker, line_str in extracted_lines_all:
                import re
                parts = re.split(r'[ 　]+', line_str, maxsplit=1)
                car_name = parts[0]
                model_name = parts[1] if len(parts) > 1 else ""
                
                key = (maker, car_name)
                if key not in grouped_for_merge:
                    grouped_for_merge[key] = []
                if model_name and model_name not in grouped_for_merge[key]:
                    grouped_for_merge[key].append(model_name)
                    
            unique_lines = []
            for (maker, car_name), models in grouped_for_merge.items():
                if models:
                    merged_line = f"{car_name} " + " ".join(models)
                else:
                    merged_line = car_name
                unique_lines.append((maker, merged_line))
            elements = unique_lines
            
            raw_title = str(group.iloc[0].get('name', ''))
            
            brand_prefix = ""
            first_maker_pos = -1
            for m in MAKER_LIST:
                pos = raw_title.find(m)
                if pos != -1:
                    if first_maker_pos == -1 or pos < first_maker_pos:
                        first_maker_pos = pos
                        
            if first_maker_pos > 0:
                brand_prefix = raw_title[:first_maker_pos].strip()
                raw_title = raw_title[first_maker_pos:]
                
            for m in MAKER_LIST:
                raw_title = raw_title.replace(m, "")
            for _, line_str in elements:
                import re
                parts = re.split(r'[ 　]+', line_str)
                for p in parts:
                    raw_title = raw_title.replace(p, "")
            base_title = re.sub(r"\s+", " ", raw_title).strip()

            if len(elements) > 50:
                grouped_by_maker = {}
                for maker, line_str in elements:
                    if maker not in grouped_by_maker:
                        grouped_by_maker[maker] = []
                    grouped_by_maker[maker].append(line_str)
                
                level2_elements = []
                for maker, lines_group in grouped_by_maker.items():
                    for i in range(0, len(lines_group), 3):
                        combined_lines = lines_group[i:i+3]
                        level2_elements.append((maker, combined_lines))
                        
                if len(level2_elements) <= 50:
                    elements = level2_elements
                else:
                    level3_elements = []
                    for maker, lines_group in grouped_by_maker.items():
                        level3_elements.append((maker, lines_group))
                        
                    if len(level3_elements) <= 50:
                        elements = level3_elements
                    else:
                        level4_lines = []
                        for maker, lines_group in grouped_by_maker.items():
                            level4_lines.append(maker)
                            level4_lines.extend(lines_group)
                        elements = [("COMBINED", level4_lines)]
            else:
                elements = [(maker, [line_str]) for maker, line_str in elements]
                
            if not elements:
                elements = [(None, [])]
                
            for seq, (maker, lines_list) in enumerate(elements, start=1):
                row_idx = seq - 1 if (seq - 1) < len(group) else len(group) - 1
                out_row = group.iloc[row_idx].copy()
                
                p_str = str(p_code) if pd.notna(p_code) else ''
                
                if store_type == "競り3（3号店・送料込み）":
                    suf = out_row.get('suffix', '')
                    base_code = f"{p_str}{suf}"
                    L = len(base_code)
                    if p_str == '':
                        out_row['管理番号'] = ""
                    elif L + 4 <= 20:
                        out_row['管理番号'] = f"{base_code}-Y{seq:02d}"
                    elif L + 2 <= 20:
                        alpha = chr(64 + seq) if seq <= 26 and seq > 0 else chr(64 + ((seq - 1) % 26 + 1))
                        out_row['管理番号'] = f"{base_code}-{alpha}"
                    else:
                        skipped_count += 1
                        continue
                else:
                    if p_str != '':
                        out_row['管理番号'] = f"{p_str}-Y{seq:02d}"
                    else:
                        out_row['管理番号'] = ""
                        
                compressed_str = "\n".join(lines_list)
                
                import re
                
                clean_title_maker = ""
                if maker is not None and maker != "COMBINED":
                    clean_title_maker = re.sub(r'[ /A-Za-zａ-ｚＡ-Ｚ]+', '', maker).strip()
                
                title_parts = []
                if brand_prefix:
                    title_parts.append(brand_prefix)
                if clean_title_maker:
                    title_parts.append(clean_title_maker)
                
                prefix = " ".join(title_parts)
                if prefix:
                    prefix += " "
                    
                car_str_part = compressed_str.replace('\n', ' ')
                car_str_part = re.sub(r"\s+", " ", car_str_part).strip()
                
                def build_title(cars):
                    mid = f"{cars} " if cars else ""
                    return f"{prefix}{mid}{base_title}".strip()
                
                test_title = build_title(car_str_part)
                
                if len(test_title) <= 65:
                    final_title = test_title
                else:
                    car_blocks = car_str_part.split(" ") if car_str_part else []
                    min_len = min(2, len(car_blocks))
                    
                    while len(car_blocks) > min_len:
                        car_blocks.pop()
                        current_cars = " ".join(car_blocks)
                        if len(build_title(current_cars)) <= 65:
                            break
                    
                    final_title = build_title(" ".join(car_blocks))
                    if len(final_title) > 65:
                        current_cars = " ".join(car_blocks)
                        mid = f"{current_cars} " if current_cars else ""
                        
                        import re
                        base_blocks = re.split(r'[ 　]+', base_title)
                        while len(base_blocks) > 0:
                            base_blocks.pop()
                            current_base = " ".join(base_blocks)
                            test_t = f"{prefix}{mid}{current_base}".strip()
                            if len(test_t) <= 65 and len(test_t) > 0:
                                final_title = test_t
                                break
                        else:
                            final_title = f"{prefix}{mid}"[:65].strip()
                
                out_row['タイトル'] = final_title
                
                add1 = str(out_row.get('additional1', ''))
                html = html_template
                
                is_clickpost_row = False
                try:
                    if int(float(out_row.get('postage-set', 0))) == 6:
                        is_clickpost_row = True
                except (ValueError, TypeError):
                    pass
                
                if "14週間" in add1:
                    html = html.replace('<CENTER><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/6month.jpg">', '<CENTER><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/14day.jpg">')
                
                current_tekigou = '<BR><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/tekigou.jpg">'
                if "parts010.gif" in add1 or "supplies" in add1:
                    new_tekigou = '<BR><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/tekigou2.jpg">'
                    html = html.replace(current_tekigou, new_tekigou)
                    current_tekigou = new_tekigou
                    
                if is_clickpost_row:
                    html = html.replace(current_tekigou, current_tekigou + '<BR><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/YO-post.jpg">')
                    
                import re
                
                match_center = re.search(r"<\s*center\s*>(.*?)<\s*/center\s*>", add1, flags=re.IGNORECASE | re.DOTALL)
                if match_center:
                    center_inner = match_center.group(1)
                    img_matches = list(re.finditer(r"<\s*img\b[^>]*>", center_inner, flags=re.IGNORECASE))
                    if len(img_matches) >= 3:
                        second_img_end = img_matches[1].end()
                        extracted_images = center_inner[second_img_end:]
                        extracted_images = re.sub(r"(?i)(?:<\s*br\s*[^>]*>|\s)+$", "", extracted_images)
                        
                        match_last_center = list(re.finditer(r"<\s*/center\s*>", html, flags=re.IGNORECASE))
                        if match_last_center:
                            last_center_idx = match_last_center[-1].start()
                            html = html[:last_center_idx] + extracted_images + html[last_center_idx:]

                match_parts = re.search(r"●純正品番.*?<\s*br\s*[^>]*>([\x00-\x7F\xA1-\xDF]*)", add1, flags=re.IGNORECASE | re.DOTALL)
                parts_exists = False
                if match_parts:
                    ext_parts = match_parts.group(1)
                    ext_parts = re.sub(r"(?i)^(?:<\s*br\s*[^>]*>|\s)+", "", ext_parts)
                    ext_parts = re.sub(r"(?i)(?:<\s*br\s*[^>]*>|\s)+$", "", ext_parts)
                    if ext_parts and ext_parts not in ["-", "－"]:
                        parts_exists = True
                        html = html.replace('【純正品番】', ext_parts)
                if not parts_exists:
                    html = re.sub(r"<\s*tr[^>]*>(?:(?!<\s*/?tr[^>]*>).)*?【純正品番】.*?<\s*/tr\s*>", "", html, flags=re.IGNORECASE | re.DOTALL)
                    
                target_block_start = ""
                if "【商品詳細】" in add1:
                    after_detail = add1.split("【商品詳細】", 1)[1]
                    find_idx = after_detail.find("●適合車種")
                    if find_idx != -1:
                        target_block_start = after_detail[find_idx:]
                else:
                    find_idx = add1.rfind("●適合車種")
                    if find_idx != -1:
                        target_block_start = add1[find_idx:]
                        
                block_content = ""
                if target_block_start:
                    end_pattern = re.compile(r'(※|<A\b)', flags=re.IGNORECASE)
                    end_match = end_pattern.search(target_block_start)
                    block_content = target_block_start[:end_match.start()] if end_match else target_block_start

                clean_maker = ""
                for m in MAKER_LIST:
                    if m in add1:
                        clean_maker = "ダイハツ" if m == "DAIHATSU" else "メルセデス・ベンツ" if m == "メルセデスベンツ" else m
                        break
                        
                html_cars = compressed_str.replace('\n', '<BR>') if compressed_str else ""
                
                match_desc = re.search(r"(【商品詳細】.*)", add1, flags=re.IGNORECASE | re.DOTALL)
                if match_desc:
                    extracted_detail = match_desc.group(1)
                else:
                    if "●適合車種" in add1:
                        idx = add1.rfind("●適合車種")
                        extracted_detail = add1[idx:]
                    else:
                        extracted_detail = ""
                        
                search_link_block = f'<A HREF=https://auctions.yahoo.co.jp/seller/CYWC2j57DBqjcNEscUthj1EQCzRbG?p={clean_maker}&b=1&n=50&select=23 TARGET=new>その他{clean_maker}対応パーツはこちら</A><BR><BR><A HREF=https://auctions.yahoo.co.jp/seller/CYWC2j57DBqjcNEscUthj1EQCzRbG?b=1&is_postage_mode=1&n=50&select=23 TARGET=new>【当店ストアページ】</A>より、お探しの車種や純正品番からも検索いただけます！<BR><BR> <BR>'
                
                html_display_maker = maker if (maker is not None and maker != "COMBINED") else clean_maker
                new_block_full = (
                    f"<B>●適合車種</B><BR>"
                    f"{html_display_maker}<BR>"
                    f"{html_cars}<BR>"
                    f"※上記車種にグレードや型式記載されている場合でも、年式・仕様等により適合しない場合が御座います。必ず実車に取付されている純正品番をご確認の上ご注文お願いします。<BR><BR>"
                    f"{search_link_block}"
                )
                
                extracted_detail = re.sub(
                    r"(?:<\s*b\s*>\s*)?●適合車種.*?ご注文お願いします。(?:<\s*br\s*[^>]*>\s*)*",
                    new_block_full,
                    extracted_detail,
                    flags=re.IGNORECASE | re.DOTALL
                )
                    
                html = html + extracted_detail
                
                if clean_maker:
                    html = html.replace('【メーカー】', html_display_maker)
                    
                html_cars = compressed_str.replace('\n', '<BR>') if compressed_str else ""
                html = html.replace('【適合車種】', html_cars)
                
                html = re.sub(r"(?i)(?:<\s*br\s*[^>]*>\s*){4}", "<BR><BR>", html)
                
                # 保証案内の追加
                if store_type == "競り3（3号店・送料込み）":
                    guarantee_url = "https://store.shopping.yahoo.co.jp/solltd3/solpage01.html"
                else:
                    guarantee_url = "https://store.shopping.yahoo.co.jp/solltd/solpage01.html"
                html = html + f"<B>●保証について</B><BR>保証内容はご購入頂いた商品のみとなります。<BR>当社では初期不良、商品保証期間で対応が異なります。<BR><B><A HREF={guarantee_url} TARGET=new>コチラ</A></B>をご一読ください。 <BR> <BR>"
                
                html = html.replace('\n', '').replace('\r', '')
                out_row['説明'] = html
                
                prod_match = re.search(r"●商品説明.*?<\s*br\s*[^>]*>(.*?)(?:<\s*br\s*[^>]*>|$)", add1, flags=re.IGNORECASE)
                product_name = ""
                if prod_match:
                    product_name = prod_match.group(1).strip()
                    product_name = re.sub(r"<[^>]+>", "", product_name)
                    product_name = re.sub(r"リビルト|新品|[【】\[\]「」『』]", "", product_name).strip()
                    product_name = re.sub(r"\s+", " ", product_name).strip()
                    
                img_car_str = compressed_str.replace('\n', ' ') if compressed_str else ""
                img_car_str = re.sub(r"\s+", " ", img_car_str).strip()
                
                maker_prod_parts = [p for p in [clean_maker, product_name] if p]
                maker_prod_str = " ".join(maker_prod_parts)
                
                final_comment = ""
                if get_width(maker_prod_str) > 20.0:
                    final_comment = truncate_text(maker_prod_str, 20.0)
                else:
                    if img_car_str:
                        car_blocks = img_car_str.split(" ")
                        while len(car_blocks) > 0:
                            current_car = " ".join(car_blocks)
                            parts = [p for p in [clean_maker, current_car, product_name] if p]
                            test_comment = " ".join(parts)
                            if get_width(test_comment) <= 20.0:
                                final_comment = test_comment
                                break
                            car_blocks.pop()
                        if not final_comment:
                            final_comment = maker_prod_str
                    else:
                        final_comment = maker_prod_str
                        
                for i in range(1, 11):
                    out_row[f'画像{i}コメント'] = final_comment
                    
                out_row['最低評価'] = 0
                out_row['悪評割合制限'] = 'はい'
                out_row['入札者認証制限'] = 'いいえ'
                out_row['自動延長'] = 'いいえ'
                out_row['商品の自動再出品'] = 3
                out_row['注目のオークション'] = 0
                out_row['消費税設定'] = 10
                out_row['税込みフラグ'] = 'はい'
                out_row['商品保存先フォルダパス'] = '新規作成中'
                out_row['配送グループ'] = 1
                out_row['発送までの日数'] = 4
                
                output_rows.append(out_row)

    final_result_df = pd.DataFrame(output_rows)
    
    if image_settings:
        for col_name, val in image_settings.items():
            if val.strip():
                final_result_df[col_name] = val

    # 画像コメントクリーンアップ処理
    for i in range(1, 11):
        img_col = f"画像{i}"
        comment_col = f"画像{i}コメント"
        if comment_col in final_result_df.columns:
            if img_col in final_result_df.columns:
                is_empty = final_result_df[img_col].fillna("").astype(str).str.strip() == ""
                final_result_df.loc[is_empty, comment_col] = ""
            else:
                final_result_df[comment_col] = ""
                
    expected_columns = [
        "管理番号", "カテゴリ", "タイトル", "説明", "ストア内商品検索用キーワード", 
        "開始価格", "即決価格", "個数", "期間", "終了時間", 
        "商品発送元の都道府県", "商品発送元の市区町村", "送料負担", "代金先払い、後払い", "商品の状態", 
        "画像1", "画像1コメント", "画像2", "画像2コメント", "画像3", "画像3コメント", 
        "画像4", "画像4コメント", "画像5", "画像5コメント", "画像6", "画像6コメント", 
        "画像7", "画像7コメント", "画像8", "画像8コメント", "画像9", "画像9コメント", 
        "画像10", "画像10コメント", "最低評価", "悪評割合制限", "入札者認証制限", "自動延長", 
        "商品の自動再出品", "自動値下げ", "注目のオークション", "重量設定", "消費税設定", 
        "税込みフラグ", "JANコード・ISBNコード", "ブランドID", "商品スペックサイズ種別", 
        "商品スペックサイズID", "商品分類ID", "商品保存先フォルダパス", "配送グループ", "発送までの日数"
    ]
    
    for col in expected_columns:
        if col not in final_result_df.columns:
            final_result_df[col] = ""
            
    final_df = final_result_df[expected_columns].copy()
    
    return final_df, skipped_count
