// Script para gerenciar o formulário de chamados e modal de prévia

// Variáveis globais para autocomplete de serviços
let servicosDisponiveis = [];
let dropdownAtivo = false;
let itemSelecionado = -1;

// Função auxiliar para escapar HTML e prevenir XSS
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}

document.addEventListener('DOMContentLoaded', function() {
    const planilhaInput = document.getElementById('planilha');
    const statusDiv = document.getElementById('planilha-status');
    const qtdGroup = document.getElementById('quantidade-group');
    const ignorarCabecalhoGroup = document.getElementById('ignorar-cabecalho-group');
    const previewButtonGroup = document.getElementById('preview-button-group');
    const formChamado = document.getElementById('formChamado');
    const btnPreview = document.getElementById('btn-preview');
    const modalPreview = document.getElementById('modal-preview');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const modalLoading = document.getElementById('modal-loading');
    const modalError = document.getElementById('modal-error');
    const modalPreviewContent = document.getElementById('modal-preview-content');
    
    // Elementos da sidebar de chamados (esquerda)
    const sidebar = document.getElementById('chamados-sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const chamadosList = document.getElementById('chamados-list');
    const chamadosLoading = document.getElementById('chamados-loading');
    const chamadosError = document.getElementById('chamados-error');
    const chamadosPagination = document.getElementById('chamados-pagination');
    
    // Elementos da sidebar de chamados do grupo (direita)
    const chamadosGrupoList = document.getElementById('chamados-grupo-list');
    const chamadosGrupoLoading = document.getElementById('chamados-grupo-loading');
    const chamadosGrupoError = document.getElementById('chamados-grupo-error');
    const chamadosGrupoPagination = document.getElementById('chamados-grupo-pagination');
    
    // Variáveis de paginação para MEUS CHAMADOS
    let todosChamados = [];
    let paginaAtual = 1;
    const itensPorPagina = 10;
    
    // Variáveis de paginação para TODOS ANALISTAS
    let todosChamadosGrupo = [];
    let paginaAtualGrupo = 1;
    const itensPorPaginaGrupo = 10;

    // ==================== SISTEMA DE CACHE NO FRONTEND ====================
    const CACHE_KEY_FILA = 'chamados_fila_cache';
    const CACHE_KEY_GRUPO = 'chamados_grupo_cache';
    const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutos em milissegundos
    
    /**
     * Obtém dados do cache localStorage se ainda válidos
     */
    function obterCache(chave) {
        try {
            const cacheData = localStorage.getItem(chave);
            if (!cacheData) {
                return null;
            }
            
            const parsed = JSON.parse(cacheData);
            const agora = Date.now();
            
            // Verifica se cache expirou
            if (agora > parsed.expira_em) {
                localStorage.removeItem(chave);
                console.log(`[Cache] Cache expirado para chave: ${chave}`);
                return null;
            }
            
            console.log(`[Cache] Cache hit para chave: ${chave}`);
            return parsed.dados;
        } catch (e) {
            console.error('[Cache] Erro ao ler cache:', e);
            return null;
        }
    }
    
    /**
     * Salva dados no cache localStorage com TTL
     */
    function salvarCache(chave, dados) {
        try {
            const cacheData = {
                dados: dados,
                expira_em: Date.now() + CACHE_TTL_MS,
                criado_em: Date.now()
            };
            localStorage.setItem(chave, JSON.stringify(cacheData));
            console.log(`[Cache] Dados salvos no cache para chave: ${chave}`);
        } catch (e) {
            console.error('[Cache] Erro ao salvar cache:', e);
            // Se localStorage estiver cheio, tenta limpar cache antigo
            try {
                const keys = Object.keys(localStorage);
                for (let key of keys) {
                    if (key.startsWith('chamados_') && key.endsWith('_cache')) {
                        localStorage.removeItem(key);
                    }
                }
                // Tenta salvar novamente
                localStorage.setItem(chave, JSON.stringify(cacheData));
            } catch (e2) {
                console.error('[Cache] Erro ao limpar e salvar cache:', e2);
            }
        }
    }
    
    /**
     * Atualiza cache em background sem bloquear a UI
     */
    async function atualizarChamadosFilaEmBackground() {
        try {
            console.log('[Cache] Atualizando cache de MEUS CHAMADOS em background...');
            // Obter dados atuais ANTES de buscar novos (para comparação)
            const cacheAtual = obterCache(CACHE_KEY_FILA);
            const dadosAtuais = cacheAtual ? JSON.stringify(cacheAtual.chamados || []) : null;
            
            const response = await fetch('/api/chamados/fila');
            if (response.ok) {
                const data = await response.json();
                if (data.sucesso) {
                    // Comparar dados ANTES de salvar no cache
                    const dadosNovos = JSON.stringify(data.chamados || []);
                    if (dadosAtuais !== dadosNovos) {
                        console.log('[Cache] Dados mudaram, atualizando lista...');
                        todosChamados = data.chamados || [];
                        renderizarChamadosFila();
                    } else {
                        console.log('[Cache] Dados não mudaram, apenas atualizando cache...');
                    }
                    // Salvar no cache após comparar
                    salvarCache(CACHE_KEY_FILA, data);
                }
            }
        } catch (error) {
            console.error('[Cache] Erro ao atualizar cache em background:', error);
        }
    }
    
    /**
     * Atualiza cache do grupo em background sem bloquear a UI
     */
    async function atualizarChamadosGrupoEmBackground() {
        try {
            console.log('[Cache] Atualizando cache de TODOS ANALISTAS em background...');
            // Obter dados atuais ANTES de buscar novos (para comparação)
            const cacheAtual = obterCache(CACHE_KEY_GRUPO);
            const dadosAtuais = cacheAtual ? JSON.stringify(cacheAtual.chamados || []) : null;
            
            const response = await fetch('/api/chamados/grupo-itsm-todos');
            if (response.ok) {
                const data = await response.json();
                if (data.sucesso) {
                    // Comparar dados ANTES de salvar no cache
                    const dadosNovos = JSON.stringify(data.chamados || []);
                    if (dadosAtuais !== dadosNovos) {
                        console.log('[Cache] Dados mudaram, atualizando lista...');
                        todosChamadosGrupo = data.chamados || [];
                        renderizarChamadosGrupo();
                    } else {
                        console.log('[Cache] Dados não mudaram, apenas atualizando cache...');
                    }
                    // Salvar no cache após comparar
                    salvarCache(CACHE_KEY_GRUPO, data);
                }
            }
        } catch (error) {
            console.error('[Cache] Erro ao atualizar cache em background:', error);
        }
    }

    const servicoInput = document.getElementById('servico');
    const servicoIdInput = document.getElementById('servico_id');
    const servicoDropdown = document.getElementById('servico-dropdown');
    
    // Listener para remover erro visual do telefone quando o usuário digitar
    const telefoneInput = document.getElementById('telefone_contato');
    const telefoneError = document.getElementById('telefone-error');
    if (telefoneInput && telefoneError) {
        telefoneInput.addEventListener('input', function() {
            if (this.value && this.value.trim()) {
                // Remover erro visual quando o campo for preenchido
                this.style.borderColor = '';
                this.style.backgroundColor = '';
                telefoneError.style.display = 'none';
            }
        });
        
        telefoneInput.addEventListener('blur', function() {
            if (!this.value || !this.value.trim()) {
                // Mostrar erro visual quando o campo perder o foco e estiver vazio
                this.style.borderColor = 'var(--error-border)';
                this.style.backgroundColor = 'var(--error-bg)';
                telefoneError.style.display = 'block';
            }
        });
    }
    
    if (servicoInput && servicoDropdown) {
        // Carrega os serviços ao iniciar
        carregarServicos();
        
        // Event listener para quando o usuário clica no campo
        servicoInput.addEventListener('focus', function() {
            if (servicosDisponiveis.length > 0) {
                mostrarDropdown();
            }
        });
        
        // Event listener para quando o usuário digita
        servicoInput.addEventListener('input', function() {
            mostrarDropdown();
        });
        
        // Event listener para teclas especiais
        servicoInput.addEventListener('keydown', function(e) {
            const items = servicoDropdown.querySelectorAll('.dropdown-item');
            
            if (dropdownAtivo && items.length > 0) {
                switch(e.key) {
                    case 'ArrowDown':
                        e.preventDefault();
                        itemSelecionado = Math.min(itemSelecionado + 1, items.length - 1);
                        atualizarSelecao(items);
                        break;
                    case 'ArrowUp':
                        e.preventDefault();
                        itemSelecionado = Math.max(itemSelecionado - 1, -1);
                        atualizarSelecao(items);
                        break;
                    case 'Enter':
                        e.preventDefault();
                        if (itemSelecionado >= 0 && items[itemSelecionado]) {
                            items[itemSelecionado].click();
                        }
                        break;
                        case 'Escape':
                            servicoDropdown.innerHTML = '';
                            servicoDropdown.style.display = 'none';
                            dropdownAtivo = false;
                            itemSelecionado = -1;
                            break;
                }
            }
        });
        
            // Fechar dropdown ao clicar fora
            document.addEventListener('click', function(e) {
                if (!e.target.closest('.autocomplete-container')) {
                    servicoDropdown.innerHTML = '';
                    servicoDropdown.style.display = 'none';
                    dropdownAtivo = false;
                    itemSelecionado = -1;
                }
            });
    }

    // Gerenciar upload de planilha
    if (planilhaInput) {
        planilhaInput.addEventListener('change', async function(e) {
            const file = e.target.files[0];
            if (file) {
                // Mostrar status de carregamento
                statusDiv.textContent = '⏳ Carregando planilha...';
                statusDiv.style.display = 'block';
                statusDiv.style.color = 'var(--text-secondary)';
                statusDiv.style.background = 'var(--bg-section)';
                statusDiv.style.border = '1px solid var(--border-primary)';
                planilhaInput.disabled = true;
                
                try {
                    // Criar FormData para enviar o arquivo
                    const formData = new FormData();
                    formData.append('planilha', file);
                    
                    // Enviar arquivo para processamento
                    const response = await fetch('/chamado/carregar-planilha', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (data.sucesso) {
                        // Sucesso: mostrar mensagem de confirmação
                        statusDiv.textContent = '✓ ' + (data.mensagem || 'Arquivo selecionado: ' + file.name);
                        statusDiv.style.color = 'var(--success-text)';
                        statusDiv.style.background = 'var(--success-bg)';
                        statusDiv.style.border = '1px solid var(--success-border)';
                        qtdGroup.style.display = 'block';
                        ignorarCabecalhoGroup.style.display = 'block';
                        previewButtonGroup.style.display = 'block';
                    } else {
                        // Erro: mostrar mensagem de erro
                        statusDiv.textContent = '✗ ' + (data.erro || 'Erro ao carregar planilha');
                        statusDiv.style.color = 'var(--error-text)';
                        statusDiv.style.background = 'var(--error-bg)';
                        statusDiv.style.border = '1px solid var(--error-border)';
                        qtdGroup.style.display = 'none';
                        ignorarCabecalhoGroup.style.display = 'none';
                        previewButtonGroup.style.display = 'none';
                        // Limpar seleção do arquivo
                        planilhaInput.value = '';
                    }
                } catch (error) {
                    // Erro de rede ou outro erro
                    statusDiv.textContent = '✗ Erro ao carregar planilha: ' + error.message;
                    statusDiv.style.color = 'var(--error-text)';
                    statusDiv.style.background = 'var(--error-bg)';
                    statusDiv.style.border = '1px solid var(--error-border)';
                    qtdGroup.style.display = 'none';
                    ignorarCabecalhoGroup.style.display = 'none';
                    previewButtonGroup.style.display = 'none';
                    // Limpar seleção do arquivo
                    planilhaInput.value = '';
                } finally {
                    planilhaInput.disabled = false;
                }
            } else {
                statusDiv.textContent = '';
                statusDiv.style.display = 'none';
                qtdGroup.style.display = 'none';
                ignorarCabecalhoGroup.style.display = 'none';
                previewButtonGroup.style.display = 'none';
            }
        });
    }

    // Event listeners para templates
    const btnSalvarTemplate = document.getElementById('btn-salvar-template');
    const btnCarregarTemplate = document.getElementById('btn-carregar-template');
    const modalSalvarTemplate = document.getElementById('modal-salvar-template');
    const modalListarTemplates = document.getElementById('modal-listar-templates');
    const nomeTemplateInput = document.getElementById('nome-template-input');
    const btnConfirmarSalvarTemplate = document.getElementById('btn-confirmar-salvar-template');
    const btnCancelarSalvarTemplate = document.getElementById('btn-cancelar-salvar-template');
    const btnFecharListarTemplates = document.getElementById('btn-fechar-listar-templates');
    const listaTemplatesContainer = document.getElementById('lista-templates-container');
    
    // Abrir modal de salvar template
    if (btnSalvarTemplate) {
        btnSalvarTemplate.addEventListener('click', function() {
            const titulo = document.getElementById('ds_titulo').value.trim();
            const descricao = document.getElementById('ds_chamado').value.trim();
            
            if (!titulo && !descricao) {
                return;
            }
            
            // Limpa o campo e mostra o modal
            if (nomeTemplateInput) {
                nomeTemplateInput.value = '';
            }
            if (modalSalvarTemplate) {
                modalSalvarTemplate.style.display = 'flex';
                if (nomeTemplateInput) {
                    nomeTemplateInput.focus();
                }
            }
        });
    }
    
    // Confirmar salvar template
    if (btnConfirmarSalvarTemplate) {
        btnConfirmarSalvarTemplate.addEventListener('click', async function() {
            const nomeTemplate = nomeTemplateInput ? nomeTemplateInput.value.trim() : '';
            
            if (!nomeTemplate) {
                return;
            }
            
            const titulo = document.getElementById('ds_titulo').value.trim();
            const descricao = document.getElementById('ds_chamado').value.trim();
            
            try {
                btnConfirmarSalvarTemplate.disabled = true;
                btnConfirmarSalvarTemplate.textContent = 'Salvando...';
                
                const response = await fetch('/chamado/template/salvar', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        nome_template: nomeTemplate,
                        titulo: titulo,
                        descricao: descricao
                    })
                });
                
                const data = await response.json();
                
                if (data.sucesso) {
                    if (modalSalvarTemplate) {
                        modalSalvarTemplate.style.display = 'none';
                    }
                } else {
                    console.error('Erro ao salvar template:', data.mensagem || 'Erro desconhecido');
                }
            } catch (error) {
                console.error('Erro ao salvar template:', error);
            } finally {
                btnConfirmarSalvarTemplate.disabled = false;
                btnConfirmarSalvarTemplate.textContent = 'Salvar';
            }
        });
    }
    
    // Cancelar salvar template
    if (btnCancelarSalvarTemplate) {
        btnCancelarSalvarTemplate.addEventListener('click', function() {
            if (modalSalvarTemplate) {
                modalSalvarTemplate.style.display = 'none';
            }
        });
    }
    
    // Fechar modal de listar templates
    if (btnFecharListarTemplates) {
        btnFecharListarTemplates.addEventListener('click', function() {
            if (modalListarTemplates) {
                modalListarTemplates.style.display = 'none';
            }
        });
    }
    
    // Fechar modais ao clicar fora
    if (modalSalvarTemplate) {
        modalSalvarTemplate.addEventListener('click', function(e) {
            if (e.target === modalSalvarTemplate) {
                modalSalvarTemplate.style.display = 'none';
            }
        });
    }
    
    if (modalListarTemplates) {
        modalListarTemplates.addEventListener('click', function(e) {
            if (e.target === modalListarTemplates) {
                modalListarTemplates.style.display = 'none';
            }
        });
    }
    
    // Carregar template
    if (btnCarregarTemplate) {
        btnCarregarTemplate.addEventListener('click', async function() {
            try {
                // Primeiro, lista os templates
                const responseListar = await fetch('/chamado/template/listar');
                const dataListar = await responseListar.json();
                
                if (!dataListar.sucesso || !dataListar.templates || dataListar.templates.length === 0) {
                    console.log('Nenhum template encontrado');
                    return;
                }
                
                // Se houver apenas 1 template, carrega diretamente
                if (dataListar.templates.length === 1) {
                    const template = dataListar.templates[0];
                    carregarTemplateSelecionado(template.nome);
                } else {
                    // Se houver mais de 1, mostra lista
                    mostrarListaTemplates(dataListar.templates);
                }
            } catch (error) {
                console.error('Erro ao listar templates:', error);
            }
        });
    }
    
    // Função para mostrar lista de templates
    function mostrarListaTemplates(templates) {
        if (!listaTemplatesContainer || !modalListarTemplates) {
            return;
        }
        
        listaTemplatesContainer.innerHTML = '';
        
        templates.forEach(template => {
            const templateItem = document.createElement('div');
            templateItem.style.cssText = 'padding: 12px; margin-bottom: 8px; border: 1px solid var(--border-primary, #ddd); border-radius: 4px; transition: background 0.2s; display: flex; justify-content: space-between; align-items: center;';
            templateItem.style.backgroundColor = 'var(--bg-secondary, #f5f5f5)';
            
            const templateInfo = document.createElement('div');
            templateInfo.style.cssText = 'flex: 1; cursor: pointer;';
            templateInfo.innerHTML = `
                <div style="font-weight: 600; color: var(--text-primary, #333); margin-bottom: 4px;">${escapeHtml(template.nome)}</div>
                <div style="font-size: 12px; color: var(--text-secondary, #666); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    ${escapeHtml(template.titulo || 'Sem título')}
                </div>
            `;
            
            templateInfo.addEventListener('mouseenter', function() {
                templateItem.style.backgroundColor = 'var(--bg-tertiary, #e5e5e5)';
            });
            
            templateInfo.addEventListener('mouseleave', function() {
                templateItem.style.backgroundColor = 'var(--bg-secondary, #f5f5f5)';
            });
            
            templateInfo.addEventListener('click', function() {
                carregarTemplateSelecionado(template.nome);
                modalListarTemplates.style.display = 'none';
            });
            
            const btnExcluir = document.createElement('button');
            btnExcluir.type = 'button';
            btnExcluir.textContent = 'Excluir';
            btnExcluir.style.cssText = 'padding: 6px 12px; font-size: 12px; background: var(--btn-primary-bg, #6b7280); color: white; border: none; border-radius: 4px; cursor: pointer; margin-left: 10px;';
            btnExcluir.addEventListener('mouseenter', function() {
                this.style.backgroundColor = 'var(--btn-primary-bg-hover, #4b5563)';
            });
            btnExcluir.addEventListener('mouseleave', function() {
                this.style.backgroundColor = 'var(--btn-primary-bg, #6b7280)';
            });
            btnExcluir.addEventListener('click', async function(e) {
                e.stopPropagation(); // Evita que o clique no botão dispare o clique no item
                if (confirm(`Tem certeza que deseja excluir o template "${template.nome}"?`)) {
                    await excluirTemplate(template.nome);
                    // Recarrega a lista após exclusão
                    const responseListar = await fetch('/chamado/template/listar');
                    const dataListar = await responseListar.json();
                    if (dataListar.sucesso && dataListar.templates) {
                        if (dataListar.templates.length === 0) {
                            modalListarTemplates.style.display = 'none';
                        } else {
                            mostrarListaTemplates(dataListar.templates);
                        }
                    }
                }
            });
            
            templateItem.appendChild(templateInfo);
            templateItem.appendChild(btnExcluir);
            listaTemplatesContainer.appendChild(templateItem);
        });
        
        modalListarTemplates.style.display = 'flex';
    }
    
    // Função para excluir template
    async function excluirTemplate(nomeTemplate) {
        try {
            const response = await fetch(`/chamado/template/excluir?nome_template=${encodeURIComponent(nomeTemplate)}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            
            if (data.sucesso) {
                console.log(`Template "${nomeTemplate}" excluído com sucesso`);
            } else {
                console.error('Erro ao excluir template:', data.mensagem || 'Erro desconhecido');
            }
        } catch (error) {
            console.error('Erro ao excluir template:', error);
        }
    }
    
    // Função para carregar template selecionado
    async function carregarTemplateSelecionado(nomeTemplate) {
        try {
            btnCarregarTemplate.disabled = true;
            btnCarregarTemplate.textContent = 'Carregando...';
            
            const response = await fetch(`/chamado/template/carregar?nome_template=${encodeURIComponent(nomeTemplate)}`);
            const data = await response.json();
            
            if (data.sucesso && data.template) {
                // Preenche os campos com o template
                const tituloInput = document.getElementById('ds_titulo');
                const descricaoInput = document.getElementById('ds_chamado');
                
                if (tituloInput && data.template.titulo) {
                    tituloInput.value = data.template.titulo;
                }
                
                if (descricaoInput && data.template.descricao) {
                    descricaoInput.value = data.template.descricao;
                }
            } else {
                console.error('Erro ao carregar template:', data.mensagem || 'Template não encontrado');
            }
        } catch (error) {
            console.error('Erro ao carregar template:', error);
        } finally {
            btnCarregarTemplate.disabled = false;
            btnCarregarTemplate.textContent = 'Carregar Template';
        }
    }

    // Abrir modal de prévia
    if (btnPreview) {
        btnPreview.addEventListener('click', async function() {
            const titulo = document.getElementById('ds_titulo').value;
            const descricao = document.getElementById('ds_chamado').value;
            const solicitante = document.getElementById('solicitante') ? document.getElementById('solicitante').value : '';
            const qtdChamados = parseInt(document.getElementById('qtd_chamados').value) || 5;
            const ignorarPrimeiraLinha = document.getElementById('ignorar_primeira_linha').checked;

            if (!titulo || !descricao) {
                alert('Por favor, preencha o título e a descrição antes de visualizar a prévia.');
                return;
            }

            // Mostrar modal
            modalPreview.style.display = 'flex';
            modalLoading.style.display = 'block';
            modalError.style.display = 'none';
            modalPreviewContent.style.display = 'none';

            try {
                const response = await fetch('/chamado/preview', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        titulo: titulo,
                        descricao: descricao,
                        solicitante: solicitante || null,
                        qtd_chamados: qtdChamados,
                        ignorar_primeira_linha: ignorarPrimeiraLinha
                    })
                });

                const data = await response.json();

                modalLoading.style.display = 'none';

                if (!response.ok || data.erro) {
                    modalError.textContent = data.erro || 'Erro ao gerar prévia';
                    modalError.style.display = 'block';
                    return;
                }

                // Exibir prévia
                let html = '';
                if (data.total_linhas) {
                    html += `<div style="margin-bottom: 16px; padding: 12px; background: var(--bg-section); border-radius: var(--border-radius); border: 1px solid var(--border-primary);">
                        <strong style="color: var(--text-primary);">Total de linhas disponíveis:</strong> 
                        <span style="color: var(--text-secondary);">${data.total_linhas}</span>
                    </div>`;
                }

                if (data.preview && data.preview.length > 0) {
                    data.preview.forEach(function(item) {
                        html += `<div style="margin-bottom: 20px; padding: 16px; background: var(--bg-section); border-radius: var(--border-radius); border: 1px solid var(--border-primary);">`;
                        html += `<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">`;
                        html += `<span style="color: var(--text-muted); font-size: 13px; font-weight: 600;">Linha ${item.linha}:</span>`;
                        if (item.erro) {
                            html += `<span style="color: var(--error-text); font-size: 13px;">⚠️ ${item.erro}</span>`;
                        } else {
                            html += `<span style="color: var(--success-text); font-size: 13px;">✓ Processado</span>`;
                        }
                        html += `</div>`;
                        html += `<div style="margin-bottom: 8px;">`;
                        html += `<strong style="color: var(--text-primary); font-size: 14px; display: block; margin-bottom: 4px;">Título:</strong>`;
                        html += `<div style="color: var(--text-secondary); padding: 10px; background: var(--bg-input); border-radius: var(--border-radius); border: 1px solid var(--border-primary);">${escapeHtml(item.titulo || '(vazio)')}</div>`;
                        html += `</div>`;
                        html += `<div style="margin-bottom: 8px;">`;
                        html += `<strong style="color: var(--text-primary); font-size: 14px; display: block; margin-bottom: 4px;">Descrição:</strong>`;
                        html += `<div style="color: var(--text-secondary); padding: 10px; background: var(--bg-input); border-radius: var(--border-radius); border: 1px solid var(--border-primary); white-space: pre-wrap;">${escapeHtml(item.descricao || '(vazio)')}</div>`;
                        html += `</div>`;
                        if (item.solicitante !== undefined && item.solicitante !== null && item.solicitante !== '') {
                            html += `<div>`;
                            html += `<strong style="color: var(--text-primary); font-size: 14px; display: block; margin-bottom: 4px;">Solicitante:</strong>`;
                            html += `<div style="color: var(--text-secondary); padding: 10px; background: var(--bg-input); border-radius: var(--border-radius); border: 1px solid var(--border-primary);">${escapeHtml(item.solicitante)}</div>`;
                            html += `</div>`;
                        }
                        html += `</div>`;
                    });
                } else {
                    html += `<div style="text-align: center; padding: 40px; color: var(--text-muted);">Nenhuma prévia disponível</div>`;
                }

                modalPreviewContent.innerHTML = html;
                modalPreviewContent.style.display = 'block';
            } catch (error) {
                modalLoading.style.display = 'none';
                modalError.textContent = 'Erro ao carregar prévia: ' + error.message;
                modalError.style.display = 'block';
            }
        });
    }

    // Fechar modal
    if (btnCloseModal) {
        btnCloseModal.addEventListener('click', function() {
            modalPreview.style.display = 'none';
        });
    }

    // Fechar modal ao clicar fora
    if (modalPreview) {
        modalPreview.addEventListener('click', function(e) {
            if (e.target === modalPreview) {
                modalPreview.style.display = 'none';
            }
        });
    }

    // Fechar modal com ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modalPreview && modalPreview.style.display === 'flex') {
            modalPreview.style.display = 'none';
        }
    });

    // Validação e interceptação do formulário
    if (formChamado) {
        formChamado.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Validação do campo telefone
            const telefoneInput = document.getElementById('telefone_contato');
            const telefoneError = document.getElementById('telefone-error');
            
            if (!telefoneInput || !telefoneInput.value || !telefoneInput.value.trim()) {
                // Mostrar erro visual
                if (telefoneInput) {
                    telefoneInput.style.borderColor = 'var(--error-border)';
                    telefoneInput.style.backgroundColor = 'var(--error-bg)';
                }
                if (telefoneError) {
                    telefoneError.style.display = 'block';
                }
                
                // Scroll para o campo
                if (telefoneInput) {
                    telefoneInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    telefoneInput.focus();
                }
                
                // Mostrar mensagem de erro no topo
                const errorFlash = document.createElement('div');
                errorFlash.className = 'flash error';
                errorFlash.textContent = '⚠️ O campo Telefone de Contato é obrigatório para abrir um chamado.';
                const formSection = document.querySelector('.form-section-box');
                if (formSection && formSection.parentNode) {
                    formSection.parentNode.insertBefore(errorFlash, formSection);
                    setTimeout(() => {
                        errorFlash.remove();
                    }, 5000);
                }
                
                return;
            } else {
                // Remover erro visual se o campo estiver preenchido
                if (telefoneInput) {
                    telefoneInput.style.borderColor = '';
                    telefoneInput.style.backgroundColor = '';
                }
                if (telefoneError) {
                    telefoneError.style.display = 'none';
                }
            }
            
            const titulo = document.getElementById('ds_titulo').value;
            const descricao = document.getElementById('ds_chamado').value;
            
            if (!titulo || !descricao) {
                alert('Por favor, preencha o título e a descrição do chamado.');
                return false;
            }
            
            // Mostrar modal de processamento
            const modalProcessamento = document.getElementById('modal-processamento');
            const modalProcessamentoChamados = document.getElementById('modal-processamento-chamados');
            const modalProcessamentoContador = document.getElementById('modal-processamento-contador');
            
            modalProcessamento.style.display = 'flex';
            modalProcessamentoChamados.innerHTML = '';
            modalProcessamentoContador.textContent = 'Preparando...';
            
            // Criar FormData com todos os dados do formulário
            const formData = new FormData(formChamado);
            
            try {
                // Fazer requisição AJAX com header Accept: application/json
                const response = await fetch('/chamado', {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json'
                    },
                    body: formData
                });
                
                const data = await response.json();
                
                const modalProcessamentoLoading = document.getElementById('modal-processamento-loading');
                const modalProcessamentoConcluido = document.getElementById('modal-processamento-concluido');
                const modalProcessamentoFooter = document.getElementById('modal-processamento-footer');
                const btnConcluir = document.getElementById('btn-concluir-processamento');
                
                // Função para finalizar processamento e mostrar botão
                const finalizarProcessamento = () => {
                    if (modalProcessamentoLoading) modalProcessamentoLoading.style.display = 'none';
                    if (modalProcessamentoConcluido) modalProcessamentoConcluido.style.display = 'block';
                    if (modalProcessamentoFooter) modalProcessamentoFooter.style.display = 'flex';
                    
                    // Adicionar evento ao botão concluir (remover listeners anteriores)
                    if (btnConcluir) {
                        // Remover listeners anteriores
                        const novoBtn = btnConcluir.cloneNode(true);
                        btnConcluir.parentNode.replaceChild(novoBtn, btnConcluir);
                        
                        // Adicionar novo listener
                        novoBtn.addEventListener('click', function() {
                            modalProcessamento.style.display = 'none';
                            window.location.reload();
                        });
                    }
                };
                
                if (data.sucesso) {
                    // Verificar se é chamado único ou múltiplos
                    if (data.chamado_id) {
                        // Chamado único
                        adicionarChamadoAoModal(modalProcessamentoChamados, data.chamado_id, true);
                        modalProcessamentoContador.textContent = 'Chamado criado com sucesso!';
                        
                        // Ocultar spinner e mostrar conclusão
                        setTimeout(finalizarProcessamento, 500);
                    } else if (data.chamados_ids && data.chamados_ids.length > 0) {
                        // Múltiplos chamados
                        modalProcessamentoContador.textContent = `Processando ${data.chamados_ids.length} chamado(s)...`;
                        
                        // Calcular total de itens (sucessos + erros)
                        const totalItens = data.chamados_ids.length + (data.detalhes ? data.detalhes.filter(d => !d.sucesso).length : 0);
                        let itensProcessados = 0;
                        
                        // Adicionar cada chamado ao modal com delay para mostrar progresso
                        data.chamados_ids.forEach((chamadoId, index) => {
                            setTimeout(() => {
                                adicionarChamadoAoModal(modalProcessamentoChamados, chamadoId, true);
                                itensProcessados++;
                                modalProcessamentoContador.textContent = `${itensProcessados} de ${totalItens} item(s) processado(s)`;
                                
                                // Se é o último chamado de sucesso, verificar se há erros
                                if (index === data.chamados_ids.length - 1) {
                                    // Processar erros se houver
                                    if (data.detalhes) {
                                        const erros = data.detalhes.filter(d => !d.sucesso);
                                        erros.forEach((detalhe, erroIndex) => {
                                            setTimeout(() => {
                                                adicionarChamadoAoModal(modalProcessamentoChamados, null, false, detalhe.mensagem || 'Erro ao criar chamado');
                                                itensProcessados++;
                                                modalProcessamentoContador.textContent = `${itensProcessados} de ${totalItens} item(s) processado(s)`;
                                                
                                                // Se é o último erro, finalizar
                                                if (erroIndex === erros.length - 1) {
                                                    setTimeout(() => {
                                                        // Atualizar contador final
                                                        if (data.chamados_erro > 0) {
                                                            modalProcessamentoContador.textContent = `${data.chamados_criados} criado(s), ${data.chamados_erro} erro(s)`;
                                                        } else {
                                                            modalProcessamentoContador.textContent = `${data.chamados_criados} chamado(s) criado(s) com sucesso!`;
                                                        }
                                                        finalizarProcessamento();
                                                    }, 300);
                                                }
                                            }, (erroIndex + 1) * 200);
                                        });
                                        
                                        // Se não há erros, finalizar imediatamente
                                        if (erros.length === 0) {
                                            setTimeout(() => {
                                                modalProcessamentoContador.textContent = `${data.chamados_criados} chamado(s) criado(s) com sucesso!`;
                                                finalizarProcessamento();
                                            }, 300);
                                        }
                                    } else {
                                        // Sem detalhes, finalizar imediatamente
                                        setTimeout(() => {
                                            modalProcessamentoContador.textContent = `${data.chamados_criados} chamado(s) criado(s) com sucesso!`;
                                            finalizarProcessamento();
                                        }, 300);
                                    }
                                }
                            }, index * 200); // Delay para mostrar progresso
                        });
                    } else {
                        // Nenhum chamado criado
                        modalProcessamentoContador.textContent = 'Nenhum chamado foi criado';
                        setTimeout(finalizarProcessamento, 500);
                    }
                } else {
                    // Erro
                    modalProcessamentoContador.textContent = 'Erro no processamento';
                    adicionarChamadoAoModal(modalProcessamentoChamados, null, false, data.erro || 'Erro desconhecido');
                    
                    setTimeout(() => {
                        if (modalProcessamentoLoading) modalProcessamentoLoading.style.display = 'none';
                        if (modalProcessamentoFooter) modalProcessamentoFooter.style.display = 'flex';
                        
                        // Adicionar evento ao botão concluir
                        if (btnConcluir) {
                            const novoBtn = btnConcluir.cloneNode(true);
                            btnConcluir.parentNode.replaceChild(novoBtn, btnConcluir);
                            novoBtn.addEventListener('click', function() {
                                modalProcessamento.style.display = 'none';
                            });
                        }
                    }, 500);
                }
            } catch (error) {
                console.error('Erro ao processar chamado:', error);
                const modalProcessamentoLoading = document.getElementById('modal-processamento-loading');
                const modalProcessamentoFooter = document.getElementById('modal-processamento-footer');
                const btnConcluir = document.getElementById('btn-concluir-processamento');
                
                modalProcessamentoContador.textContent = 'Erro ao processar';
                adicionarChamadoAoModal(modalProcessamentoChamados, null, false, error.message);
                
                setTimeout(() => {
                    if (modalProcessamentoLoading) modalProcessamentoLoading.style.display = 'none';
                    if (modalProcessamentoFooter) modalProcessamentoFooter.style.display = 'flex';
                }, 500);
                
                // Adicionar evento ao botão concluir
                if (btnConcluir) {
                    btnConcluir.addEventListener('click', function() {
                        modalProcessamento.style.display = 'none';
                    });
                }
            }
        });
    }

    // Função auxiliar para formatar data (apenas dia e mês)
    function formatarDataDiaMes(dataStr) {
        if (!dataStr) return 'N/A';
        try {
            // Formato ISO esperado: "2025-11-17T13:52:04.637-0400" ou "2025-11-17T13:52:04"
            if (dataStr.includes('T')) {
                const dataParte = dataStr.split('T')[0]; // "2025-11-17"
                const partesData = dataParte.split('-');
                if (partesData.length >= 3) {
                    return `${partesData[2]}/${partesData[1]}`; // "17/11"
                }
            }
            // Formato antigo: "17/11/2025 17:52" ou "17/11/2025"
            const partes = dataStr.split(' ');
            const dataParte = partes[0]; // "17/11/2025"
            const partesData = dataParte.split('/');
            if (partesData.length >= 2) {
                return `${partesData[0]}/${partesData[1]}`; // "17/11"
            }
            return dataStr;
        } catch (e) {
            return dataStr;
        }
    }

    // Função auxiliar para obter três primeiras palavras
    function obterTresPrimeirasPalavras(texto) {
        if (!texto) return 'N/A';
        const palavras = texto.trim().split(/\s+/);
        if (palavras.length >= 3) {
            return `${palavras[0]} ${palavras[1]} ${palavras[2]}`;
        } else if (palavras.length === 2) {
            return `${palavras[0]} ${palavras[1]}`;
        }
        return palavras[0] || 'N/A';
    }

    // Função auxiliar para filtrar apenas letras (remove números e caracteres especiais)
    function filtrarApenasLetras(texto) {
        if (!texto) return 'N/A';
        // Remove tudo que não for letra (incluindo acentos) ou espaço, mantém espaços múltiplos como um único espaço
        const apenasLetras = texto.replace(/[^a-zA-ZÀ-ÿ\s]/g, '').replace(/\s+/g, ' ').trim();
        return apenasLetras || 'N/A';
    }

    // Função para criar botão de chamado
    function criarItemChamado(chamado) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'chamado-btn';
        button.dataset.processInstanceId = chamado.processInstanceId;
        
        const processInstanceId = chamado.processInstanceId || 'N/A';
        
        // Extrai informações dos detalhes
        const formFields = chamado.detalhes?.formFields || {};
        const numSolicitacao = formFields.num_solicitacao || processInstanceId;
        const processId = chamado.processId || '';
        
        // Define o campo de título baseado no tipo de chamado
        let dsTitulo = 'Sem título';
        if (processId === 'Abertura de Chamados') {
            dsTitulo = formFields.ds_titulo || chamado.processDescription || 'Sem título';
        } else if (processId === 'SAIS - Solicitação de Alteração em Item de Serviço') {
            dsTitulo = formFields.ds_assunto || chamado.processDescription || 'Sem título';
        } else {
            dsTitulo = formFields.ds_titulo || chamado.processDescription || 'Sem título';
        }
        
        const dtAbertura = formatarDataDiaMes(chamado.startDate || '');
        const nmEmitente = filtrarApenasLetras(formFields.nm_emitente || 'N/A');
        
        // Define o campo para o tooltip baseado no tipo de processo
        let tooltipTexto = 'Sem descrição';
        if (processId === 'SAIS - Solicitação de Alteração em Item de Serviço') {
            tooltipTexto = formFields.ds_objetivo || 'Sem descrição';
        } else {
            tooltipTexto = formFields.ds_chamado || 'Sem descrição';
        }
        
        // Cria estrutura HTML com as informações
        button.innerHTML = `
            <div class="chamado-btn-content">
                <div class="chamado-btn-header">
                    <span class="chamado-num">#${numSolicitacao}</span>
                    <span class="chamado-data">${dtAbertura}</span>
                </div>
                <div class="chamado-titulo">${dsTitulo}</div>
                <div class="chamado-emitente">${nmEmitente}</div>
            </div>
        `;
        
        button.title = tooltipTexto;
        
        // Adiciona evento de clique para abrir detalhes
        button.addEventListener('click', function() {
            // Remove active de todos os botões
            document.querySelectorAll('.chamado-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Adiciona active ao botão clicado
            button.classList.add('active');
            
            // Abre o chamado no Fluig (nova aba)
            const fluigUrl = `https://fluig.uisa.com.br/portal/p/1/pageworkflowview?app_ecm_workflowview_detailsProcessInstanceID=${processInstanceId}`;
            window.open(fluigUrl, '_blank');
        });
        
        return button;
    }

    // Função para carregar e exibir chamados na sidebar
    async function carregarChamadosFila() {
        if (!chamadosList || !chamadosLoading) {
            console.warn('[carregarChamadosFila] Elementos da sidebar não encontrados');
            return;
        }
        
        // Verificar cache primeiro
        const cache = obterCache(CACHE_KEY_FILA);
        if (cache) {
            console.log('[carregarChamadosFila] Usando dados do cache');
            // Esconder loading e erros
            chamadosLoading.style.display = 'none';
            if (chamadosError) chamadosError.style.display = 'none';
            
            todosChamados = cache.chamados || [];
            paginaAtual = 1;
            renderizarChamadosFila();
            
            // Atualizar em background (sem bloquear UI)
            atualizarChamadosFilaEmBackground();
            return;
        }
        
        try {
            chamadosLoading.style.display = 'flex';
            if (chamadosError) chamadosError.style.display = 'none';
            chamadosList.innerHTML = '';
            if (chamadosPagination) chamadosPagination.style.display = 'none';
            
            console.log('[carregarChamadosFila] Fazendo requisição para /api/chamados/fila...');
            const response = await fetch('/api/chamados/fila');
            
            console.log('[carregarChamadosFila] Status da resposta:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('[carregarChamadosFila] Erro HTTP:', response.status, errorText);
                chamadosLoading.style.display = 'none';
                if (chamadosError) {
                    chamadosError.textContent = `Erro ao carregar chamados (${response.status}). Tente recarregar a página.`;
                    chamadosError.style.display = 'block';
                }
                return;
            }
            
            const data = await response.json();
            console.log('[carregarChamadosFila] Dados recebidos:', data);
            
            chamadosLoading.style.display = 'none';
            
            if (!data.sucesso) {
                console.warn('[carregarChamadosFila] Requisição não foi bem-sucedida:', data.erro);
                if (chamadosError) {
                    chamadosError.textContent = data.erro || 'Erro ao carregar chamados';
                    chamadosError.style.display = 'block';
                }
                return;
            }
            
            todosChamados = data.chamados || [];
            paginaAtual = 1;
            console.log('[carregarChamadosFila] Total de chamados:', todosChamados.length);
            
            // Salvar no cache
            salvarCache(CACHE_KEY_FILA, data);
            
            // Renderiza a primeira página
            renderizarChamadosFila();
            
            console.log('[carregarChamadosFila] Chamados renderizados com sucesso');
            
        } catch (error) {
            console.error('[carregarChamadosFila] Erro ao carregar chamados:', error);
            chamadosLoading.style.display = 'none';
            if (chamadosError) {
                chamadosError.textContent = `Erro ao carregar chamados: ${error.message}. Tente recarregar a página.`;
                chamadosError.style.display = 'block';
            }
        }
    }

    // Toggle da sidebar
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
        });
    }

    // Função genérica para renderizar paginação
    function renderizarPaginacao(container, totalItens, paginaAtualParam, itensPorPagina, callback) {
        if (!container) return;
        
        const totalPaginas = Math.ceil(totalItens / itensPorPagina);
        
        // Mostra paginação apenas se houver 11 ou mais chamados
        if (totalItens < 11) {
            container.style.display = 'none';
            return;
        }
        
        container.style.display = 'flex';
        container.innerHTML = '';
        
        // Cria container de paginação
        const paginationWrapper = document.createElement('div');
        paginationWrapper.className = 'pagination-wrapper';
        
        // Botões de página
        for (let i = 1; i <= totalPaginas; i++) {
            const pageBtn = document.createElement('button');
            pageBtn.type = 'button';
            pageBtn.className = 'pagination-btn';
            if (i === paginaAtualParam) {
                pageBtn.classList.add('active');
            }
            pageBtn.textContent = i;
            pageBtn.addEventListener('click', () => {
                callback(i);
            });
            paginationWrapper.appendChild(pageBtn);
        }
        
        container.appendChild(paginationWrapper);
    }
    
    // Função para renderizar paginação do grupo
    function renderizarPaginacaoGrupo(totalItens, paginaAtual, itensPorPagina) {
        renderizarPaginacao(
            chamadosGrupoPagination,
            totalItens,
            paginaAtual,
            itensPorPagina,
            (novaPagina) => {
                paginaAtualGrupo = novaPagina;
                renderizarChamadosGrupo();
            }
        );
    }
    
    // Função para renderizar paginação de MEUS CHAMADOS
    function renderizarPaginacaoFila(totalItens, paginaAtualParam, itensPorPagina) {
        renderizarPaginacao(
            chamadosPagination,
            totalItens,
            paginaAtualParam,
            itensPorPagina,
            (novaPagina) => {
                paginaAtual = novaPagina;
                renderizarChamadosFila();
            }
        );
    }
    
    // Função para renderizar chamados da página atual do grupo
    function renderizarChamadosGrupo() {
        if (!chamadosGrupoList) return;
        
        chamadosGrupoList.innerHTML = '';
        
        const inicio = (paginaAtualGrupo - 1) * itensPorPaginaGrupo;
        const fim = inicio + itensPorPaginaGrupo;
        const chamadosPagina = todosChamadosGrupo.slice(inicio, fim);
        
        if (chamadosPagina.length === 0) {
            chamadosGrupoList.innerHTML = '<div class="chamado-empty">Nenhum chamado encontrado</div>';
        } else {
            // Renderiza cada chamado como botão
            chamadosPagina.forEach(chamado => {
                const chamadoBtn = criarItemChamado(chamado);
                chamadosGrupoList.appendChild(chamadoBtn);
            });
            
            // Preenche com espaçadores invisíveis se houver menos de 10 itens para manter altura fixa
            const itensFaltantes = itensPorPaginaGrupo - chamadosPagina.length;
            if (itensFaltantes > 0) {
                // Cria um espaçador que replica a estrutura de um botão de chamado
                for (let i = 0; i < itensFaltantes; i++) {
                    const spacer = document.createElement('button');
                    spacer.type = 'button';
                    spacer.className = 'chamado-btn chamado-spacer';
                    spacer.disabled = true;
                    spacer.style.visibility = 'hidden';
                    spacer.style.pointerEvents = 'none';
                    spacer.innerHTML = `
                        <div class="chamado-btn-content">
                            <div class="chamado-btn-header">
                                <span class="chamado-num">#000000</span>
                                <span class="chamado-data">00/00</span>
                            </div>
                            <div class="chamado-titulo">Espaçador</div>
                            <div class="chamado-emitente">Espaçador</div>
                        </div>
                    `;
                    chamadosGrupoList.appendChild(spacer);
                }
            }
        }
        
        // Renderiza paginação (apenas se houver 11+ chamados)
        renderizarPaginacaoGrupo(todosChamadosGrupo.length, paginaAtualGrupo, itensPorPaginaGrupo);
    }
    
    // Função para renderizar chamados da página atual de MEUS CHAMADOS
    function renderizarChamadosFila() {
        if (!chamadosList) return;
        
        chamadosList.innerHTML = '';
        
        const inicio = (paginaAtual - 1) * itensPorPagina;
        const fim = inicio + itensPorPagina;
        const chamadosPagina = todosChamados.slice(inicio, fim);
        
        if (chamadosPagina.length === 0) {
            chamadosList.innerHTML = '<div class="chamado-empty">Nenhum chamado encontrado na sua fila</div>';
        } else {
            // Renderiza cada chamado como botão
            chamadosPagina.forEach(chamado => {
                const chamadoBtn = criarItemChamado(chamado);
                chamadosList.appendChild(chamadoBtn);
            });
            
            // Preenche com espaçadores invisíveis se houver menos de 10 itens para manter altura fixa
            const itensFaltantes = itensPorPagina - chamadosPagina.length;
            if (itensFaltantes > 0) {
                // Cria um espaçador que replica a estrutura de um botão de chamado
                for (let i = 0; i < itensFaltantes; i++) {
                    const spacer = document.createElement('button');
                    spacer.type = 'button';
                    spacer.className = 'chamado-btn chamado-spacer';
                    spacer.disabled = true;
                    spacer.style.visibility = 'hidden';
                    spacer.style.pointerEvents = 'none';
                    spacer.innerHTML = `
                        <div class="chamado-btn-content">
                            <div class="chamado-btn-header">
                                <span class="chamado-num">#000000</span>
                                <span class="chamado-data">00/00</span>
                            </div>
                            <div class="chamado-titulo">Espaçador</div>
                            <div class="chamado-emitente">Espaçador</div>
                        </div>
                    `;
                    chamadosList.appendChild(spacer);
                }
            }
        }
        
        // Renderiza paginação (apenas se houver 11+ chamados)
        renderizarPaginacaoFila(todosChamados.length, paginaAtual, itensPorPagina);
    }
    
    // Função para carregar chamados do grupo ITSM_TODOS
    async function carregarChamadosGrupo() {
        if (!chamadosGrupoList || !chamadosGrupoLoading) {
            console.warn('[carregarChamadosGrupo] Elementos da sidebar direita não encontrados');
            return;
        }
        
        // Verificar cache primeiro
        const cache = obterCache(CACHE_KEY_GRUPO);
        if (cache) {
            console.log('[carregarChamadosGrupo] Usando dados do cache');
            // Esconder loading e erros
            chamadosGrupoLoading.style.display = 'none';
            if (chamadosGrupoError) chamadosGrupoError.style.display = 'none';
            
            todosChamadosGrupo = cache.chamados || [];
            paginaAtualGrupo = 1;
            renderizarChamadosGrupo();
            
            // Atualizar em background (sem bloquear UI)
            atualizarChamadosGrupoEmBackground();
            return;
        }
        
        try {
            chamadosGrupoLoading.style.display = 'flex';
            if (chamadosGrupoError) chamadosGrupoError.style.display = 'none';
            chamadosGrupoList.innerHTML = '';
            if (chamadosGrupoPagination) chamadosGrupoPagination.style.display = 'none';
            
            console.log('[carregarChamadosGrupo] Fazendo requisição para /api/chamados/grupo-itsm-todos...');
            const response = await fetch('/api/chamados/grupo-itsm-todos');
            
            console.log('[carregarChamadosGrupo] Status da resposta:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('[carregarChamadosGrupo] Erro HTTP:', response.status, errorText);
                chamadosGrupoLoading.style.display = 'none';
                if (chamadosGrupoError) {
                    chamadosGrupoError.textContent = `Erro ao carregar chamados (${response.status}). Tente recarregar a página.`;
                    chamadosGrupoError.style.display = 'block';
                }
                return;
            }
            
            const data = await response.json();
            console.log('[carregarChamadosGrupo] Dados recebidos:', data);
            
            chamadosGrupoLoading.style.display = 'none';
            
            if (!data.sucesso) {
                console.warn('[carregarChamadosGrupo] Requisição não foi bem-sucedida:', data.erro);
                if (chamadosGrupoError) {
                    chamadosGrupoError.textContent = data.erro || 'Erro ao carregar chamados';
                    chamadosGrupoError.style.display = 'block';
                }
                return;
            }
            
            todosChamadosGrupo = data.chamados || [];
            paginaAtualGrupo = 1;
            console.log('[carregarChamadosGrupo] Total de chamados:', todosChamadosGrupo.length);
            
            // Salvar no cache
            salvarCache(CACHE_KEY_GRUPO, data);
            
            // Renderiza a primeira página
            renderizarChamadosGrupo();
            
            console.log('[carregarChamadosGrupo] Chamados renderizados com sucesso');
            
        } catch (error) {
            console.error('[carregarChamadosGrupo] Erro ao carregar chamados:', error);
            chamadosGrupoLoading.style.display = 'none';
            if (chamadosGrupoError) {
                chamadosGrupoError.textContent = `Erro ao carregar chamados: ${error.message}. Tente recarregar a página.`;
                chamadosGrupoError.style.display = 'block';
            }
        }
    }

    // Carrega chamados ao carregar a página
    if (chamadosList && chamadosLoading) {
        console.log('[chamado.js] Elementos da sidebar encontrados, iniciando carregamento de chamados...');
        carregarChamadosFila();
    } else {
        console.warn('[chamado.js] Elementos da sidebar não encontrados:', {
            chamadosList: !!chamadosList,
            chamadosLoading: !!chamadosLoading
        });
    }
    
    // Carrega chamados do grupo ao carregar a página
    if (chamadosGrupoList && chamadosGrupoLoading) {
        console.log('[chamado.js] Elementos da sidebar direita encontrados, iniciando carregamento de chamados do grupo...');
        carregarChamadosGrupo();
    } else {
        console.warn('[chamado.js] Elementos da sidebar direita não encontrados:', {
            chamadosGrupoList: !!chamadosGrupoList,
            chamadosGrupoLoading: !!chamadosGrupoLoading
        });
    }
});

