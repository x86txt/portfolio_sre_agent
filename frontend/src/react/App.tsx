import React, { useEffect } from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";

import { Button } from "../components/ui/button";
import { SseProvider, useSseRevision } from "./sse";
import { IncidentDetailPage } from "./pages/IncidentDetailPage";
import { IncidentsPage } from "./pages/IncidentsPage";

function Header() {
  const { connected } = useSseRevision();
  return (
    <header className="sticky top-0 z-50 border-b bg-background/70 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
        <div className="flex items-center gap-3">
          <Link to="/" className="text-lg font-semibold">
            <span className="text-primary">ai</span>Triage
          </Link>
          <span className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-400" : "bg-muted-foreground/60"}`} />
            <span>{connected ? "Live" : "Offline"}</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const root = document.documentElement;
              root.classList.toggle("dark");
              const isDark = root.classList.contains("dark");
              try {
                localStorage.setItem("theme", isDark ? "dark" : "light");
              } catch {
                // ignore
              }
            }}
          >
            Theme
          </Button>
        </div>
      </div>
    </header>
  );
}

export default function App() {
  useEffect(() => {
    try {
      const theme = localStorage.getItem("theme");
      if (theme === "light") document.documentElement.classList.remove("dark");
      if (theme === "dark") document.documentElement.classList.add("dark");
    } catch {
      // ignore
    }
  }, []);

  return (
    <SseProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-background">
          <Header />
          <main className="mx-auto max-w-6xl px-6 py-6">
            <Routes>
              <Route path="/" element={<IncidentsPage />} />
              <Route path="/incidents/:id" element={<IncidentDetailPage />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </SseProvider>
  );
}


