<script setup lang="ts">
import { marked } from 'marked'

const { messages, isLoading, sendMessage } = useChat()
const input = ref('')
const chatContainer = ref<HTMLElement>()

const bronnen = [
  { naam: 'Kanker.nl', url: 'https://www.kanker.nl/', beschrijving: 'Reliable information for patients and loved ones' },
  { naam: 'IKNL', url: 'https://www.iknl.nl', beschrijving: 'Scientific and data-driven knowledge' },
  { naam: 'NKR figures', url: 'https://nkr-cijfers.iknl.nl', beschrijving: 'Statistics from the Netherlands Cancer Registry' },
  { naam: 'Cancer Atlas', url: 'https://kankeratlas.iknl.nl/', beschrijving: 'Interactive map with regional incidence' },
  { naam: 'Guidelines Database', url: 'https://richtlijnendatabase.nl/', beschrijving: 'Oncological guidelines' },
  { naam: 'IKNL Publications', url: 'https://iknl.nl/onderzoek/publicaties', beschrijving: 'Analyses and reports' },
  { naam: 'Scientific publications', url: 'https://iknl.nl/onderzoek/publicaties', beschrijving: 'Articles by IKNL researchers' },
]

const showBronnen = ref(false)
const showContact = ref(false)

function renderMarkdown(content: string): string {
  return marked.parse(content, { async: false }) as string
}

async function handleSend() {
  const text = input.value.trim()
  if (!text || isLoading.value) return
  input.value = ''
  await sendMessage(text)
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

watch(messages, () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}, { deep: true })
</script>

<template>
  <div class="page">
    <header class="header">
      <div class="header-content">
        <div class="logo">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="#D97A8C"/>
          </svg>
          <span>OncoGuide</span>
        </div>
        <div class="header-actions">
          <button class="header-btn" @click="showContact = !showContact; showBronnen = false">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/>
            </svg>
            Contact
          </button>
          <button class="header-btn" @click="showBronnen = !showBronnen; showContact = false">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
            </svg>
            Sources
          </button>
        </div>
      </div>
    </header>

    <div class="container">
      <div class="chat-wrapper" :class="{ 'with-sidebar': showBronnen || showContact }">
        <main class="chat-panel">
          <div v-if="messages.length === 0" class="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
              <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="#D97A8C" opacity="0.3"/>
            </svg>
            <h2>Ask a question about cancer</h2>
            <p>Our AI assistant answers your questions based on reliable Dutch sources.</p>
            <div class="suggestions">
              <button v-for="s in ['What is chemotherapy?', 'How does immunotherapy work?', 'What are the most common symptoms?']" :key="s" class="suggestion" @click="input = s; handleSend()">
                {{ s }}
              </button>
            </div>
          </div>

          <div v-else ref="chatContainer" class="messages">
            <div v-for="msg in messages" :key="msg.id" class="message" :class="msg.role">
              <div class="bubble" :class="msg.role">
                <div v-if="msg.role === 'assistant'" v-html="renderMarkdown(msg.content)" class="markdown" />
                <span v-else>{{ msg.content }}</span>
              </div>
            </div>
            <div v-if="isLoading" class="message assistant">
              <div class="bubble assistant">
                <span class="typing">
                  <span /><span /><span />
                </span>
              </div>
            </div>
          </div>

          <div class="input-bar">
            <textarea
              v-model="input"
              placeholder="Ask a question..."
              rows="1"
              :disabled="isLoading"
              @keydown="handleKeydown"
            />
            <button class="send-btn" :disabled="!input.trim() || isLoading" @click="handleSend">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </main>

        <aside v-if="showContact" class="sidebar">
          <h3>Phone contact</h3>
          <p class="sidebar-desc">Call our AI assistant for information about cancer.</p>

          <a href="tel:+31851234567" class="phone-card">
            <div class="phone-icon-wrap">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/>
              </svg>
            </div>
            <div>
              <span class="phone-number">+31 85 123 4567</span>
              <span class="phone-label">Call now</span>
            </div>
          </a>

          <div class="contact-info">
            <h4>How does it work?</h4>
            <p>When you call, you will be connected to an AI assistant that answers your questions about cancer through a phone conversation.</p>

            <h4>What information is used?</h4>
            <p>The assistant bases its answers on the same reliable sources as the chatbot:</p>
            <ul>
              <li><a href="https://www.kanker.nl/" target="_blank" rel="noopener">Kanker.nl</a></li>
              <li><a href="https://www.iknl.nl" target="_blank" rel="noopener">IKNL</a> and <a href="https://nkr-cijfers.iknl.nl" target="_blank" rel="noopener">NKR figures</a></li>
              <li><a href="https://richtlijnendatabase.nl/" target="_blank" rel="noopener">Guidelines Database</a></li>
              <li><a href="https://iknl.nl/onderzoek/publicaties" target="_blank" rel="noopener">Scientific publications</a></li>
            </ul>

            <h4>Good to know</h4>
            <p>This is an AI-powered information line, not medical advice. Always consult your treating physician for personal medical questions.</p>
          </div>
        </aside>

        <aside v-if="showBronnen" class="sidebar">
          <h3>Sources</h3>
          <p class="sidebar-desc">The chatbot uses these reliable sources as reference.</p>
          <a v-for="bron in bronnen" :key="bron.url" :href="bron.url" target="_blank" rel="noopener" class="bron-card">
            <span class="bron-naam">{{ bron.naam }}</span>
            <span class="bron-desc">{{ bron.beschrijving }}</span>
          </a>
        </aside>
      </div>
    </div>
  </div>
