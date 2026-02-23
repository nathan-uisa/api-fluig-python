// Sistema de abas
document.addEventListener('DOMContentLoaded', function() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            // Remove active de todos os botões e conteúdos
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Adiciona active ao botão clicado e ao conteúdo correspondente
            this.classList.add('active');
            const targetContent = document.getElementById(`tab-${targetTab}`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });
    
    // Inicializar autocomplete de serviços para o campo de configurações
    inicializarAutocompleteConfig();
    
    // Carregar configurações salvas
    carregarConfiguracoesSalvas();
    
    // Carregar lista de configurações salvas
    carregarListaConfiguracoes();
    
    // Adicionar evento de clique no botão de salvar
    const btnSalvar = document.getElementById('btn-salvar-config');
    if (btnSalvar) {
        btnSalvar.addEventListener('click', function() {
            salvarConfiguracoes().then(() => {
                // Recarregar lista após salvar
                carregarListaConfiguracoes();
            });
        });
    }
    
    // Carregar configurações gerais
    carregarConfiguracoesGerais();
    
    // Adicionar evento de clique no botão de salvar configurações gerais
    const btnSalvarGerais = document.getElementById('btn-salvar-gerais');
    if (btnSalvarGerais) {
        btnSalvarGerais.addEventListener('click', function() {
            salvarConfiguracoesGerais();
        });
    }
    
    // Adicionar evento de clique no botão de reiniciar serviços
    const btnReiniciarServicos = document.getElementById('btn-reiniciar-servicos');
    if (btnReiniciarServicos) {
        btnReiniciarServicos.addEventListener('click', function() {
            if (confirm('Tem certeza que deseja reiniciar os serviços? Isso aplicará as configurações atuais.')) {
                reiniciarServicosBackground();
            }
        });
    }
});

