// --- VARIÁVEIS GLOBAIS ---
var ID_PASTA_DRIVE = "1ZbYzUiVWON-54NrKrg9BhqEdRQsJT5F2"; // ID da pasta definido pelo usuário

function API_MAIN() {
  var labelProcessados = "PROCESSADOS";
  var query = 'is:unread'; // Processa apenas não lidos

  var labelProcessadosObj;
  try {
    labelProcessadosObj = GmailApp.getUserLabelByName(labelProcessados);
    if (!labelProcessadosObj) {
      labelProcessadosObj = GmailApp.createLabel(labelProcessados);
    }
  } catch (e) {
    labelProcessadosObj = GmailApp.createLabel(labelProcessados);
  }

  // Busca threads não lidas
  const threadsEmails = GmailApp.search(query);

  for (var i = 0; i < threadsEmails.length; i++) {
    var thread = threadsEmails[i];
    var labels = thread.getLabels();
    var jaProcessado = false;

    // Verifica se já tem a label PROCESSADOS (dupla verificação)
    for (var j = 0; j < labels.length; j++) {
      if (labels[j].getName() === labelProcessados) {
        jaProcessado = true;
        break;
      }
    }

    if (jaProcessado) {
      console.log("Email já processado - pulando thread ID: " + thread.getId());
      continue;
    }

    // Pega a primeira mensagem da thread
    var message = thread.getMessages()[0];

    var emailSubject = message.getSubject();
    var emailBody = message.getPlainBody();
    var emailFrom = message.getFrom();
    
    // Extrai apenas o email do remetente (remove o nome <email>)
    var match = emailFrom.match(/<([^>]+)>/);
    var emailRemetente = match ? match[1] : emailFrom;

    console.log("Processando email de: " + emailRemetente);
    console.log("Assunto: " + emailSubject);

    // Validação de segurança do domínio
    var validacaoEmail = validarEmailUisa(emailRemetente);
    if (!validacaoEmail.valido) {
      console.log("Email bloqueado - não processado: " + emailRemetente + " - Motivo: " + validacaoEmail.mensagem);
      try {
        thread.addLabel(labelProcessadosObj);
        thread.markRead();
      } catch (e) {
        console.log("Erro ao adicionar label: " + e.toString());
        thread.markRead();
      }
      continue;
    }

    // Marca como processado ANTES de chamar a API para evitar loops em caso de erro fatal
    try {
      thread.addLabel(labelProcessadosObj);
      thread.markRead();
    } catch (e) {
      console.log("Erro ao adicionar label: " + e.toString());
    }

    // --- CHAMADA PRINCIPAL ---
    var resposta = API_EMAIL_CHAMADO(emailSubject, emailBody, emailRemetente, message);

    if (resposta) {
      try {
        // A API pode retornar o processInstanceId diretamente como número ou como JSON
        var respostaProcessada = null;
        
        // Tentar parsear como JSON primeiro
        try {
          respostaProcessada = JSON.parse(resposta);
          console.log("Resposta da API (JSON): " + JSON.stringify(respostaProcessada));
        } catch (e) {
          // Se não for JSON, pode ser um número direto
          var numeroResposta = parseFloat(resposta.trim());
          if (!isNaN(numeroResposta)) {
            respostaProcessada = numeroResposta;
            console.log("Resposta da API (número): " + respostaProcessada);
          } else {
            console.log("Resposta da API (texto): " + resposta);
            respostaProcessada = resposta;
          }
        }
        
        processarRespostaChamado(respostaProcessada, emailRemetente, emailSubject);
      } catch (e) {
        console.log("Erro ao processar resposta: " + e.message);
      }
    }
  }
}

