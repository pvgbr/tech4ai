
import json
import datetime
from groq import Groq
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

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

def agendar_reuniao_boas_vindas():
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

    # Perguntar a data e hora da reunião ao usuário
    data_reuniao = input("Perfeito. Vamos agendar sua reunião de boas-vindas! \nPor favor, insira a data da reunião (DD/MM): ")
    hora_reuniao = input("Por favor, insira a hora de início da reunião (HH:MM, 24h): ")
    
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
    print(f"Reunião agendada com sucesso! Acesse o Google Calendar para mais informações: {evento.get('htmlLink')}")
    return evento 

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

def chat():
    print("\nOlá! Eu sou a Tech4AI, sua assistente virtual.")
    print("Eu posso ajudar com as seguintes funções:")
    print("- Responder perguntas sobre a Tech4humans")
    print("- Agendar reuniões de boas-vindas")
    print("Como posso ajudar você hoje?\n")
    
    historico_mensagens = carregar_historico()
    reunioes_agendadas = carregar_reunioes()
    
    evento_agendado = None  # Variável para armazenar detalhes do evento agendado
    
    while True:
        user_message = input("Você: ")
        if user_message.lower() in ["sair", "exit", "quit"]:
            print("Encerrando o chat.")
            salvar_historico(historico_mensagens)
            salvar_reunioes(reunioes_agendadas)
            break

        # Adicionar mensagem do usuário ao histórico
        historico_mensagens.append({
            "role": "user",
            "content": user_message
        })

        if any(keyword in user_message.lower() for keyword in ["agendar reunião", "agendar reuniao", "marcar reunião", "marcar reuniao", "reunião boas-vindas", "reunião boas vindas", "gostaria de agendar", "gostaria de marcar", "agendar uma reunião", "marcar uma reunião"]):
            evento_agendado = agendar_reuniao_boas_vindas()
            reunioes_agendadas.append(evento_agendado)
            continue

        if any(keyword in user_message.lower() for keyword in ["dados da reunião", "detalhes da reunião", "informações da reunião", "reunião agendada"]):
            if reunioes_agendadas:
                response = "Detalhes das reuniões agendadas:\n"
                for evento in reunioes_agendadas:
                    response += f"Título: {evento['summary']}\nDescrição: {evento['description']}\nInício: {evento['start']['dateTime']}\nFim: {evento['end']['dateTime']}\nLink: {evento.get('htmlLink')}\n\n"
            else:
                response = "Nenhuma reunião foi agendada ainda."
        else:
            response = ""
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
        
        historico_mensagens.append({
            "role": "system",
            "content": response
        })
        
        print(f"Tech4AI: {response}")

        salvar_historico(historico_mensagens)
        salvar_reunioes(reunioes_agendadas)

if __name__ == "__main__":
    chat()