import os
import re
import glob

TARGET_BUILDINGS = {
    "airports",
}

def find_matching_brace(text, start_index):
    if start_index < 0 or start_index >= len(text) or text[start_index] != '{':
        return -1
    depth = 1
    i = start_index + 1
    while i < len(text):
        c = text[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1

def get_indent_before(text, pos):
    line_start = text.rfind('\n', 0, pos) + 1
    j = line_start
    while j < len(text) and text[j] in ('\t', ' '):
        j += 1
    return text[line_start:j]

def extract_top_level_building_name(block_text):
    m = re.search(r'(?m)^\s*building\s*=\s*"([^"]+)"', block_text)
    if m:
        return m.group(1)
    return None

def replace_add_ownership_in_block(block_text):
    changed = False
    details = {"converted": False, "reason": ""}
    m_add = re.search(r'add_ownership\s*=\s*\{', block_text)
    if not m_add:
        return block_text, changed, details
    add_start = m_add.end() - 1
    add_end = find_matching_brace(block_text, add_start)
    if add_end == -1:
        return block_text, changed, details
    add_block = block_text[add_start:add_end+1]
    if re.search(r'(?m)^\s*country\s*=\s*\{', add_block):
        return block_text, changed, details
    m_nested_building = re.search(r'(?m)^\s*building\s*=\s*\{', add_block)
    if not m_nested_building:
        return block_text, changed, details
    nb_start = m_nested_building.end() - 1
    nb_end = find_matching_brace(add_block, nb_start)
    if nb_end == -1:
        return block_text, changed, details
    nested_block = add_block[nb_start:nb_end+1]
    m_country = re.search(r'(?m)^\s*country\s*=\s*"?(c:[A-Z0-9_]+)"?\s*$', nested_block)
    m_levels = re.search(r'(?m)^\s*levels\s*=\s*([0-9]+)\s*$', nested_block)
    if not (m_country and m_levels):
        return block_text, changed, details
    country_code = m_country.group(1)
    levels = m_levels.group(1)
    add_indent = get_indent_before(block_text, m_add.start())
    inner_indent = add_indent + "\t"
    inner_inner_indent = inner_indent + "\t"
    replacement = (
        "{\n"
        f"{inner_indent}country={{\n"
        f"{inner_inner_indent}country=\"{country_code}\"\n"
        f"{inner_inner_indent}levels={levels}\n"
        f"{inner_indent}}}\n"
        f"{add_indent}"
        "}"
    )
    new_add_block = replacement
    new_block_text = block_text[:add_start] + new_add_block + block_text[add_end+1:]
    details["converted"] = True
    changed = True
    return new_block_text, changed, details

def process_file_content(text):
    changes = []
    pattern = re.compile(r'create_building\s*=\s*\{')
    matches = list(pattern.finditer(text))
    for m in reversed(matches):
        cb_open = m.end() - 1
        cb_close = find_matching_brace(text, cb_open)
        if cb_close == -1:
            continue
        block = text[cb_open:cb_close+1]
        top_building = extract_top_level_building_name(block)
        if top_building not in TARGET_BUILDINGS:
            continue
        new_block, changed, details = replace_add_ownership_in_block(block)
        if changed:
            text = text[:cb_open] + new_block + text[cb_close+1:]
            changes.append((top_building, details["reason"]))
    return text, changes

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    txt_files = glob.glob(os.path.join(script_dir, '*.txt'))
    if not txt_files:
        print("No .txt files found in the script's directory.")
        return
    for filepath in txt_files:
        print(f"--- Processing: {os.path.basename(filepath)} ---")
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                original = f.read()
            modified, changes = process_file_content(original)
            if modified != original:
                with open(filepath, 'w', encoding='utf-8-sig') as f:
                    f.write(modified)
                if changes:
                    for btype, reason in changes:
                        print(f"  * {btype}: {reason}")
                print(f"  [SUCCESS] File modified.")
            else:
                print("  No changes needed.")
        except Exception as e:
            print(f"  [ERROR] {e}")
    print("\nScript finished.")

if __name__ == '__main__':
    main()
