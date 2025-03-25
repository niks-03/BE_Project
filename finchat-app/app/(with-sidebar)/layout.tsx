// app/(with-sidebar)/layout.tsx
'use client';
import React, { useState } from 'react';
import Link from 'next/link';
import { ThemeProvider } from '@/components/theme-provider';
import { useTheme } from 'next-themes';
import { 
  ChevronLeft,
  ChevronsLeft,
  ChevronsRight, 
  ChevronRight, 
  Home, 
  MessageSquare, 
  Map 
} from 'lucide-react';

export default function WithSidebarLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { theme } = useTheme();

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <div 
        className={`h-full bg-gray-100 dark:bg-transparent dark:border-r-1 transition-all duration-300 ${
          isCollapsed ? "w-20" : "w-64"
        } flex flex-col`}
      >
        <div className="p-4 flex justify-end pr-6 ">
          <button 
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1 rounded-full hover:bg-gray-200 dark:hover:bg-gray-800 dark:text-gray-200"
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? (
              <ChevronsRight size={24} />
            ) : (
              <ChevronsLeft size={24} />
            )}
          </button>
        </div>
        <nav className="flex flex-col gap-2 px-4">
          <Link href="/" className={`p-2 hover:bg-gray-200 dark:hover:bg-gray-900 rounded flex items-center ${isCollapsed ? "justify-center" : ""} dark:text-gray-200`}>
            <Home size={20} />
            {!isCollapsed && <span className="ml-2">Home</span>}
          </Link>
          <Link href="/chat" className={`p-2 hover:bg-gray-200 dark:hover:bg-gray-900 rounded flex items-center ${isCollapsed ? "justify-center" : ""} dark:text-gray-200`}>
            <MessageSquare size={20} />
            {!isCollapsed && <span className="ml-2">Chat</span>}
          </Link>
          <Link href="/visualize" className={`p-2 hover:bg-gray-200 dark:hover:bg-gray-900 rounded flex items-center ${isCollapsed ? "justify-center" : ""} dark:text-gray-200`}>
            <Map size={20} />
            {!isCollapsed && <span className="ml-2">Visualize</span>}
          </Link>
        </nav>
      </div>
      
      {/* Main Content - fixed width to prevent layout shifts */}
      <div className="flex-1 overflow-hidden">
      <ThemeProvider
              attribute="class"
              defaultTheme="system"
              enableSystem
              disableTransitionOnChange
            >
        {children}
        </ThemeProvider>
      </div>
    </div>
  );
}