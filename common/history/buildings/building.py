import re
import os

def find_matching_brace(s, start_idx):
    assert s[start_idx] == '{'
    depth = 0
    for i in range(start_idx, len(s)):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                return i
    return -1

def normalize_region_token(token):
    m = re.match(r's:([A-Z0-9_]+)', token)
    return m.group(1) if m else token

def infer_country_from_region_state(region_state_header):
    m = re.search(r'region_state\s*:\s*([A-Z0-9_]+)', region_state_header)
    if m:
        return m.group(1)
    return "USA"

def build_add_ownership_snippet(country_token, levels, region_name, indent):
    snippet_lines = [
        indent + 'add_ownership={',
        indent + '\tbuilding={',
        indent + '\t\ttype="building_financial_district"',
        indent + f'\t\tcountry="c:{country_token}"',
        indent + f'\t\tlevels={levels}',
        indent + f'\t\tregion="{region_name}"',
        indent + '\t}',
        indent + '}'
    ]
    return '\n'.join(snippet_lines)

def process_text(text):
    out = []
    L = len(text)
    region_pattern = re.compile(r'(^|\n)\s*(s:STATE_[A-Z0-9_]+)\s*=\s*\{', re.MULTILINE)

    last_end = 0
    for region_match in region_pattern.finditer(text):
        out.append(text[last_end:region_match.start(2)])
        region_token = region_match.group(2)
        region_name = normalize_region_token(region_token)
        brace_open_idx = text.find('{', region_match.end(2))
        if brace_open_idx == -1:
            out.append(text[region_match.start(2):region_match.end(2)])
            last_end = region_match.end(2)
            continue
        brace_close_idx = find_matching_brace(text, brace_open_idx)
        if brace_close_idx == -1:
            out.append(text[region_match.start(2):])
            last_end = L
            break

        region_block = text[region_match.start(2):brace_close_idx+1]
        rs_pattern = re.compile(r'(region_state\s*:\s*[A-Z0-9_]+\s*=\s*\{)', re.MULTILINE)
        rs_matches = list(rs_pattern.finditer(region_block))
        if not rs_matches:
            processed_region_block = process_region_state_block(region_block, region_name, None)
        else:
            processed_region_block = ""
            last_rs_end = 0
            for rs_match in rs_matches:
                processed_region_block += region_block[last_rs_end:rs_match.start(1)]
                rs_brace_open = region_block.find('{', rs_match.end(1)-1)
                if rs_brace_open == -1:
                    processed_region_block += region_block[rs_match.start(1):rs_match.end(1)]
                    last_rs_end = rs_match.end(1)
                    continue
                rs_brace_close = find_matching_brace(region_block, rs_brace_open)
                if rs_brace_close == -1:
                    processed_region_block += region_block[rs_match.start(1):]
                    last_rs_end = len(region_block)
                    break
                rs_block = region_block[rs_match.start(1):rs_brace_close+1]
                processed_rs_block = process_region_state_block(rs_block, region_name, rs_block)
                processed_region_block += processed_rs_block
                last_rs_end = rs_brace_close+1
            processed_region_block += region_block[last_rs_end:]
        out.append(processed_region_block)
        last_end = brace_close_idx+1

    out.append(text[last_end:])
    return ''.join(out)

def process_region_state_block(rs_text, top_region_name, rs_block_text_for_country):
    hdr_search = re.search(r'region_state\s*:\s*([A-Z0-9_]+)', rs_text)
    country_token = hdr_search.group(1) if hdr_search else "USA"

    out = []
    last = 0
    cb_pattern = re.compile(r'(\s*)(create_building\s*=\s*\{)', re.MULTILINE)
    for cb_match in cb_pattern.finditer(rs_text):
        out.append(rs_text[last:cb_match.start(0)])
        
        base_indent = cb_match.group(1)
        content_indent = base_indent + '\t'
        
        brace_open = rs_text.find('{', cb_match.end(2)-1)
        if brace_open == -1:
            out.append(rs_text[cb_match.start(0):cb_match.end(0)])
            last = cb_match.end(0)
            continue
        brace_close = find_matching_brace(rs_text, brace_open)
        if brace_close == -1:
            out.append(rs_text[cb_match.start(0):])
            last = len(rs_text)
            break
        cb_block = rs_text[cb_match.start(0):brace_close+1]

        if re.search(r'\badd_ownership\s*=', cb_block):
            out.append(cb_block)
            last = brace_close+1
            continue

        m_levels = re.search(r'\blevels?\s*=\s*([0-9]+)', cb_block)
        levels_val = m_levels.group(1) if m_levels else '1'

        cb_block_no_levels = re.sub(r'^\s*levels?\s*=\s*[0-9]+\s*\n?', '', cb_block, flags=re.MULTILINE)
        
        ownership_snippet = build_add_ownership_snippet(country_token, levels_val, top_region_name, content_indent)
        
        pattern = re.compile(
            r'(?P<before>.*?)(?P<bld_line>^\s*building\s*=\s*"[^"]+"[ \t]*\n)(?P<after>.*)',
            re.MULTILINE | re.DOTALL
        )
        match = pattern.search(cb_block_no_levels)
        
        if match:
            before = match.group('before')
            bld_line = match.group('bld_line')
            after = match.group('after')
            modified_cb_block = f"{before}{bld_line}{ownership_snippet}\n{after}"
        else:
            closing_brace_pos = cb_block_no_levels.rfind('}')
            block_content_before_brace = cb_block_no_levels[:closing_brace_pos].rstrip()
            modified_cb_block = f"{block_content_before_brace}\n{ownership_snippet}\n{base_indent}}}"

        out.append(modified_cb_block)
        last = brace_close + 1

    out.append(rs_text[last:])
    return ''.join(out)

if __name__ == '__main__':
    input_filepath = "14_siberia.txt" 
    base, ext = os.path.splitext(input_filepath)
    output_filepath = f"{base}_owned{ext}"

    print(f"Reading from: {input_filepath}")
    
    with open(input_filepath, 'r', encoding='utf-8') as infile:
        original_text = infile.read()

    modified_text = process_text(original_text)

    with open(output_filepath, 'w', encoding='utf-8') as outfile:
        outfile.write(modified_text)

    print(f"Processing complete. Output written to: {output_filepath}")