"""
Teste completo do sistema de deduplicação de emails
Simula todo o processo incluindo salvamento no Drive, mas não abre chamados reais
"""
import sys
import os
import importlib.util
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.utilitarios_centrais.logger import logger

# Importações diretas para evitar dependências circulares
spec_deduplicator = importlib.util.spec_from_file_location(
    "email_deduplicator",
    root_dir / "src" / "gmail_monitor" / "email_deduplicator.py"
)
email_deduplicator_module = importlib.util.module_from_spec(spec_deduplicator)
spec_deduplicator.loader.exec_module(email_deduplicator_module)
EmailDeduplicator = email_deduplicator_module.EmailDeduplicator


def testar_deduplicacao_completa():
    """Testa todo o processo de deduplicação"""
    try:
        print("\n" + "="*80)
        print("TESTE COMPLETO DE DEDUPLICAÇÃO DE EMAILS")
        print("="*80 + "\n")
        
        # Inicializa o deduplicador
        print("1. Inicializando EmailDeduplicator...")
        deduplicator = EmailDeduplicator()
        
        print(f"   Padrões configurados: {len(deduplicator.padroes_config) if deduplicator.padroes_config else 0}")
        if deduplicator.padroes_config:
            for idx, padrao in enumerate(deduplicator.padroes_config, 1):
                print(f"      {idx}. {padrao}")
        
        print(f"   Emails configurados para deduplicação: {len(deduplicator.emails_deduplicacao) if deduplicator.emails_deduplicacao else 0}")
        if deduplicator.emails_deduplicacao:
            for idx, email in enumerate(deduplicator.emails_deduplicacao, 1):
                print(f"      {idx}. {email}")
        else:
            print("      (Nenhum email específico - todos serão verificados)")
        
        if not deduplicator.padroes_config:
            print("\n⚠️  AVISO: Nenhum padrão de deduplicação configurado!")
            print("   Configure os padrões na página de configurações antes de executar este teste.")
            return
        
        print("\n" + "-"*80)
        print("2. TESTE DE EXTRAÇÃO DE IDENTIFICADORES")
        print("-"*80 + "\n")
        
        # Simula diferentes emails com padrões
        emails_teste = [
            {
                "remetente": "seglog@uisa.com.br",
                "assunto": "Forescout : Windows 172.17.5.89 entrou em quarentena",
                "corpo": "Olá, CounterACT enviou um equipamento para quarentena. Informações do host: Endereço IP: 172.17.5.89 Endereço MAC: d09466bc0244 Nome do host: Irresolvable/Irresolvable",
                "esperado": "d09466bc0244"
            },
            {
                "remetente": "seglog@uisa.com.br",
                "assunto": "Forescout : Windows 172.17.214.58 entrou em quarentena",
                "corpo": "Olá, CounterACT enviou um equipamento para quarentena. Informações do host: Endereço IP: 172.17.214.58 Endereço MAC: d8cb8adc9c43 Nome do host: Irresolvable/Irresolvable",
                "esperado": "d8cb8adc9c43"
            },
            {
                "remetente": "outro@uisa.com.br",
                "assunto": "Teste sem padrão",
                "corpo": "Este email não tem padrão de deduplicação",
                "esperado": None
            },
            {
                "remetente": "seglog@uisa.com.br",
                "assunto": "CounterACT Information - Message No. 3",
                "corpo": "Hello, This Email was sent by CounterACT. Endereço MAC: a1b2c3d4e5f6 Subject: Equipamento enviado para quarentena",
                "esperado": "a1b2c3d4e5f6"
            }
        ]
        
        resultados_extracao = []
        for idx, email in enumerate(emails_teste, 1):
            print(f"[{idx}/{len(emails_teste)}] Testando extração de identificador...")
            print(f"   Remetente: {email['remetente']}")
            print(f"   Assunto: {email['assunto'][:60]}...")
            
            identificador, padrao_usado = deduplicator.extrair_identificador(
                email['assunto'], 
                email['corpo']
            )
            
            if identificador:
                print(f"   ✅ Identificador extraído: {identificador}")
                print(f"      Padrão usado: {padrao_usado}")
                
                if email['esperado']:
                    if identificador.lower() == email['esperado'].lower():
                        print(f"      ✅ CORRETO - Esperado: {email['esperado']}")
                    else:
                        print(f"      ⚠️  DIFERENTE - Esperado: {email['esperado']}, Obtido: {identificador}")
                else:
                    print(f"      ⚠️  Identificador encontrado mas não era esperado")
            else:
                print(f"   ❌ Nenhum identificador extraído")
                if email['esperado'] is None:
                    print(f"      ✅ CORRETO - Nenhum identificador era esperado")
                else:
                    print(f"      ⚠️  Esperado: {email['esperado']}")
            
            resultados_extracao.append({
                "email": email,
                "identificador": identificador,
                "padrao_usado": padrao_usado
            })
            print()
        
        print("\n" + "-"*80)
        print("3. TESTE DE VERIFICAÇÃO DE DUPLICAÇÃO (COM FILTRO DE EMAILS)")
        print("-"*80 + "\n")
        
        resultados_duplicacao = []
        for idx, resultado in enumerate(resultados_extracao, 1):
            email = resultado['email']
            identificador = resultado['identificador']
            
            print(f"[{idx}/{len(resultados_extracao)}] Verificando duplicação...")
            print(f"   Remetente: {email['remetente']}")
            print(f"   Identificador: {identificador if identificador else 'N/A'}")
            
            # Verifica duplicação
            eh_duplicado, identificador_ret, process_id = deduplicator.verificar_duplicado(
                email['assunto'],
                email['corpo'],
                email['remetente']
            )
            
            if eh_duplicado:
                print(f"   ✅ DUPLICADO detectado!")
                print(f"      Process ID existente: {process_id if process_id else 'N/A'}")
            elif identificador_ret:
                print(f"   ℹ️  Novo identificador (não duplicado)")
                print(f"      Identificador: {identificador_ret}")
            else:
                print(f"   ⚠️  Nenhum identificador retornado")
                if deduplicator.emails_deduplicacao and email['remetente'].lower() not in deduplicator.emails_deduplicacao:
                    print(f"      (Email não está na lista de deduplicação)")
                else:
                    print(f"      (Nenhum padrão encontrado no email)")
            
            resultados_duplicacao.append({
                "email": email,
                "eh_duplicado": eh_duplicado,
                "identificador": identificador_ret,
                "process_id": process_id
            })
            print()
        
        print("\n" + "-"*80)
        print("4. TESTE DE SALVAMENTO NO DRIVE")
        print("-"*80 + "\n")
        
        # Simula abertura de chamados (mas não abre de verdade)
        chamados_simulados = []
        for idx, resultado in enumerate(resultados_duplicacao, 1):
            email = resultado['email']
            identificador = resultado['identificador']
            
            if identificador and not resultado['eh_duplicado']:
                # Simula abertura de chamado
                process_id_simulado = 1000 + idx  # ID fictício
                chamados_simulados.append({
                    "identificador": identificador,
                    "process_id": process_id_simulado,
                    "email": email
                })
                
                print(f"[{idx}] Simulando abertura de chamado...")
                print(f"   Identificador: {identificador}")
                print(f"   Process ID simulado: {process_id_simulado}")
                
                # Marca como processado (salva no Drive)
                deduplicator.marcar_como_processado(
                    email['assunto'],
                    email['corpo'],
                    process_id_simulado
                )
                print(f"   ✅ Identificador salvo no Drive")
                print()
        
        print("\n" + "-"*80)
        print("5. TESTE DE VERIFICAÇÃO DE DUPLICAÇÃO (APÓS SALVAMENTO)")
        print("-"*80 + "\n")
        
        # Recarrega identificadores do Drive
        print("Recarregando identificadores do Drive...")
        deduplicator._carregar_identificadores_processados()
        print(f"   {len(deduplicator.identificadores_processados)} identificador(es) carregado(s)")
        print()
        
        # Testa novamente os mesmos emails para verificar se são detectados como duplicados
        for idx, resultado in enumerate(resultados_duplicacao, 1):
            email = resultado['email']
            identificador_original = resultado['identificador']
            
            if not identificador_original:
                continue
            
            print(f"[{idx}] Verificando duplicação novamente (após salvamento)...")
            print(f"   Remetente: {email['remetente']}")
            print(f"   Identificador: {identificador_original}")
            
            eh_duplicado, identificador_ret, process_id = deduplicator.verificar_duplicado(
                email['assunto'],
                email['corpo'],
                email['remetente']
            )
            
            if eh_duplicado:
                print(f"   ✅ DUPLICADO detectado corretamente!")
                print(f"      Process ID: {process_id if process_id else 'N/A'}")
                
                # Verifica se o process_id corresponde ao que foi salvo
                chamado_correspondente = next(
                    (c for c in chamados_simulados if c['identificador'] == identificador_original),
                    None
                )
                if chamado_correspondente:
                    if process_id == chamado_correspondente['process_id']:
                        print(f"      ✅ Process ID correto!")
                    else:
                        print(f"      ⚠️  Process ID diferente - Esperado: {chamado_correspondente['process_id']}, Obtido: {process_id}")
            else:
                print(f"   ⚠️  NÃO detectado como duplicado (pode ser problema)")
            print()
        
        print("\n" + "-"*80)
        print("6. TESTE DE FILTRO DE EMAILS")
        print("-"*80 + "\n")
        
        # Testa com email que NÃO está na lista
        if deduplicator.emails_deduplicacao:
            email_fora_lista = {
                "remetente": "email_nao_configurado@uisa.com.br",
                "assunto": "Teste com padrão",
                "corpo": "Endereço MAC: teste12345678"
            }
            
            print("Testando email que NÃO está na lista de deduplicação...")
            print(f"   Remetente: {email_fora_lista['remetente']}")
            print(f"   Lista configurada: {', '.join(deduplicator.emails_deduplicacao)}")
            
            eh_duplicado, identificador, process_id = deduplicator.verificar_duplicado(
                email_fora_lista['assunto'],
                email_fora_lista['corpo'],
                email_fora_lista['remetente']
            )
            
            if not identificador:
                print(f"   ✅ CORRETO - Verificação pulada (email não está na lista)")
            else:
                print(f"   ⚠️  Verificação não foi pulada - Identificador: {identificador}")
            print()
        
        # Resumo final
        print("\n" + "="*80)
        print("RESUMO DO TESTE")
        print("="*80)
        print(f"Total de emails testados: {len(emails_teste)}")
        print(f"   Identificadores extraídos: {sum(1 for r in resultados_extracao if r['identificador'])}")
        print(f"   Chamados simulados: {len(chamados_simulados)}")
        print(f"   Identificadores salvos no Drive: {len(deduplicator.identificadores_processados)}")
        print("="*80 + "\n")
        
        print("✅ Teste completo finalizado!")
        print("   Todos os identificadores foram salvos no Google Drive.")
        print("   Nenhum chamado real foi aberto (apenas simulação).\n")
        
    except Exception as e:
        print(f"\n❌ Erro durante o teste: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\nIniciando teste completo de deduplicação...\n")
    testar_deduplicacao_completa()
    print("\nTeste finalizado!\n")
