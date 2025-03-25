import { NextResponse } from 'next/server';

export async function POST() {
  try {
    const response = await fetch('http://127.0.0.1:8000/clear-uploads', {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to clear uploads');
    }

    return NextResponse.json({ message: 'Uploads cleared successfully' });
  } catch (error) {
    console.error('Error clearing uploads:', error);
    return NextResponse.json(
      { error: 'Failed to clear uploads' },
      { status: 500 }
    );
  }
} 