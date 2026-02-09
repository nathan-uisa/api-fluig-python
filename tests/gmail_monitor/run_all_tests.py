"""
Script para executar todos os testes do módulo Gmail Monitor
"""
import sys
import subprocess
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))


def executar_teste(nome_teste, script_path):
    """Executa um teste e retorna True se bem-sucedido"""
    print("\n" + "="*80)
    print(f" Executando: {nome_teste}")
    print("="*80)
    
    try:
        resultado = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(root_dir),
            capture_output=False,
            text=True
        )
        return resultado.returncode == 0
    except Exception as e:
        print(f" Erro ao executar {nome_teste}: {str(e)}")
        return False


def main():
    """Executa todos os testes"""
    print("\n" + "="*80)
    print(" EXECUTANDO TODOS OS TESTES DO GMAIL MONITOR")
    print("="*80)
    
    testes_dir = Path(__file__).parent
    
    # Lista de testes a executar (em ordem)
    # Nota: test_listar_contatos_people.py requer query obrigatória, então nao é executado automaticamente
    testes = [
        ("Verificação de Permissões", testes_dir / "test_checar_permissoes.py"),
        ("Listar Emails Nao Lidos", testes_dir / "test_listar_emails_nao_lidos.py"),
        ("Listar Emails Processados", testes_dir / "test_listar_emails_processados.py"),
        # ("Listar Contatos People API", testes_dir / "test_listar_contatos_people.py"),  # Requer query obrigatória
    ]
    
    resultados = {}
    
    for nome, script in testes:
        if script.exists():
            sucesso = executar_teste(nome, script)
            resultados[nome] = sucesso
        else:
            print(f"  Script nao encontrado: {script}")
            resultados[nome] = False
    
    # Resumo
    print("\n" + "="*80)
    print(" RESUMO DOS TESTES")
    print("="*80)
    
    total = len(resultados)
    sucessos = sum(1 for v in resultados.values() if v)
    falhas = total - sucessos
    
    for nome, sucesso in resultados.items():
        status = " PASSOU" if sucesso else " FALHOU"
        print(f"  {status} - {nome}")
    
    print("\n" + "-"*80)
    print(f"Total: {total} | Sucessos: {sucessos} | Falhas: {falhas}")
    
    if falhas == 0:
        print("\n Todos os testes passaram!")
    else:
        print(f"\n  {falhas} teste(s) falharam. Verifique os logs acima.")
    
    print("="*80 + "\n")
    
    # Nota sobre testes que requerem parâmetros
    print(" Nota: Alguns testes requerem parâmetros e nao são executados automaticamente:")
    print("   - Envio de email:")
    print("     python tests/gmail_monitor/test_enviar_email.py email@exemplo.com")
    print("   - Listar contatos (requer query obrigatória):")
    print("     python tests/gmail_monitor/test_listar_contatos_people.py --query usuario@uisa.com.br\n")
    
    return falhas == 0


if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
