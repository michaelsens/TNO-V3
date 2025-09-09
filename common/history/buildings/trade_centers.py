import os
import re
import glob

def find_matching_brace(text, start_index):
    """Finds the matching closing brace for an opening brace."""
    if text[start_index] != '{':
        return -1
    depth = 1
    for i in range(start_index + 1, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return i
    return -1

def create_trade_center_snippet(state_name, country_code, indent):
    """Generates the formatted string for the new trade center building."""
    region_name = state_name.replace('s:', '')
    
    return (
        f'{indent}create_building={{\n'
        f'{indent}\tbuilding="building_trade_center"\n'
        f'{indent}\tadd_ownership={{\n'
        f'{indent}\t\tbuilding={{\n'
        f'{indent}\t\t\ttype="building_financial_district"\n'
        f'{indent}\t\t\tcountry="c:{country_code}"\n'
        f'{indent}\t\t\tlevels=3\n'
        f'{indent}\t\t\tregion="{region_name}"\n'
        f'{indent}\t\t}}\n'
        f'{indent}\t}}\n'
        f'{indent}\tactivate_production_methods={{ "pm_trade_center_trade_quantity_normal" }}\n'
        f'{indent}\treserves=1\n'
        f'{indent}}}'
    )

def process_file_content(text):
    """
    Processes the text content of a file to add trade centers where they are missing.
    Returns the modified text and a list of changes.
    """
    changes_made = []
    
    # We process the file backwards to avoid index shifting issues with insertions
    for match in reversed(list(re.finditer(r'(s:STATE_[A-Z0-9_]+)\s*=\s*\{', text))):
        state_token = match.group(1)
        state_name = state_token.replace('s:', '')
        
        # Find the full scope of the state block
        open_brace_idx = match.end() - 1
        close_brace_idx = find_matching_brace(text, open_brace_idx)
        if close_brace_idx == -1:
            continue # Malformed block, skip it
            
        state_block = text[open_brace_idx : close_brace_idx + 1]
        
        # If a trade center already exists, skip this state
        if 'building="building_trade_center"' in state_block:
            continue
            
        # Find the country and where to insert the new building.
        insertion_point_match = re.search(r'region_state:([A-Z0-9_]+)\s*=\s*\{', state_block)
        
        if insertion_point_match:
            country_code = insertion_point_match.group(1)
            
            # Find the line of the match to determine indentation
            line_start = state_block.rfind('\n', 0, insertion_point_match.start()) + 1
            indent = '\t' + state_block[line_start : insertion_point_match.start()]
            
            # Find the position right after the opening brace '{'
            insertion_offset = insertion_point_match.end()
            
            # Build the new block and insert it
            snippet = create_trade_center_snippet(state_token, country_code, indent)
            new_state_block = f'{state_block[:insertion_offset]}\n{snippet}{state_block[insertion_offset:]}'
            
            # Replace the old state block with the new one in the full text
            text = text[:open_brace_idx] + new_state_block + text[close_brace_idx+1:]
            changes_made.append(state_name)

    return text, changes_made

def main():
    """Main function to find and process all .txt files in the script's directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    txt_files = glob.glob(os.path.join(script_dir, '*.txt'))
    
    if not txt_files:
        print("No .txt files found in the script's directory.")
        return

    for filepath in txt_files:
        print(f"--- Processing: {os.path.basename(filepath)} ---")
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                original_content = f.read()
            
            modified_content, changes = process_file_content(original_content)
            
            if original_content != modified_content:
                with open(filepath, 'w', encoding='utf-8-sig') as f:
                    f.write(modified_content)
                
                if changes:
                    for state in sorted(changes):
                        print(f"  + Added Trade Center to: {state}")
                print(f"  [SUCCESS] File '{os.path.basename(filepath)}' was modified.")
            else:
                print("  No changes needed for this file.")

        except Exception as e:
            print(f"  [ERROR] Could not process file: {e}")
    
    print("\nScript finished.")

if __name__ == '__main__':
    main()