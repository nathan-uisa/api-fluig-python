#!/usr/bin/env python3
"""
Script temporário para remover emojis dos arquivos de teste
"""
import re
from pathlib import Path

# Mapeamento de emojis para texto ou vazio
emoji_replacements = {
    '🚀': '',
    '📧': '',
    '🔍': '',
    '✅': '',
    '❌': '',
    '⚠️': '',
    '📨': '',
    '📝': '',
    '📅': '',
    '🏷️': '',
    '👤': '',
    '📞': '',
    '🏢': '',
    '📊': '',
    '💡': '',
    '📋': '',
    '🔐': '',
    '📄': '',
    '📎': '',
    '🔗': '',
    '📤': '',
    '📥': '',
    '✨': '',
    '🧪': '',
    '👥': '',
}

files_to_process = [
    'test_enviar_email.py',
    'test_listar_contatos_people.py',
    'test_processar_email_mais_recente.py',
    'run_all_tests.py'
]

base_dir = Path(__file__).parent

for filename in files_to_process:
    filepath = base_dir / filename
    if not filepath.exists():
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Substitui emojis
    for emoji, replacement in emoji_replacements.items():
        content = content.replace(emoji, replacement)
    
    # Substituições específicas de texto
    replacements = {
        'NÃO': 'NAO',
        'não': 'nao',
        'Não': 'Nao',
        'permissões': 'permissoes',
        'permissão': 'permissao',
        'Verifique': 'Verifique',
        '⚠️': 'AVISO:',
        '✅': '',
        '❌': '',
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Processado: {filename}")

print("Concluido!")
