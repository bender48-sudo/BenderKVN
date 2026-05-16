with open("/opt/remna-shop/src/shop_bot/bot/handlers.py") as f:
    lines = f.readlines()

NL = chr(92) + chr(110)  # literal \n in source code
Q = chr(34)  # double quote
SQ = chr(39)  # single quote

def build_text_active():
    t = Q
    t += chr(0x1f464) + " <b>" + chr(0x412) + chr(0x430) + chr(0x448) + " "
    t += chr(0x430) + chr(0x43a) + chr(0x43a) + chr(0x430) + chr(0x443) + chr(0x43d) + chr(0x442)
    t += " BenderVPN</b>" + NL + NL
    t += chr(0x1f4c5) + " " + chr(0x41f) + chr(0x43e) + chr(0x434) + chr(0x43f)
    t += chr(0x438) + chr(0x441) + chr(0x43a) + chr(0x430) + ": "
    t += chr(0x430) + chr(0x43a) + chr(0x442) + chr(0x438) + chr(0x432) + chr(0x43d) + chr(0x430)
    t += " " + chr(0x434) + chr(0x43e) + " "
    t += "{exp.strftime(" + SQ + "%d.%m.%Y" + SQ + ")}" + NL
    t += chr(0x1f465) + " " + chr(0x41f) + chr(0x440) + chr(0x438) + chr(0x433) + chr(0x43b)
    t += chr(0x430) + chr(0x448) + chr(0x435) + chr(0x43d) + chr(0x43e) + " "
    t += chr(0x434) + chr(0x440) + chr(0x443) + chr(0x437) + chr(0x435) + chr(0x439)
    t += ": {ref_count}" + Q
    return t

def build_text_nosub():
    t = Q
    t += chr(0x1f464) + " <b>" + chr(0x412) + chr(0x430) + chr(0x448) + " "
    t += chr(0x430) + chr(0x43a) + chr(0x43a) + chr(0x430) + chr(0x443) + chr(0x43d) + chr(0x442)
    t += " BenderVPN</b>" + NL + NL
    t += chr(0x423) + " " + chr(0x432) + chr(0x430) + chr(0x441) + " " + chr(0x43d) + chr(0x435) + chr(0x442)
    t += " " + chr(0x430) + chr(0x43a) + chr(0x442) + chr(0x438) + chr(0x432) + chr(0x43d)
    t += chr(0x43e) + chr(0x439) + " " + chr(0x43f) + chr(0x43e) + chr(0x434) + chr(0x43f)
    t += chr(0x438) + chr(0x441) + chr(0x43a) + chr(0x438) + "." + Q
    return t

def build_support_msg():
    t = Q
    t += chr(0x1f4ac) + " <b>" + chr(0x41f) + chr(0x43e) + chr(0x434) + chr(0x434) + chr(0x435)
    t += chr(0x440) + chr(0x436) + chr(0x43a) + chr(0x430) + "</b>" + NL + NL
    t += chr(0x41d) + chr(0x430) + chr(0x43f) + chr(0x438) + chr(0x448) + chr(0x438) + chr(0x442) + chr(0x435)
    t += " " + chr(0x432) + chr(0x430) + chr(0x448) + " " + chr(0x432) + chr(0x43e) + chr(0x43f)
    t += chr(0x440) + chr(0x43e) + chr(0x441) + " " + chr(0x43f) + chr(0x440) + chr(0x44f) + chr(0x43c)
    t += chr(0x43e) + " " + chr(0x437) + chr(0x434) + chr(0x435) + chr(0x441) + chr(0x44c)
    t += " " + chr(0x2014) + NL
    t += chr(0x43c) + chr(0x44b) + " " + chr(0x43e) + chr(0x442) + chr(0x432) + chr(0x435) + chr(0x442)
    t += chr(0x438) + chr(0x43c) + " " + chr(0x432) + " " + chr(0x441) + chr(0x430) + chr(0x43c)
    t += chr(0x43e) + chr(0x435) + " " + chr(0x431) + chr(0x43b) + chr(0x438) + chr(0x436)
    t += chr(0x430) + chr(0x439) + chr(0x448) + chr(0x435) + chr(0x435) + " "
    t += chr(0x432) + chr(0x440) + chr(0x435) + chr(0x43c) + chr(0x44f) + " " + chr(0x1f64f) + Q
    return t

def build_invite_text():
    t = Q
    t += chr(0x1f465) + " <b>" + chr(0x41f) + chr(0x440) + chr(0x438) + chr(0x433) + chr(0x43b)
    t += chr(0x430) + chr(0x441) + chr(0x438) + chr(0x442) + chr(0x435) + " "
    t += chr(0x434) + chr(0x440) + chr(0x443) + chr(0x433) + chr(0x430) + "</b>" + NL + NL
    t += chr(0x41a) + chr(0x43e) + chr(0x433) + chr(0x434) + chr(0x430) + " "
    t += chr(0x434) + chr(0x440) + chr(0x443) + chr(0x433) + " " + chr(0x430) + chr(0x43a) + chr(0x442)
    t += chr(0x438) + chr(0x432) + chr(0x438) + chr(0x440) + chr(0x443) + chr(0x435) + chr(0x442)
    t += " " + chr(0x43f) + chr(0x43e) + chr(0x434) + chr(0x43f) + chr(0x438) + chr(0x441)
    t += chr(0x43a) + chr(0x443) + " " + chr(0x2014) + NL
    t += chr(0x432) + chr(0x44b) + " " + chr(0x43e) + chr(0x431) + chr(0x430) + " "
    t += chr(0x43f) + chr(0x43e) + chr(0x43b) + chr(0x443) + chr(0x447) + chr(0x438) + chr(0x442)
    t += chr(0x435) + " +3 " + chr(0x434) + chr(0x43d) + chr(0x44f) + " " + chr(0x1f381) + NL + NL
    t += chr(0x1f465) + " " + chr(0x41f) + chr(0x440) + chr(0x438) + chr(0x433) + chr(0x43b)
    t += chr(0x430) + chr(0x448) + chr(0x435) + chr(0x43d) + chr(0x43e) + ": {ref_count}" + Q
    return t

