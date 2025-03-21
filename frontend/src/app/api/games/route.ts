import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const response = await fetch('http://localhost:8000/api/games')
    if (!response.ok) {
      throw new Error('Failed to fetch games from backend')
    }
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error in games API:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch games' },
      { status: 500 }
    )
  }
} 