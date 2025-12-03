def prompt2(var1,var2):
    
    prompt= f"""
        ### Contexto
        Estou validando a qualidade de um chamado de TI.
        ### Título do Chamado
            {var1}
        ### Descrição do Chamado
            {var2}
        ### Tarefa
            Avalie se o Título e a Descrição são condizentes.
            Caso tenha erros de digitação, ortografia e gramática, corrija 
        Responda às seguintes perguntas:
            1.  O título resume com precisão o problema ou a solicitação descrita?
            2.  A descrição fornece detalhes suficientes para justificar o título?
            3.  Há alguma informação conflitante entre o título e a descrição? 
        ### Formato de Saída Obrigatório
        ### Siga estritamente um dos dois formatos abaixo, sem adicionar comentários extras.
            # CASO 1: O chamado é INSUFICIENTE
                Se o chamado não atender aos Critérios para "Suficiente", responda #NÃO# com hastag e, em seguida, gere uma mensagem amigável e construtiva para o usuário final que será enviada por e-mail.
                •Estrutura da Mensagem de Resposta:
                    •Saudação e Status: Comece com uma saudação amigável e explique que o chamado ainda não pôde ser aberto.
                    •Motivo Específico: Identifique de forma clara e educada o que faltou (ex: "o título está muito genérico" ou "precisamos de mais detalhes na descrição").
                ♦Exemplo (para um chamado com descrição vaga): #NÃO#. Olá! Vimos sua solicitação, mas seu chamado ainda não pôde ser aberto.
                ♦Para que nossa equipe de TI possa entender e resolver seu problema o mais rápido possível, precisamos de um pouco mais de contexto. A descrição "Não funciona" é muito vaga.
            #CASO 1: O chamado é SUFICIENTE
                Se o chamado atender aos Critérios para "Suficiente", responda #SIM# e, em seguida, forneça o &Título& e a &Descrição& já corrigidos (erros de digitação e gramática) e prontos para serem inseridos no sistema de chamados.
                ♦Exemplo: #SIM#. &Título& Usuário com dificuldade para acessar a pasta da rede &Descrição& O usuário informa que não consegue acessar a pasta compartilhada 'X:\Financeiro'.   O sistema retorna a mensagem de erro 'Acesso negado'. O acesso funcionava normalmente ontem.
            """
    return prompt

def prompt1(var1,var2):
    prompt= f"""
        ### Contexto
        Estou validando a qualidade de um chamado de TI.
        ### Título do Chamado
            {var1}
        ### Descrição do Chamado
            {var2}
        ### Tarefa
            Avalie se o Título e a Descrição são condizentes.
            Caso tenha erros de digitação, ortografia e gramática, corrija 
        Responda às seguintes perguntas:
            1.  O título faz sentido para o problema ou a solicitação descrita?
            2.  A descrição faz sentido para o problema ou a solicitação descrita?
        
        ### Formato de Saída Obrigatório
        ### Siga estritamente um dos dois formatos abaixo, sem adicionar comentários extras.
            # CASO 1: O chamado é INSUFICIENTE
                ### OBS: Não peça para o usuário Anexar arquivos ou imagens.
                Se o chamado não atender aos Critérios para "Suficiente", responda #NÃO# com hastag e, em seguida, gere uma mensagem amigável e construtiva para o usuário final que será enviada por e-mail.
                •Estrutura da Mensagem de Resposta:
                    •Saudação e Status: Comece com uma saudação amigável e explique que o chamado ainda não pôde ser aberto.
                    •Motivo Específico: Identifique de forma clara e educada o que faltou (ex: "o título está muito genérico" ou "precisamos de mais detalhes na descrição").
                ♦Exemplo (para um chamado com descrição vaga): #NÃO#. Olá! Vimos sua solicitação, mas seu chamado ainda não pôde ser aberto.
                ♦Para que nossa equipe de TI possa entender e resolver seu problema o mais rápido possível, precisamos de um pouco mais de contexto. A descrição "Não funciona" é muito vaga.
            #CASO 1: O chamado é SUFICIENTE
                Se o chamado atender aos Critérios para "Suficiente", responda #SIM# e, em seguida, forneça o &Título& e a &Descrição& já corrigidos (erros de digitação e gramática) e prontos para serem inseridos no sistema de chamados.
                ♦Exemplo: #SIM#. &Título& Usuário com dificuldade para acessar a pasta da rede &Descrição& O usuário informa que não consegue acessar a pasta compartilhada 'X:\Financeiro'.   O sistema retorna a mensagem de erro 'Acesso negado'. O acesso funcionava normalmente ontem.
            """
    return prompt

def prompt3(var1):

    """
    On 2025-11-18 at 19:10:00 UTC, a high-severity alert with a risk score of 75 was triggered within the UISA environment due to a user account being added to a group. * User AD2190321_EXT added Dayanny Salvadego Scudeler Romao to the group GRP-SPO-UISA-SEG-TRAB-09-SEG-TRABALHO from host UISASRV177.ita.corp. * This GROUP_MODIFICATION event, logged on UISASRV177.ita.corp with process ID 900, requires investigation to validate the authorization and legitimacy of the group membership change."""
    prompt=f"""
        ### Tarefa
            Analise o "Resumo do Alerta" abaixo e extraia o ID do usuário principal OU o email do usuário. 
            Priorize a extração do email do usuário quando disponível, caso contrário, extraia o ID do usuário (string numérica geralmente de 7 a 9 dígitos).

        ### Contexto e Padrões para Email
            O email do usuário pode aparecer em vários formatos:
                1.  Após a palavra "user" ou "associated with user" seguido de um email.
                    * Exemplo: "...associated with user nome.sobrenome@uisa.com.br..."
                    * Extração: nome.sobrenome@uisa.com.br
                2.  Em contexto de login ou autenticação.
                    * Exemplo: "...logins by nome.sobrenome@uisa.com.br from..."
                    * Extração: nome.sobrenome@uisa.com.br
                3.  Em formato padrão de email (texto@dominio.com).
                    * Exemplo: "...user nome.sobrenome@uisa.com.br..."
                    * Extração: nome.sobrenome@uisa.com.br

        ### Contexto e Padrões para ID do Usuário
            O ID do usuário pode aparecer em vários formatos:
                1.  Imediatamente após a palavra "user", seguido por uma vírgula.
                    * Exemplo: "...A user, 8002789, from the NIVEL A NEW group..."
                    * Extração: 8002789
                2.  Imediatamente após a palavra "user", seguido por parênteses.
                    * Exemplo: "...involves user 8002789 (userDisplayName 8002789)..."
                    * Extração: 8002789
                3.  Dentro de parênteses, logo após a palavra "user".
                    * Exemplo: "...A user (0899275) on host FSSO_UISA..."
                    * Extração: 0899275  

        ### Formato de Saída
            Responda APENAS com o email do usuário (se encontrado) OU o ID do usuário extraído. 
            Não inclua texto adicional, explicações ou saudações.
            Caso não haja email nem ID do usuário, responda apenas com "NÃO ENCONTRADO".         

        ### Resumo do Alerta
        {var1}
    """
    return prompt

def prompt4(var1):
    prompt=f"""
        ### Tarefa
        traduza o texto abaixo para o português brasileiro.
        ### Texto
        {var1}
        ### Formato de Saída
        Responda APENAS com o texto traduzido para o português brasileiro.
    """
    return prompt