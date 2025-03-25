import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  try {
    // Parse the JSON from the request
    const { prompt } = await request.json()

    if (!prompt) {
      return NextResponse.json({ error: "No message provided" }, { status: 400 })
    }

    // Log the received message
    console.log("Chat message:", prompt)

    // Send the message to the Python API
    const response = await fetch("http://127.0.0.1:8000/doc-chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt: prompt }),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `API responded with status: ${response.status}`)
    }

    const data = await response.json()

    // Return the response from the Python API
    return NextResponse.json({
      response: data.response || "I've processed your question about the document.",
    })
  } catch (error) {
    console.error("Error in doc-chat API route:", error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to process message" },
      { status: 500 },
    )
  }
}

