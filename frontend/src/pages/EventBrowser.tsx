import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { filterEvents } from "../api/client";

export function EventBrowser() {
  const [camera, setCamera] = useState("");
  const [type, setType] = useState("");
  const [result, setResult] = useState<{ person_events: any[]; vehicle_events: any[] } | null>(null);
  const runFilter = useMutation(filterEvents, {
    onSuccess: (data) => setResult(data),
  });

  return (
    <div className="grid">
      <div className="card">
        <div style={{ fontWeight: 700, marginBottom: 12 }}>Filter events</div>
        <div className="toolbar">
          <input placeholder="Camera (optional)" value={camera} onChange={(e) => setCamera(e.target.value)} />
          <select value={type} onChange={(e) => setType(e.target.value)}>
            <option value="">Any type</option>
            <option value="person">Persons</option>
            <option value="vehicle">Vehicles</option>
          </select>
          <button onClick={() => runFilter.mutate({ camera: camera || undefined, event_type: type || undefined })}>Run</button>
        </div>
      </div>
      <div className="card">
        <div style={{ fontWeight: 700, marginBottom: 12 }}>Results</div>
        {result ? (
          <div className="list">
            {result.person_events.map((e) => (
              <div key={e.id} className="pill">
                Person • {e.camera} • {new Date(e.occurred_at).toLocaleString()}
              </div>
            ))}
            {result.vehicle_events.map((e) => (
              <div key={e.id} className="pill">
                Vehicle • {e.camera} • {new Date(e.occurred_at).toLocaleString()}
              </div>
            ))}
          </div>
        ) : (
          <div style={{ opacity: 0.6 }}>Run a query to see events.</div>
        )}
      </div>
    </div>
  );
}