function API_EMAIL_CHAMADO(Assunto, Corpo, Email, message) {
  // URLs atualizadas para a nova versão da API (v2.0.0)
  var base_url = "https://prd-api-fluig-python-186726132534.us-east1.run.app/";
  var url_uisa = base_url + "/api/v1/fluig/prd/chamados/abrir";
  var url_movti = base_url + "/api/v1/terceiros/movit/chamados/abrir-classificado";

  var telefoneDoContato = buscarTelefoneNoDiretorio(Email);

  // --- LÓGICA DE ANEXOS INTEGRADA ---
  var anexosIds = [];
  
  if (message) {
    try {
      var anexos = message.getAttachments();
      
      if (anexos && anexos.length > 0) {
        console.log("Encontrados " + anexos.length + " anexo(s) no email.");
        
        for (var i = 0; i < anexos.length; i++) {
          var anexo = anexos[i];
          var nomeArquivo = anexo.getName();
          
          // Chama a função auxiliar para salvar e pegar o ID
          var fileId = salvarAnexoNoDrive(anexo, nomeArquivo, ID_PASTA_DRIVE);
          
          if (fileId) {
            anexosIds.push(fileId);
            console.log("Anexo processado com sucesso. ID adicionado à lista: " + fileId);
          }
        }
      } else {
        console.log("Nenhum anexo encontrado no email.");
      }
    } catch (e) {
      console.log("Erro ao processar anexos da mensagem: " + e.toString());
    }
  }

  // Verifica se é email Movit
  var isMovit = Email && typeof Email === 'string' && Email.toLowerCase().trim().endsWith("@movti.com.br");

  var dados;
  var endpointUrl;

  if (isMovit) {
    // Payload Movit
    endpointUrl = url_movti;
    dados = {
      "titulo": Assunto,
      "descricao": Corpo
    };
    console.log("Endpoint: Movti");
  } else {
    // Payload UISA
    endpointUrl = url_uisa;
    dados = {
      "titulo": Assunto,
      "descricao": Corpo,
      "usuario": Email,
      "telefone": telefoneDoContato || null
    };

    // INSERE OS IDS DOS ANEXOS NO JSON SE HOUVER ARQUIVOS SALVOS
    if (anexosIds.length > 0) {
      dados.anexos_ids = anexosIds;
      console.log("Incluindo " + anexosIds.length + " IDs de anexos no payload.");
    }

    console.log("Endpoint: Uisa Padrão");
  }

  console.log("PAYLOAD A ENVIAR: ", JSON.stringify(dados));

  var options = {
    "method": "post",
    "headers": {
      "API-KEY": "CV7uYNpRr2tciYu2s4IEWaikuIAw",
      "Content-Type": "application/json"
    },
    "payload": JSON.stringify(dados),
    "muteHttpExceptions": true
  };

  try {
    var response = UrlFetchApp.fetch(endpointUrl, options);
    var responseCode = response.getResponseCode();
    var responseBody = response.getContentText();
    
    console.log("Código HTTP: " + responseCode);
    console.log("Body Retorno: " + responseBody);

    if (responseCode === 200 || responseCode === 201) {
      // A API retorna o processInstanceId diretamente como número ou JSON
      return responseBody;
    } else {
      // Tentar extrair mensagem de erro se disponível
      try {
        var errorJson = JSON.parse(responseBody);
        console.log("Erro da API: " + (errorJson.detail || errorJson.message || JSON.stringify(errorJson)));
      } catch (e) {
        console.log("Resposta de erro não é JSON válido");
      }
      console.log("Falha na API. Código: " + responseCode);
      return null;
    }

  } catch (e) {
    console.log("Erro fatal na conexão (UrlFetch): " + e.toString());
    return null;
  }
}

// --- FUNÇÃO AUXILIAR PARA SALVAR E RETORNAR ID ---
function salvarAnexoNoDrive(anexo, nomeArquivo, folderId) {
  try {
    var folder = DriveApp.getFolderById(folderId);
    
    // Cria o arquivo no Drive usando o blob do anexo
    var file = folder.createFile(anexo.copyBlob());
    
    // Define o nome (garantia extra)
    file.setName(nomeArquivo);
    
    var fileId = file.getId();
    console.log("Arquivo salvo: " + nomeArquivo + " | ID: " + fileId);
    
    return fileId;
  } catch (e) {
    console.log("ERRO CRÍTICO ao salvar anexo " + nomeArquivo + ": " + e.toString());
    return null;
  }
}