// Carregar e exibir lista de configurações salvas
function carregarListaConfiguracoes() {
    fetch('/configuracoes/listar')
        .then(response => response.json())
        .then(data => {
            if (data.sucesso && data.configuracoes) {
                const container = document.getElementById('configuracoes-container');
                const vazias = document.getElementById('configuracoes-vazias');
                
                if (!container) return;
                
                if (data.configuracoes.length === 0) {
                    container.style.display = 'none';
                    if (vazias) vazias.style.display = 'block';
                    return;
                }
                
                if (vazias) vazias.style.display = 'none';
                container.style.display = 'grid';
                
                // Limpar container
                container.innerHTML = '';
                
                // Adicionar cada configuração
                data.configuracoes.forEach(config => {
                    const card = document.createElement('div');
                    card.className = 'config-card';
                    card.style.cssText = `
                        background: var(--bg-secondary, #f8f9fa);
                        border: 1px solid var(--border-primary, #e0e0e0);
                        border-radius: 8px;
                        padding: 15px;
                        transition: all 0.2s ease;
                    `;
                    
                    card.innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;">
                            <div style="display: flex; flex-direction: column; gap: 8px; flex: 1; cursor: pointer;">
                                <div style="font-weight: 600; color: var(--text-primary, #333); font-size: 14px;">
                                    ${escapeHtml(config.email || 'Sem email')}
                                </div>
                                <div style="color: var(--text-secondary, #666); font-size: 13px;">
                                    <strong>Serviço:</strong> ${escapeHtml(config.servico || 'Não definido')}
                                </div>
                                ${config.usuario_responsavel ? `
                                <div style="color: var(--text-secondary, #666); font-size: 13px;">
                                    <strong>Usuário Responsável:</strong> ${escapeHtml(config.usuario_responsavel)}
                                </div>
                                ` : ''}
                            </div>
                            <button class="btn-excluir-config" data-email="${escapeHtml(config.email)}" 
                                    style="background: #dc3545; color: white; border: none; border-radius: 6px; padding: 6px 12px; cursor: pointer; font-size: 12px; transition: background 0.2s; flex-shrink: 0;"
                                    title="Excluir configuração"
                                    onclick="event.stopPropagation(); excluirConfiguracao('${escapeHtml(config.email)}')">
                                <svg style="width: 14px; height: 14px; vertical-align: middle; margin-right: 4px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                </svg>
                                Excluir
                            </button>
                        </div>
                    `;
                    
                    // Efeito hover no card
                    card.addEventListener('mouseenter', function() {
                        this.style.background = 'var(--bg-tertiary, #f0f0f0)';
                        this.style.borderColor = 'var(--border-focus, #007bff)';
                    });
                    
                    card.addEventListener('mouseleave', function() {
                        this.style.background = 'var(--bg-secondary, #f8f9fa)';
                        this.style.borderColor = 'var(--border-primary, #e0e0e0)';
                    });
                    
                    // Efeito hover no botão de exclusão
                    const btnExcluir = card.querySelector('.btn-excluir-config');
                    if (btnExcluir) {
                        btnExcluir.addEventListener('mouseenter', function() {
                            this.style.background = '#c82333';
                        });
                        btnExcluir.addEventListener('mouseleave', function() {
                            this.style.background = '#dc3545';
                        });
                    }
                    
                    // Ao clicar no card (exceto no botão), carrega a configuração nos campos
                    const cardContent = card.querySelector('div[style*="cursor: pointer"]');
                    if (cardContent) {
                        cardContent.addEventListener('click', function() {
                            carregarConfiguracaoPorEmail(config.email);
                        });
                    }
                    
                    container.appendChild(card);
                });
            }
        })
        .catch(error => {
            console.error('Erro ao carregar lista de configurações:', error);
        });
}

// Função para excluir configuração
function excluirConfiguracao(email) {
    if (!email) {
        alert('Email não fornecido');
        return;
    }
    
    // Confirmar exclusão
    if (!confirm(`Tem certeza que deseja excluir a configuração para o email "${email}"?`)) {
        return;
    }
    
    // Fazer requisição DELETE
    fetch(`/configuracoes/excluir?email=${encodeURIComponent(email)}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            alert('Configuração excluída com sucesso!');
            // Recarregar lista de configurações
            carregarListaConfiguracoes();
        } else {
            alert('Erro ao excluir configuração: ' + (data.erro || 'Erro desconhecido'));
        }
    })
    .catch(error => {
        console.error('Erro ao excluir configuração:', error);
        alert('Erro ao excluir configuração: ' + error.message);
    });
}

// Carregar configuração específica por email
function carregarConfiguracaoPorEmail(email) {
    if (!email) return;
    
    fetch(`/configuracoes/carregar?email=${encodeURIComponent(email)}`)
        .then(response => response.json())
        .then(data => {
            if (data.sucesso && data.configs) {
                preencherCamposComConfiguracao(data.configs);
            }
        })
        .catch(error => {
            console.error('Erro ao carregar configuração:', error);
        });
}

// Preencher campos do formulário com uma configuração
function preencherCamposComConfiguracao(configs) {
    if (configs.email_solicitante) {
        const emailInput = document.getElementById('email_solicitante');
        if (emailInput) emailInput.value = configs.email_solicitante;
    }
    if (configs.usuario_responsavel) {
        const usuarioResponsavelInput = document.getElementById('usuario_responsavel');
        if (usuarioResponsavelInput) usuarioResponsavelInput.value = configs.usuario_responsavel;
    }
    if (configs.servico_id) {
        const servicoIdInput = document.getElementById('config_servico_id');
        if (servicoIdInput) servicoIdInput.value = configs.servico_id;
    }
    if (configs.servico) {
        const servicoInput = document.getElementById('config_servico');
        if (servicoInput) servicoInput.value = configs.servico;
    }
    if (configs.ds_grupo_servico) {
        const dsGrupoServicoInput = document.getElementById('config_ds_grupo_servico');
        if (dsGrupoServicoInput) dsGrupoServicoInput.value = configs.ds_grupo_servico;
    }
    if (configs.item_servico) {
        const itemServicoInput = document.getElementById('config_item_servico');
        if (itemServicoInput) itemServicoInput.value = configs.item_servico;
    }
    if (configs.urg_alta) {
        const urgAltaInput = document.getElementById('config_urg_alta');
        if (urgAltaInput) urgAltaInput.value = configs.urg_alta;
    }
    if (configs.urg_media) {
        const urgMediaInput = document.getElementById('config_urg_media');
        if (urgMediaInput) urgMediaInput.value = configs.urg_media;
    }
    if (configs.urg_baixa) {
        const urgBaixaInput = document.getElementById('config_urg_baixa');
        if (urgBaixaInput) urgBaixaInput.value = configs.urg_baixa;
    }
    if (configs.ds_resp_servico) {
        const dsRespServicoInput = document.getElementById('config_ds_resp_servico');
        if (dsRespServicoInput) dsRespServicoInput.value = configs.ds_resp_servico;
    }
    if (configs.ds_tipo) {
        const dsTipoSelect = document.getElementById('config_ds_tipo');
        if (dsTipoSelect) dsTipoSelect.value = configs.ds_tipo;
    }
    if (configs.ds_urgencia) {
        const dsUrgenciaSelect = document.getElementById('config_ds_urgencia');
        if (dsUrgenciaSelect) dsUrgenciaSelect.value = configs.ds_urgencia;
    }
    if (configs.equipe_responsavel) {
        const equipeResponsavelInput = document.getElementById('config_equipe_responsavel');
        if (equipeResponsavelInput) equipeResponsavelInput.value = configs.equipe_responsavel;
    }
    if (configs.status) {
        const statusSelect = document.getElementById('config_status');
        if (statusSelect) statusSelect.value = configs.status;
    }
    if (configs.solicitante) {
        const solicitanteInput = document.getElementById('config_solicitante');
        if (solicitanteInput) solicitanteInput.value = configs.solicitante;
    }
}

// Carregar configurações salvas ao carregar a página
function carregarConfiguracoesSalvas() {
    fetch('/configuracoes/carregar')
        .then(response => response.json())
        .then(data => {
            if (data.sucesso && data.configs) {
                const configs = data.configs;
                
                // Preencher campos com valores salvos
                if (configs.email_solicitante) {
                    const emailInput = document.getElementById('email_solicitante');
                    if (emailInput) emailInput.value = configs.email_solicitante;
                }
                if (configs.usuario_responsavel) {
                    const usuarioResponsavelInput = document.getElementById('usuario_responsavel');
                    if (usuarioResponsavelInput) usuarioResponsavelInput.value = configs.usuario_responsavel;
                }
                if (configs.servico_id) {
                    const servicoIdInput = document.getElementById('config_servico_id');
                    if (servicoIdInput) servicoIdInput.value = configs.servico_id;
                }
                if (configs.servico) {
                    const servicoInput = document.getElementById('config_servico');
                    if (servicoInput) servicoInput.value = configs.servico;
                }
                if (configs.ds_grupo_servico) {
                    const dsGrupoServicoInput = document.getElementById('config_ds_grupo_servico');
                    if (dsGrupoServicoInput) dsGrupoServicoInput.value = configs.ds_grupo_servico;
                }
                if (configs.item_servico) {
                    const itemServicoInput = document.getElementById('config_item_servico');
                    if (itemServicoInput) itemServicoInput.value = configs.item_servico;
                }
                if (configs.urg_alta) {
                    const urgAltaInput = document.getElementById('config_urg_alta');
                    if (urgAltaInput) urgAltaInput.value = configs.urg_alta;
                }
                if (configs.urg_media) {
                    const urgMediaInput = document.getElementById('config_urg_media');
                    if (urgMediaInput) urgMediaInput.value = configs.urg_media;
                }
                if (configs.urg_baixa) {
                    const urgBaixaInput = document.getElementById('config_urg_baixa');
                    if (urgBaixaInput) urgBaixaInput.value = configs.urg_baixa;
                }
                if (configs.ds_resp_servico) {
                    const dsRespServicoInput = document.getElementById('config_ds_resp_servico');
                    if (dsRespServicoInput) dsRespServicoInput.value = configs.ds_resp_servico;
                }
                if (configs.ds_tipo) {
                    const dsTipoSelect = document.getElementById('config_ds_tipo');
                    if (dsTipoSelect) dsTipoSelect.value = configs.ds_tipo;
                }
                if (configs.ds_urgencia) {
                    const dsUrgenciaSelect = document.getElementById('config_ds_urgencia');
                    if (dsUrgenciaSelect) dsUrgenciaSelect.value = configs.ds_urgencia;
                }
                if (configs.equipe_responsavel) {
                    const equipeResponsavelInput = document.getElementById('config_equipe_responsavel');
                    if (equipeResponsavelInput) equipeResponsavelInput.value = configs.equipe_responsavel;
                }
                if (configs.status) {
                    const statusSelect = document.getElementById('config_status');
                    if (statusSelect) statusSelect.value = configs.status;
                }
                if (configs.solicitante) {
                    const solicitanteInput = document.getElementById('config_solicitante');
                    if (solicitanteInput) solicitanteInput.value = configs.solicitante;
                }
            }
        })
        .catch(error => {
            console.error('Erro ao carregar configurações:', error);
        });
}

// Função para salvar configurações
function salvarConfiguracoes() {
    return new Promise((resolve, reject) => {
    const btnSalvar = document.getElementById('btn-salvar-config');
    if (!btnSalvar) return;
    
    // Desabilitar botão durante o salvamento
    btnSalvar.disabled = true;
    btnSalvar.textContent = 'Salvando...';
    
    // Coletar valores dos campos
    const formData = new FormData();
    
    const emailSolicitante = document.getElementById('email_solicitante')?.value || '';
    const usuarioResponsavel = document.getElementById('usuario_responsavel')?.value || '';
    const servicoId = document.getElementById('config_servico_id')?.value || '';
    const servico = document.getElementById('config_servico')?.value || '';
    const dsGrupoServico = document.getElementById('config_ds_grupo_servico')?.value || '';
    const itemServico = document.getElementById('config_item_servico')?.value || '';
    const urgAlta = document.getElementById('config_urg_alta')?.value || '';
    const urgMedia = document.getElementById('config_urg_media')?.value || '';
    const urgBaixa = document.getElementById('config_urg_baixa')?.value || '';
    const dsRespServico = document.getElementById('config_ds_resp_servico')?.value || '';
    const dsTipo = document.getElementById('config_ds_tipo')?.value || '';
    const dsUrgencia = document.getElementById('config_ds_urgencia')?.value || '';
    const equipeResponsavel = document.getElementById('config_equipe_responsavel')?.value || '';
    const status = document.getElementById('config_status')?.value || '';
    const solicitante = document.getElementById('config_solicitante')?.value || '';
    
    // Adicionar valores ao FormData (apenas se não estiverem vazios)
    if (emailSolicitante) formData.append('email_solicitante', emailSolicitante);
    if (usuarioResponsavel) formData.append('usuario_responsavel', usuarioResponsavel);
    if (servicoId) formData.append('servico_id', servicoId);
    if (servico) formData.append('servico', servico);
    if (dsGrupoServico) formData.append('ds_grupo_servico', dsGrupoServico);
    if (itemServico) formData.append('item_servico', itemServico);
    if (urgAlta) formData.append('urg_alta', urgAlta);
    if (urgMedia) formData.append('urg_media', urgMedia);
    if (urgBaixa) formData.append('urg_baixa', urgBaixa);
    if (dsRespServico) formData.append('ds_resp_servico', dsRespServico);
    if (dsTipo) formData.append('ds_tipo', dsTipo);
    if (dsUrgencia) formData.append('ds_urgencia', dsUrgencia);
    if (equipeResponsavel) formData.append('equipe_responsavel', equipeResponsavel);
    if (status) formData.append('status', status);
    if (solicitante) formData.append('solicitante', solicitante);
    
    // Enviar para o backend
    fetch('/configuracoes/salvar', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            // Mostrar mensagem de sucesso
            alert('Configurações salvas com sucesso!');
            btnSalvar.textContent = 'Salvar Configurações';
            btnSalvar.disabled = false;
            resolve();
        } else {
            alert('Erro ao salvar configurações: ' + (data.erro || 'Erro desconhecido'));
            btnSalvar.textContent = 'Salvar Configurações';
            btnSalvar.disabled = false;
            reject(new Error(data.erro || 'Erro desconhecido'));
        }
    })
    .catch(error => {
        console.error('Erro ao salvar configurações:', error);
        alert('Erro ao salvar configurações: ' + error.message);
        btnSalvar.textContent = 'Salvar Configurações';
        btnSalvar.disabled = false;
        reject(error);
    });
    });
}

