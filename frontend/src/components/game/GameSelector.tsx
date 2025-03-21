'use client'

import * as React from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { GameContext as GameContextType } from '@/types/game'

interface Game {
  id: string
  name: string
  platform: string
  hasGuide: boolean
}

interface GameSelectorProps {
  onGameSelect: (game: GameContextType) => void
}

export function GameSelector({ onGameSelect }: GameSelectorProps) {
  const [games, setGames] = React.useState<Game[]>([])
  const [guideUrl, setGuideUrl] = React.useState('')
  const [isImporting, setIsImporting] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [success, setSuccess] = React.useState<string | null>(null)

  // Fetch games on component mount
  React.useEffect(() => {
    fetchGames()
  }, [])

  const fetchGames = async () => {
    try {
      const response = await fetch('/api/games')
      if (!response.ok) {
        throw new Error('Failed to fetch games')
      }
      const data = await response.json()
      setGames(data.games)
    } catch (error) {
      console.error('Error fetching games:', error)
      setError('Failed to load games')
    }
  }

  const handleGameSelect = async (game: Game) => {
    try {
      const gameContext: GameContextType = {
        name: game.name,
        platform: game.platform,
        isActive: true,
        progress: {}
      }
      onGameSelect(gameContext)
    } catch (error) {
      console.error('Error selecting game:', error)
      setError('Failed to select game. Please try again.')
    }
  }

  const handleGuideImport = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!guideUrl.trim()) return

    setIsImporting(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await fetch('/api/guides/import', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: guideUrl }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to import guide')
      }

      // Refresh the games list after successful import
      await fetchGames()
      
      setSuccess(`Successfully imported guide for ${data.game} on ${data.platform}`)
      setGuideUrl('')
    } catch (error) {
      console.error('Error importing guide:', error)
      setError(error instanceof Error ? error.message : 'Failed to import guide. Please try again.')
    } finally {
      setIsImporting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium mb-4">Available Games</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {games.length === 0 ? (
            <p className="text-muted-foreground">No games with guides available. Import a guide to get started!</p>
          ) : (
            games.map(game => (
              <Card
                key={game.id}
                className="p-4 cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => handleGameSelect(game)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">{game.name}</h4>
                    <p className="text-sm text-muted-foreground">{game.platform}</p>
                  </div>
                  {game.hasGuide && (
                    <div className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary">
                      Guide Available
                    </div>
                  )}
                </div>
              </Card>
            ))
          )}
        </div>
      </div>

      <div>
        <h3 className="text-lg font-medium mb-4">Import Guide</h3>
        <form onSubmit={handleGuideImport} className="space-y-4">
          <div className="flex gap-2">
            <Input
              type="url"
              placeholder="Paste GameFAQs guide URL..."
              value={guideUrl}
              onChange={(e) => setGuideUrl(e.target.value)}
              className="flex-grow"
            />
            <Button type="submit" disabled={isImporting || !guideUrl.trim()}>
              {isImporting ? 'Importing...' : 'Import'}
            </Button>
          </div>
          {error && (
            <div className="text-sm text-red-500">
              {error}
            </div>
          )}
          {success && (
            <div className="text-sm text-green-500">
              {success}
            </div>
          )}
        </form>
      </div>
    </div>
  )
} 