'use client'

import * as React from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import type { GameContext } from '@/types/game'
import { sendChatMessage, getChatSession } from '@/lib/api'
import { useState, useEffect } from 'react'

interface ChatInterfaceProps {
  gameContext: GameContext | null
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

const SESSION_ID_KEY = 'gamefriend_chat_session_id'
const MESSAGES_KEY = 'gamefriend_chat_messages'

export function ChatInterface({ gameContext }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Initialize state from localStorage after component mounts
  useEffect(() => {
    const storedSessionId = localStorage.getItem(SESSION_ID_KEY);
    const storedMessages = localStorage.getItem(MESSAGES_KEY);
    
    if (storedSessionId) {
      setSessionId(storedSessionId);
    }
    
    if (storedMessages) {
      setMessages(JSON.parse(storedMessages));
    }
  }, []);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem(MESSAGES_KEY, JSON.stringify(messages));
  }, [messages]);

  // Save sessionId to localStorage whenever it changes
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem(SESSION_ID_KEY, sessionId);
    }
  }, [sessionId]);

  // Load chat session when sessionId changes
  useEffect(() => {
    if (sessionId) {
      console.log('Loading chat session:', sessionId);
      loadChatSession();
    }
  }, [sessionId]);

  const loadChatSession = async () => {
    if (!sessionId) return
    
    try {
      console.log('Fetching chat session:', sessionId)
      const response = await getChatSession(sessionId)
      console.log('Chat session loaded:', response)
      
      if (response && response.messages) {
        const formattedMessages = response.messages.map((msg: any) => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.created_at,
        }))
        console.log('Setting messages:', formattedMessages)
        setMessages(formattedMessages)
      }
    } catch (error) {
      console.error('Error loading chat session:', error)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading || !gameContext) return

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString()
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const requestData = {
        message: input.trim(),
        game_context: gameContext.name,
        session_id: sessionId || undefined
      }
      console.log('Sending message:', requestData)
      const response = await sendChatMessage(input.trim(), gameContext.name, sessionId)
      console.log('Received response:', response)

      if (response.session_id) {
        setSessionId(response.session_id)
      }

      if (response.messages && response.messages.length > 0) {
        const lastMessage = response.messages[response.messages.length - 1]
        const assistantMessage: Message = {
          role: lastMessage.role as 'user' | 'assistant',
          content: lastMessage.content,
          timestamp: lastMessage.created_at
        }
        setMessages((prev) => [...prev, assistantMessage])
      }
    } catch (error) {
      console.error('Error sending message:', error)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date().toISOString()
        }
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="container mx-auto p-4">
      <Card className="p-4">
        <div className="h-[500px] overflow-y-auto mb-4 space-y-4">
          {messages.map((message, i) => (
            <div key={i} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-lg p-3 ${
                message.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'
              }`}>
                {message.content}
              </div>
            </div>
          ))}
        </div>
        <div className="flex space-x-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
          />
          <Button onClick={handleSubmit}>Send</Button>
        </div>
      </Card>
    </div>
  )
}