<script setup lang="ts">
import { marked } from 'marked'

interface Profile {
  kankersoort: string
  stadium?: string
  behandelingen?: string[]
  symptomen?: string[]
  medicatie?: string[]
  diagnosedatum?: string
  notities?: string
}

const route = useRoute()
const input = ref('')
const chatContainer = ref<HTMLElement>()
const showChat = ref(false)

const profile = computed<Profile | null>(() => {
  try {
    const raw = route.params.data as string
    const decoded = atob(raw.replace(/-/g, '+').replace(/_/g, '/'))
    const json = JSON.parse(decoded)
    return {
      kankersoort: json.k,
      stadium: json.s,
      behandelingen: json.b,
      symptomen: json.y,
      medicatie: json.m,
      diagnosedatum: json.d,
      notities: json.n,
    }
  } catch {
    return null
  }
})

const { messages, isLoading, sendMessage } = useChat(profile)

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

const appLink = computed(() => `oncoguide://profiel/${route.params.data}`)

onMounted(() => {
  window.location.href = appLink.value
})

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
      </div>
    </header>

    <div class="app-banner">
      <div class="banner-content">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="#D97A8C"/>
        </svg>
        <div class="banner-text">
          <strong>OncoGuide</strong>
          <span>Open in the app for the full experience</span>
        </div>
        <a :href="appLink" class="banner-btn">Open App</a>
      </div>
    </div>

    <div v-if="!profile" class="error-state">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#6B6670" stroke-width="2">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      <h2>Profile not found</h2>
      <p>The link is invalid or expired.</p>
    </div>

    <div v-else class="content">
      <div v-if="!showChat" class="profile-view">
        <div class="profile-card">
          <div class="profile-header">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#D97A8C" stroke-width="2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
            <h2>Shared disease profile</h2>
          </div>

          <div class="profile-field">
            <label>Cancer type</label>
            <span>{{ profile.kankersoort }}</span>
          </div>

          <div v-if="profile.stadium" class="profile-field">
            <label>Stage</label>
            <span>{{ profile.stadium }}</span>
          </div>

          <div v-if="profile.behandelingen?.length" class="profile-field">
            <label>Treatments</label>
            <div class="chips">
              <span v-for="b in profile.behandelingen" :key="b" class="chip">{{ b }}</span>
            </div>
          </div>

          <div v-if="profile.symptomen?.length" class="profile-field">
            <label>Symptoms</label>
            <div class="chips">
              <span v-for="s in profile.symptomen" :key="s" class="chip">{{ s }}</span>
            </div>
          </div>

          <div v-if="profile.medicatie?.length" class="profile-field">
            <label>Medication</label>
            <div class="chips">
              <span v-for="m in profile.medicatie" :key="m" class="chip">{{ m }}</span>
            </div>
          </div>

          <div v-if="profile.diagnosedatum" class="profile-field">
            <label>Diagnosis date</label>
            <span>{{ profile.diagnosedatum }}</span>
          </div>

          <div v-if="profile.notities" class="profile-field">
            <label>Notes</label>
            <span>{{ profile.notities }}</span>
          </div>
        </div>

        <button class="chat-btn" @click="showChat = true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          Ask a question about this disease profile
        </button>
      </div>

      <div v-else class="chat-view">
        <button class="profile-bar" @click="showChat = false">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#D97A8C" stroke-width="2">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
          </svg>
          <strong>{{ profile.kankersoort }}</strong>
          <span v-if="profile.stadium"> · {{ profile.stadium }}</span>
          <span class="bar-link">View profile</span>
        </button>

        <div v-if="messages.length === 0" class="empty-chat">
          <p>Ask a question about this disease profile</p>
          <div class="suggestions">
            <button class="suggestion" @click="input = `What is ${profile.kankersoort}?`; handleSend()">
              What is {{ profile.kankersoort }}?
            </button>
            <button v-if="profile.behandelingen?.length" class="suggestion" @click="input = `What can I expect with ${profile.behandelingen[0]}?`; handleSend()">
              What can I expect with {{ profile.behandelingen[0] }}?
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
              <span class="typing"><span /><span /><span /></span>
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
      </div>
    </div>
  </div>
</template>

<style>
@import '~/assets/main.css';

.page {
  min-height: 100vh;
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
  max-width: 700px;
  margin: 0 auto;
  height: 56px;
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  color: var(--primary);
}

.app-banner {
  background: var(--primary-container);
  border-bottom: 1px solid var(--primary-light);
  padding: 10px 24px;
  flex-shrink: 0;
}

.banner-content {
  max-width: 700px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.banner-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  font-size: 13px;
}

.banner-text strong {
  font-size: 14px;
}

.banner-text span {
  color: var(--text-secondary);
}

.banner-btn {
  padding: 6px 16px;
  background: var(--primary);
  color: white;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
}

.banner-btn:hover {
  opacity: 0.9;
  text-decoration: none;
}

.error-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  text-align: center;
}

.error-state h2 {
  margin-top: 16px;
  font-size: 20px;
}

.error-state p {
  color: var(--text-secondary);
  margin-top: 4px;
}

.content {
  flex: 1;
  display: flex;
  flex-direction: column;
  max-width: 700px;
  width: 100%;
  margin: 0 auto;
}

.profile-view {
  padding: 24px;
}

.profile-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
}

.profile-header h2 {
  font-size: 20px;
}

.profile-field {
  margin-bottom: 16px;
}

.profile-field:last-child {
  margin-bottom: 0;
}

.profile-field label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.profile-field span {
  font-size: 15px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  display: inline-block;
  padding: 4px 12px;
  background: var(--surface-dim);
  border-radius: 20px;
  font-size: 13px;
}

.chat-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  margin-top: 16px;
  padding: 14px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: var(--radius);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}

.chat-btn:hover {
  opacity: 0.9;
}

.chat-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.profile-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: var(--surface);
  border: none;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  font-size: 14px;
  text-align: left;
  width: 100%;
  transition: background 0.15s;
}

.profile-bar:hover {
  background: var(--surface-dim);
}

.bar-link {
  margin-left: auto;
  color: var(--primary);
  font-size: 13px;
}

.empty-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  text-align: center;
}

.empty-chat p {
  color: var(--text-secondary);
  font-size: 16px;
  margin-bottom: 16px;
}

.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
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

.message { display: flex; }
.message.user { justify-content: flex-end; }
.message.assistant { justify-content: flex-start; }

.bubble {
  max-width: 80%;
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

.markdown p { margin-bottom: 8px; }
.markdown p:last-child { margin-bottom: 0; }
.markdown ul, .markdown ol { padding-left: 20px; margin-bottom: 8px; }
.markdown strong { font-weight: 600; }

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

.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.send-btn:not(:disabled):hover { opacity: 0.85; }

@media (max-width: 768px) {
  .bubble { max-width: 90%; }
}
</style>