// Função para inicializar autocomplete de serviços na página de configurações
function inicializarAutocompleteConfig() {
    const configServicoInput = document.getElementById('config_servico');
    const configServicoIdInput = document.getElementById('config_servico_id');
    const configServicoDropdown = document.getElementById('config-servico-dropdown');
    
    if (!configServicoInput || !configServicoDropdown) {
        return;
    }
    
    // Variáveis locais para o autocomplete de configurações
    let configDropdownAtivo = false;
    let configItemSelecionado = -1;
    
    // Carregar serviços se ainda não foram carregados
    if (typeof servicosDisponiveis === 'undefined' || servicosDisponiveis.length === 0) {
        if (typeof carregarServicos === 'function') {
            carregarServicos();
        }
    }
    
    // Função para mostrar dropdown de configurações
    function mostrarDropdownConfig() {
        if (typeof servicosDisponiveis === 'undefined' || servicosDisponiveis.length === 0) {
            if (typeof carregarServicos === 'function') {
                carregarServicos();
            }
            // Aguardar um pouco e tentar novamente
            setTimeout(mostrarDropdownConfig, 500);
            return;
        }
        
        const textoFiltro = configServicoInput.value.trim().toLowerCase();
        let servicosFiltrados;
        
        if (textoFiltro.length === 0) {
            servicosFiltrados = servicosDisponiveis;
        } else {
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
            
            configServicoDropdown.innerHTML = dropdownHTML;
            configServicoDropdown.style.display = 'block';
            configDropdownAtivo = true;
            configItemSelecionado = -1;
            
            // Adicionar eventos de clique nos itens
            configServicoDropdown.querySelectorAll('.dropdown-item').forEach(function(item) {
                if (item.getAttribute('data-id')) {
                    item.addEventListener('click', function() {
                        const nome = this.getAttribute('data-servico');
                        const documentid = this.getAttribute('data-id');
                        configServicoInput.value = nome;
                        if (configServicoIdInput) {
                            configServicoIdInput.value = documentid;
                        }
                        configServicoDropdown.innerHTML = '';
                        configServicoDropdown.style.display = 'none';
                        configDropdownAtivo = false;
                        configItemSelecionado = -1;
                        
                        // Buscar e preencher os dados do serviço selecionado
                        if (documentid) {
                            buscarESelecionarServicoConfig(documentid);
                        }
                    });
                }
            });
        } else {
            configServicoDropdown.innerHTML = '';
            configServicoDropdown.style.display = 'none';
            configDropdownAtivo = false;
        }
    }
    
    // Event listeners
    configServicoInput.addEventListener('focus', function() {
        if (typeof servicosDisponiveis !== 'undefined' && servicosDisponiveis.length > 0) {
            mostrarDropdownConfig();
        }
    });
    
    configServicoInput.addEventListener('input', function() {
        mostrarDropdownConfig();
    });
    
    configServicoInput.addEventListener('keydown', function(e) {
        const items = configServicoDropdown.querySelectorAll('.dropdown-item');
        
        if (configDropdownAtivo && items.length > 0) {
            switch(e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    configItemSelecionado = Math.min(configItemSelecionado + 1, items.length - 1);
                    items.forEach((item, index) => {
                        if (index === configItemSelecionado) {
                            item.classList.add('selected');
                        } else {
                            item.classList.remove('selected');
                        }
                    });
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    configItemSelecionado = Math.max(configItemSelecionado - 1, -1);
                    items.forEach((item, index) => {
                        if (index === configItemSelecionado) {
                            item.classList.add('selected');
                        } else {
                            item.classList.remove('selected');
                        }
                    });
                    break;
                case 'Enter':
                    e.preventDefault();
                    if (configItemSelecionado >= 0 && items[configItemSelecionado]) {
                        items[configItemSelecionado].click();
                    }
                    break;
                case 'Escape':
                    configServicoDropdown.innerHTML = '';
                    configServicoDropdown.style.display = 'none';
                    configDropdownAtivo = false;
                    configItemSelecionado = -1;
                    break;
            }
        }
    });
    
    // Fechar dropdown ao clicar fora
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.autocomplete-container') || 
            (!configServicoInput.contains(e.target) && !configServicoDropdown.contains(e.target))) {
            if (configServicoDropdown && !configServicoDropdown.contains(e.target)) {
                configServicoDropdown.innerHTML = '';
                configServicoDropdown.style.display = 'none';
                configDropdownAtivo = false;
                configItemSelecionado = -1;
            }
        }
    });
}

