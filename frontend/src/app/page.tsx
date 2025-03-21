'use client'

import * as React from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { GameSelector } from '@/components/game/GameSelector'
import { ChatInterface } from '@/components/chat/ChatInterface'
import type { GameContext } from '@/types/game'

export default function Home() {
  const [activeGame, setActiveGame] = React.useState<GameContext | null>(null)

  const handleGameSelect = (game: GameContext) => {
    setActiveGame(game)
  }

  return (
    <main className="container mx-auto p-4 md:p-8">
      <div className="flex flex-col gap-8">
        <div>
          <h1 className="text-4xl font-bold mb-2">GameFriend</h1>
          <p className="text-muted-foreground">
            Your AI-powered gaming companion
          </p>
        </div>

        <Tabs defaultValue="chat" className="w-full">
          <TabsList>
            <TabsTrigger value="chat">Chat</TabsTrigger>
            <TabsTrigger value="games">Games</TabsTrigger>
          </TabsList>
          <TabsContent value="chat" className="mt-4">
            <ChatInterface gameContext={activeGame} />
          </TabsContent>
          <TabsContent value="games" className="mt-4">
            <GameSelector onGameSelect={handleGameSelect} />
          </TabsContent>
        </Tabs>
      </div>
    </main>
  )
}
