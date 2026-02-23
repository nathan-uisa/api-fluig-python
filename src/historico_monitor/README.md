# Sistema de Monitoramento de Histórico de Chamados

Este módulo fornece funcionalidades para monitorar e acompanhar a evolução de chamados abertos via email no Fluig.

## Funcionalidades

- **Salvamento Automático**: Quando um chamado é aberto via email (endpoint `/email/abrir`), o histórico inicial é automaticamente salvo
- **Monitoramento Periódico**: Verifica atualizações nos históricos a cada 1 hora (configurável)
- **Detecção de Mudanças**: Identifica novos eventos (MOVEMENT, OBSERVATION, ATTACHMENT) nos chamados
- **Armazenamento Simples**: Usa ConfigParser para salvar históricos em arquivos `.ini`

## Estrutura

```
src/historico_monitor/
├── __init__.py              # Exporta classes principais
├── historico_manager.py     # Gerencia salvamento/leitura de históricos
├── historico_monitor.py     # Monitora atualizações periodicamente
├── background_service.py    # Serviço em background para inicialização automática
├── iniciar_monitor.py       # Script para iniciar monitoramento
└── historicos/              # Pasta onde são salvos os arquivos .ini
    └── historico_{process_instance_id}.ini
```

## Uso

### Salvamento Automático

O histórico é automaticamente salvo quando um chamado é aberto via email através do endpoint:

```
POST /api/v1/fluig/{ambiente}/chamados/email/abrir
```

Não é necessário fazer nada adicional - o sistema salva automaticamente após a criação do chamado.

### Monitoramento Manual

Para verificar atualizações manualmente em um chamado específico:

```python
from src.historico_monitor.historico_monitor import HistoricoMonitor

monitor = HistoricoMonitor()
resultado = monitor.verificar_atualizacoes_chamado(
    process_instance_id=123456,
    ambiente="PRD"
)

if resultado['tem_atualizacoes']:
    print(f"Novos itens: {resultado['quantidade_novos']}")
```

### Monitoramento Periódico

Para iniciar o monitoramento automático que verifica todos os chamados a cada 1 hora:

```python
from src.historico_monitor.historico_monitor import HistoricoMonitor

monitor = HistoricoMonitor(intervalo_horas=1.0)
monitor.iniciar_monitoramento(ambiente="PRD", em_background=True)
```

Ou execute o script:

```bash
python -m src.historico_monitor.iniciar_monitor
```

### Listar Chamados Monitorados

Para listar todos os chamados que têm histórico salvo:

```python
from src.historico_monitor.historico_manager import HistoricoManager

manager = HistoricoManager()
chamados = manager.listar_chamados_monitorados()
print(f"Chamados monitorados: {chamados}")
```

### Ler Histórico Salvo

Para ler o histórico salvo de um chamado:

```python
from src.historico_monitor.historico_manager import HistoricoManager

manager = HistoricoManager()
historico = manager.ler_historico(process_instance_id=123456)

if historico:
    items = historico.get('items', [])
    print(f"Total de eventos: {len(items)}")
```

## Formato dos Arquivos

Os históricos são salvos em arquivos `.ini` usando ConfigParser:

```ini
[METADADOS]
process_instance_id = 123456
ambiente = PRD
data_criacao = 2026-02-13T10:00:00.000000
data_ultima_atualizacao = 2026-02-13T11:00:00.000000
total_items = 5
has_next = false

[HISTORICO]
dados_completos = {
  "items": [...],
  "hasNext": false
}
```

## Configuração

### Variáveis de Ambiente

O monitoramento pode ser configurado através de variáveis de ambiente no arquivo `.env`:

```env
# Habilitar/desabilitar monitoramento (padrão: true)
HISTORICO_MONITOR_ENABLED=true

# Intervalo de verificação em minutos (padrão: 60 = 1 hora)
HISTORICO_CHECK_INTERVAL_MINUTES=60

# Ambiente do Fluig para monitoramento (padrão: PRD)
HISTORICO_MONITOR_AMBIENTE=PRD
```

### Configuração Programática

O intervalo de verificação também pode ser configurado ao criar o monitor:

```python
monitor = HistoricoMonitor(intervalo_horas=2.0)  # Verifica a cada 2 horas
```
## Notas

- O monitoramento roda em thread separada (daemon) quando `em_background=True`
- Erros ao salvar histórico não impedem a abertura do chamado
- Os arquivos são salvos em `src/historico_monitor/historicos/`
- O sistema detecta automaticamente novos itens comparando o total de eventos
- O monitoramento é iniciado automaticamente quando a aplicação FastAPI inicia (no Cloud Run)