// Função para buscar e preencher dados do serviço selecionado na página de configurações
function buscarESelecionarServicoConfig(documentid) {
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
            preencherCamposServicoConfig(data.servico);
            console.log('Serviço selecionado e campos preenchidos na configuração:', data.servico);
        } else {
            console.error('Erro ao buscar detalhes do serviço:', data.erro || 'Serviço não encontrado');
        }
    })
    .catch(error => {
        console.error('Erro ao buscar detalhes do serviço:', error);
    });
}

// Função para preencher os campos de classificação na página de configurações
function preencherCamposServicoConfig(servicoData) {
    const dsGrupoServico = document.getElementById('config_ds_grupo_servico');
    const itemServico = document.getElementById('config_item_servico');
    const servicoInput = document.getElementById('config_servico');
    const servicoIdInput = document.getElementById('config_servico_id');
    const urgAlta = document.getElementById('config_urg_alta');
    const urgMedia = document.getElementById('config_urg_media');
    const urgBaixa = document.getElementById('config_urg_baixa');
    const dsRespServico = document.getElementById('config_ds_resp_servico');
    const equipeResponsavel = document.getElementById('config_equipe_responsavel');
    const urgenciaSelect = document.getElementById('config_ds_urgencia');
    
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
    
    console.log('Campos de configuração preenchidos automaticamente com sucesso');
}

