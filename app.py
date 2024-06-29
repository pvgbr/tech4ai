import json
import datetime
from groq import Groq
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from flask import Flask, request, jsonify, send_from_directory, session
from markupsafe import escape, Markup
import re

app = Flask(__name__, static_folder='web')
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

def agendar_reuniao_boas_vindas(data_reuniao, hora_reuniao):
    # Config Google Calendar
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
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
        'summary': 'Reunião de Boas-Vindas',
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
    return [
        {
            "role": "system",
            "content": f"Contexto da empresa: {json.dumps(resumo_base_de_dados)}"
        }
    ]

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

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    user_message = request.json.get('message')
    historico_mensagens = carregar_historico()
    historico_mensagens.append({"role": "user", "content": user_message})

    response = ""
    
    if 'agendar_reuniao' in session:
        if 'data_reuniao' not in session:
            session['data_reuniao'] = user_message
            response = "Por favor, forneça a hora da reunião (HH:MM)."
        elif 'hora_reuniao' not in session:
            session['hora_reuniao'] = user_message
            link_reuniao = agendar_reuniao_boas_vindas(session['data_reuniao'], session['hora_reuniao'])
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
                max_tokens=512,
                top_p=1,
                stream=True,
                stop=None,
            )
            for chunk in completion:
                response += chunk.choices[0].delta.content or ""

    historico_mensagens.append({"role": "system", "content": response})
    salvar_historico(historico_mensagens)
    
    # Escapar o conteúdo HTML
    response = escape(response)
    
    # Substituir as quebras de linha
    response = response.replace('\n', Markup('<br>'))
    
    # Substituir **texto** por <b>texto</b>
    response = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', response)
    
    # Substituir *texto* por <b>texto</b> (para suportar a formatação original)
    response = re.sub(r'\*(.*?)\*', r'<b>\1</b>', response)

    response = re.sub(r'(https?://\S+)', r'<a href="\1" target="_blank">\1</a>', response)
    
    response = Markup(response)
    
    return jsonify({"response": str(response)})

if __name__ == "__main__":
    app.run(debug=True)