// Função para adicionar chamado ao modal
function adicionarChamadoAoModal(container, chamadoId, sucesso, mensagemErro = null) {
    const chamadoItem = document.createElement('div');
    chamadoItem.className = `chamado-item ${sucesso ? 'success' : 'error'}`;
    
    if (sucesso && chamadoId) {
        chamadoItem.innerHTML = `
            <div class="chamado-item-icon">✓</div>
            <div class="chamado-item-content">
                <div class="chamado-item-id">Chamado #${chamadoId}</div>
                <div class="chamado-item-mensagem">Criado com sucesso</div>
            </div>
        `;
    } else {
        chamadoItem.innerHTML = `
            <div class="chamado-item-icon">✗</div>
            <div class="chamado-item-content">
                <div class="chamado-item-id">Erro</div>
                <div class="chamado-item-mensagem">${mensagemErro || 'Falha ao criar chamado'}</div>
            </div>
        `;
    }
    
    container.appendChild(chamadoItem);
    container.scrollTop = container.scrollHeight;
}



// Função para atualizar a seleção visual no dropdown
function atualizarSelecao(items) {
    items.forEach((item, index) => {
        if (index === itemSelecionado) {
            item.classList.add('selected');
            item.scrollIntoView({ block: 'nearest' });
        } else {
            item.classList.remove('selected');
        }
    });
}


