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
    const response = await fetch("http://127.0.0.1:8000/visualize", {
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

    // Get the binary data as an ArrayBuffer
    const arrayBuffer = await response.arrayBuffer()
    console.log("arraybuffer image data:", arrayBuffer)
    // Convert ArrayBuffer to Base64 string
    const base64 = Buffer.from(arrayBuffer).toString("base64")

    console.log("Base64 image data:", base64)

    // Return both the text response and the base64 encoded image
    return NextResponse.json({
      response: "Here's the visualization you requested.",
      imageData: base64, // Base64 encoded image data
    })
  } catch (error) {
    console.error("Error in visualization API route:", error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to process message" },
      { status: 500 },
    )
  }
}

