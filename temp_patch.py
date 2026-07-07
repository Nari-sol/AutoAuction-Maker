import pandas as pd

with open('converter.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_content = """        group_len = len(group)
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
                    end_pattern = re.compile(r'(※|<A\\b)', flags=re.IGNORECASE)
                    end_match = end_pattern.search(target_block_start)
                    block_content = target_block_start[:end_match.start()] if end_match else target_block_start
                    lines_arr = re.split(r'<\\s*br\\s*[^>]*>', block_content, flags=re.IGNORECASE)
                    
                    if len(lines_arr) >= 3:
                        maker_name_ext = re.sub(r'<[^>]+>', '', lines_arr[1]).strip()
                        for line_str in lines_arr[2:]:
                            line_clean = re.sub(r'<[^>]+>', '', line_str).strip()
                            if line_clean:
                                extracted_lines.append(line_clean)
                                
                compressed_str = "\\n".join(extracted_lines)
                
                html = html_template
                if "14週間" in add1:
                    html = html.replace('<CENTER><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/6month.jpg">', '<CENTER><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/14day.jpg">')
                if "parts010.gif" in add1:
                    html = html.replace('<BR><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/tekigou.jpg">', '<BR><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/tekigou2.jpg">')
                if "supplies" in add1:
                    html = html.replace('<BR><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/tekigou.jpg">', '<BR><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/tekigou2.jpg">')
                    
                import re
                match_parts = re.search(r"●純正品番.*?<\\s*br\\s*[^>]*>([\\x00-\\x7F\\xA1-\\xDF]*)", add1, flags=re.IGNORECASE | re.DOTALL)
                parts_exists = False
                if match_parts:
                    ext_parts = match_parts.group(1)
                    ext_parts = re.sub(r"(?i)^(?:<\\s*br\\s*[^>]*>|\\s)+", "", ext_parts)
                    ext_parts = re.sub(r"(?i)(?:<\\s*br\\s*[^>]*>|\\s)+$", "", ext_parts)
                    if ext_parts and ext_parts not in ["-", "－"]:
                        parts_exists = True
                        html = html.replace('【純正品番】', ext_parts)
                if not parts_exists:
                    html = re.sub(r"<\\s*tr[^>]*>(?:(?!<\\s*/?tr[^>]*>).)*?【純正品番】.*?<\\s*/tr\\s*>", "", html, flags=re.IGNORECASE | re.DOTALL)
                    
                match_desc = re.search(r"(【商品詳細】.*?●適合車種(?:.*?<\\s*br\\s*[^>]*>){4})(.*)", add1, flags=re.IGNORECASE | re.DOTALL)
                if match_desc:
                    html = html + match_desc.group(1)
                    extracted_rest = match_desc.group(2)
                else:
                    extracted_rest = ""
                    
                clean_maker = ""
                for m in MAKER_LIST:
                    if m in add1:
                        clean_maker = "ダイハツ" if m == "DAIHATSU" else "メルセデス・ベンツ" if m == "メルセデスベンツ" else m
                        break
                        
                search_link_block = f'<A HREF=https://auctions.yahoo.co.jp/seller/CYWC2j57DBqjcNEscUthj1EQCzRbG?p={clean_maker}&b=1&n=50&select=23 TARGET=new>その他{clean_maker}対応パーツはこちら</A><BR><BR><A HREF=https://auctions.yahoo.co.jp/seller/CYWC2j57DBqjcNEscUthj1EQCzRbG?b=1&is_postage_mode=1&n=50&select=23 TARGET=new>【当店ストアページ】</A>より、お探しの車種や純正品番からも検索いただけます！<BR><BR> <BR>'
                html = html + search_link_block + extracted_rest
                
                if clean_maker:
                    html = html.replace('【メーカー】', clean_maker)
                    
                html_cars = compressed_str.replace('\\n', '<BR>') if compressed_str else ""
                html = html.replace('【適合車種】', html_cars)
                html = re.sub(r"(?i)(?:<\\s*br\\s*[^>]*>\\s*){4}", "<BR><BR>", html)
                out_row['説明'] = html
                
                prod_match = re.search(r"●商品説明.*?<\\s*br\\s*[^>]*>(.*?)(?:<\\s*br\\s*[^>]*>|$)", add1, flags=re.IGNORECASE)
                product_name = ""
                if prod_match:
                    product_name = prod_match.group(1).strip()
                    product_name = re.sub(r"<[^>]+>", "", product_name)
                    product_name = re.sub(r"リビルト|新品|[【】\\[\\]「」『』]", "", product_name).strip()
                    product_name = re.sub(r"\\s+", " ", product_name).strip()
                    
                img_car_str = compressed_str.replace('\\n', ' ') if compressed_str else ""
                img_car_str = re.sub(r"\\s+", " ", img_car_str).strip()
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
                    end_pattern = re.compile(r'(※|<A\\b)', flags=re.IGNORECASE)
                    end_match = end_pattern.search(target_block_start)
                    block_content = target_block_start[:end_match.start()] if end_match else target_block_start
                        
                    lines_arr = re.split(r'<\\s*br\\s*[^>]*>', block_content, flags=re.IGNORECASE)
                    
                    if len(lines_arr) >= 3:
                        maker_name_ext = re.sub(r'<[^>]+>', '', lines_arr[1]).strip()
                        for line_str in lines_arr[2:]:
                            line_clean = re.sub(r'<[^>]+>', '', line_str).strip()
                            if line_clean:
                                extracted_lines_all.append((maker_name_ext, line_clean))
            
            unique_lines = []
            seen = set()
            for e in extracted_lines_all:
                if e not in seen:
                    seen.add(e)
                    unique_lines.append(e)
            elements = unique_lines
            
            raw_title = str(group.iloc[0].get('name', ''))
            for m in MAKER_LIST:
                raw_title = raw_title.replace(m, "")
            for _, line_str in elements:
                import re
                parts = re.split(r'[ 　]+', line_str)
                for p in parts:
                    raw_title = raw_title.replace(p, "")
            base_title = re.sub(r"\\s+", " ", raw_title).strip()

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
                        
                compressed_str = "\\n".join(lines_list)
                
                title_car_str = ""
                if maker == "COMBINED":
                    title_car_str = compressed_str.replace('\\n', ' ')
                elif maker is not None:
                    title_car_str = f"{maker} {compressed_str.replace(chr(10), ' ')}"
                
                import re
                title_car_str = re.sub(r"\\s+", " ", title_car_str).strip()
                
                final_title = ""
                if title_car_str:
                    test_title = f"{title_car_str} {base_title}".strip()
                    if len(test_title) <= 65:
                        final_title = test_title
                    else:
                        available_len = 65 - len(title_car_str) - 1
                        if available_len > 0:
                            truncated_base = base_title[:available_len].strip()
                            final_title = f"{title_car_str} {truncated_base}"
                        else:
                            final_title = title_car_str[:65]
                else:
                    final_title = base_title[:65]
                
                out_row['タイトル'] = final_title
                
                add1 = str(out_row.get('additional1', ''))
                html = html_template
                
                if "14週間" in add1:
                    html = html.replace('<CENTER><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/6month.jpg">', '<CENTER><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/14day.jpg">')
                if "parts010.gif" in add1:
                    html = html.replace('<BR><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/tekigou.jpg">', '<BR><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/tekigou2.jpg">')
                if "supplies" in add1:
                    html = html.replace('<BR><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/tekigou.jpg">', '<BR><BR><IMG SRC="https://shopping.c.yimg.jp/lib/solltd/tekigou2.jpg">')
                    
                import re
                match_parts = re.search(r"●純正品番.*?<\\s*br\\s*[^>]*>([\\x00-\\x7F\\xA1-\\xDF]*)", add1, flags=re.IGNORECASE | re.DOTALL)
                parts_exists = False
                if match_parts:
                    ext_parts = match_parts.group(1)
                    ext_parts = re.sub(r"(?i)^(?:<\\s*br\\s*[^>]*>|\\s)+", "", ext_parts)
                    ext_parts = re.sub(r"(?i)(?:<\\s*br\\s*[^>]*>|\\s)+$", "", ext_parts)
                    if ext_parts and ext_parts not in ["-", "－"]:
                        parts_exists = True
                        html = html.replace('【純正品番】', ext_parts)
                if not parts_exists:
                    html = re.sub(r"<\\s*tr[^>]*>(?:(?!<\\s*/?tr[^>]*>).)*?【純正品番】.*?<\\s*/tr\\s*>", "", html, flags=re.IGNORECASE | re.DOTALL)
                    
                match_desc = re.search(r"(【商品詳細】.*?●適合車種(?:.*?<\\s*br\\s*[^>]*>){4})(.*)", add1, flags=re.IGNORECASE | re.DOTALL)
                if match_desc:
                    html = html + match_desc.group(1)
                    extracted_rest = match_desc.group(2)
                else:
                    extracted_rest = ""
                    
                clean_maker = ""
                for m in MAKER_LIST:
                    if m in add1:
                        clean_maker = "ダイハツ" if m == "DAIHATSU" else "メルセデス・ベンツ" if m == "メルセデスベンツ" else m
                        break
                        
                search_link_block = f'<A HREF=https://auctions.yahoo.co.jp/seller/CYWC2j57DBqjcNEscUthj1EQCzRbG?p={clean_maker}&b=1&n=50&select=23 TARGET=new>その他{clean_maker}対応パーツはこちら</A><BR><BR><A HREF=https://auctions.yahoo.co.jp/seller/CYWC2j57DBqjcNEscUthj1EQCzRbG?b=1&is_postage_mode=1&n=50&select=23 TARGET=new>【当店ストアページ】</A>より、お探しの車種や純正品番からも検索いただけます！<BR><BR> <BR>'
                html = html + search_link_block + extracted_rest
                
                if clean_maker:
                    html = html.replace('【メーカー】', clean_maker)
                    
                html_cars = compressed_str.replace('\\n', '<BR>') if compressed_str else ""
                html = html.replace('【適合車種】', html_cars)
                
                html = re.sub(r"(?i)(?:<\\s*br\\s*[^>]*>\\s*){4}", "<BR><BR>", html)
                out_row['説明'] = html
                
                prod_match = re.search(r"●商品説明.*?<\\s*br\\s*[^>]*>(.*?)(?:<\\s*br\\s*[^>]*>|$)", add1, flags=re.IGNORECASE)
                product_name = ""
                if prod_match:
                    product_name = prod_match.group(1).strip()
                    product_name = re.sub(r"<[^>]+>", "", product_name)
                    product_name = re.sub(r"リビルト|新品|[【】\\[\\]「」『』]", "", product_name).strip()
                    product_name = re.sub(r"\\s+", " ", product_name).strip()
                    
                img_car_str = compressed_str.replace('\\n', ' ') if compressed_str else ""
                img_car_str = re.sub(r"\\s+", " ", img_car_str).strip()
                
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
"""

lines[101:388] = [new_content + '\\n']

with open('converter.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
