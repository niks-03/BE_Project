import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  try {
    // Parse the FormData from the request
    const formData = await request.formData()
    const file = formData.get("file") as File

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 })
    }

    // Log the received file
    console.log("Processing document:", file.name, file.type, file.size)

    // Create a new FormData to send to the Python API
    const apiFormData = new FormData()
    apiFormData.append("file", file)

    // Send the file to the Python API
    const response = await fetch("http://127.0.0.1:8000/process-document", {
      method: "POST",
      body: apiFormData,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `API responded with status: ${response.status}`)
    }

    const data = await response.json()

    // Return the response from the Python API
    return NextResponse.json(data)
  } catch (error) {
    console.error("Error in process-document API route:", error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to process document" },
      { status: 500 },
    )
  }
}

