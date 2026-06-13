import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from PyPDF2 import PdfReader
from google import genai

# =====================================================================
# CONFIGURAÇÕES E VARIÁVEIS DE ACESSO
# =====================================================================
TOKEN_TELEGRAM = "8853899021:AAETpmOM9ACw29kfR35XjU_K2cvdGPS3euM"
CHAVE_GEMINI = "AQ.Ab8RN6JBfMmv9qHSE7LT86oA5azvAC8nMdDRehnb7ePFvOdF9A"

# Inicialização segura do Telegram: Remove sessões antigas
bot = telebot.TeleBot(TOKEN_TELEGRAM)
try:
    print("[BOT] Limpando webhooks antigos do Telegram...")
    bot.delete_webhook()
    time.sleep(2)
except Exception as e:
    print(f"[AVISO] Falha ao resetar conexao inicial: {e}")

# Inicialização oficial da biblioteca nova para chaves AQ
client = genai.Client(api_key=CHAVE_GEMINI)

# =====================================================================
# 1. SERVIDOR WEB FALSO (Evita Port Scan Timeout no Render)
# =====================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"CortexBot com Gemini esta ativo e rodando!")

    def log_message(self, format, *args):
        return

def iniciar_servidor_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"[SERVIDOR] Servidor de ping iniciado na porta {port}")
    server.serve_forever()

threading.Thread(target=iniciar_servidor_web, daemon=True).start()

# =====================================================================
# 2. FUNÇÃO DE BUSCA DE CONTEXTO NO PDF
# =====================================================================
def obter_contexto_pdf(termo_busca):
    try:
        arquivos = os.listdir('.')
        pdfs_encontrados = [arq for arq in arquivos if arq.lower().endswith('.pdf')]

        if not pdfs_encontrados:
            return ""

        termo_busca = termo_busca.lower()
        paragrafos_encontrados = []

        for pdf_nome in pdfs_encontrados:
            reader = PdfReader(pdf_nome)
            limite_paginas = min(30, len(reader.pages))
            
            for num_pag in range(limite_paginas):
                texto_pagina = reader.pages[num_pag].extract_text()
                if texto_pagina and any(palavra in texto_pagina.lower() for palavra in termo_busca.split()):
                    
                    if "\n\n" in texto_pagina:
                        paragrafos = texto_pagina.split('\n\n')
                    else:
                        paragrafos = texto_pagina.split('\n')
                    
                    for paragrafo in paragrafos:
                        paragrafo_limpo = paragrafo.strip().replace('\n', ' ')
                        if len(paragrafo_limpo) > 20:
                            if any(p in paragrafo_limpo.lower() for p in termo_busca.split()):
                                paragrafos_encontrados.append(paragrafo_limpo)

        return "\n".join(paragrafos_encontrados[:4])
    except Exception as e:
        print(f"[ERRO PDF] Falha ao ler base de dados: {e}")
        return ""

# =====================================================================
# 3. GERENCIAMENTO DE MENSAGENS E INTEGRAÇÃO GEMINI
# =====================================================================
@bot.message_handler(commands=['start', 'help'])
def enviar_boas_vindas(message):
    boas_vindas = "Ola! Eu sou o CortexBot. Agora estou equipado com a inteligencia do Gemini e integrado aos seus PDFs locais. Como posso te ajudar hoje?"
    bot.reply_to(message, boas_vindas)

@bot.message_handler(func=lambda message: True)
def responder_usuario(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Busca os parágrafos relevantes nos arquivos PDF locais
    contexto_documento = obter_contexto_pdf(message.text)
    
    instrucao_sistema = (
        "Voce eh o CortexBot, um assistente versatil, focado em ajudar com tarefas diarias, "
        "calculos ou estruturacao de documentos (como Ordens de Servico). "
        "Se houver um contexto extraido de documentos abaixo, use-o prioritariamente para responder. "
        "REGRA CRUCIAL: Responda APENAS com texto puro. Eh estritamente proibido o uso de qualquer "
        "tipo de formatacao markdown, asteriscos (*), negrito ou italico."
    )
    
    if contexto_documento:
        prompt_final = f"Contexto dos documentos locais:\n{contexto_documento}\n\nPergunta do usuario: {message.text}"
    else:
        prompt_final = message.text

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_final,
            config={
                'system_instruction': instrucao_sistema
            }
        )
        
        texto_resposta = response.text
        texto_resposta = texto_resposta.replace('*', '').replace('_', '')
        bot.reply_to(message, texto_resposta)
        
    except Exception as e:
        print(f"[ERRO GEMINI] Falha na geracao de conteudo: {e}")
        bot.reply_to(message, f"Erro ao processar resposta com a IA: {e}")

# =====================================================================
# INICIALIZAÇÃO DO BOT
# =====================================================================
if __name__ == "__main__":
    print("[BOT] CortexBot híbrido (PDF + Gemini) inicializado com sucesso.")
    bot.infinity_polling(skip_pending=True)
