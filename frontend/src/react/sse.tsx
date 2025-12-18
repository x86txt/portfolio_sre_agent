import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

import { streamUrl } from "./api";

type SseContextValue = {
  revision: number;
  connected: boolean;
};

const SseContext = createContext<SseContextValue>({ revision: 0, connected: false });

export function SseProvider({ children }: { children: React.ReactNode }) {
  const [revision, setRevision] = useState(0);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const url = streamUrl();
    const es = new EventSource(url);

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);

    const bump = () => setRevision((r) => r + 1);
    es.addEventListener("incident_updated", bump as any);
    es.addEventListener("alert_ingested", bump as any);

    return () => es.close();
  }, []);

  const value = useMemo(() => ({ revision, connected }), [revision, connected]);
  return <SseContext.Provider value={value}>{children}</SseContext.Provider>;
}

export function useSseRevision() {
  return useContext(SseContext);
}


