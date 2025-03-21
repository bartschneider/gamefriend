export interface GameProgress {
  currentLocation?: string
  completedObjectives?: string[]
  currentObjective?: string
  collectedItems?: string[]
  unlockedAreas?: string[]
}

export interface GameContext {
  name: string
  platform: string
  progress: GameProgress
  isActive: boolean
} 