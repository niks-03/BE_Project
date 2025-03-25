"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar } from "@/components/ui/avatar"
import { Send, Upload, Bot, User, FileText, Loader2, Trash2, Download } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { UserButton } from "@clerk/nextjs"

// Define message type
type Message = {
  role: "user" | "assistant"
  content: string
  timestamp: Date
  imageData?: string
}

type VisualizeDocumentState = {
  name: string;
  size: number;
  isProcessed: boolean;
}

export default function ChatPage() {
  const [imageData, setImageData] = useState(() => {
    if (typeof window !== 'undefined') {
      const savedImageData = localStorage.getItem('VisualizeImageData');
      return savedImageData || '';
    }
    return '';
  });
  // const [messages, setMessages] = useState<Message[]>([])
  const [messages, setMessages] = useState<Message[]>(() => {
    if (typeof window !== 'undefined') {
      const savedMessages = localStorage.getItem('VisualizeChatMessages');
      return savedMessages ? JSON.parse(savedMessages) : [];
    }
    return [];
  });

  const [visualizeDocumentState, setDocumentState] = useState<VisualizeDocumentState | null> (() =>{
    if (typeof window !== 'undefined') {
      const savedDocumentState = localStorage.getItem('VisualizeDocumentState');
      return savedDocumentState ? JSON.parse(savedDocumentState) : null;
    }
    return null;
  });
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [uploadedDocument, setUploadedDocument] = useState<File | null>(null)
  const [isProcessingDocument, setIsProcessingDocument] = useState(false)
  // const [isDocumentProcessed, setIsDocumentProcessed] = useState(false)
  const [isDocumentProcessed, setIsDocumentProcessed] = useState(
    visualizeDocumentState?.isProcessed || false
  )
  const [processingError, setProcessingError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem('VisualizeChatMessages', JSON.stringify(messages));
    }
  }, [messages]);

  useEffect(() => {
    if (uploadedDocument) {
      const docState: VisualizeDocumentState ={
        name: uploadedDocument.name,
        size: uploadedDocument.size,
        isProcessed: isDocumentProcessed
      };
      localStorage.setItem("VisualizeDocumentState", JSON.stringify(docState));
    }
  }, [uploadedDocument, isDocumentProcessed]);

  useEffect(() => {
    if (imageData) {
      localStorage.setItem('VisualizeImageData', imageData);
    }
  }, [imageData]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!input.trim() || !isDocumentProcessed) return

    // Add user message to chat
    const userMessage: Message = {
      role: "user",
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      // Send message to doc-chat API
      const response = await fetch("/api/visualize-chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ prompt: input }),
      })

      if (!response.ok) {
        throw new Error(`API responded with status: ${response.status}`)
      }

      const data = await response.json()

      if (data.imageData) {
        console.log(`Received image data of length: ${data.imageData.length}`);
        setImageData(data.imageData);
        localStorage.setItem('VisualizeImageData', data.imageData);
      } else {
        console.log('No image data received');
      }

      // Add assistant response to chat
      const assistantMessage: Message = {
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
        imageData: data.imageData,
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error("Error sending message:", error)
      // Add error message
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, there was an error processing your request.",
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileUpload = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setUploadedDocument(e.target.files[0])
      setIsDocumentProcessed(false)
      setProcessingError(null)
    }
  }

  const processDocument = async () => {
    if (!uploadedDocument) return

    setIsProcessingDocument(true)
    setProcessingError(null)

    try {
      const formData = new FormData()
      formData.append("file", uploadedDocument)

      const response = await fetch("/api/process-visualization-doc", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || "Failed to process document")
      }

      const data = await response.json()
      setIsDocumentProcessed(true)

      // Add system message about successful document processing
      setMessages([
        {
          role: "assistant",
          content: `Document "${uploadedDocument.name}" has been processed successfully. You can now ask questions about it.`,
          timestamp: new Date(),
        },
      ])

      const docState: VisualizeDocumentState = {
        name: uploadedDocument.name,
        size: uploadedDocument.size,
        isProcessed: true
      };
      localStorage.setItem('VisualizeDocumentState', JSON.stringify(docState));

    } catch (error) {
      console.error("Error processing document:", error)
      setProcessingError(error instanceof Error ? error.message : "Failed to process document")
    } finally {
      setIsProcessingDocument(false)
    }
  }

  const handleClearUploads = async () => {
    try {
      const response = await fetch('/api/clear-uploads', {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to clear uploads');
      }

      // Reset the chat state
      setUploadedDocument(null);
      setIsDocumentProcessed(false);
      setMessages([]);
      setImageData('');

      localStorage.removeItem('VisualizeDocumentState');
      localStorage.removeItem('VisualizeChatMessages');
      localStorage.removeItem('VisualizeImageData');
      
    } catch (error) {
      console.error('Error clearing uploads:', error);
      setProcessingError('Failed to clear uploads');
    }
  }

    // Display document info from localStorage if we don't have an actual File object
    const documentName = uploadedDocument?.name || visualizeDocumentState?.name;
    const documentSize = uploadedDocument?.size || visualizeDocumentState?.size;

  return (
    <div className="flex flex-col h-screen bg-background">
      <div className="absolute top-4 right-4 z-50">
        <UserButton/>
      </div>
      {/* Document upload area - only show if no document is processed */}
      {!isDocumentProcessed && (
        <div className="border-b py-4">
          <div className="max-w-3xl mx-auto px-4">
            <div className="flex flex-col sm:flex-row items-center gap-4 justify-between">
              <div className="flex-1">
                <h2 className="text-lg font-medium">Data Visualize</h2>
                <p className="text-sm text-muted-foreground">Upload a document to start chatting about its contents</p>
              </div>

              <div className="flex gap-2 w-full sm:w-auto">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  className="hidden"
                  accept=".xlsx, .xls, .csv"
                />

                <Button onClick={handleFileUpload} variant="outline" className="flex-1 sm:flex-initial">
                  <Upload className="h-4 w-4 mr-2" />
                  Select Document
                </Button>

                <Button
                  onClick={processDocument}
                  disabled={!uploadedDocument || isProcessingDocument}
                  className="flex-1 sm:flex-initial"
                >
                  {isProcessingDocument ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <FileText className="h-4 w-4 mr-2" />
                      Process Document
                    </>
                  )}
                </Button>
              </div>
            </div>

            {uploadedDocument && !isProcessingDocument && !isDocumentProcessed && (
              <div className="mt-2 text-sm">
                Selected: <span className="font-medium">{uploadedDocument.name}</span> ({(uploadedDocument.size / 1024).toFixed(2)} KB)
              </div>
            )}

            {processingError && (
              <Alert variant="destructive" className="mt-4">
                <AlertDescription>{processingError}</AlertDescription>
              </Alert>
            )}
          </div>
        </div>
      )}

      {/* Document info when processed */}
      {isDocumentProcessed && (documentName) && (
        <div className="border-b py-2">
          <div className="max-w-3xl mx-auto px-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm">
                <FileText className="h-4 w-4" />
                <span>
                  Chatting about: <span className="font-medium">{documentName}</span>
                </span>
              </div>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={handleClearUploads}
                className="text-destructive hover:text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Clear Chat
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Chat messages area */}
      <div className="flex-1 overflow-y-auto py-4 px-4">
        <div className="max-w-3xl mx-auto">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              {isDocumentProcessed
                ? "Ask a question about your document"
                : "Upload and process a document to start chatting"}
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((message, index) => (
                <div key={index} className="flex items-start gap-3">
                  <div className="shrink-0">
                    {message.role === "assistant" ? (
                      <Avatar className="h-8 w-8 bg-primary flex items-center justify-center">
                        <Bot className="h-6 w-5.5 text-primary-foreground" />
                      </Avatar>
                    ) : (
                      <Avatar className="h-8 w-8 bg-primary flex items-center justify-center">
                        <User className="h-6 w-5.5 text-primary-foreground" />
                      </Avatar>
                    )}
                  </div>

                  <div className="flex-1">
                    <div className="font-medium mb-1">{message.role === "assistant" ? "Assistant" : "You"}</div>
                    <div className={`whitespace-pre-wrap p-3 rounded-lg ${message.role === "assistant" ? "bg-secondary" : "bg-primary/30"}`}>
                      {message.content}
                      {message.imageData && (
                        <div className="image-container relative">
                          <img 
                            src={`data:image/png;base64,${message.imageData}`}
                            alt="Data Visualization" 
                            className="max-w-full" 
                          />
                          <button 
                            onClick={() => {
                              // Create a download link
                              const link = document.createElement('a');
                              link.href = `data:image/png;base64,${message.imageData}`;
                              link.download = `visualization_${new Date().toISOString().slice(0,10)}.png`;
                              link.click();
                            }}
                            className="absolute -top-6 -right-0 bg-white/80 hover:bg-white p-1.5 rounded-full shadow-md"
                          >
                            <Download className="size-5 text-gray-700" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* Add loading message */}
              {isLoading && (
                <div className="flex items-start gap-3">
                  <div className="shrink-0">
                    <Avatar className="h-8 w-8 bg-primary flex items-center justify-center">
                      <Bot className="h-6 w-5.5 text-primary-foreground" />
                    </Avatar>
                  </div>
                  <div className="flex-1">
                    <div className="font-medium mb-1">Assistant</div>
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Thinking...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Input area - fixed at bottom */}
      <div className="border-t bg-background py-4">
        <div className="max-w-3xl mx-auto px-4">
          <form onSubmit={handleSendMessage} className="flex gap-2">
            <div className="flex-grow relative">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={
                  isDocumentProcessed
                    ? "Ask a question about your document..."
                    : "Process a document to start chatting..."
                }
                disabled={isLoading || !isDocumentProcessed}
                className="pr-20"
              />
            </div>

            <Button
              type="submit"
              size="icon"
              disabled={isLoading || !isDocumentProcessed || !input.trim()}
              className="shrink-0"
            >
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}

