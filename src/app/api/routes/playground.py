from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

PLAYGROUND_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SDR Agent Playground</title>
    <style>
      :root {
        --bg-1: #f5f7ff;
        --bg-2: #edf3ff;
        --panel: #ffffff;
        --line: #d5deee;
        --text: #13213d;
        --muted: #5b6986;
        --accent: #0b6efd;
        --accent-soft: #f0f5ff;
        --ok: #1b8f4e;
        --bad: #bd1f3e;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: "Trebuchet MS", "Segoe UI", Arial, sans-serif;
        background: linear-gradient(140deg, var(--bg-1), var(--bg-2));
        color: var(--text);
      }
      main {
        max-width: 980px;
        margin: 0 auto;
        min-height: 100vh;
        padding: 28px 16px 40px;
      }
      .card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 14px;
        box-shadow: 0 12px 34px rgba(6, 30, 63, 0.08);
        overflow: hidden;
      }
      .hero {
        padding: 16px 20px;
        background: linear-gradient(140deg, #0e4a89, #1c71e7);
        color: white;
      }
      .hero h1 {
        margin: 0;
        font-size: 1.4rem;
      }
      .hero p {
        margin: 6px 0 0;
        opacity: 0.9;
      }
      .body {
        padding: 18px;
      }
      .toolbar {
        display: grid;
        gap: 12px;
        grid-template-columns: 1fr 120px;
      }
      .row {
        display: flex;
        gap: 8px;
        align-items: center;
      }
      label {
        font-weight: 600;
        color: var(--muted);
      }
      input[type="text"], textarea {
        width: 100%;
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 10px 12px;
        font-size: 0.98rem;
      }
      input[type="text"] {
        width: 100%;
      }
      textarea {
        resize: none;
        min-height: 94px;
      }
      button {
        border: none;
        background: var(--accent);
        color: white;
        border-radius: 10px;
        padding: 10px 16px;
        font-weight: 700;
        cursor: pointer;
      }
      button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .chat {
        margin-top: 18px;
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 12px;
        min-height: 300px;
        background: #fbfdff;
        overflow: auto;
      }
      .bubble {
        border-radius: 12px;
        padding: 10px 12px;
        margin: 10px 0;
        max-width: 85%;
        white-space: pre-wrap;
        line-height: 1.35;
        animation: fadein 220ms ease;
      }
      .user {
        margin-left: auto;
        background: var(--accent-soft);
        border: 1px solid #9fc0ff;
      }
      .assistant {
        margin-right: auto;
        background: #ffffff;
        border: 1px solid #dbe3f6;
      }
      .meta {
        color: var(--muted);
        font-size: 0.82rem;
        margin-top: 6px;
      }
      .ok { color: var(--ok); }
      .bad { color: var(--bad); }
      .help {
        margin-top: 10px;
        font-size: 0.86rem;
        color: var(--muted);
      }
      #status {
        margin-top: 8px;
        font-size: 0.92rem;
        color: var(--muted);
      }
      .loading {
        opacity: 0;
        animation: pulse 900ms ease-in-out infinite;
      }
      @keyframes pulse {
        0%, 100% { opacity: .25; }
        50% { opacity: 1; }
      }
      @keyframes fadein {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: none; }
      }
      @media (max-width: 700px) {
        .toolbar {
          grid-template-columns: 1fr;
        }
        .row {
          flex-wrap: wrap;
        }
      }
    </style>
  </head>
  <body>
    <main>
      <section class="card">
        <div class="hero">
          <h1>Playground SDR</h1>
          <p>Testa o agente da Sunne sem autenticação.</p>
        </div>
        <div class="body">
          <div class="toolbar">
            <div class="row">
              <label for="thread-id">Thread ID</label>
              <input id="thread-id" type="text" readonly />
            </div>
            <div class="row">
              <button id="new-thread">Nova thread</button>
            </div>
          </div>

          <div class="help">
            O chat chama <code>POST /chat</code> e grava estado por <strong>thread_id</strong>.
            Mude a thread para começar uma simulação nova.
          </div>

          <div class="row" style="margin-top: 14px">
            <textarea id="message" placeholder="Digite a mensagem do lead..."></textarea>
            <button id="send" style="width: 180px">Enviar</button>
          </div>

          <div id="status"></div>
          <div id="chat" class="chat" aria-live="polite"></div>
        </div>
      </section>
    </main>

    <script>
      const chatEl = document.getElementById("chat");
      const threadIdEl = document.getElementById("thread-id");
      const messageEl = document.getElementById("message");
      const sendButton = document.getElementById("send");
      const newThreadButton = document.getElementById("new-thread");
      const statusEl = document.getElementById("status");

      function randomThreadId() {
        const prefix = "playground-web";
        const randomPart = Math.random().toString(36).slice(2, 11);
        return `${prefix}-${Date.now()}-${randomPart}`;
      }

      function setThreadId(threadId) {
        threadIdEl.value = threadId;
        localStorage.setItem("playground_thread_id", threadId);
      }

      function initThreadId() {
        const stored = localStorage.getItem("playground_thread_id");
        setThreadId(stored || randomThreadId());
      }

      function addBubble(role, content, meta) {
        const wrap = document.createElement("div");
        wrap.className = `bubble ${role}`;
        wrap.textContent = content || "";
        chatEl.appendChild(wrap);
        if (meta && meta.trim().length) {
          const metaRow = document.createElement("div");
          metaRow.className = "meta";
          metaRow.textContent = meta;
          chatEl.appendChild(metaRow);
        }
        chatEl.scrollTop = chatEl.scrollHeight;
      }

      function setStatus(message, isError = false) {
        statusEl.textContent = message;
        statusEl.className = isError ? "bad" : "";
      }

      function clearInput() {
        messageEl.value = "";
        messageEl.focus();
      }

      async function sendMessage() {
        const message = messageEl.value.trim();
        if (!message) {
          setStatus("Digite uma mensagem antes de enviar.", true);
          return;
        }

        sendButton.disabled = true;
        setStatus("Aguardando resposta...");
        addBubble("user", message, `thread_id: ${threadIdEl.value}`);

        clearInput();
        const typing = document.createElement("div");
        typing.className = "bubble assistant loading";
        typing.textContent = "Agente digitando...";
        chatEl.appendChild(typing);
        chatEl.scrollTop = chatEl.scrollHeight;

        try {
          const response = await fetch("/chat", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              thread_id: threadIdEl.value,
              message: message,
            }),
          });

          const payload = await response.json();
          chatEl.removeChild(typing);

          if (!response.ok) {
            const detail = payload && payload.detail ? JSON.stringify(payload.detail) : "Erro interno";
            addBubble("assistant", "Falha no retorno da API.", `status: ${response.status} ${detail}`);
            setStatus("Falha na chamada.", true);
            return;
          }

          addBubble("assistant", payload.response_text || "", `status: ${payload.status} | intent: ${payload.intent || "n/a"}`);
          if (payload.response_parts && payload.response_parts.length) {
            payload.response_parts.forEach((part) => {
              if (part.type === "media" && part.media_id) {
                addBubble("assistant", `Mídia: ${part.media_id}`);
              }
              if (part.type === "audio" && part.text) {
                addBubble("assistant", `Áudio: ${part.text}`);
              }
            });
          }
          if (payload.intent_reason) {
            addBubble("assistant", "", `intent_reason: ${payload.intent_reason}`);
          }
          setStatus("Mensagem entregue.");
        } catch (error) {
          if (typing.parentElement) {
            chatEl.removeChild(typing);
          }
          addBubble("assistant", "Não foi possível conectar ao endpoint /chat.");
          setStatus(`Erro: ${error.message}`, true);
        } finally {
          sendButton.disabled = false;
        }
      }

      sendButton.addEventListener("click", sendMessage);
      newThreadButton.addEventListener("click", () => {
        setThreadId(randomThreadId());
        chatEl.innerHTML = "";
        setStatus(`Nova thread: ${threadIdEl.value}`);
      });
      messageEl.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          sendMessage();
        }
      });

      initThreadId();
      setStatus("Pronto para testar.");
      messageEl.focus();
    </script>
  </body>
</html>
"""

playground_router = APIRouter()


@playground_router.get("/playground", response_class=HTMLResponse, include_in_schema=False)
def playground() -> str:
    return PLAYGROUND_HTML
