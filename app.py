import json
import datetime
import re
import os
from groq import Groq
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, render_template
from markupsafe import escape, Markup

app = Flask(__name__, static_folder='web', template_folder='web')
app.secret_key = 'tech4ai'

client = Groq(api_key="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")

with open('base_de_dados.json', 'r') as f:
    base_de_dados = json.load(f)

def resumir_dados(dados):
    resumo = {
        "empresa": {
            "nome": dados["empresa"].get("nome"),
            "fundacao": dados["empresa"].get("fundacao"),
            "localizacao": dados["empresa"].get("localizacao"),
            "sobre": dados["empresa"].get("sobre"),
            "produtos": dados["empresa"].get("produtos"),
        },
        "circulos": [
            {
                "nome": circulo["nome"],
                "times": [
                    {
                        "nome": time["nome"],
                        "responsabilidades": time["responsabilidades"][:200]
                    } for time in circulo["times"]
                ]
            } for circulo in dados["empresa"].get("circulos", [])
        ],
        "programas": [
            {
                "programa": programa["programa"],
                "descricao": programa["descricao"][:200] 
            } for programa in dados["empresa"].get("programas", [])
        ],
        "virtudes": [
            {
                "pilar": virtude["pilar"],
                "topicos": [
                    {
                        "nome": topico["nome"],
                        "descricao": topico["descricao"][:200] 
                    } for topico in virtude["topicos"]
                ]
            } for virtude in dados["empresa"].get("virtudes", [])
        ]
    }
    return resumo

resumo_base_de_dados = resumir_dados(base_de_dados)

# Configurações do OAuth 2.0
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/userinfo.profile']

# Limpar o histórico ao iniciar o servidor
def limpar_historico():
    with open('gerenciar_contexto.json', 'w') as f:
        json.dump([], f, ensure_ascii=False, indent=4)

limpar_historico()

@app.route('/login')
def login():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)

    # Obter informações do perfil do usuário
    people_service = build('people', 'v1', credentials=credentials)
    profile = people_service.people().get(resourceName='people/me', personFields='names').execute()
    nome_usuario = profile.get('names', [])[0].get('displayName')
    session['nome_usuario'] = nome_usuario

    return redirect(url_for('index'))

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

@app.route('/')
def index():
    if 'credentials' not in session:
        return redirect(url_for('login'))  # Redireciona para a tela de login
    nome_usuario = session.get('nome_usuario', 'Usuário')
    return render_template('index.html', nome_usuario=nome_usuario)

def get_credentials():
    if 'credentials' not in session:
        return None
    credentials = Credentials(**session['credentials'])
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        session['credentials'] = credentials_to_dict(credentials)
    return credentials

def agendar_reuniao_boas_vindas(data_reuniao, hora_reuniao):
    # Verificar se a data está no formato correto
    if not re.match(r'^\d{2}/\d{2}$', data_reuniao):
        return "Data inválida. Por favor, forneça a data no formato DD/MM."
    
    # Verificar se a hora está no formato correto
    if not re.match(r'^\d{2}:\d{2}$', hora_reuniao):
        return "Hora inválida. Por favor, forneça a hora no formato HH:MM."

    creds = get_credentials()
    if not creds:
        return redirect(url_for('login'))

    service = build('calendar', 'v3', credentials=creds)

    # Converter a data para (AAAA-MM-DD)
    dia, mes = data_reuniao.split('/')
    ano = datetime.datetime.now().year
    data_iso = f"{ano}-{mes}-{dia}"
    
    inicio = f"{data_iso}T{hora_reuniao}:00-03:00"  # Fuso horario
    
    # Fim da reuniao em 1h
    inicio_datetime = datetime.datetime.fromisoformat(inicio)
    fim_datetime = inicio_datetime + datetime.timedelta(hours=1)
    fim = fim_datetime.isoformat()
    
    evento = {
        'summary': f'Reunião de Boas-Vindas com {session["nome_usuario"]}',
        'description': 'Bem-vindo à Tech4humans! Esta é uma reunião para conhecê-lo melhor e apresentar nossa equipe.',
        'start': {
            'dateTime': inicio,
            'timeZone': 'America/Sao_Paulo',
        },
        'end': {
            'dateTime': fim,
            'timeZone': 'America/Sao_Paulo',
        },
    }
    evento = service.events().insert(calendarId='primary', body=evento).execute()
    return evento.get('htmlLink')