// Função para carregar configurações gerais
function carregarConfiguracoesGerais() {
    fetch('/configuracoes/gerais/carregar')
        .then(response => response.json())
        .then(data => {
            if (data.sucesso && data.configs) {
                const gmailCheckInterval = document.getElementById('gmail_check_interval');
                if (gmailCheckInterval && data.configs.gmail_check_interval) {
                    gmailCheckInterval.value = data.configs.gmail_check_interval;
                }
                
                const gmailMonitorEnabled = document.getElementById('gmail_monitor_enabled');
                if (gmailMonitorEnabled) {
                    gmailMonitorEnabled.checked = data.configs.gmail_monitor_enabled === 'true';
                }
                
                const blackListEmails = document.getElementById('black_list_emails');
                if (blackListEmails && data.configs.black_list_emails) {
                    blackListEmails.value = data.configs.black_list_emails;
                }
                
                const emailsList = document.getElementById('emails_list');
                if (emailsList && data.configs.emails_list) {
                    emailsList.value = data.configs.emails_list;
                }
                
                const historicoCheckIntervalMinutes = document.getElementById('historico_check_interval_minutes');
                if (historicoCheckIntervalMinutes && data.configs.historico_check_interval_minutes) {
                    historicoCheckIntervalMinutes.value = data.configs.historico_check_interval_minutes;
                }
                
                const historicoCheckIntervalHours = document.getElementById('historico_check_interval_hours');
                if (historicoCheckIntervalHours && data.configs.historico_check_interval_hours) {
                    historicoCheckIntervalHours.value = data.configs.historico_check_interval_hours;
                }
                
                const historicoMonitorEnabled = document.getElementById('historico_monitor_enabled');
                if (historicoMonitorEnabled) {
                    historicoMonitorEnabled.checked = data.configs.historico_monitor_enabled === 'true';
                }
                
                const historicoExcludeEmails = document.getElementById('historico_exclude_emails');
                if (historicoExcludeEmails && data.configs.historico_exclude_emails) {
                    historicoExcludeEmails.value = data.configs.historico_exclude_emails;
                }
                
                const emailDeduplicationPatterns = document.getElementById('email_deduplication_patterns');
                if (emailDeduplicationPatterns && data.configs.email_deduplication_patterns) {
                    emailDeduplicationPatterns.value = data.configs.email_deduplication_patterns;
                }
                
                const emailDeduplicationEmails = document.getElementById('email_deduplication_emails');
                if (emailDeduplicationEmails && data.configs.email_deduplication_emails) {
                    emailDeduplicationEmails.value = data.configs.email_deduplication_emails;
                }
            }
        })
        .catch(error => {
            console.error('Erro ao carregar configurações gerais:', error);
        });
}

