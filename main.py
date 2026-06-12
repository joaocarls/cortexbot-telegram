import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from PyPDF2 import PdfReader
from google import genai

# =====================================================================
# CONFIGURAÇÕES E VARIÁVEIS DE ACESSO (Chaves Fixas Direto no Código)
# =====================================================================
TOKEN_TELEGRAM = "8853899021:AAETpmOM9ACw29kfR35XjU_K2cvdGPS3euM"
CHAVE_GEMINI = "AQ.Ab8RN6JBfMmv9qHSE7LT86oA5azvAC8nMdDRehnb7ePFvOdF9A"

# Inicialização dos clientes
bot = telebot.TeleBot(TOKEN_TELEGRAM)

# Ajuste fino: Se estiver no Render, usamos apenas os headers para chaves do tipo "AQ."
# Se estiver local, usamos a inicialização padrão.
if os.environ.get("RENDER"):
    client = genai.Client(http_options={'headers': {'x-goog-api-key': CHAVE_GEMINI}})
else:
    client = genai.Client(api_key=CHAVE_GEMINI, http_options={'headers': {'x-goog-api-key': CHAVE_GEMINI}})

# =====================================================================
# 1. SERVIDOR WEB FALSO (Evita Port Scan Timeout no Render)
# =====================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"CortexBot esta ativo e rodando!")

    def log_message(self, format, *args):
        return

def iniciar_servidor_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"[SERVIDOR] Servidor de ping iniciado na porta {port}")
    server.serve_forever()

threading.Thread(target=iniciar_servidor_web, daemon=True).start()

# =====================================================================
# 4. FUNÇÃO DE EXTRAÇÃO DO PDF LOCAL
# =====================================================================
def extrair_contexto_pdf():
    try:
        arquivos = os.listdir('.')
        pdf_encontrado = None
        for arquivo in arquivos:
            if arquivo.lower().endswith('.pdf'):
                pdf_encontrado = arquivo
                break

        if not pdf_encontrado:
            print("[AVISO] Nenhum arquivo PDF encontrado no diretorio raiz. Usando apenas conhecimento geral.")
            return ""

        print(f"[PDF] Lido arquivo encontrado: {pdf_encontrado}")
        reader = PdfReader(pdf_encontrado)
        texto_extraido = []
        
        limite_paginas = min(30, len(reader.pages))
        for i in range(limite_paginas):
            texto_pagina = reader.pages[i].extract_text()
            if texto_pagina:
                texto_extraido.append(texto_pagina)

        return "\n".join(texto_extraido)
    except Exception as e:
        print(f"[ERRO] Falha ao ler o PDF: {e}")
        return ""

# =====================================================================
# 5. GERENCIAMENTO DE MENSAGENS E INTEGRAÇÃO COM GEMINI
# =====================================================================
@bot.message_handler(commands=['start', 'help'])
def enviar_boas_vindas(message):
    boas_vindas = "Ola! Eu sou o CortexBot. Estou pronto para ajudar com suas tarefas diarias, calculos ou estruturacao de documentos. Como posso te ajudar hoje?"
    bot.reply_to(message, boas_vindas)

@bot.message_handler(func=lambda message: True)
def responder_usuario(message):
    bot.send_chat_action(message.chat.id, 'typing')
    contexto_pdf = extrair_contexto_pdf()
    
    instrucao_sistema = (
        "Voce eh o CortexBot, um assistente versatil que ajuda em tarefas diarias, "
        "calculos ou estruturacao de documentos (como Ordens de Servico). "
        "Priorize as informacoes do contexto fornecido sempre que o assunto for relacionado a ele. "
        "REGRA CRUCIAL: Responda APENAS com texto puro. Eh estritamente proibido o uso de qualquer "
        "tipo de formatacao como asteriscos (*), negrito, italico ou markdown."
    )
    
    prompt_completo = f"Contexto extraido do documento:\n{contexto_pdf}\n\nPergunta do usuario: {message.text}" if contexto_pdf else message.text

    try:
        # Mudança do identificador do modelo para o padrão estrito 'models/gemini-2.5-flash'
        response = client.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=prompt_completo,
            config={
                'system_instruction': instrucao_sistema
            }
        )
        
        texto_resposta = response.text
        texto_resposta = texto_resposta.replace('*', '')
        bot.reply_to(message, texto_resposta)
        
    except Exception as e:
        print(f"[ERRO API] Erro ao gerar resposta do Gemini: {e}")
        bot.reply_to(message, f"Erro interno na API da IA: {e}")

# =====================================================================
# INICIALIZAÇÃO DO BOT
# =====================================================================
if __name__ == "__main__":
    print("[BOT] CortexBot inicializado com sucesso. Aguardando mensagens...")
    bot.infinity_polling()
