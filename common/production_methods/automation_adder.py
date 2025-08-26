import re
import math
from collections import defaultdict

def generate_pms(input_path, output_path):
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = f.read()
    except FileNotFoundError:
        print(f"Error: Input file not found at '{input_path}'")
        return
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return

    pm_start_pattern = re.compile(r"(pm_automation_([a-zA-Z_0-9]+?)_(\d+))\s*=\s*\{")
    modifier_pattern = re.compile(r"(\w+)\s*=\s*(-?\d+\.?\d*)")
    
    pm_groups = defaultdict(dict)

    for match in pm_start_pattern.finditer(data):
        block_content_start = match.end()
        open_braces = 1
        scan_index = block_content_start
        while open_braces > 0 and scan_index < len(data):
            if data[scan_index] == '{':
                open_braces += 1
            elif data[scan_index] == '}':
                open_braces -= 1
            scan_index += 1
        
        if open_braces != 0: continue
        
        full_block = data[match.start():scan_index]
        name = match.group(2)
        level = int(match.group(3))
        
        modifiers = {
            'workforce_scaled': {},
            'level_scaled': {}
        }
        
        workforce_match = re.search(r"workforce_scaled\s*=\s*\{(.*?)\}", full_block, re.DOTALL)
        if workforce_match:
            for mod_match in modifier_pattern.finditer(workforce_match.group(1)):
                key, value_str = mod_match.groups()
                modifiers['workforce_scaled'][key] = float(value_str)

        level_match = re.search(r"level_scaled\s*=\s*\{(.*?)\}", full_block, re.DOTALL)
        if level_match:
            for mod_match in modifier_pattern.finditer(level_match.group(1)):
                key, value_str = mod_match.groups()
                modifiers['level_scaled'][key] = float(value_str)
        
        tech_base_name = ""
        tech_match = re.search(r"unlocking_technologies\s*=\s*\{(.*?)\}", full_block, re.DOTALL)
        if tech_match:
            tech_name_full = tech_match.group(1).strip()
            if '_' in tech_name_full:
                parts = tech_name_full.rsplit('_', 1)
                if parts[1].isdigit():
                    tech_base_name = parts[0]

        pm_groups[name][level] = {
            'modifiers': modifiers,
            'tech_base_name': tech_base_name
        }

    newly_generated_pms = defaultdict(list)

    for name, levels in sorted(pm_groups.items()):
        if 1 not in levels or 2 not in levels or 3 not in levels:
            continue

        base_pm_data = levels[1]
        base_pm = base_pm_data['modifiers']
        tech_base_name = base_pm_data.get('tech_base_name')

        if not tech_base_name:
            tech_base_name = name.replace("building_", "") if name.startswith("building_") else name
            if "mine" in tech_base_name:
                tech_base_name = "mining"
            if tech_base_name == "dye_facotry":
                tech_base_name = "dye_factory"

        employment_scaling = {}
        for key, val1 in base_pm['level_scaled'].items():
            val2 = levels[2]['modifiers']['level_scaled'].get(key, val1)
            val3 = levels[3]['modifiers']['level_scaled'].get(key, val2)
            inc1 = val2 - val1
            inc2 = val3 - val2
            ratio = inc2 / inc1 if inc1 != 0 else 1.0
            employment_scaling[key] = {'val3': val3, 'inc2': inc2, 'ratio': ratio}

        for level in range(4, 7):
            new_pm = {
                'workforce_scaled': {},
                'level_scaled': {}
            }
            
            for key, base_value in base_pm['workforce_scaled'].items():
                new_pm['workforce_scaled'][key] = int(base_value * level)
            
            for key, scaling_data in employment_scaling.items():
                inc_prev = scaling_data['inc2']
                val_prev = scaling_data['val3']
                ratio = scaling_data['ratio']
                
                inc_new = inc_prev * ratio
                val_new = val_prev + inc_new
                
                new_pm['level_scaled'][key] = int(round(val_new))
                
                employment_scaling[key]['inc2'] = inc_new
                employment_scaling[key]['val3'] = val_new

            output = f"pm_automation_{name}_{level} = {{\n"
            output += '\ttexture = "gfx/interface/icons/production_method_icons/assembly_lines.dds"\n\t\n\t\n\t\n'
            output += f"\tunlocking_technologies = {{\n\t\t{tech_base_name}_{level}\n\t}}\n\t\n"
            output += "\tbuilding_modifiers = {\n"
            
            if new_pm['workforce_scaled']:
                output += "\t\tworkforce_scaled = {\n"
                for key, value in new_pm['workforce_scaled'].items():
                    output += f"\t\t\t{key} = {value}\n"
                output += "\t\t}\n\n"

            if new_pm['level_scaled']:
                output += "\t\tlevel_scaled = {\n"
                for key, value in new_pm['level_scaled'].items():
                    output += f"\t\t\t{key} = {value}\n"
                output += "\t\t}\n"
            
            output += "\t}\n}"
            newly_generated_pms[name].append(output)

    output_parts = []
    last_index = 0
    for match in pm_start_pattern.finditer(data):
        block_content_start = match.end()
        open_braces = 1
        scan_index = block_content_start
        while open_braces > 0 and scan_index < len(data):
            if data[scan_index] == '{':
                open_braces += 1
            elif data[scan_index] == '}':
                open_braces -= 1
            scan_index += 1
        
        if open_braces != 0: continue

        output_parts.append(data[last_index:match.start()])
        output_parts.append(data[match.start():scan_index])
        
        name = match.group(2)
        level = int(match.group(3))

        if level == 3 and name in newly_generated_pms:
            output_parts.append("\n\n" + "\n\n".join(newly_generated_pms[name]))
        
        last_index = scan_index
    
    output_parts.append(data[last_index:])
    final_output = "".join(output_parts)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_output)
    except Exception as e:
        print(f"An error occurred while writing to the file: {e}")

if __name__ == "__main__":
    input_file_path = './tno_automation_pm.txt'
    output_file_path = './tno_automation_pm_new.txt'

    print(f"Starting PM generation...")
    print(f"Reading from: '{input_file_path}'")
    
    generate_pms(input_file_path, output_file_path)
    
    print(f"Processing complete. Output written to '{output_file_path}'")