// Função para salvar configurações gerais
function salvarConfiguracoesGerais() {
    const btnSalvar = document.getElementById('btn-salvar-gerais');
    if (!btnSalvar) return;
    
    // Desabilitar botão durante o salvamento
    btnSalvar.disabled = true;
    btnSalvar.textContent = 'Salvando...';
    
    const gmailCheckInterval = document.getElementById('gmail_check_interval')?.value || '';
    const gmailMonitorEnabled = document.getElementById('gmail_monitor_enabled')?.checked ? 'true' : 'false';
    const blackListEmails = document.getElementById('black_list_emails')?.value || '';
    const emailsList = document.getElementById('emails_list')?.value || '';
    const historicoCheckIntervalMinutes = document.getElementById('historico_check_interval_minutes')?.value || '';
    const historicoCheckIntervalHours = document.getElementById('historico_check_interval_hours')?.value || '';
    const historicoMonitorEnabled = document.getElementById('historico_monitor_enabled')?.checked ? 'true' : 'false';
    const historicoExcludeEmails = document.getElementById('historico_exclude_emails')?.value || '';
    const emailDeduplicationPatterns = document.getElementById('email_deduplication_patterns')?.value || '';
    const emailDeduplicationEmails = document.getElementById('email_deduplication_emails')?.value || '';
    
    if (!gmailCheckInterval || parseInt(gmailCheckInterval) < 1) {
        alert('Por favor, informe um intervalo válido (mínimo 1 minuto)');
        btnSalvar.textContent = 'Salvar Configurações Gerais';
        btnSalvar.disabled = false;
        return;
    }
    
    if (historicoCheckIntervalMinutes && (parseInt(historicoCheckIntervalMinutes) < 1 || parseInt(historicoCheckIntervalMinutes) > 1440)) {
        alert('Por favor, informe um intervalo válido para histórico (entre 1 e 1440 minutos)');
        btnSalvar.textContent = 'Salvar Configurações Gerais';
        btnSalvar.disabled = false;
        return;
    }
    
    const formData = new FormData();
    formData.append('gmail_check_interval', gmailCheckInterval);
    formData.append('gmail_monitor_enabled', gmailMonitorEnabled);
    formData.append('black_list_emails', blackListEmails);
    formData.append('emails_list', emailsList);
    formData.append('historico_check_interval_minutes', historicoCheckIntervalMinutes);
    formData.append('historico_check_interval_hours', historicoCheckIntervalHours);
    formData.append('historico_monitor_enabled', historicoMonitorEnabled);
    formData.append('historico_exclude_emails', historicoExcludeEmails);
    formData.append('email_deduplication_patterns', emailDeduplicationPatterns);
    formData.append('email_deduplication_emails', emailDeduplicationEmails);
    
    fetch('/configuracoes/gerais/salvar', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            alert('Configurações gerais salvas com sucesso!');
            btnSalvar.textContent = 'Salvar Configurações Gerais';
            btnSalvar.disabled = false;
        } else {
            alert('Erro ao salvar configurações gerais: ' + (data.erro || 'Erro desconhecido'));
            btnSalvar.textContent = 'Salvar Configurações Gerais';
            btnSalvar.disabled = false;
        }
    })
    .catch(error => {
        console.error('Erro ao salvar configurações gerais:', error);
        alert('Erro ao salvar configurações gerais: ' + error.message);
        btnSalvar.textContent = 'Salvar Configurações Gerais';
        btnSalvar.disabled = false;
    });
}

// Função para reiniciar serviços em background
function reiniciarServicosBackground() {
    const btnReiniciar = document.getElementById('btn-reiniciar-servicos');
    if (!btnReiniciar) return;
    
    // Desabilitar botão durante o reinício
    btnReiniciar.disabled = true;
    btnReiniciar.textContent = 'Reiniciando...';
    
    fetch('/configuracoes/gerais/reiniciar-servicos', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            alert('Serviços reiniciados com sucesso! As configurações foram aplicadas.');
            btnReiniciar.textContent = 'Reiniciar Serviços';
            btnReiniciar.disabled = false;
        } else {
            alert('Erro ao reiniciar serviços: ' + (data.erro || 'Erro desconhecido'));
            btnReiniciar.textContent = 'Reiniciar Serviços';
            btnReiniciar.disabled = false;
        }
    })
    .catch(error => {
        console.error('Erro ao reiniciar serviços:', error);
        alert('Erro ao reiniciar serviços: ' + error.message);
        btnReiniciar.textContent = 'Reiniciar Serviços';
        btnReiniciar.disabled = false;
    });
}
