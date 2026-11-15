import os
import re
import json

def parse_lua_value(text, pos=0):
    while pos < len(text):
        if text[pos].isspace():
            pos += 1
            continue
        if text.startswith('--', pos):
            newline = text.find('\n', pos)
            pos = len(text) if newline == -1 else newline + 1
            continue
        break

    if pos >= len(text):
        return None, pos

    # String literal
    if text[pos] in ('"', "'"):
        quote = text[pos]
        pos += 1
        val_chars = []
        while pos < len(text):
            c = text[pos]
            if c == '\\':
                pos += 1
                if pos < len(text):
                    val_chars.append(text[pos])
                    pos += 1
                continue
            if c == quote:
                pos += 1
                break
            val_chars.append(c)
            pos += 1
        return ''.join(val_chars), pos

    # Table or Constructor: e.g. Sound { ... } or UnitBlueprint { ... } or just { ... }
    m = re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\{', text[pos:])
    if text[pos] == '{' or m:
        if text[pos] != '{':
            pos += text[pos:].find('{')
        pos += 1  # skip {
        
        is_dict = False
        items_list = []
        items_dict = {}
        
        while True:
            while pos < len(text):
                if text[pos].isspace():
                    pos += 1
                    continue
                if text.startswith('--', pos):
                    newline = text.find('\n', pos)
                    pos = len(text) if newline == -1 else newline + 1
                    continue
                break

            if pos >= len(text) or text[pos] == '}':
                if pos < len(text):
                    pos += 1
                break

            key_m = re.match(r'^([a-zA-Z0-9_]+)\s*=', text[pos:]) or re.match(r'^\[\s*([\"\'a-zA-Z0-9_]+)\s*\]\s*=', text[pos:])
            if key_m:
                is_dict = True
                key = key_m.group(1).strip('"\'')
                pos += key_m.end()
                val, pos = parse_lua_value(text, pos)
                items_dict[key] = val
            else:
                val, pos = parse_lua_value(text, pos)
                items_list.append(val)

            while pos < len(text):
                if text[pos].isspace():
                    pos += 1
                elif text[pos] in (',', ';'):
                    pos += 1
                    break
                else:
                    break

        if is_dict:
            if items_list:
                items_dict['_items'] = items_list
            return items_dict, pos
        else:
            return items_list, pos

    # Boolean / Nil
    for word, val in [('true', True), ('false', False), ('nil', None)]:
        if text.startswith(word, pos) and (pos + len(word) >= len(text) or not text[pos+len(word)].isalnum()):
            return val, pos + len(word)

    # Number
    num_m = re.match(r'^-?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?', text[pos:])
    if num_m:
        val_str = num_m.group(0)
        pos += num_m.end()
        return float(val_str) if '.' in val_str or 'e' in val_str.lower() else int(val_str), pos

    # Identifier / string
    ident_m = re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*', text[pos:])
    if ident_m:
        val = ident_m.group(0)
        pos += ident_m.end()
        return val, pos

    return None, pos + 1

if __name__ == '__main__':
    mod_units = r'C:\Users\User\Documents\My Games\Gas Powered Games\Supreme Commander Forged Alliance\mods\RaptorFaction\units'
    parsed_count = 0
    for u in sorted(os.listdir(mod_units)):
        bp_path = os.path.join(mod_units, u, f'{u}_unit.bp')
        if os.path.exists(bp_path):
            with open(bp_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            res, _ = parse_lua_value(content)
            if isinstance(res, dict):
                parsed_count += 1
                name = res.get('General', {}).get('UnitName', u)
                hp = res.get('Defense', {}).get('Health', 0)
                mass = res.get('Economy', {}).get('BuildCostMass', 0)
                weps = len(res.get('Weapon', []))
                print(f'{u}: {name} (HP: {hp}, Mass: {mass}, Weapons: {weps})')
    print(f'Successfully parsed {parsed_count} / {len(os.listdir(mod_units))} units!')