def carregar_historico():
    try:
        with open('gerenciar_contexto.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def salvar_historico(historico):
    with open('gerenciar_contexto.json', 'w') as f:
        json.dump(historico, f, ensure_ascii=False, indent=4)

def carregar_reunioes():
    try:
        with open('reunioes_agendadas.json', 'r') as f:
            conteudo = f.read().strip()
            if conteudo:
                return json.loads(conteudo)
            else:
                return []
    except FileNotFoundError:
        return []

def salvar_reunioes(reunioes):
    with open('reunioes_agendadas.json', 'w') as f:
        json.dump(reunioes, f, ensure_ascii=False, indent=4)

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

def truncar_historico(historico, max_tokens=1024):
    total_tokens = 0
    truncado = []
    
    # Garantir que pelo menos as 3 últimas mensagens sejam incluídas
    ultimas_mensagens = historico[-6:] 
    for mensagem in reversed(ultimas_mensagens):
        mensagem_tokens = len(mensagem['content'].split())
        truncado.insert(0, mensagem)
        total_tokens += mensagem_tokens

    # Adicionar mensagens anteriores até atingir o limite de tokens
    for mensagem in reversed(historico[:-6]):
        mensagem_tokens = len(mensagem['content'].split())
        if total_tokens + mensagem_tokens > max_tokens:
            break
        truncado.insert(0, mensagem)
        total_tokens += mensagem_tokens
    
    return truncado

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    user_message = request.json.get('message')
    historico_mensagens = carregar_historico()
    
    # Adicionar contexto ao agente
    contexto_agente = {
        "role": "system",
        "content": "Você é um assistente virtual para novos funcionários da Tech4humans. Sua função é ajudar os novos funcionários com informações sobre a empresa, agendar reuniões de boas-vindas, fornecer tutorias de plataformas, como discord, vscode, jira e github, e responder a perguntas de forma educada e profissional. Não forneça informações pessoais, evite linguagem ofensiva e não fale sobre outras empresas"
    }
    historico_mensagens.insert(0, contexto_agente)
    
    historico_mensagens.append({"role": "user", "content": user_message})
    historico_mensagens.append({"role": "system", "content": json.dumps(resumo_base_de_dados)})
    historico_mensagens = truncar_historico(historico_mensagens)

    response = ""


    # Verificações de segurança e conteúdo
    if re.search(r'\b(discurso de ódio|insultos|linguagem ofensiva)\b', user_message, re.IGNORECASE):
        response = "Desculpe, não tolero discurso de ódio ou linguagem ofensiva."
    elif re.search(r'\b(informação pessoal|dados pessoais)\b', user_message, re.IGNORECASE):
        response = "Desculpe, não posso fornecer informações pessoais."
    elif re.search(r'[\{\}\[\]]', user_message):  # Verificação para injeções
        response = "Desculpe, a requisição contém caracteres não permitidos."
    elif 'agendar_reuniao' in session:
        if 'data_reuniao' not in session:
            if not re.match(r'^\d{2}/\d{2}$', user_message):
                response = "Data inválida. Por favor, forneça a data no formato DD/MM."
            else:
                session['data_reuniao'] = user_message
                response = "Por favor, forneça a hora da reunião (HH:MM)."
        elif 'hora_reuniao' not in session:
            if not re.match(r'^\d{2}:\d{2}$', user_message):
                response = "Hora inválida. Por favor, forneça a hora no formato HH:MM."
            else:
                session['hora_reuniao'] = user_message
                link_reuniao = agendar_reuniao_boas_vindas(session['data_reuniao'], session['hora_reuniao'])
                if "Data inválida" in link_reuniao or "Hora inválida" in link_reuniao:
                    response = link_reuniao
                    session.pop('hora_reuniao')
                else:
                    response = f"Reunião agendada com sucesso! Acesse o Google Calendar para mais informações: {link_reuniao}"
                    session.pop('agendar_reuniao')
                    session.pop('data_reuniao')
                    session.pop('hora_reuniao')
    else:
        if any(keyword in user_message.lower() for keyword in ["agendar reunião", "agendar reuniao", "marcar reunião", "marcar reuniao", "reunião boas-vindas", "reunião boas vindas", "gostaria de agendar", "gostaria de marcar", "agendar uma reunião", "marcar uma reunião"]):
            session['agendar_reuniao'] = True
            response = "Por favor, forneça a data da reunião (DD/MM)."
        else:
            completion = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=historico_mensagens,
                temperature=1,
                max_tokens=1024,
                top_p=1,
                stream=True,
                stop=None,
            )
            for chunk in completion:
                response += chunk.choices[0].delta.content or ""

    historico_mensagens.append({"role": "system", "content": response})
    salvar_historico(historico_mensagens)
    
    response = escape(response)
    response = response.replace('\n', Markup('<br>'))
    response = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', response)
    response = re.sub(r'(https?://\S+)', r'<a href="\1" target="_blank">\1</a>', response)
    response = Markup(response)
    
    return jsonify({"response": str(response)})


@app.route('/reiniciar_agente', methods=['POST'])
def reiniciar_agente():
    limpar_historico()
    session.clear()
    return jsonify({"message": "Agente reiniciado com sucesso."})

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify(success=True)

if __name__ == "__main__":
    app.run(debug=True)