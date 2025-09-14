import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Terminal, ChevronRight, Home, Book, Wrench, Zap, Shield, FileCode, Search } from "lucide-react";

const sidebarItems = [
  {
    title: "Getting Started",
    items: [
      { href: "/docs", label: "Introduction", icon: Home },
      { href: "/docs/quickstart", label: "Quick Start", icon: Zap },
      { href: "/docs/configuration", label: "Configuration", icon: Wrench },
    ]
  },
  {
    title: "Core Features",
    items: [
      { href: "/docs/repository", label: "Repository Management", icon: FileCode },
      { href: "/docs/symbols", label: "Symbol Extraction", icon: Zap },
      { href: "/docs/search", label: "Code Search", icon: Search },
      { href: "/docs/research", label: "Documentation Research", icon: Book },
    ]
  },
  {
    title: "Reference",
    items: [
      { href: "/docs/api", label: "API Reference", icon: Book },
      { href: "/docs/tools", label: "Available Tools", icon: Wrench },
      { href: "/docs/examples", label: "Examples", icon: FileCode },
      { href: "/docs/system-prompts", label: "System Prompts", icon: Zap },
    ]
  }
];

export default function DocsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-white relative dotted-pattern">
      {/* Top Navigation */}
      <nav className="sticky top-0 z-50 w-full border-b-4 border-black bg-white">
        <div className="container flex h-16 items-center px-4">
          <Link href="/" className="flex items-center space-x-1 sm:space-x-2">
            <Terminal className="h-5 w-5 sm:h-6 sm:w-6 text-primary flex-shrink-0" />
            <span className="font-bold text-sm sm:text-xl whitespace-nowrap">kit-dev for mcp</span>
          </Link>
          <div className="ml-auto flex items-center space-x-1 sm:space-x-3">
            <Button variant="ghost" size="sm" className="px-2 sm:px-4 neo-button" asChild>
              <Link href="/docs">
                <span className="sm:hidden">Docs</span>
                <span className="hidden sm:inline">Documentation</span>
              </Link>
            </Button>
            <Button variant="ghost" size="sm" className="px-2 sm:px-4 neo-button" asChild>
              <Link href="/docs/tools">Tools</Link>
            </Button>
            <Button variant="ghost" size="sm" className="px-2 sm:px-4 neo-button" asChild>
              <Link href="https://github.com/cased/kit">
                <span className="sm:hidden">GitHub</span>
                <span className="hidden sm:inline">GitHub</span>
              </Link>
            </Button>
          </div>
        </div>
      </nav>

      <div className="flex">
        {/* Sidebar */}
        <aside className="hidden md:block w-64 border-r-4 border-black bg-white min-h-[calc(100vh-4rem)] sticky top-16">
          <div className="p-6 space-y-6">
            {sidebarItems.map((section, i) => (
              <div key={i}>
                <h4 className="font-semibold text-sm text-muted-foreground mb-3">
                  {section.title}
                </h4>
                <div className="space-y-1">
                  {section.items.map((item, j) => {
                    const Icon = item.icon;
                    return (
                      <Link
                        key={j}
                        href={item.href}
                        className="flex items-center space-x-2 px-3 py-2 border-2 border-transparent hover:border-black hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] text-sm transition-all"
                      >
                        <Icon className="h-4 w-4 text-muted-foreground" />
                        <span>{item.label}</span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 w-full max-w-full lg:max-w-4xl overflow-x-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}