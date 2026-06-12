import os
import http.server
import threading
import telebot
from PyPDF2 import PdfReader
from google import genai

# ========================================================
# 1. SERVIDOR WEB FALSO (Para evitar o erro de porta do Render)
# ========================================================
def run_fake_server():
    port = int(os.environ.get("PORT", 10000))
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, http.server.SimpleHTTPRequestHandler)
    print(f"📡 Servidor de autenticação ativo na porta {port}")
    httpd.serve_forever()

# Inicia o servidor web em segundo plano para o Render não derrubar o bot
threading.Thread(target=run_fake_server, daemon=True).start()

# ========================================================
# 2. CONFIGURAÇÕES DO BOT E AUTENTICAÇÃO DA IA
# ========================================================
# Seu Token do Telegram
TOKEN_TELEGRAM = "8853899021:AAETpmOM9ACw29kfR35XjU_K2cvdGPS3euM"
bot = telebot.TeleBot(TOKEN_TELEGRAM)

# Sua chave do Gemini (Formato AQ.Ab8...)
CHAVE_GEMINI = "AQ.Ab8RN6JBfMmv9qHSE7LT86oA5azvAC8nMdDRehnb7ePFvOdF9A"

# CORREÇÃO DO ERRO 401: Passando a chave direto no cabeçalho HTTP
client = genai.Client(http_options={'headers': {'x-goog-api-key': CHAVE_GEMINI}})

print("🧠 CortexBot OPERACIONAL e com leitura automática de PDFs ativa.")

# ========================================================
# 3. MENU PRINCIPAL DO TELEGRAM
# ========================================================
@bot.message_handler(commands=['start', 'ajuda'])
def enviar_boas_vindas(mensagem):
    menu = (
        "🧠 Olá! Sou o CortexBot, seu assistente pessoal inteligente.\n\n"
        "Estou aqui para simplificar suas tarefas, analisar seus documentos e apoiar você no que for preciso.\n\n"
        "Pode falar comigo normalmente e eu farei o meu melhor para ajudar!"
    )
    bot.reply_to(mensagem, menu)

# ========================================================
# 4. PROCESSAMENTO DE MENSAGENS E LEITURA DE PDF
# ========================================================
@bot.message_handler(func=lambda mensagem: True)
def processar_mensagem_ia(mensagem):
    try:
        pergunta_usuario = message_text := mensagem.text
        
        # Procura e lê qualquer arquivo PDF na pasta do servidor
        texto_livro = ""
        arquivo_pdf_encontrado = None

        for arquivo in os.listdir('.'):
            if arquivo.endswith('.pdf'):
                arquivo_pdf_encontrado = arquivo
                break  

        if arquivo_pdf_encontrado:
            print(f"📖 Lendo o arquivo: {arquivo_pdf_encontrado}")
            leitor = PdfReader(arquivo_pdf_encontrado)
            for i, pagina in enumerate(leitor.pages):
                texto_livro += f"\n--- PAGINA {i+1} ---\n" + pagina.extract_text()
                if i >= 30:  # Limite de segurança para leitura rápida
                    break
        else:
            print("⚠️ Nenhum arquivo PDF foi encontrado na pasta. Respondendo com conhecimento geral.")

        # Estruturação do Prompt para a Inteligência Artificial
        comando_para_ia = f"""
Você é o CortexBot, um assistente virtual inteligente e versátil. Seu papel é ser um facilitador para o usuário em suas atividades diárias, sejam elas estudos, organização de serviços ou análises de dados.

Sempre que o usuário te pedir algo:
1. Analise o contexto do livro abaixo se for solicitado. (Mesmo se o usuário não citar o nome do arquivo, use o conteúdo abaixo se a pergunta for sobre o tema do livro).
2. Ajude com cálculos ou estruturação de documentos (como OS) se for necessário.
3. Mantenha um tom prestativo, objetivo e profissional.

IMPORTANTE: Responda apenas com texto puro. Não use nenhum tipo de formatação, asteriscos, negrito ou itálico.

CONTEÚDO DO LIVRO:
{texto_livro}

SOLICITAÇÃO DO USUÁRIO:
{pergunta_usuario}
        """

        # Chamada da API do Gemini
        resposta_ia = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=comando_para_ia,
        )

        bot.reply_to(mensagem, resposta_ia.text)

    except Exception as e:
        print(f"❌ Erro interno no processamento: {e}")
        bot.reply_to(mensagem, f"Ocorreu um erro no meu sistema: {e}")

# Inicialização estável para servidores em nuvem
bot.infinity_polling()
