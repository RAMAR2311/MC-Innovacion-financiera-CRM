import os

def fix_file(filepath):
    char_map = {
        '{{ client.id }\\n        };': '{{ client.id }};',
        '{{ client.id }\\n            };': '{{ client.id }};',
        '{{ client.id }\\r\\n        };': '{{ client.id }};',
        '{{ client.id }\\r\\n            };': '{{ client.id }};',
        '{{ client.id }\\n        };': '{{ client.id }};',
        '{{ client.id }\\r\\n        };': '{{ client.id }};',
    }
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Direct fixes for known problematic snippets
    content = content.replace('const clientId = {{ client.id }\n        };', 'const clientId = {{ client.id }};')
    content = content.replace('const clientId = {{ client.id }\r\n        };', 'const clientId = {{ client.id }};')
    content = content.replace('const clientId = {{ client.id }\n            };', 'const clientId = {{ client.id }};')
    content = content.replace('const clientId = {{ client.id }\r\n            };', 'const clientId = {{ client.id }};')
    
    # Fix closures
    if 'client_dashboard.html' in filepath:
        content = content.replace('});\\n    </script>', '    });\\n</script>')
        content = content.replace('});\\r\\n    </script>', '    });\\r\\n</script>')
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

templates = [
    r'c:\Users\Marlo\OneDrive\Documentos\ZENIC\templates\client_dashboard.html',
    r'c:\Users\Marlo\OneDrive\Documentos\ZENIC\templates\client_detail.html'
]

for t in templates:
    if os.path.exists(t):
        print(f"Fixing {t}")
        fix_file(t)
    else:
        print(f"Not found: {t}")
