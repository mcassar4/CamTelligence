import { useQuery } from "@tanstack/react-query";
import { fetchRecentPersons, fetchRecentVehicles, getMediaUrl } from "../api/client";

export function LiveEvents() {
  const persons = useQuery(["persons"], () => fetchRecentPersons(8), { refetchInterval: 4000 });
  const vehicles = useQuery(["vehicles"], () => fetchRecentVehicles(8), { refetchInterval: 5000 });

  return (
    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
      {persons.data?.map((person) => {
        const cropUrl = getMediaUrl(person.crop_asset);
        return (
          <div key={person.id} className="card">
            <div className="toolbar">
              <span className="badge">Person</span>
              <span className="pill">{person.camera}</span>
            </div>
            {cropUrl ? (
              <img src={cropUrl} alt={`Person capture from ${person.camera}`} className="media-preview" loading="lazy" />
            ) : (
              <div className="media-placeholder">No crop available</div>
            )}
            <div style={{ fontWeight: 700 }}>Person detected</div>
            <div style={{ opacity: 0.7, fontSize: 12 }}>{new Date(person.occurred_at).toLocaleString()}</div>
          </div>
        );
      })}
      {vehicles.data?.map((vehicle) => {
        const cropUrl = getMediaUrl(vehicle.crop_asset);
        return (
          <div key={vehicle.id} className="card">
            <div className="toolbar">
              <span className="badge" style={{ background: "#f97316", color: "#0b1021" }}>
                Vehicle
              </span>
              <span className="pill">{vehicle.camera}</span>
            </div>
            {cropUrl ? (
              <img src={cropUrl} alt={`Vehicle capture from ${vehicle.camera}`} className="media-preview" loading="lazy" />
            ) : (
              <div className="media-placeholder">No crop available</div>
            )}
            <div style={{ fontWeight: 700 }}>Vehicle detected</div>
            <div style={{ opacity: 0.7, fontSize: 12 }}>{new Date(vehicle.occurred_at).toLocaleString()}</div>
          </div>
        );
      })}
    </div>
  );
}
