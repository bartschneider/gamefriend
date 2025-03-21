'use client'

import * as React from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import type { GameContext } from '@/types/game'
import { sendChatMessage, getChatSession } from '@/lib/api'
import { useState, useEffect } from 'react'
import { useDebounce } from '@/hooks/useDebounce'
import { cn } from '@/lib/utils'

interface ChatInterfaceProps {
  gameContext: GameContext | null
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

// Helper functions for game-specific storage keys
const getSessionKey = (gameName: string) => `gamefriend_chat_session_${gameName}`
const getMessagesKey = (gameName: string) => `gamefriend_chat_messages_${gameName}`

const MAX_MESSAGE_LENGTH = 1000
const MIN_MESSAGE_LENGTH = 1
const MESSAGE_COOLDOWN = 1000 // 1 second

export function ChatInterface({ gameContext }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [lastMessageTime, setLastMessageTime] = useState<number>(0)
  const debouncedInput = useDebounce(input, 300)

  // Initialize state from localStorage after component mounts
  useEffect(() => {
    if (!gameContext) return;
    
    const sessionKey = getSessionKey(gameContext.name);
    const messagesKey = getMessagesKey(gameContext.name);
    const storedSessionId = localStorage.getItem(sessionKey);
    
    if (storedSessionId) {
      setSessionId(storedSessionId);
      // Don't load messages from localStorage, fetch from backend instead
    }
  }, [gameContext]);

  // Load chat session when sessionId or gameContext changes
  useEffect(() => {
    if (sessionId && gameContext) {
      loadChatSession();
    } else {
      // Only clear messages if we're switching games
      if (gameContext) {
        setMessages([]);
        setSessionError(null);
      }
    }
  }, [sessionId, gameContext]);

  const loadChatSession = async () => {
    if (!sessionId || !gameContext) return;
    
    setIsLoadingSession(true);
    setSessionError(null);
    
    try {
      const response = await getChatSession(sessionId);
      
      if (response && response.messages) {
        const formattedMessages = response.messages.map((msg: any) => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.created_at,
        }));
        setMessages(formattedMessages);
        // Update localStorage with the latest messages from backend
        const messagesKey = getMessagesKey(gameContext.name);
        localStorage.setItem(messagesKey, JSON.stringify(formattedMessages));
      }
    } catch (error) {
      console.error('Error loading chat session:', error);
      setSessionError('Failed to load chat history. Please try again.');
      // Don't clear the session on error, just show the error message
    } finally {
      setIsLoadingSession(false);
    }
  };

  // Validate message content
  const validateMessage = (content: string): string | null => {
    if (content.length < MIN_MESSAGE_LENGTH) {
      return 'Message cannot be empty'
    }
    if (content.length > MAX_MESSAGE_LENGTH) {
      return `Message cannot exceed ${MAX_MESSAGE_LENGTH} characters`
    }
    if (!/^[\w\s.,!?-]+$/.test(content)) {
      return 'Message contains invalid characters'
    }
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading || !gameContext) return

    // Check cooldown
    const now = Date.now()
    if (now - lastMessageTime < MESSAGE_COOLDOWN) {
      setSessionError(`Please wait ${Math.ceil((MESSAGE_COOLDOWN - (now - lastMessageTime)) / 1000)} seconds before sending another message`)
      return
    }

    // Validate message
    const validationError = validateMessage(input.trim())
    if (validationError) {
      setSessionError(validationError)
      return
    }

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString()
    }

    // Optimistically add user message
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    setLastMessageTime(now)

    try {
      const response = await sendChatMessage(input.trim(), gameContext.name, sessionId)

      if (response.session_id) {
        setSessionId(response.session_id)
        const sessionKey = getSessionKey(gameContext.name);
        localStorage.setItem(sessionKey, response.session_id);
      }

      if (response.messages && response.messages.length > 0) {
        const formattedMessages = response.messages.map((msg: any) => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.created_at,
        }));
        
        setMessages(formattedMessages);
        
        const messagesKey = getMessagesKey(gameContext.name);
        localStorage.setItem(messagesKey, JSON.stringify(formattedMessages));
      }
    } catch (error) {
      console.error('Error sending message:', error)
      setMessages((prev) => prev.slice(0, -1))
      setSessionError('Failed to send message. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  if (!gameContext) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] text-center p-4">
        <h3 className="text-xl font-medium mb-2">No Game Selected</h3>
        <p className="text-muted-foreground">
          Please select a game from the Games tab to start chatting
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[60vh]">
      <div className="bg-primary/5 border-b p-4 mb-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">{gameContext.name}</h2>
            <p className="text-sm text-muted-foreground">{gameContext.platform}</p>
          </div>
          <div className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary">
            {sessionId ? 'Active Session' : 'New Session'}
          </div>
        </div>
      </div>

      {sessionError && (
        <div className="bg-destructive/10 text-destructive px-4 py-2 mb-4 rounded-md">
          {sessionError}
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {isLoadingSession ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-muted-foreground">Loading chat history...</div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-muted-foreground">Start a conversation about {gameContext.name}</div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={cn(
                  "max-w-[80%] rounded-lg p-3",
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted',
                  "prose prose-sm dark:prose-invert"
                )}
                dangerouslySetInnerHTML={{ __html: message.content }}
              />
            </div>
          ))
        )}
      </div>

      <div className="flex gap-2">
        <div className="flex-1 relative">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about the game..."
            className="flex-1"
            maxLength={MAX_MESSAGE_LENGTH}
          />
          <div className="absolute bottom-2 right-2 text-xs text-muted-foreground">
            {input.length}/{MAX_MESSAGE_LENGTH}
          </div>
        </div>
        <Button 
          onClick={handleSubmit} 
          disabled={isLoading || !input.trim() || Date.now() - lastMessageTime < MESSAGE_COOLDOWN}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </Button>
      </div>
    </div>
  );
}