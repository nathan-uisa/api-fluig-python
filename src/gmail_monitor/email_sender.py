"""
Módulo para envio de emails via Gmail API
"""
from typing import Optional, List, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import base64
import html
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger
from src.historico_monitor.historico_fluxo import HistoricoFluxoManager


def criar_template_email_erro(mensagem_erro: str) -> str:
    """
    Cria um template HTML formatado para o email de erro ao abrir chamado
    
    Args:
        mensagem_erro: Mensagem de erro a ser exibida
    
    Returns:
        String HTML formatada
    """
    html_template = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333333;
                background-color: #f4f4f4;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                color: #ffffff;
                padding: 30px 20px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 600;
            }}
            .content {{
                padding: 30px 20px;
            }}
            .error-icon {{
                text-align: center;
                margin-bottom: 20px;
            }}
            .error-icon svg {{
                width: 64px;
                height: 64px;
                color: #ef4444;
            }}
            .message {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .message h2 {{
                color: #1f2937;
                font-size: 20px;
                margin: 0 0 10px 0;
                font-weight: 600;
            }}
            .message p {{
                color: #6b7280;
                font-size: 16px;
                margin: 0;
            }}
            .error-box {{
                background-color: #fef2f2;
                border-left: 4px solid #ef4444;
                padding: 20px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .error-box-label {{
                font-size: 12px;
                color: #991b1b;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 10px;
                font-weight: 600;
            }}
            .error-box-message {{
                font-size: 14px;
                color: #7f1d1d;
                margin: 0;
                line-height: 1.6;
            }}
            .footer {{
                background-color: #f9fafb;
                padding: 20px;
                text-align: center;
                border-top: 1px solid #e5e7eb;
            }}
            .footer p {{
                color: #6b7280;
                font-size: 12px;
                margin: 5px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Chamado Não Pôde Ser Aberto</h1>
            </div>
            <div class="content">
                <div class="error-icon">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                </div>
                <div class="message">
                    <h2>Ocorreu um erro</h2>
                    <p>Infelizmente, não foi possível abrir o chamado no momento.</p>
                    <p>Entre em contato com o suporte Telefone e Whatsapp: +55 (65) 99895838.</p>
                </div>
                <div class="error-box">
                    <div class="error-box-label">Motivo</div>
                    <div class="error-box-message">{html.escape(mensagem_erro)}</div>
                </div>
            </div>
            <div class="footer">
                <p><strong>UISA</strong></p>
                <p>Por favor, tente novamente ou entre em contato com o suporte.</p>
                <p>Este é um email automático, por favor não responda.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_template


def criar_template_email_atualizacao(
    process_instance_id: int,
    link: str,
    novos_items: List[Dict[str, Any]],
    email_remetente: str
) -> str:
    """
    Cria um template HTML formatado para o email de notificação de atualização do chamado
    
    Args:
        process_instance_id: ID do chamado
        link: Link para visualizar o chamado no Fluig
        novos_items: Lista de novos itens do histórico
        email_remetente: Email do remetente
    
    Returns:
        String HTML formatada
    """
    # Usa o gerenciador de fluxo para processar os itens
    fluxo_manager = HistoricoFluxoManager()
    itens_processados = fluxo_manager.processar_itens(novos_items[:10])  # Limita a 10 itens
    
    # Formata os itens processados em HTML
    itens_html = ""
    for item_processado in itens_processados:
        tipo = item_processado.get('tipo', 'UNKNOWN')
        descricao_principal = item_processado.get('descricao_principal', '')
        descricao_secundaria = item_processado.get('descricao_secundaria', '')
        mostrar_observacao = item_processado.get('mostrar_observacao', False)
        observation_description = item_processado.get('observation_description', '')
        mostrar_responsaveis = item_processado.get('mostrar_responsaveis', False)
        responsaveis = item_processado.get('responsaveis', '')
        usuario = item_processado.get('usuario', 'Sistema')
        data_formatada = item_processado.get('data', 'Data não disponível')
        eh_attachment = item_processado.get('eh_attachment', False)
        attachment_description = item_processado.get('attachment_description', '')
        eh_imagem = item_processado.get('eh_imagem', False)
        cid_imagem = item_processado.get('cid_imagem', '')
        
        # Monta seção de comentário se necessário
        comentario_html = ''
        if mostrar_observacao and observation_description:
            comentario_html = f"""
            <div style="background-color: #fff7ed; border-left: 3px solid #f48631; padding: 10px; margin: 8px 0; border-radius: 4px;">
                <div style="color: #f48631; font-size: 11px; font-weight: 600; text-transform: uppercase; margin-bottom: 5px;">Comentário</div>
                <div style="color: #1f2937; font-size: 14px; margin-bottom: 5px;">{html.escape(observation_description)}</div>
                <div style="color: #6b7280; font-size: 11px;">Por: {html.escape(usuario)}</div>
            </div>
            """
        
        # HTML da imagem para ATTACHMENT (se for imagem)
        imagem_html = ''
        if eh_attachment and eh_imagem:
            imagem_html = f"""
            <div style="margin: 10px 0; text-align: center;">
                <img src="cid:{cid_imagem}" alt="{html.escape(attachment_description)}" style="max-width: 100%; height: auto; border-radius: 4px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);" />
            </div>
            """
        
        # HTML dos responsáveis se necessário
        responsaveis_html = ''
        if mostrar_responsaveis and responsaveis:
            responsaveis_html = f"""
            <div style="color: #6b7280; font-size: 12px; margin: 5px 0;">
                <strong>Responsáveis:</strong> {html.escape(responsaveis)}
            </div>
            """
        
        itens_html += f"""
        <div style="padding: 10px; margin: 5px 0; background-color: #f9fafb; border-left: 3px solid #f48631; border-radius: 4px;">
            <div style="font-weight: 600; color: #f48631; font-size: 12px; text-transform: uppercase;">{tipo}</div>
            <div style="color: #1f2937; font-size: 16px; font-weight: 600; margin: 5px 0;">{html.escape(descricao_principal)}</div>
            {f'<div style="color: #6b7280; font-size: 13px; margin: 3px 0;">{html.escape(descricao_secundaria)}</div>' if descricao_secundaria else ''}
            {responsaveis_html}
            {imagem_html}
            {comentario_html}
            <div style="color: #6b7280; font-size: 12px;">Por: {html.escape(usuario)} | {data_formatada}</div>
        </div>
        """
    
    if len(novos_items) > 10:
        itens_html += f'<div style="text-align: center; color: #6b7280; font-size: 12px; margin-top: 10px;">... e mais {len(novos_items) - 10} atualização(ões)</div>'
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333333;
                background-color: #f4f4f4;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #f48631 0%, #e67e22 100%);
                color: #ffffff;
                padding: 30px 20px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 600;
            }}
            .content {{
                padding: 30px 20px;
            }}
            .message {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .message h2 {{
                color: #1f2937;
                font-size: 20px;
                margin: 0 0 10px 0;
                font-weight: 600;
            }}
            .message p {{
                color: #6b7280;
                font-size: 16px;
                margin: 0;
            }}
            .chamado-info {{
                background-color: #f9fafb;
                border-left: 4px solid #f48631;
                padding: 15px 20px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .chamado-info-label {{
                font-size: 12px;
                color: #f48631;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 5px;
                font-weight: 600;
            }}
            .chamado-info-value {{
                font-size: 24px;
                color: #1f2937;
                font-weight: 700;
                margin: 0;
            }}
            .atualizacoes-box {{
                margin: 20px 0;
            }}
            .atualizacoes-title {{
                font-size: 16px;
                font-weight: 600;
                color: #1f2937;
                margin-bottom: 15px;
            }}
            .button-container {{
                text-align: center;
                margin: 30px 0;
            }}
            .button {{
                display: inline-block;
                background: linear-gradient(135deg, #f48631 0%, #e67e22 100%);
                color: #ffffff;
                text-decoration: none;
                padding: 14px 32px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 16px;
                transition: transform 0.2s, box-shadow 0.2s;
                box-shadow: 0 4px 6px rgba(244, 134, 49, 0.3);
            }}
            .button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(244, 134, 49, 0.4);
            }}
            .footer {{
                background-color: #f9fafb;
                padding: 20px;
                text-align: center;
                border-top: 1px solid #e5e7eb;
            }}
            .footer p {{
                color: #6b7280;
                font-size: 12px;
                margin: 5px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Nova Atualização no Chamado</h1>
            </div>
            <div class="content">
                <div class="message">
                    <h2>Seu chamado foi atualizado!</h2>
                    <p>Há {len(novos_items)} nova(s) atualização(ões) no chamado #{process_instance_id}.</p>
                </div>
                <div class="chamado-info">
                    <div class="chamado-info-label">Número do Chamado</div>
                    <div class="chamado-info-value">#{process_instance_id}</div>
                </div>
                <div class="atualizacoes-box">
                    <div class="atualizacoes-title">Últimas Atualizações:</div>
                    {itens_html}
                </div>
                <div class="button-container">
                    <a href="{link}" class="button">Ver Chamado no Fluig</a>
                </div>
            </div>
            <div class="footer">
                <p><strong>UISA</strong></p>
                <p>Este é um email automático, por favor não responda.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_template


def criar_template_email_chamado(process_instance_id: int, link: str, email_remetente: str) -> str:
    """
    Cria um template HTML formatado para o email de confirmação de abertura de chamado
    
    Args:
        process_instance_id: ID do chamado criado
        link: Link para visualizar o chamado no Fluig
        email_remetente: Email do remetente que será usado para acompanhamento
    
    Returns:
        String HTML formatada
    """
    html_template = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333333;
                background-color: #f4f4f4;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #f48631 0%, #e67e22 100%);
                color: #ffffff;
                padding: 30px 20px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 600;
            }}
            .content {{
                padding: 30px 20px;
            }}
            .success-icon {{
                text-align: center;
                margin-bottom: 20px;
            }}
            .success-icon svg {{
                width: 64px;
                height: 64px;
                color: #10b981;
            }}
            .message {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .message h2 {{
                color: #1f2937;
                font-size: 20px;
                margin: 0 0 10px 0;
                font-weight: 600;
            }}
            .message p {{
                color: #6b7280;
                font-size: 16px;
                margin: 0;
            }}
            .chamado-info {{
                background-color: #f9fafb;
                border-left: 4px solid #f48631;
                padding: 20px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .chamado-info-label {{
                font-size: 12px;
                color: #f48631;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 5px;
                font-weight: 600;
            }}
            .chamado-info-value {{
                font-size: 28px;
                color: #1f2937;
                font-weight: 700;
                margin: 0;
            }}
            .button-container {{
                text-align: center;
                margin: 30px 0;
            }}
            .button {{
                display: inline-block;
                background: linear-gradient(135deg, #f48631 0%, #e67e22 100%);
                color: #ffffff;
                text-decoration: none;
                padding: 14px 32px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 16px;
                transition: transform 0.2s, box-shadow 0.2s;
                box-shadow: 0 4px 6px rgba(244, 134, 49, 0.3);
            }}
            .button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(244, 134, 49, 0.4);
            }}
            .footer {{
                background-color: #f9fafb;
                padding: 20px;
                text-align: center;
                border-top: 1px solid #e5e7eb;
            }}
            .footer p {{
                color: #6b7280;
                font-size: 12px;
                margin: 5px 0;
            }}
            .link-fallback {{
                margin-top: 20px;
                padding: 15px;
                background-color: #f3f4f6;
                border-radius: 4px;
                font-size: 12px;
                color: #6b7280;
                word-break: break-all;
            }}
            .acompanhamento-info {{
                background-color: #fff7ed;
                border-left: 4px solid #f48631;
                padding: 15px 20px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .acompanhamento-info p {{
                color: #78350f;
                font-size: 14px;
                margin: 0;
                line-height: 1.6;
            }}
            .acompanhamento-info strong {{
                color: #f48631;
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Chamado Criado com Sucesso</h1>
            </div>
            <div class="content">
                <div class="success-icon">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                </div>
                <div class="message">
                    <h2>Seu chamado foi aberto!</h2>
                    <p>O chamado foi criado com sucesso e está disponível para acompanhamento.</p>
                </div>
                <div class="acompanhamento-info">
                    <p>As atualizações do chamado serão enviadas para o email <strong>{html.escape(email_remetente)}</strong>.</p>
                </div>
                <div class="chamado-info">
                    <div class="chamado-info-label">Número do Chamado</div>
                    <div class="chamado-info-value">#{process_instance_id}</div>
                </div>
                <div class="button-container">
                    <a href="{link}" class="button">Acessar Chamado no Fluig</a>
                </div>
                <div class="link-fallback">
                    <strong>Link direto:</strong><br>
                    {link}
                </div>
            </div>
            <div class="footer">
                <p><strong>UISA</strong></p>
                <p>Este é um email automático, por favor não responda.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_template


def enviar_email(
    destinatario: str, 
    assunto: str, 
    corpo: str, 
    html: Optional[str] = None,
    anexos: Optional[List[Dict[str, Any]]] = None
) -> bool:
    """
    Envia um email usando Gmail API
    
    Args:
        destinatario: Email do destinatário
        assunto: Assunto do email
        corpo: Corpo do email (texto plano)
        html: Corpo do email em HTML (opcional)
        anexos: Lista de anexos. Cada anexo é um dict com:
            - 'nome': Nome do arquivo
            - 'conteudo': Bytes do arquivo
            - 'tipo': Tipo MIME (opcional, padrão: 'application/octet-stream')
            - 'cid': Content-ID para imagens inline (opcional)
        
    Returns:
        True se enviado com sucesso, False caso contrário
    """
    try:
        service = criar_servico_gmail()
        if not service:
            logger.error("[email_sender] Falha ao criar serviço Gmail")
            return False
        
        # Cria mensagem multipart
        if html or anexos:
            message = MIMEMultipart('related' if anexos else 'alternative')
            message['to'] = destinatario
            message['subject'] = assunto
            
            # Parte alternativa (texto + HTML)
            if html:
                part_alternative = MIMEMultipart('alternative')
                
                # Adiciona versão texto
                part_text = MIMEText(corpo, 'plain', 'utf-8')
                part_alternative.attach(part_text)
                
                # Adiciona versão HTML
                part_html = MIMEText(html, 'html', 'utf-8')
                part_alternative.attach(part_html)
                
                message.attach(part_alternative)
            else:
                # Apenas texto se não houver HTML
                part_text = MIMEText(corpo, 'plain', 'utf-8')
                message.attach(part_text)
            
            # Adiciona anexos
            if anexos:
                for anexo in anexos:
                    nome = anexo.get('nome', 'anexo')
                    conteudo = anexo.get('conteudo')
                    tipo_mime = anexo.get('tipo', 'application/octet-stream')
                    cid = anexo.get('cid')
                    
                    if conteudo is None:
                        logger.warning(f"[email_sender] Anexo '{nome}' sem conteúdo, ignorando")
                        continue
                    
                    # Se for imagem e tiver CID, adiciona como inline
                    if cid and tipo_mime.startswith('image/'):
                        img = MIMEImage(conteudo)
                        img.add_header('Content-ID', f'<{cid}>')
                        img.add_header('Content-Disposition', 'inline', filename=nome)
                        message.attach(img)
                    else:
                        # Anexo normal
                        part = MIMEBase(*tipo_mime.split('/', 1))
                        part.set_payload(conteudo)
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename="{nome}"')
                        message.attach(part)
                        
        else:
            # Apenas texto plano
            message = MIMEText(corpo, 'plain', 'utf-8')
        message['to'] = destinatario
        message['subject'] = assunto
        
        # Codifica em base64url
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Envia email
        send_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        logger.info(f"[email_sender] Email enviado para: {destinatario} | ID: {send_message.get('id')}")
        return True
        
    except HttpError as e:
        logger.error(f"[email_sender] Erro HTTP ao enviar email: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"[email_sender] Erro ao enviar email: {str(e)}")
        import traceback
        logger.debug(f"[email_sender] Traceback: {traceback.format_exc()}")
        return False


def criar_servico_gmail():
    """
    Cria serviço do Gmail API usando conta de serviço com delegação de domínio
    """
    try:
        logger.debug("[email_sender] Criando serviço Gmail API...")
        
        credenciais_info = {
            "type": ConfigEnvSetings.TYPE,
            "project_id": ConfigEnvSetings.PROJECT_ID,
            "private_key_id": ConfigEnvSetings.PRIVCATE_JEY_ID,
            "private_key": ConfigEnvSetings.PRIVATE_KEY.replace('\\n', '\n'),
            "client_email": ConfigEnvSetings.CLIENT_EMAIL,
            "client_id": ConfigEnvSetings.CLIENT_ID,
            "auth_uri": ConfigEnvSetings.AUTH_URI,
            "token_uri": ConfigEnvSetings.TOKEN_URI,
            "auth_provider_x509_cert_url": ConfigEnvSetings.AUTH_PROVIDER_X509_CERT_URL,
            "client_x509_cert_url": ConfigEnvSetings.CLIENT_X509_CERT_URL,
            "universe_domain": ConfigEnvSetings.UNIVERSE_DOMAIN
        }
        
        credentials = service_account.Credentials.from_service_account_info(
            credenciais_info,
            scopes=['https://www.googleapis.com/auth/gmail.send']
        )
        
        # Se houver um usuário configurado para delegação, usa ele
        # Caso contrário, usa a conta de serviço diretamente
        if hasattr(ConfigEnvSetings, 'GMAIL_DELEGATE_USER') and ConfigEnvSetings.GMAIL_DELEGATE_USER:
            credentials = credentials.with_subject(ConfigEnvSetings.GMAIL_DELEGATE_USER)
        
        service = build('gmail', 'v1', credentials=credentials)
        logger.debug("[email_sender] Serviço Gmail API criado com sucesso")
        return service
        
    except Exception as e:
        logger.error(f"[email_sender] Erro ao criar serviço Gmail API: {str(e)}")
        import traceback
        logger.debug(f"[email_sender] Traceback: {traceback.format_exc()}")
        return None
