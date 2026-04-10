interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

interface ChatProfile {
  kankersoort?: string
  stadium?: string
  behandelingen?: string[]
  symptomen?: string[]
  medicatie?: string[]
}

const API_BASE = 'http://localhost:8000'

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

export function useChat(profile?: Ref<ChatProfile | null>) {
  const messages = ref<ChatMessage[]>([])
  const isLoading = ref(false)

  function addMessage(role: 'user' | 'assistant', content: string): ChatMessage {
    const msg: ChatMessage = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      role,
      content,
    }
    messages.value = [...messages.value, msg]
    return msg
  }

  async function sendMessage(content: string) {
    addMessage('user', content)
    isLoading.value = true

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          ...(profile?.value ? { profile: profile.value } : {}),
        }),
      })

      if (!response.ok) throw new Error('Request failed')

      const data = await response.json()
      const answer = data.answer as string

      const assistantMsg = addMessage('assistant', '')
      const words = answer.split(' ')

      for (let i = 0; i < words.length; i++) {
        assistantMsg.content += (i > 0 ? ' ' : '') + words[i]
        messages.value = [...messages.value.slice(0, -1), { ...assistantMsg }]
        await sleep(30)
      }
    } catch {
      addMessage('assistant', 'The chatbot is currently unavailable. Please try again later.')
    } finally {
      isLoading.value = false
    }
  }

  function clearMessages() {
    messages.value = []
  }

  return { messages, isLoading, sendMessage, clearMessages }
}
