import telebot
from PyPDF2 import PdfReader
from google import genai
import os  # Biblioteca que permite ao Python mexer nas pastas

# Configuração do Bot do Telegram
TOKEN_TELEGRAM = "8853899021:AAETpmOM9ACw29kfR35XjU_K2cvdGPS3euM"
bot = telebot.TeleBot(TOKEN_TELEGRAM)

# Configuração da IA do Google
CHAVE_GEMINI = "AQ.Ab8RN6JBfMmv9qHSE7LT86oA5azvAC8nMdDRehnb7ePFvOdF9A"
client = genai.Client(api_key=CHAVE_GEMINI)

print("🧠 CortexBot OPERACIONAL e com leitura automática de PDFs ativa.")

# --- MENU PRINCIPAL ---
@bot.message_handler(commands=['start', 'ajuda'])
def enviar_boas_vindas(mensagem):
    menu = (
        "🧠 Olá! Sou o CortexBot, seu assistente pessoal inteligente.\n\n"
        "Estou aqui para simplificar suas tarefas, analisar seus documentos e apoiar você no que for preciso.\n\n"
        "Pode falar comigo normalmente e eu farei o meu melhor para ajudar!"
    )
    bot.reply_to(mensagem, menu)

# --- CAPTURA QUALQUER TEXTO ---
@bot.message_handler(func=lambda mensagem: True)
def processar_mensagem_ia(mensagem):
    try:
        pergunta_usuario = mensagem.text
        bot.reply_to(mensagem, "⚡ Processando...")

        # 1. FUNÇÃO INTELIGENTE: Procura e lê qualquer arquivo PDF na pasta
        texto_livro = ""
        arquivo_pdf_encontrado = None

        # O Python varre a pasta procurando um arquivo que termina com .pdf
        for arquivo in os.listdir('.'):
            if arquivo.endswith('.pdf'):
                arquivo_pdf_encontrado = arquivo
                break  # Encontrou o primeiro PDF, pode parar de procurar

        if arquivo_pdf_encontrado:
            leitor = PdfReader(arquivo_pdf_encontrado)
            for i, pagina in enumerate(leitor.pages):
                texto_livro += f"\n--- PAGINA {i+1} ---\n" + pagina.extract_text()
                if i >= 30:  # Limite para leitura rápida
                    break
        else:
            print("⚠️ Nenhum arquivo PDF foi encontrado na pasta.")

        # 2. Prompt com tom profissional e geral
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

        resposta_ia = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=comando_para_ia,
        )

        bot.reply_to(mensagem, resposta_ia.text)

    except Exception as e:
        bot.reply_to(mensagem, f"Ocorreu um erro no meu sistema: {e}")

bot.polling()