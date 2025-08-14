import React, { useEffect, useState } from "react";
import api from "../services/api";   // ✅ relative import

export default function ExamplesPicker({ value = [], onChange }) {
  const [loading, setLoading] = useState(false);
  const [examples, setExamples] = useState([]);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    api.get("/examples")
      .then(({ data }) => mounted && setExamples(data.examples || data || []))
      .finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
  }, []);

  function toggle(id) {
    if (!onChange) return;
    const set = new Set(value);
    set.has(id) ? set.delete(id) : set.add(id);
    onChange(Array.from(set));
  }

  if (loading) return <div>Loading examples…</div>;
  if (!examples.length) return <div>No examples uploaded yet.</div>;

  return (
    <div style={{display:"grid", gap:8}}>
      {examples.map((ex) => {
        const id = ex.id || ex.ID || ex.uuid;
        const checked = value.includes(id);
        return (
          <label key={id} style={{border:"1px solid #e1e1e1", borderRadius:8, padding:10, display:"flex", alignItems:"center", gap:8}}>
            <input type="checkbox" checked={checked} onChange={()=>toggle(id)} />
            <div>
              <div style={{fontWeight:600}}>{ex.title || "Untitled example"}</div>
              <div style={{color:"#666", fontSize:12}}>
                {ex.client_type || "—"} · {ex.domain || "—"} · {ex.contract_vehicle || "—"}
              </div>
            </div>
          </label>
        );
      })}
    </div>
  );
}
