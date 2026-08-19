from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

PLAYGROUND_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Playground SDR Sunne</title>
    <style>
      :root {
        --iphone-chat-header: #1f7248;
        --iphone-chat-background: #efeae2;
        --iphone-chat-bubble-user: #d9fdd3;
        --iphone-chat-bubble-assistant: #ffffff;
        --iphone-chat-input-background: #f0f2f5;
        --iphone-chat-action: #00a884;
        --iphone-chat-read: #53bdeb;
        --iphone-chat-text: #111b21;
        --iphone-chat-muted: #667781;
        --iphone-chat-frame-light: #f47b3b;
        --iphone-chat-frame-main: #e8501e;
        --iphone-chat-frame-dark: #9e3009;
        --phone-width: 440px;
        --phone-height: 956px;
        --phone-scale: calc(var(--phone-height-current) / var(--phone-height));

        --ok: #10b981;
        --warn: #b45309;
        --danger: #b91c1c;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-height: 100vh;
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: #fff;
        background:
          radial-gradient(circle at 30% 4%, rgb(244 123 59 / 9%), transparent 28%),
          linear-gradient(160deg, #0f172a, #1f2937 60%);
      }

      .page {
        min-height: 100vh;
        padding: 24px 14px 36px;
        display: grid;
        gap: 16px;
        place-items: center;
      }

      .controls {
        width: min(100%, 980px);
        display: grid;
        gap: 10px;
        grid-template-columns: minmax(0, 1fr) auto;
        color: #f8fafc;
        align-items: center;
      }

      .title {
        margin: 0;
        font-size: 1rem;
        font-weight: 700;
        letter-spacing: -0.01em;
      }

      .thread-card {
        display: grid;
        gap: 8px;
        justify-items: end;
      }

      .thread-row {
        display: flex;
        gap: 8px;
        align-items: center;
      }

      .thread-label {
        font-size: 0.86rem;
        color: #d9e2ef;
      }

      .thread-id {
        width: min(360px, 56vw);
        max-width: 420px;
        min-width: 180px;
        background: #0f1b2a;
        border: 1px solid rgb(255 255 255 / 20%);
        border-radius: 999px;
        padding: 8px 12px;
        color: #fff;
      }

      .btn {
        border: 1px solid rgb(255 255 255 / 24%);
        color: #f8fafc;
        background: rgb(15 23 42 / 76%);
        border-radius: 999px;
        padding: 8px 11px;
        font-size: 0.86rem;
        font-weight: 700;
        cursor: pointer;
      }

      .btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      .status-line {
        font-size: 0.82rem;
        color: #cbd5e1;
        justify-self: end;
      }

      .status-line.warn {
        color: #facc15;
      }

      .status-line.ok {
        color: #6ee7b7;
      }

      .status-line.danger {
        color: #fda4af;
      }

      .iphone-chat-frame {
        position: relative;
        width: min(100%, calc(var(--phone-width) * var(--phone-scale)));
        height: calc(var(--phone-height) * var(--phone-scale));
      }

      .iphone-chat-device {
        position: absolute;
        inset: 0 auto auto 0;
        width: var(--phone-width);
        height: var(--phone-height);
        transform: scale(var(--phone-scale));
        transform-origin: top left;
      }

      .iphone-chat-glow,
      .iphone-chat-edge {
        pointer-events: none;
        position: absolute;
      }

      .iphone-chat-glow--accent {
        inset: -16px;
        border-radius: 68px;
        background: linear-gradient(
          to bottom,
          color-mix(in srgb, var(--iphone-chat-frame-main) 8%, transparent),
          transparent
        );
        filter: blur(24px);
      }

      .iphone-chat-glow--shadow {
        inset: -8px;
        border-radius: 64px;
        background: linear-gradient(to bottom, rgb(0 0 0 / 3%), rgb(0 0 0 / 8%));
        filter: blur(20px);
      }

      .iphone-chat-shell {
        position: relative;
        width: 100%;
        height: 100%;
        box-sizing: border-box;
        padding: 2.5px;
        border-radius: 59px;
        background: linear-gradient(
          180deg,
          var(--iphone-chat-frame-light),
          var(--iphone-chat-frame-main) 32%,
          var(--iphone-chat-frame-dark)
        );
        box-shadow:
          0 0 0 .5px rgb(255 255 255 / 12%),
          0 25px 50px -12px rgb(0 0 0 / 35%),
          0 12px 25px -5px rgb(0 0 0 / 20%),
          inset 0 1px 0 rgb(255 255 255 / 20%),
          inset 0 -1px 0 rgb(0 0 0 / 15%);
      }

      .iphone-chat-sheen {
        position: absolute;
        inset: 0;
        border-radius: inherit;
        background: linear-gradient(to bottom right, rgb(255 255 255 / 15%), transparent 40%);
        pointer-events: none;
      }

      .iphone-chat-bezel {
        width: 100%;
        height: 100%;
        box-sizing: border-box;
        padding: 7px;
        border-radius: 56px;
        background: #080808;
      }

      .iphone-chat-side-button {
        position: absolute;
        z-index: -1;
        width: 3px;
        background: linear-gradient(
          to right,
          var(--iphone-chat-frame-light),
          var(--iphone-chat-frame-main)
        );
      }

      .iphone-chat-side-button--action {
        top: 169px;
        left: -2.5px;
        height: 31px;
        border-radius: 2px 0 0 2px;
      }

      .iphone-chat-side-button--volume-up {
        top: 224px;
        left: -2.5px;
        height: 57px;
        border-radius: 2px 0 0 2px;
      }

      .iphone-chat-side-button--volume-down {
        top: 293px;
        left: -2.5px;
        height: 57px;
        border-radius: 2px 0 0 2px;
      }

      .iphone-chat-side-button--power {
        top: 246px;
        right: -2.5px;
        height: 74px;
        border-radius: 0 2px 2px 0;
        background: linear-gradient(
          to left,
          var(--iphone-chat-frame-light),
          var(--iphone-chat-frame-main)
        );
      }

      .iphone-chat-screen {
        position: relative;
        display: flex;
        width: 100%;
        height: 100%;
        overflow: hidden;
        flex-direction: column;
        border-radius: 49px;
        background: var(--iphone-chat-background);
      }

      .iphone-chat-dynamic-island {
        position: absolute;
        z-index: 30;
        top: 12px;
        left: 50%;
        display: flex;
        width: 126px;
        height: 37px;
        box-sizing: border-box;
        align-items: center;
        padding-inline: 17px;
        transform: translateX(-50%);
        border-radius: 999px;
        background: #000;
        box-shadow: 0 0 0 .5px rgb(255 255 255 / 8%);
      }

      .iphone-chat-camera-lens {
        position: relative;
        width: 11px;
        height: 11px;
        border: 1px solid #222230;
        border-radius: 50%;
        background: #08080f;
        box-shadow: inset 2px 2px 0 rgb(58 58 94 / 30%);
      }

      .iphone-chat-status-bar {
        position: relative;
        z-index: 20;
        display: flex;
        height: 62px;
        box-sizing: border-box;
        flex: none;
        align-items: center;
        justify-content: space-between;
        padding: 14px 30px 0;
        color: #fff;
        background: var(--iphone-chat-header);
      }

      .iphone-chat-status-time {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
        font-size: 16px;
        font-weight: 600;
        letter-spacing: -.02em;
      }

      .iphone-chat-status-icons {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
      }

      .dot {
        width: 4px;
        height: 4px;
        border-radius: 999px;
        background: #22d3ee;
        animation: signal 1.2s infinite;
      }

      .dot:nth-child(2) { animation-delay: .2s; }
      .dot:nth-child(3) { animation-delay: .4s; }

      .iphone-chat-home-area {
        display: flex;
        flex: none;
        justify-content: center;
        padding-block: 9px;
        background: var(--iphone-chat-input-background);
      }

      .iphone-chat-home-indicator {
        width: 146px;
        height: 5px;
        border-radius: 999px;
        background: rgb(0 0 0 / 20%);
      }

      .iphone-chat-edge--top {
        top: 0;
        right: 15%;
        left: 15%;
        height: 1.5px;
        border-radius: 999px;
        background: linear-gradient(to right, transparent, rgb(255 255 255 / 25%), transparent);
      }

      .iphone-chat-edge--left,
      .iphone-chat-edge--right {
        top: 15%;
        bottom: 15%;
        width: 1px;
        background: linear-gradient(to bottom, transparent, rgb(255 255 255 / 10%), transparent);
      }

      .iphone-chat-edge--left { left: 0; }
      .iphone-chat-edge--right { right: 0; }

      .iphone-chat-edge {
        pointer-events: none;
        position: absolute;
      }

      .iphone-chat-header {
        display: flex;
        min-height: 56px;
        box-sizing: border-box;
        flex: none;
        align-items: center;
        gap: 5px;
        padding: 4px 8px 8px;
        color: #fff;
        border-bottom: 1px solid rgb(0 0 0 / 5%);
        background: var(--iphone-chat-header);
      }

      .iphone-chat-header-action,
      .iphone-chat-composer-icon,
      .iphone-chat-primary-action {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border: 0;
        background: transparent;
        font: inherit;
        color: inherit;
      }

      .iphone-chat-header-action {
        width: 44px;
        height: 44px;
        flex: none;
        border-radius: 50%;
      }

      .icon {
        width: 22px;
        height: 22px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        line-height: 1;
      }

      .iphone-chat-avatar {
        display: flex;
        width: 38px;
        height: 38px;
        flex: none;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        border-radius: 50%;
        color: #fff;
        background: #6bb89c;
        font-size: 17px;
        font-weight: 600;
      }

      .iphone-chat-contact {
        min-width: 0;
        flex: 1;
        margin-left: 4px;
      }

      .iphone-chat-contact strong,
      .iphone-chat-contact span {
        display: block;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .iphone-chat-contact strong {
        font-size: 16px;
        font-weight: 500;
        line-height: 1.25;
      }

      .iphone-chat-contact span {
        color: rgb(255 255 255 / 72%);
        font-size: 12px;
        line-height: 1.25;
      }

      .header-tools {
        display: flex;
        flex: none;
        gap: 0;
      }

      .iphone-chat-message-list {
        display: flex;
        min-height: 0;
        flex: 1;
        flex-direction: column;
        overflow-y: auto;
        padding: 8px 13px;
        background-color: var(--iphone-chat-background);
        background: radial-gradient(
          circle at 10% 10%,
          rgb(255 255 255 / 20%),
          transparent 32%
        );
        scrollbar-color: rgb(0 0 0 / 20%) transparent;
        scrollbar-width: thin;
      }

      .iphone-chat-message-list::-webkit-scrollbar {
        width: 6px;
      }

      .iphone-chat-message-list::-webkit-scrollbar-track {
        background: transparent;
      }

      .iphone-chat-message-list::-webkit-scrollbar-thumb {
        border-radius: 3px;
        background: rgb(0 0 0 / 20%);
      }

      .date-separator {
        display: flex;
        justify-content: center;
        margin: 8px 0 10px;
      }

      .date-separator span {
        padding: 5px 12px;
        border-radius: 7px;
        color: var(--iphone-chat-muted);
        background: rgb(255 255 255 / 82%);
        box-shadow: 0 1px 1px rgb(0 0 0 / 10%);
        font-size: 12px;
      }

      .message-row {
        display: flex;
        margin-top: 8px;
        animation: message-in .25s ease-out;
      }

      .message-row--user {
        justify-content: flex-end;
      }

      .message-row--assistant {
        justify-content: flex-start;
      }

      .message-row--grouped {
        margin-top: 2px;
      }

      .message-bubble {
        position: relative;
        min-width: 72px;
        max-width: 82%;
        box-sizing: border-box;
        padding: 7px 10px 19px;
        border-radius: 8px;
        box-shadow: 0 1px .5px rgb(0 0 0 / 13%);
      }

      .message-bubble--user {
        border-top-right-radius: 1px;
        background: var(--iphone-chat-bubble-user);
      }

      .message-bubble--assistant {
        border-top-left-radius: 1px;
        background: var(--iphone-chat-bubble-assistant);
      }

      .message-bubble--user:not(.message-bubble--without-tail)::before,
      .message-bubble--assistant:not(.message-bubble--without-tail)::before,
      .typing-bubble::before {
        position: absolute;
        top: 0;
        width: 7px;
        height: 13px;
        content: "";
      }

      .message-bubble--user:not(.message-bubble--without-tail)::before {
        right: -7px;
        clip-path: polygon(0 0, 100% 0, 0 100%);
        background: var(--iphone-chat-bubble-user);
      }

      .message-bubble--assistant:not(.message-bubble--without-tail)::before,
      .typing-bubble::before {
        left: -7px;
        clip-path: polygon(100% 0, 0 0, 100% 100%);
        background: var(--iphone-chat-bubble-assistant);
      }

      .message-bubble--without-tail {
        border-top-right-radius: 8px;
        border-top-left-radius: 8px;
      }

      .message-text {
        margin: 0;
        color: var(--iphone-chat-text);
        font-size: 14.4px;
        line-height: 19px;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
      }

      .message-meta {
        position: absolute;
        right: 7px;
        bottom: 4px;
        display: flex;
        align-items: center;
        gap: 3px;
        color: var(--iphone-chat-muted);
        font-size: 11px;
        line-height: 1;
      }

      .read-receipt {
        color: var(--iphone-chat-read);
      }

      .typing-bubble {
        position: relative;
        display: flex;
        align-items: center;
        gap: 5px;
        padding: 11px 13px;
        border-radius: 1px 8px 8px;
        background: var(--iphone-chat-bubble-assistant);
        box-shadow: 0 1px .5px rgb(0 0 0 / 13%);
      }

      .typing-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #8696a0;
        animation: typing 1.4s infinite;
      }

      .typing-dot:nth-child(2) { animation-delay: .2s; }
      .typing-dot:nth-child(3) { animation-delay: .4s; }

      .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        clip-path: inset(50%);
        white-space: nowrap;
      }

      .iphone-chat-composer {
        display: flex;
        box-sizing: border-box;
        flex: none;
        align-items: flex-end;
        gap: 6px;
        padding: 6px;
        background: var(--iphone-chat-input-background);
      }

      .iphone-chat-composer-field {
        display: flex;
        min-width: 0;
        min-height: 46px;
        box-sizing: border-box;
        flex: 1;
        align-items: flex-end;
        gap: 2px;
        padding: 2px 5px;
        border-radius: 23px;
        background: #fff;
      }

      .iphone-chat-composer-icon {
        width: 40px;
        height: 40px;
        flex: none;
        border-radius: 50%;
        color: #8696a0;
      }

      .composer-textarea {
        min-width: 0;
        min-height: 24px;
        max-height: 100px;
        flex: 1;
        resize: none;
        overflow-y: auto;
        box-sizing: border-box;
        margin: 0;
        padding: 10px 2px;
        color: var(--iphone-chat-text);
        border: 0;
        outline: 0;
        background: transparent;
        font: inherit;
        font-size: 15px;
        line-height: 20px;
      }

      .composer-textarea::placeholder { color: #8696a0; }

      .composer-actions {
        display: flex;
        flex: none;
        align-items: flex-end;
      }

      .primary-action {
        width: 46px;
        height: 46px;
        flex: none;
        border-radius: 50%;
        color: #fff;
        background: var(--iphone-chat-action);
        border: 0;
        transition: background-color .15s ease, opacity .15s ease;
      }

      .primary-action:not(:disabled):active { background: #008f72; }
      .primary-action:disabled { cursor: default; opacity: .72; }

      @keyframes message-in {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
      }

      @keyframes typing {
        0%, 60%, 100% { opacity: .3; transform: translateY(0); }
        30% { opacity: 1; transform: translateY(-4px); }
      }

      @keyframes signal {
        0%, 80%, 100% { opacity: .3; transform: translateY(0); }
        40% { opacity: .9; transform: translateY(-1px); }
      }

      @media (max-width: 620px) {
        .controls {
          grid-template-columns: 1fr;
          justify-items: stretch;
        }

        .thread-card {
          justify-items: start;
        }

        .status-line {
          justify-self: start;
        }
      }
    </style>
  </head>
  <body>
    <main class="page">
      <section class="controls">
      <h1 class="title">
        Playground SDR Sunne • iPhone 17 Pro Max Chat
      </h1>

        <div class="thread-card">
          <div class="thread-row">
            <span class="thread-label">Thread:</span>
            <input id="thread-id" class="thread-id" type="text" readonly />
            <button id="copy-thread" class="btn" type="button">Copiar</button>
            <button id="new-thread" class="btn" type="button">Nova thread</button>
          </div>
          <div class="thread-row">
            <span class="status-line" id="status">Pronto para testar.</span>
          </div>
        </div>
      </section>

      <section
        id="phone"
        class="iphone-chat-frame"
        aria-label="Simulação de chat no formato iPhone"
      >
        <div class="iphone-chat-device">
          <div class="iphone-chat-glow iphone-chat-glow--accent" aria-hidden="true"></div>
          <div class="iphone-chat-glow iphone-chat-glow--shadow" aria-hidden="true"></div>

          <div class="iphone-chat-shell">
            <div class="iphone-chat-sheen" aria-hidden="true"></div>
            <div class="iphone-chat-bezel">
              <div
                class="iphone-chat-side-button iphone-chat-side-button--action"
                aria-hidden="true"
              ></div>
              <div
                class="iphone-chat-side-button iphone-chat-side-button--volume-up"
                aria-hidden="true"
              ></div>
              <div
                class="iphone-chat-side-button iphone-chat-side-button--volume-down"
                aria-hidden="true"
              ></div>
              <div
                class="iphone-chat-side-button iphone-chat-side-button--power"
                aria-hidden="true"
              ></div>

              <div class="iphone-chat-screen">
                <div class="iphone-chat-dynamic-island" aria-hidden="true">
                  <div class="iphone-chat-camera-lens"></div>
                </div>

                <header class="iphone-chat-status-bar" aria-label="status">
                  <span class="iphone-chat-status-time" id="status-time">9:41</span>
                  <span class="iphone-chat-status-icons" aria-hidden="true">
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span>LTE</span>
                    <span>🔋</span>
                  </span>
                </header>

                <header class="iphone-chat-header">
                  <button type="button" class="iphone-chat-header-action" aria-label="Voltar">
                    <span class="icon" aria-hidden="true">‹</span>
                  </button>

                  <div class="iphone-chat-avatar" aria-hidden="true">S</div>

                  <div class="iphone-chat-contact">
                    <strong>SDR Sunne</strong>
                    <span>Consultor online</span>
                  </div>

                  <nav class="header-tools" aria-label="Ações da conversa">
                    <button
                      type="button"
                      class="iphone-chat-header-action"
                      aria-label="Chamada de vídeo"
                      disabled
                    >▶</button>
                    <button
                      type="button"
                      class="iphone-chat-header-action"
                      aria-label="Chamada de voz"
                      disabled
                    >☎</button>
                    <button
                      type="button"
                      class="iphone-chat-header-action"
                      aria-label="Menu"
                      disabled
                    >⋮</button>
                  </nav>
                </header>

                <div
                  id="chat"
                  class="iphone-chat-message-list"
                  role="log"
                  aria-live="polite"
                  aria-relevant="additions text"
                >
                  <div class="date-separator">
                    <span>Hoje</span>
                  </div>
                </div>

                <div class="iphone-chat-composer">
                  <div class="iphone-chat-composer-field">
                    <button
                      type="button"
                      class="iphone-chat-composer-icon"
                      id="emoji-btn"
                      aria-label="Escolher emoji"
                    >
                      😊
                    </button>

                    <textarea
                      id="message"
                      class="composer-textarea"
                      rows="1"
                      placeholder="Mensagem do lead"
                      aria-label="Mensagem do lead"
                    ></textarea>

                    <div class="composer-actions">
                      <button
                        type="button"
                        class="iphone-chat-composer-icon"
                        id="attach-btn"
                        aria-label="Anexar"
                      >
                        📎
                      </button>
                    </div>
                  </div>

                  <button
                    type="button"
                    class="primary-action"
                    id="send"
                    aria-label="Enviar mensagem"
                    title="Enviar"
                  >
                    ➤
                  </button>
                </div>

                <div class="iphone-chat-home-area" aria-hidden="true">
                  <div class="iphone-chat-home-indicator"></div>
                </div>
              </div>
            </div>
          </div>

          <div class="iphone-chat-edge iphone-chat-edge--top" aria-hidden="true"></div>
          <div class="iphone-chat-edge iphone-chat-edge--left" aria-hidden="true"></div>
          <div class="iphone-chat-edge iphone-chat-edge--right" aria-hidden="true"></div>
        </div>
      </section>
    </main>

    <script>
      const phone = document.getElementById("phone");
      const chatEl = document.getElementById("chat");
      const messageEl = document.getElementById("message");
      const sendButton = document.getElementById("send");
      const newThreadButton = document.getElementById("new-thread");
      const copyThreadButton = document.getElementById("copy-thread");
      const statusEl = document.getElementById("status");
      const threadIdEl = document.getElementById("thread-id");
      const statusTimeEl = document.getElementById("status-time");

      

      const viewportReserve = 150;
      const minScale = 0.62;

      function setScale() {
        const maxHeight = window.innerHeight - viewportReserve;
        const scaleByHeight = Math.min(1, maxHeight / 956);
        const maxWidth = Math.min(window.innerWidth - 24, 440);
        const scaleByWidth = Math.max(minScale, maxWidth / 440);
        const scale = Math.min(1, scaleByHeight, scaleByWidth);
        phone.style.setProperty("--phone-scale", String(scale));
        phone.style.setProperty("--phone-height-current", `${956 * scale}px`);
      }

      function randomThreadId() {
        const prefix = "sunne-play";
        const randomPart = Math.random().toString(36).slice(2, 10);
        return `${prefix}-${Date.now()}-${randomPart}`;
      }

      function initThread() {
        const stored = localStorage.getItem("playground_thread_id");
        threadIdEl.value = stored || randomThreadId();
        localStorage.setItem("playground_thread_id", threadIdEl.value);
      }

      function setStatus(message, kind = "") {
        statusEl.textContent = message;
        statusEl.className = `status-line ${kind}`;
      }

      function setStatusTime() {
        const now = new Date();
        statusTimeEl.textContent = now.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        });
      }

      function isDarkMode() {
        const hours = new Date().getHours();
        return hours >= 19 || hours <= 6;
      }

      let lastRole = null;

      function addMessage(role, content, meta = "") {
        const row = document.createElement("div");
        row.className = `message-row message-row--${role}`;

        if (lastRole === role) {
          row.classList.add("message-row--grouped");
        }

        const isUser = role === "user";
        const bubble = document.createElement("article");
        bubble.className = `message-bubble message-bubble--${role}`;

        if (lastRole === role) {
          bubble.classList.add("message-bubble--without-tail");
        }

        const text = document.createElement("p");
        text.className = "message-text";
        text.textContent = content;
        bubble.appendChild(text);

        const metaRow = document.createElement("span");
        metaRow.className = "message-meta";

        const metaTime = new Date().toLocaleTimeString("pt-BR", {
          hour: "2-digit",
          minute: "2-digit",
        });

        const time = document.createElement("time");
        time.setAttribute("datetime", new Date().toISOString());
        time.textContent = metaTime;
        metaRow.appendChild(time);

        if (isUser) {
          const receipt = document.createElement("span");
          receipt.className = "read-receipt";
          receipt.textContent = "✓✓";
          receipt.setAttribute("aria-label", "Mensagem lida");
          metaRow.appendChild(receipt);
        } else if (meta) {
          metaRow.textContent = `${metaTime} • ${meta}`;
        }

        bubble.appendChild(metaRow);
        row.appendChild(bubble);
        chatEl.appendChild(row);
        chatEl.scrollTop = chatEl.scrollHeight;
        lastRole = role;
      }

      function addTyping() {
        const row = document.createElement("div");
        row.id = "typing-indicator";
        row.className = "message-row message-row--assistant";
        const bubble = document.createElement("div");
        bubble.className = "typing-bubble";
        bubble.setAttribute("role", "status");
        const label = document.createElement("span");
        label.className = "sr-only";
        label.textContent = "Digitando";
        bubble.appendChild(label);
        [0, 1, 2].forEach(() => {
          const dot = document.createElement("span");
          dot.className = "typing-dot";
          bubble.appendChild(dot);
        });
        row.appendChild(bubble);
        chatEl.appendChild(row);
      }

      function removeTyping() {
        const typing = document.getElementById("typing-indicator");
        if (typing) {
          typing.remove();
        }
      }

      function withJson(payload) {
        try {
          return JSON.stringify(payload);
        } catch (_error) {
          return "";
        }
      }

      async function sendMessage() {
        const message = messageEl.value.trim();
        if (!message) {
          setStatus("Digite uma mensagem antes de enviar.", "warn");
          return;
        }

        sendButton.disabled = true;
        messageEl.disabled = true;
        setStatus("Enviando para /chat...", "ok");
        addMessage("user", message, `thread_id: ${threadIdEl.value}`);

        messageEl.value = "";
        addTyping();

        try {
          const response = await fetch("/chat", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              thread_id: threadIdEl.value,
              message,
            }),
          });

          const payload = await response.json().catch(() => null);
          removeTyping();

          if (!response.ok) {
            const detail = payload && payload.detail
              ? withJson(payload.detail)
              : "Erro interno";
            addMessage(
              "assistant",
              "Falha no retorno da API.",
              `status ${response.status} • ${detail}`
            );
            setStatus("Erro de resposta da API.", "danger");
            return;
          }

          addMessage(
            "assistant",
            payload.response_text || "",
            `status: ${payload.status || "n/a"} | intent: ${payload.intent || "n/a"}`
          );

          if (payload.response_parts && payload.response_parts.length) {
            payload.response_parts.forEach((part) => {
              if (part.type === "media" && part.media_id) {
                addMessage("assistant", `Mídia: ${part.media_id}`);
              }
              if (part.type === "audio" && part.text) {
                addMessage("assistant", `Áudio: ${part.text}`);
              }
            });
          }

          setStatus("Mensagem entregue com sucesso.", "ok");
          setStatusTime();
        } catch (error) {
          removeTyping();
          addMessage("assistant", "Não foi possível conectar ao endpoint /chat.");
          setStatus(`Erro de conexão: ${error.message}`, "danger");
        } finally {
          sendButton.disabled = false;
          messageEl.disabled = false;
          messageEl.focus();
        }
      }

      function clearChat() {
        chatEl.innerHTML = '';
        const separator = document.createElement("div");
        separator.className = "date-separator";
        separator.innerHTML = '<span>Hoje</span>';
        chatEl.appendChild(separator);
        lastRole = null;
      }

      function resizeTextarea() {
        messageEl.style.height = "auto";
        messageEl.style.height = `${Math.min(messageEl.scrollHeight, 100)}px`;
      }

      function wireEvents() {
        messageEl.addEventListener("input", resizeTextarea);
        sendButton.addEventListener("click", sendMessage);

        messageEl.addEventListener("keydown", (event) => {
          if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
            event.preventDefault();
            sendMessage();
          }
        });

        newThreadButton.addEventListener("click", () => {
          threadIdEl.value = randomThreadId();
          localStorage.setItem("playground_thread_id", threadIdEl.value);
          clearChat();
          setStatus(`Nova thread criada: ${threadIdEl.value}`, "ok");
        });

        copyThreadButton.addEventListener("click", async () => {
          await navigator.clipboard.writeText(threadIdEl.value);
          setStatus("Thread ID copiada.", "ok");
        });

        window.addEventListener("resize", setScale);
      }

      function init() {
        initThread();
        setScale();
        wireEvents();
        setStatusTime();
        setStatus("Pronto para testar.");
        addMessage("assistant", "Oi, aqui é o playground da Sunne. Teste a jornada do agente.");
        messageEl.focus();
      }

      init();
    </script>
  </body>
</html>
"""

playground_router = APIRouter()


@playground_router.get("/playground", response_class=HTMLResponse, include_in_schema=False)
def playground() -> str:
    return PLAYGROUND_HTML
