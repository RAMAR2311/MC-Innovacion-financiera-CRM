path = 'c:/Users/Marlo/OneDrive/Documentos/ZENIC/templates/client_detail.html'
try:
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Lines to remove: 260 to 454 (1-based)
    # Indices to remove: 259 to 453 (0-based)
    # We want to keep 0..258 (lines 1..259)
    # We want to keep 454..end (lines 455..end)

    print(f"Original line count: {len(lines)}")
    print(f"Line 260 content: {lines[259]}")
    print(f"Line 455 content: {lines[454]}")

    new_lines = lines[:259] + lines[454:]

    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"New line count: {len(new_lines)}")
except Exception as e:
    print(f"Error: {e}")
