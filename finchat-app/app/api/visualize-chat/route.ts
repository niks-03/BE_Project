import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  try {
    // Parse the JSON from the request
    const { prompt, advanced } = await request.json()

    if (!prompt) {
      return NextResponse.json({ error: "No message provided" }, { status: 400 })
    }

    // Log the received message and advanced mode
    console.log("Chat message:", prompt)
    console.log("Advanced mode:", advanced)

    // Send the message to the Python API
    const response = await fetch("http://127.0.0.1:8000/visualize", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ 
        prompt: prompt,
        advance: advanced ? "true" : "false"  // Convert boolean to string
      }),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `API responded with status: ${response.status}`)
    }

    // If in advanced mode, return all the data
    if (advanced) {
      const data = await response.json()
      console.log("Raw advanced visualization data:", data)
      
      // Ensure all required fields are present
      if (!data.image || !data.data || !data.explanation) {
        console.error("Missing required fields in advanced response:", {
          hasImage: !!data.image,
          hasData: !!data.data,
          hasExplanation: !!data.explanation
        })
        throw new Error("Invalid response format from visualization API")
      }

      const responseData = {
        response: "Here's the visualization with detailed data.",
        imageData: data.image,
        graphData: data.data.visualization_data,
        graphExplanation: data.explanation,
      }
      
      console.log("Processed advanced visualization data:", responseData)
      return NextResponse.json(responseData)
    }
    else {
      const arrayBuffer = await response.arrayBuffer()
      console.log("arraybuffer image data:", arrayBuffer)
      // Convert ArrayBuffer to Base64 string
      const base64 = Buffer.from(arrayBuffer).toString("base64")

      console.log("Base64 image data:", base64)
      return NextResponse.json({
        response: "Here's the visualization you requested.",
        imageData: base64,
      })
    }
    
  } catch (error) {
    console.error("Error in visualization API route:", error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to process message" },
      { status: 500 },
    )
  }
}

