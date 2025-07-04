import feedparser
import requests
import os
import time
import html

# --- CONFIGURAÇÕES ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

RSS_URL = 'https://www.workana.com/rss/jobs?category=it-programming&language=pt'
PROCESSED_PROJECTS_FILE = 'processed_projects.txt'

# --- FUNÇÕES ---

def load_processed_projects():
    """Carrega os links dos projetos já processados a partir de um arquivo de texto."""
    if not os.path.exists(PROCESSED_PROJECTS_FILE):
        return set()
    with open(PROCESSED_PROJECTS_FILE, 'r') as f:
        return set(line.strip() for line in f)

def save_processed_project(project_link):
    """Salva um novo link de projeto no arquivo para não processar novamente."""
    with open(PROCESSED_PROJECTS_FILE, 'a') as f:
        f.write(project_link + '\n')

def get_gemini_response(title, description):
    """Envia o projeto para a API do Gemini e retorna a mensagem personalizada."""
    print(f"Pedindo ao Gemini para criar mensagem para: {title}")
    prompt = f"""
    Você é um freelancer especialista em desenvolvimento de software e websites. 
    Analise o título e a descrição do projeto a seguir e escreva uma mensagem de abertura curta (2 a 3 parágrafos) e impactante para o cliente na Workana. 
    A mensagem deve: 
    1. Demonstrar que eu li e entendi a necessidade principal. 
    2. Mencionar brevemente como minha experiência se alinha ao que é pedido. 
    3. Terminar com uma frase proativa que convide a uma discussão técnica sobre o projeto, sem ser uma pergunta de 'sim' ou 'não'.
    O tom deve ser profissional, mas acessível. Não use saudações como 'Olá' ou 'Prezado', comece direto ao ponto. Não se despeça no final.

    Projeto:
    Título: {title}
    Descrição: {description}
    """

    api_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}'

    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except requests.exceptions.RequestException as e:
        print(f"Erro ao chamar a API do Gemini: {e}")
        return None

def send_telegram_message(message_text):
    """Envia a mensagem final para o seu bot do Telegram."""
    api_url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'

    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message_text,
        'parse_mode': 'HTML'
    }

    try:
        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status()
        print("Notificação enviada com sucesso para o Telegram.")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar mensagem para o Telegram: {e}")

# --- LÓGICA PRINCIPAL ---

if not all([GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    print("ERRO: Variáveis de ambiente (GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) não configuradas.")
else:
    print("Robô iniciado. Pressione Ctrl+C para parar.")
    while True:
        print(f"\nVerificando o feed RSS... [{time.ctime()}]")

        processed_links = load_processed_projects()
        feed = feedparser.parse(RSS_URL)

        if not feed.entries:
            print("Feed vazio ou com erro. Tentando novamente em 1 minuto.")
        else:
            new_projects_found = 0
            for entry in reversed(feed.entries):
                project_link = entry.link

                if project_link not in processed_links:
                    new_projects_found += 1
                    print(f"--- NOVO PROJETO ENCONTRADO: {entry.title} ---")

                    description = html.unescape(entry.summary)
                    ai_message = get_gemini_response(entry.title, description)

                    if aiMessage:
                        message_for_telegram = (
                            f"<b>🚀 Novo Projeto na Workana!</b>\n\n"
                            f"<b>Título:</b> {html.escape(entry.title)}\n\n"
                            f"<b><a href='{html.escape(project_link)}'>CLIQUE AQUI PARA VER O PROJETO</a></b>\n\n"
                            f"👇 <b>Mensagem sugerida pela IA (copie e cole):</b> 👇\n\n"
                            f"<code>{html.escape(ai_message)}</code>"
                        )
                        send_telegram_message(message_for_telegram)

                    save_processed_project(project_link)
                    time.sleep(5)

            if new_projects_found == 0:
                print("Nenhum projeto novo encontrado.")

        time.sleep(60)