def build_ref_copy_msg():
    t = Q
    t += chr(0x1f4cb) + " <b>" + chr(0x412) + chr(0x430) + chr(0x448) + chr(0x430) + " "
    t += chr(0x440) + chr(0x435) + chr(0x444) + chr(0x435) + chr(0x440) + chr(0x430) + chr(0x43b)
    t += chr(0x44c) + chr(0x43d) + chr(0x430) + chr(0x44f) + " " + chr(0x441) + chr(0x441)
    t += chr(0x44b) + chr(0x43b) + chr(0x43a) + chr(0x430) + ":</b>" + NL + NL
    t += "<code>{ref_url}</code>" + NL + NL
    t += chr(0x41d) + chr(0x430) + chr(0x436) + chr(0x43c) + chr(0x438) + chr(0x442)
    t += chr(0x435) + " " + chr(0x43d) + chr(0x430) + " " + chr(0x441) + chr(0x441)
    t += chr(0x44b) + chr(0x43b) + chr(0x43a) + chr(0x443) + " " + chr(0x2014) + " "
    t += chr(0x43e) + chr(0x43d) + chr(0x430) + " " + chr(0x441) + chr(0x43a) + chr(0x43e)
    t += chr(0x43f) + chr(0x438) + chr(0x440) + chr(0x443) + chr(0x435) + chr(0x442)
    t += chr(0x441) + chr(0x44f) + " " + chr(0x1f446) + Q
    return t

# Scan and fix broken multi-line strings
new_lines = []
i = 0
fixes = 0
while i < len(lines):
    line = lines[i]
    stripped = line.strip()

    # Pattern: f-string or string with emoji that doesn't close on same line
    is_fstring = stripped.startswith('f"') or stripped.startswith('text = f"') or stripped.startswith('text = "')
    has_emoji = any(ord(c) > 0x2000 for c in line)
    ends_with_quote = stripped.endswith('"') or stripped.endswith('",') or stripped.endswith('")')

    if is_fstring and has_emoji and not ends_with_quote and "BenderVPN" in line:
        # Broken account text - collect and skip
        is_f = "= f" in line
        j = i + 1
        while j < len(lines) and "await callback" not in lines[j]:
            j += 1
        if chr(0x43d) + chr(0x435) + chr(0x442) in line:  # "нет" = no sub
            new_lines.append("        text = " + build_text_nosub() + "\n")
        else:
            new_lines.append("        text = f" + build_text_active() + "\n")
        # Skip stray ) if present after await
        if j < len(lines):
            new_lines.append(lines[j])  # the await line
            j += 1
        if j < len(lines) and lines[j].strip() == ")":
            j += 1  # skip stray )
        i = j
        fixes += 1
        print(f"Fixed BenderVPN text at line {i}")
        continue

    if "callback.message.answer(" in line and chr(0x1f4ac) in line and not ends_with_quote:
        # Broken support text
        j = i + 1
        while j < len(lines) and lines[j].strip() and not lines[j].startswith("@") and not lines[j].startswith("async"):
            if lines[j].strip() == "":
                break
            j += 1
        new_lines.append("    await callback.message.answer(" + build_support_msg() + ", parse_mode=" + Q + "HTML" + Q + ")\n")
        i = j
        fixes += 1
        print(f"Fixed support text at line {i}")
        continue

    if "text = (" in line:
        # Check if next line has invite emoji
        if i + 1 < len(lines) and chr(0x1f465) in lines[i+1]:
            j = i + 1
            while j < len(lines) and lines[j].strip() != ")":
                j += 1
            if j < len(lines):
                j += 1  # skip )
            new_lines.append("    text = f" + build_invite_text() + "\n")
            i = j
            fixes += 1
            print(f"Fixed invite text at line {i}")
            continue

    if "callback.message.answer(f" in line and chr(0x1f4cb) in line and chr(0x440) + chr(0x435) + chr(0x444) in line and not ends_with_quote:
        # Broken ref copy text
        j = i + 1
        while j < len(lines) and lines[j].strip() and not lines[j].startswith("@") and not lines[j].startswith("async"):
            if lines[j].strip() == "":
                break
            j += 1
        new_lines.append("    await callback.message.answer(f" + build_ref_copy_msg() + ", parse_mode=" + Q + "HTML" + Q + ")\n")
        i = j
        fixes += 1
        print(f"Fixed ref copy text at line {i}")
        continue

    new_lines.append(line)
    i += 1

with open("/opt/remna-shop/src/shop_bot/bot/handlers.py", "w") as f:
    f.writelines(new_lines)
print(f"Done! Fixed {fixes} blocks")
