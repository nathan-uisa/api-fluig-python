// Script para gerenciar o formulário de chamados e modal de prévia

// Variáveis globais para autocomplete de serviços
let servicosDisponiveis = [];
let dropdownAtivo = false;
let itemSelecionado = -1;

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