// Função para carregar lista de serviços
function carregarServicos() {
    fetch('/listar_servicos')
        .then(response => response.json())
        .then(data => {
            if (data.sucesso) {
                servicosDisponiveis = data.servicos;
                console.log('Serviços carregados:', servicosDisponiveis.length);
                
                // Se o campo de serviço estiver em foco, mostrar dropdown automaticamente
                const servicoInput = document.getElementById('servico');
                if (servicoInput && document.activeElement === servicoInput) {
                    mostrarDropdown();
                }
            } else {
                console.error('Erro ao carregar serviços:', data.erro);
            }
        })
        .catch(error => {
            console.error('Erro ao carregar serviços:', error);
        });
}




// Função para mostrar dropdown de serviços
function mostrarDropdown() {
    const dropdown = document.getElementById('servico-dropdown');
    const servicoInput = document.getElementById('servico');
    
    if (servicosDisponiveis.length === 0) {
        // Se os serviços ainda não foram carregados, tenta carregar
        carregarServicos();
        return;
    }
    
    // Filtra serviços baseado no texto digitado
    const textoFiltro = servicoInput.value.trim().toLowerCase();
    let servicosFiltrados;
    
    if (textoFiltro.length === 0) {
        // Se não há texto, mostrar todos os serviços
        servicosFiltrados = servicosDisponiveis;
    } else {
        // Se há texto, filtrar os serviços
        servicosFiltrados = servicosDisponiveis.filter(servico => {
            const servicoNome = (servico.servico || '').toLowerCase();
            const grupoServico = (servico.grupo_servico || '').toLowerCase();
            const itemServico = (servico.item_servico || '').toLowerCase();
            const numeroDoc = (servico.numero_documento || '').toLowerCase();
            const documentid = (servico.documentid || '').toLowerCase();
            
            return servicoNome.includes(textoFiltro) ||
                   grupoServico.includes(textoFiltro) ||
                   itemServico.includes(textoFiltro) ||
                   numeroDoc.includes(textoFiltro) ||
                   documentid.includes(textoFiltro);
        });
    }
    
    if (servicosFiltrados.length > 0) {
        // Cria HTML do dropdown
        let dropdownHTML = '';
        servicosFiltrados.forEach((servico, index) => {
            const nomeEscapado = escapeHtml(servico.servico || '');
            const documentid = servico.documentid || '';
            dropdownHTML += `
                <div class="dropdown-item" data-index="${index}" data-id="${documentid}" data-servico="${nomeEscapado}" style="cursor: pointer;">
                    <div style="font-weight: 600; color: var(--text-primary);">${nomeEscapado}</div>
                    ${documentid ? `<div style="font-size: 12px; color: var(--text-muted);">ID: ${escapeHtml(documentid)}</div>` : ''}
                    ${servico.grupo_servico ? `<div style="font-size: 12px; color: var(--text-muted);">Grupo: ${escapeHtml(servico.grupo_servico)}</div>` : ''}
                    ${servico.item_servico ? `<div style="font-size: 12px; color: var(--text-muted);">Item: ${escapeHtml(servico.item_servico)}</div>` : ''}
                </div>
            `;
        });
        
        dropdown.innerHTML = dropdownHTML;
        dropdown.style.display = 'block';
        dropdownAtivo = true;
        itemSelecionado = -1;
        
        // Adicionar eventos de clique nos itens
        dropdown.querySelectorAll('.dropdown-item').forEach(function(item) {
            // Ignorar a mensagem informativa
            if (item.getAttribute('data-id')) {
                item.addEventListener('click', function() {
                    const nome = this.getAttribute('data-servico');
                    const documentid = this.getAttribute('data-id');
                    selecionarServico(nome, documentid);
                });
            }
        });
    } else {
        // Se não há resultados, ocultar o dropdown completamente
        dropdown.innerHTML = '';
        dropdown.style.display = 'none';
        dropdownAtivo = false;
    }
}




