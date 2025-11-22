import { useState } from "react";
import { LiveEvents } from "./pages/LiveEvents";
import { EventBrowser } from "./pages/EventBrowser";
import { Header } from "./components/Header";

type Page = "live" | "events";

export default function App() {
  const [page, setPage] = useState<Page>("live");

  return (
    <div>
      <Header active={page} onNavigate={setPage} />
      <main className="page">
        {page === "live" && <LiveEvents />}
        {page === "events" && <EventBrowser />}
      </main>
    </div>
  );
}