// --- FUNÇÕES AUXILIARES (VALIDAÇÃO, TELEFONE, RESPOSTA) ---

function buscarTelefoneNoDiretorio(emailDoRemetente) {
  try {
    var options = {
      query: emailDoRemetente,
      readMask: "phoneNumbers,emailAddresses",
      sources: ["DIRECTORY_SOURCE_TYPE_DOMAIN_CONTACT", "DIRECTORY_SOURCE_TYPE_DOMAIN_PROFILE"]
    };
    var response = People.People.searchDirectoryPeople(options);
    var people = response.people;
    if (people && people.length > 0) {
      var person = people[0];
      var emailBate = person.emailAddresses && person.emailAddresses.some(e => e.value === emailDoRemetente);
      if (emailBate && person.phoneNumbers && person.phoneNumbers.length > 0) {
        return person.phoneNumbers[0].value;
      }
    }
    return "";
  } catch (e) {
    console.log("Aviso: Não foi possível obter telefone (People API): " + e.message);
    return "";
  }
}

function validarEmailUisa(email) {
  if (!email || typeof email !== 'string') {
    return { valido: false, mensagem: "Email inválido/vazio" };
  }
  var emailLower = email.toLowerCase().trim();
  var emailsExternosPermitidos = ["secops-soc@movti.com.br"];

  if (emailsExternosPermitidos.indexOf(emailLower) !== -1) return { valido: true, mensagem: null };
  if (!emailLower.endsWith("@uisa.com.br")) return { valido: false, mensagem: "Domínio não permitido" };

  var emailsSistemaBloqueados = [
    "fluig@uisa.com.br", "noreply@uisa.com.br", "no-reply@uisa.com.br", 
    "sistema@uisa.com.br", "automacao@uisa.com.br"
  ];

  if (emailsSistemaBloqueados.indexOf(emailLower) !== -1) {
    return { valido: false, mensagem: "Email de sistema bloqueado" };
  }
  return { valido: true, mensagem: null };
}

function processarRespostaChamado(resposta, emailRemetente, assuntoOriginal) {
  var processInstanceId = null;

  if (typeof resposta === 'number') {
    processInstanceId = resposta;
  } else if (typeof resposta === 'string' && !isNaN(parseInt(resposta))) {
    processInstanceId = parseInt(resposta);
  } else if (resposta && typeof resposta === 'object') {
    if (resposta.processInstanceId) processInstanceId = resposta.processInstanceId;
    else if (resposta.dados && resposta.dados.processInstanceId) processInstanceId = resposta.dados.processInstanceId;
    else if (resposta.status === "rejeitado" || resposta.status === "erro") {
       enviarEmail(emailRemetente, "Chamado Não Aprovado", "O chamado não pôde ser aberto.\nMotivo: " + (resposta.mensagem || "Erro genérico"));
       return;
    }
  }

  if (processInstanceId) {
    var link = "https://fluig.uisa.com.br/portal/p/1/pageworkflowview?app_ecm_workflowview_detailsProcessInstanceID=" + processInstanceId;
    enviarEmail(emailRemetente, "Chamado Aberto - #" + processInstanceId, "Chamado criado com sucesso.\nNúmero: " + processInstanceId + "\nLink: " + link);
  } else {
    console.log("Erro: processInstanceId não identificado na resposta.");
  }
}

function enviarEmail(destinatario, assunto, corpo) {
  try {
    MailApp.sendEmail({ to: destinatario, subject: assunto, body: corpo });
    console.log("Email enviado para: " + destinatario);
  } catch (e) {
    console.log("Erro envio email: " + e.toString());
  }
}

function criarTrigger() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'API_MAIN') ScriptApp.deleteTrigger(triggers[i]);
  }
  // MODIFICADO - ALTERAR PARA 30 MINUTOS
  ScriptApp.newTrigger('API_MAIN').timeBased().everyMinutes(1).create();
  console.log("Trigger configurado.");
}