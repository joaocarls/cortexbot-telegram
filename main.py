import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from google import genai

# =====================================================================
# CONFIGURAÇÕES E VARIÁVEIS DE ACESSO (Segurança Avançada)
# =====================================================================
TOKEN_TELEGRAM = os.environ.get("TOKEN_TELEGRAM")
CHAVE_GEMINI = os.environ.get("CHAVE_GEMINI")

# Inicialização segura do Telegram: Remove sessões antigas
bot = telebot.TeleBot(TOKEN_TELEGRAM)
try:
    print("[BOT] Limpando webhooks antigos do Telegram...")
    bot.delete_webhook()
    time.sleep(2)
except Exception as e:
    print(f"[AVISO] Falha ao resetar conexao inicial: {e}")

# Inicialização oficial da biblioteca nova utilizando a chave protegida
client = genai.Client(api_key=CHAVE_GEMINI)

# =====================================================================
# 1. SERVIDOR WEB FALSO (Evita Port Scan Timeout no Render)
# =====================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"CortexBot Gemini Livre esta ativo e rodando!")

    def log_message(self, format, *args):
        return

def iniciar_servidor_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"[SERVIDOR] Servidor de ping iniciado na porta {port}")
    server.serve_forever()

threading.Thread(target=iniciar_servidor_web, daemon=True).start()

# =====================================================================
# 2. GERENCIAMENTO DE MENSAGENS E INTEGRAÇÃO GEMINI LIVRE
# =====================================================================
@bot.message_handler(commands=['start', 'help'])
def enviar_boas_vindas(message):
    boas_vindas = "Ola! Eu sou o CortexBot. Agora estou equipado com a inteligencia livre do Gemini. Pode me perguntar qualquer coisa!"
    bot.reply_to(message, boas_vindas)

@bot.message_handler(func=lambda message: True)
def responder_usuario(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    instrucao_sistema = (
        "Voce eh o CortexBot, um assistente versatil, focado em ajudar com tarefas diarias, "
        "calculos ou estruturacao de documentos (como Ordens de Servico). "
        "REGRA CRUCIAL: Responda APENAS com texto puro. Eh estritamente proibido o uso de qualquer "
        "tipo de formatacao markdown, asteriscos (*), negrito ou italico."
    )

    try:
        # Chamada direta enviando apenas o texto do usuário para o modelo
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=message.text,
            config={
                'system_instruction': instrucao_sistema
            }
        )
        
        # Garante a extração correta do texto
        if hasattr(response, 'text') and response.text:
            texto_resposta = response.text
        elif response.candidates and response.candidates[0].content.parts:
            texto_resposta = response.candidates[0].content.parts[0].text
        else:
            texto_resposta = "Nao consegui gerar um texto de resposta valido."
            
        # Filtro de segurança para limpar qualquer markdown teimoso
        texto_resposta = texto_resposta.replace('*', '').replace('_', '')
        bot.reply_to(message, texto_resposta)
        
    except Exception as e:
        print(f"[ERRO GEMINI] Falha na geracao de conteudo: {e}")
        bot.reply_to(message, f"Erro ao processar resposta com a IA: {e}")

# =====================================================================
# INICIALIZAÇÃO DO BOT
# =====================================================================
if __name__ == "__main__":
    print("[BOT] CortexBot Gemini Livre inicializado com sucesso.")
    bot.infinity_polling(skip_pending=True)
