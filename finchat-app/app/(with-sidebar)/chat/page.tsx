"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar } from "@/components/ui/avatar"
import { Send, Upload, Bot, User, FileText, Loader2, Trash2 } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { UserButton } from "@clerk/nextjs"
import Markdown from 'markdown-to-jsx';

// Define message type
type Message = {
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

// Define document state type
type DocumentState = {
  name: string;
  size: number;
  isProcessed: boolean;
}

export default function ChatPage() {
  // Load messages from localStorage on component mount
  const [messages, setMessages] = useState<Message[]>(() => {
    if (typeof window !== 'undefined') {
      const savedMessages = localStorage.getItem('chatMessages');
      return savedMessages ? JSON.parse(savedMessages) : [];
    }
    return [];
  });
  
  // Load document state from localStorage
  const [documentState, setDocumentState] = useState<DocumentState | null>(() => {
    if (typeof window !== 'undefined') {
      const savedDocState = localStorage.getItem('chatDocumentState');
      return savedDocState ? JSON.parse(savedDocState) : null;
    }
    return null;
  });
  
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [document, setDocument] = useState<File | null>(null)
  const [isProcessingDocument, setIsProcessingDocument] = useState(false)
  const [isDocumentProcessed, setIsDocumentProcessed] = useState(
    documentState?.isProcessed || false
  )
  const [processingError, setProcessingError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem('chatMessages', JSON.stringify(messages));
    }
  }, [messages]);
  
  // Save document state to localStorage when it changes
  useEffect(() => {
    if (document) {
      const docState: DocumentState = {
        name: document.name,
        size: document.size,
        isProcessed: isDocumentProcessed
      };
      localStorage.setItem('chatDocumentState', JSON.stringify(docState));
    }
  }, [document, isDocumentProcessed]);

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
      const response = await fetch("/api/doc-chat", {
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

      // Add assistant response to chat
      const assistantMessage: Message = {
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
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
      setDocument(e.target.files[0])
      setIsDocumentProcessed(false)
      setProcessingError(null)
    }
  }

  const processDocument = async () => {
    if (!document) return

    setIsProcessingDocument(true)
    setProcessingError(null)

    try {
      const formData = new FormData()
      formData.append("file", document)

      const response = await fetch("/api/process-document", {
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
          content: `Document "${document.name}" has been processed successfully. You can now ask questions about it.`,
          timestamp: new Date(),
        },
      ])
      
      // Save document state
      const docState: DocumentState = {
        name: document.name,
        size: document.size,
        isProcessed: true
      };
      localStorage.setItem('chatDocumentState', JSON.stringify(docState));
      
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
      setDocument(null);
      setIsDocumentProcessed(false);
      setMessages([]);
      
      // Clear document state from localStorage
      localStorage.removeItem('chatDocumentState');
      localStorage.removeItem('chatMessages');
      
    } catch (error) {
      console.error('Error clearing uploads:', error);
      setProcessingError('Failed to clear uploads');
    }
  }

  // Display document info from localStorage if we don't have an actual File object
  const documentName = document?.name || documentState?.name;
  const documentSize = document?.size || documentState?.size;

  return (
    <div className="flex flex-col h-full bg-background relative">
      <div className="absolute top-4 right-4 z-50">
        <UserButton/>
      </div>
      {/* Document upload area - only show if no document is processed */}
      {!isDocumentProcessed && (
        <div className="border-b py-4">
          <div className="max-w-3xl mx-auto px-4">
            <div className="flex flex-col sm:flex-row items-center gap-4 justify-between">
              <div className="flex-1">
                <h2 className="text-lg font-medium">Document Chat</h2>
                <p className="text-sm text-muted-foreground">Upload a document to start chatting about its contents</p>
              </div>

              <div className="flex gap-2 w-full sm:w-auto">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  className="hidden"
                  accept=".pdf,.txt,.doc,.docx"
                />

                <Button onClick={handleFileUpload} variant="outline" className="flex-1 sm:flex-initial">
                  <Upload className="h-4 w-4 mr-2" />
                  Select Document
                </Button>

                <Button
                  onClick={processDocument}
                  disabled={!document || isProcessingDocument}
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

            {document && !isProcessingDocument && !isDocumentProcessed && (
              <div className="mt-2 text-sm">
                Selected: <span className="font-medium">{document.name}</span> ({(document.size / 1024).toFixed(2)} KB)
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
                        <Markdown>{message.content}</Markdown>
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