// Função para selecionar um serviço
function selecionarServico(nomeServico, documentid) {
    const servicoInput = document.getElementById('servico');
    const servicoIdInput = document.getElementById('servico_id');
    
    servicoInput.value = nomeServico;
    
    if (servicoIdInput) {
        servicoIdInput.value = documentid;
    }
    
    // Esconde o dropdown e limpa o conteúdo
    const dropdown = document.getElementById('servico-dropdown');
    dropdown.innerHTML = '';
    dropdown.style.display = 'none';
    dropdownAtivo = false;
    itemSelecionado = -1;
    
    // Busca e preenche os dados do serviço usando o documentid
    if (documentid) {
        buscarESelecionarServico(documentid);
    }
}


// Função para buscar e preencher dados do serviço selecionado
// Primeiro verifica se o arquivo JSON já existe localmente, se não, busca da API
function buscarESelecionarServico(documentid) {
    if (!documentid) {
        console.error('DocumentID não fornecido');
        return;
    }
    
    fetch('/buscar_detalhes_servico', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            documentid: documentid
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso && data.servico) {
            preencherCamposServico(data.servico);
            const fonte = data.fonte || 'desconhecida';
            console.log(`Serviço selecionado e campos preenchidos (fonte: ${fonte}):`, data.servico);
        } else {
            console.error('Erro ao buscar detalhes do serviço:', data.erro || 'Serviço não encontrado');
        }
    })
    .catch(error => {
        console.error('Erro ao buscar detalhes do serviço:', error);
    });
}



