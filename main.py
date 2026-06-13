import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from PyPDF2 import PdfReader
import google.generativeai as genai

# =====================================================================
# CONFIGURAÇÕES E VARIÁVEIS DE ACESSO
# =====================================================================
TOKEN_TELEGRAM = "8853899021:AAETpmOM9ACw29kfR35XjU_K2cvdGPS3euM"
CHAVE_GEMINI = "AQ.Ab8RN6JBfMmv9qHSE7LT86oA5azvAC8nMdDRehnb7ePFvOdF9A"

# Inicialização do Telegram com reset de conexões antigas
bot = telebot.TeleBot(TOKEN_TELEGRAM)
try:
    print("[BOT] Limpando webhooks antigos do Telegram...")
    bot.delete_webhook()
    time.sleep(2)
except Exception as e:
    print(f"[AVISO] Falha ao resetar conexao inicial: {e}")

# Inicialização estável do Gemini
genai.configure(api_key=CHAVE_GEMINI)

# =====================================================================
# 1. SERVIDOR WEB FALSO (Evita Port Scan Timeout no Render)
# =====================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"CortexBot com IA esta ativo e rodando!")

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
                            # Se o parágrafo contiver conexões com a pergunta, guarda como contexto
                            if any(p in paragrafo_limpo.lower() for p in termo_busca.split()):
                                paragrafos_encontrados.append(paragrafo_limpo)

        # Retorna os 4 parágrafos mais importantes colados para servirem de histórico/base
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
    
    # Busca parágrafos relacionados no documento para alimentar a IA
    contexto_documento = obter_contexto_pdf(message.text)
    
    # Prompt do sistema para moldar o comportamento e travar a formatação
    instrucao_sistema = (
        "Voce eh o CortexBot, um assistente versatil, focado em ajudar com tarefas diarias, "
        "calculos ou estruturacao de documentos (como Ordens de Servico). "
        "Se houver um contexto extraido de documentos abaixo, use-o prioritariamente para responder. "
        "REGRA CRUCIAL: Responda APENAS com texto puro. Eh estritamente proibido o uso de qualquer "
        "tipo de formatacao markdown, asteriscos (*), negrito ou italico."
    )
    
    # Montagem do prompt final estruturado
    if contexto_documento:
        prompt_final = f"{instrucao_sistema}\n\nContexto dos documentos locais:\n{contexto_documento}\n\nPergunta do usuario: {message.text}"
    else:
        prompt_final = f"{instrucao_sistema}\n\nPergunta do usuario: {message.text}"

    try:
        # Chamada utilizando o modelo estável gemini-2.5-flash
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt_final)
        
        texto_resposta = response.text
        
        # Limpeza redundante de segurança contra caracteres de formatação
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
