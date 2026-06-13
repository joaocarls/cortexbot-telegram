import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from PyPDF2 import PdfReader

# =====================================================================
# CONFIGURAÇÕES E VARIÁVEIS DE ACESSO
# =====================================================================
TOKEN_TELEGRAM = "8853899021:AAETpmOM9ACw29kfR35XjU_K2cvdGPS3euM"

# Inicialização segura do Telegram: Remove sessões antigas
bot = telebot.TeleBot(TOKEN_TELEGRAM)

try:
    print("[BOT] Removendo webhooks ou conexoes presas no Telegram...")
    bot.delete_webhook()
    time.sleep(2)
except Exception as e:
    print(f"[AVISO] Falha ao resetar conexao inicial: {e}")

# =====================================================================
# 1. SERVIDOR WEB FALSO (Evita Port Scan Timeout no Render)
# =====================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"CortexBot esta ativo e rodando sem IA!")

    def log_message(self, format, *args):
        return

def iniciar_servidor_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"[SERVIDOR] Servidor de ping iniciado na porta {port}")
    server.serve_forever()

threading.Thread(target=iniciar_servidor_web, daemon=True).start()

# =====================================================================
# 2. FUNÇÃO DE BUSCA INTELIGENTE DE PARÁGRAFOS NO PDF
# =====================================================================
def buscar_paragrafo_no_pdf(termo_busca):
    try:
        arquivos = os.listdir('.')
        pdfs_encontrados = [arq for arq in arquivos if arq.lower().endswith('.pdf')]

        if not pdfs_encontrados:
            return "Aviso: Nenhum arquivo PDF de base de conhecimento foi encontrado na pasta do servidor."

        termo_busca = termo_busca.lower()
        paragrafos_encontrados = []

        # Varre todos os arquivos PDF da pasta raiz
        for pdf_nome in pdfs_encontrados:
            print(f"[PDF] Buscando por '{termo_busca}' no arquivo: {pdf_nome}")
            reader = PdfReader(pdf_nome)
            
            # Varre as páginas do documento (limite de 30 páginas por segurança)
            limite_paginas = min(30, len(reader.pages))
            for num_pag in range(limite_paginas):
                texto_pagina = reader.pages[num_pag].extract_text()
                
                if texto_pagina and termo_busca in texto_pagina.lower():
                    # Divide o texto da página em parágrafos reais usando quebras de linha duplas ou simples agrupadas
                    # Tentamos quebra dupla primeiro (comum em blocos de texto), senão dividimos por quebra simples
                    if "\n\n" in texto_pagina:
                        paragrafos = texto_pagina.split('\n\n')
                    else:
                        paragrafos = texto_pagina.split('\n')
                    
                    for paragrafo in paragrafos:
                        # Limpa espaços extras e remove quebras internas para o bloco de texto ficar contínuo
                        paragrafo_limpo = paragrafo.strip().replace('\n', ' ')
                        
                        if termo_busca in paragrafo_limpo.lower() and len(paragrafo_limpo) > 10:
                            trecho_formatado = f"[{pdf_nome} - Pag. {num_pag + 1}]:\n{paragrafo_limpo}\n"
                            if trecho_formatado not in paragrafos_encontrados:
                                paragrafos_encontrados.append(trecho_formatado)

        if paragrafos_encontrados:
            # Retorna até os 5 parágrafos mais relevantes para não estourar o limite de caracteres do Telegram
            resultado_final = "Resultados encontrados na base de conhecimento:\n\n" + "\n---------------------\n".join(paragrafos_encontrados[:5])
            return resultado_final
        else:
            return "Nao encontrei nenhum paragrafo correspondente a esse termo nos documentos anexados."

    except Exception as e:
        return f"Erro ao ler os arquivos de base de conhecimento: {e}"

# =====================================================================
# 3. GERENCIAMENTO DE MENSAGENS DO TELEGRAM
# =====================================================================
@bot.message_handler(commands=['start', 'help'])
def enviar_boas_vindas(message):
    boas_vindas = "Ola! Eu sou o CortexBot. Minha base de dados atual eh alimentada pelos PDFs locais. Digite um termo ou palavra-chave para eu buscar os paragrafos correspondentes nos documentos."
    bot.reply_to(message, boas_vindas)

@bot.message_handler(func=lambda message: True)
def responder_usuario(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Realiza a busca inteligente por blocos de texto
    resposta_busca = buscar_paragrafo_no_pdf(message.text)
    
    # Mantém a regra estrita de texto puro sem markdown
    resposta_busca = resposta_busca.replace('*', '')
    
    bot.reply_to(message, resposta_busca)

# =====================================================================
# INICIALIZAÇÃO DO BOT
# =====================================================================
if __name__ == "__main__":
    print("[BOT] CortexBot (Modo Parágrafo Local) inicializado com sucesso. Aguardando mensagens...")
    bot.infinity_polling(skip_pending=True)