</template>

<style>
@import '~/assets/main.css';

.page {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  flex-shrink: 0;
}

.header-content {
  max-width: 1100px;
  margin: 0 auto;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  color: var(--primary);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.header-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.header-btn:hover {
  background: var(--surface-dim);
  color: var(--text);
}

.container {
  flex: 1;
  overflow: hidden;
  max-width: 1100px;
  width: 100%;
  margin: 0 auto;
}

.chat-wrapper {
  display: flex;
  height: 100%;
}

.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  text-align: center;
}

.empty-state h2 {
  margin-top: 16px;
  font-size: 22px;
  font-weight: 700;
}

.empty-state p {
  margin-top: 8px;
  color: var(--text-secondary);
  max-width: 400px;
}

.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 24px;
  justify-content: center;
}

.suggestion {
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: 20px;
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
}

.suggestion:hover {
  border-color: var(--primary);
  background: var(--primary-container);
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message {
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: var(--radius-lg);
  font-size: 15px;
  line-height: 1.5;
}

.bubble.user {
  background: var(--primary);
  color: white;
  border-bottom-right-radius: 4px;
}

.bubble.assistant {
  background: var(--surface);
  border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
}

.markdown p {
  margin-bottom: 8px;
}

.markdown p:last-child {
  margin-bottom: 0;
}

.markdown ul, .markdown ol {
  padding-left: 20px;
  margin-bottom: 8px;
}

.markdown code {
  background: var(--surface-dim);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.markdown strong {
  font-weight: 600;
}

.typing {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.typing span {
  width: 8px;
  height: 8px;
  background: var(--text-secondary);
  border-radius: 50%;
  animation: typing 1.4s infinite;
  opacity: 0.4;
}

.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { opacity: 0.4; transform: translateY(0); }
  30% { opacity: 1; transform: translateY(-4px); }
}

.input-bar {
  padding: 16px 24px;
  border-top: 1px solid var(--border);
  display: flex;
  gap: 10px;
  align-items: flex-end;
  background: var(--surface);
  flex-shrink: 0;
}

.input-bar textarea {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-family: inherit;
  font-size: 15px;
  resize: none;
  outline: none;
  background: var(--bg);
  line-height: 1.5;
  transition: border-color 0.15s;
}

.input-bar textarea:focus {
  border-color: var(--primary);
}

.send-btn {
  width: 44px;
  height: 44px;
  border: none;
  border-radius: var(--radius);
  background: var(--primary);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: opacity 0.15s;
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.send-btn:not(:disabled):hover {
  opacity: 0.85;
}

.sidebar {
  width: 300px;
  border-left: 1px solid var(--border);
  background: var(--surface);
  padding: 24px;
  overflow-y: auto;
  flex-shrink: 0;
}

.sidebar h3 {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 4px;
}

.sidebar-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.bron-card {
  display: block;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin-bottom: 8px;
  transition: all 0.15s;
  text-decoration: none;
}

.bron-card:hover {
  border-color: var(--primary);
  background: var(--primary-container);
  text-decoration: none;
}

.bron-naam {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.bron-desc {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.phone-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: var(--primary);
  border-radius: var(--radius);
  text-decoration: none;
  margin-bottom: 20px;
  transition: opacity 0.15s;
}

.phone-card:hover {
  opacity: 0.9;
  text-decoration: none;
}

.phone-icon-wrap {
  width: 44px;
  height: 44px;
  background: rgba(255,255,255,0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.phone-number {
  display: block;
  color: white;
  font-size: 16px;
  font-weight: 700;
}

.phone-label {
  display: block;
  color: rgba(255,255,255,0.8);
  font-size: 13px;
}

.contact-info {
  font-size: 14px;
  line-height: 1.6;
}

.contact-info h4 {
  font-size: 14px;
  font-weight: 600;
  margin-top: 16px;
  margin-bottom: 4px;
}

.contact-info h4:first-child {
  margin-top: 0;
}

.contact-info p {
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.contact-info ul {
  padding-left: 18px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.contact-info li {
  margin-bottom: 2px;
}

@media (max-width: 768px) {
  .header-actions {
    gap: 4px;
  }

  .header-btn {
    padding: 6px 10px;
    font-size: 13px;
  }
}

@media (max-width: 768px) {
  .chat-wrapper.with-sidebar {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
    border-left: none;
    border-top: 1px solid var(--border);
    max-height: 40vh;
  }

  .bubble {
    max-width: 90%;
  }
}
</style>