// Função para preencher os campos de classificação com os dados do serviço
function preencherCamposServico(servicoData) {
    // Preenche os campos de classificação com os dados do serviço
    const dsGrupoServico = document.getElementById('ds_grupo_servico');
    const itemServico = document.getElementById('item_servico');
    const servicoInput = document.getElementById('servico');
    const servicoIdInput = document.getElementById('servico_id');
    const urgAlta = document.getElementById('urg_alta');
    const urgMedia = document.getElementById('urg_media');
    const urgBaixa = document.getElementById('urg_baixa');
    const dsRespServico = document.getElementById('ds_resp_servico');
    const equipeResponsavel = document.getElementById('equipe_responsavel');
    const urgenciaSelect = document.getElementById('ds_urgencia');
    
    if (dsGrupoServico) dsGrupoServico.value = servicoData.grupo_servico || '';
    if (itemServico) itemServico.value = servicoData.item_servico || '';
    if (servicoInput) servicoInput.value = servicoData.servico || '';
    if (servicoIdInput) servicoIdInput.value = servicoData.documentid || '';
    if (urgAlta) urgAlta.value = servicoData.urgencia_alta || '';
    if (urgMedia) urgMedia.value = servicoData.urgencia_media || '';
    if (urgBaixa) urgBaixa.value = servicoData.urgencia_baixa || '';
    if (dsRespServico) dsRespServico.value = servicoData.ds_responsavel || '';
    if (equipeResponsavel) equipeResponsavel.value = servicoData.equipe_executante || '';
    
    // Define a urgência baseada no impacto (valores do select: Baixa, Média, Alta)
    if (urgenciaSelect && servicoData.impacto) {
        const impacto = servicoData.impacto.toString().toLowerCase();
        switch(impacto) {
            case '1':
            case 'muito alto':
                urgenciaSelect.value = 'Alta';
                break;
            case '2':
            case 'alto':
                urgenciaSelect.value = 'Alta';
                break;
            case '3':
            case 'médio':
            case 'medio':
                urgenciaSelect.value = 'Média';
                break;
            case '4':
            case 'baixo':
                urgenciaSelect.value = 'Baixa';
                break;
            case '5':
            case 'muito baixo':
                urgenciaSelect.value = 'Baixa';
                break;
            default:
                urgenciaSelect.value = 'Média';
        }
    }
    
    console.log('Campos preenchidos automaticamente com sucesso');
}