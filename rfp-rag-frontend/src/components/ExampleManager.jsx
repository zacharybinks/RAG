import React, { useState, useEffect } from "react";
import api from "../services/api";

export default function ExampleManager({ onClose }) {
  const [examples, setExamples] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadMeta, setUploadMeta] = useState({
    title: "",
    client_type: "",
    domain: "",
    contract_vehicle: "",
    complexity_tier: ""
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    loadExamples();
  }, []);

  const loadExamples = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/examples");
      setExamples(data.examples || []);
    } catch (err) {
      setError("Failed to load examples: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e) => {
    setSelectedFiles(Array.from(e.target.files));
  };

  const uploadExamples = async () => {
    if (!selectedFiles.length) {
      setError("Please select files to upload");
      return;
    }

    setUploading(true);
    setError("");
    setSuccess("");

    try {
      const formData = new FormData();
      selectedFiles.forEach(file => formData.append("files", file));
      
      // Add metadata
      Object.entries(uploadMeta).forEach(([key, value]) => {
        if (value.trim()) formData.append(key, value.trim());
      });

      await api.post("/examples/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      setSuccess("Examples uploaded successfully!");
      setSelectedFiles([]);
      setUploadMeta({
        title: "",
        client_type: "",
        domain: "",
        contract_vehicle: "",
        complexity_tier: ""
      });
      loadExamples();
    } catch (err) {
      setError("Upload failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
    }
  };

  const deleteExample = async (exampleId) => {
    if (!window.confirm("Are you sure you want to delete this example?")) return;

    try {
      await api.delete(`/examples/${exampleId}`);
      setSuccess("Example deleted successfully!");
      loadExamples();
    } catch (err) {
      setError("Delete failed: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div style={{
      position: "fixed",
      inset: 0,
      background: "rgba(0,0,0,0.5)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 9999
    }}>
      <div style={{
        background: "#fff",
        width: "min(1200px, 95vw)",
        maxHeight: "90vh",
        overflow: "auto",
        borderRadius: 10,
        padding: 24
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <h2 style={{ margin: 0 }}>Example Management</h2>
          <button onClick={onClose} style={{ padding: "8px 16px" }}>Close</button>
        </div>

        {error && (
          <div style={{ background: "#f8d7da", color: "#721c24", padding: 12, borderRadius: 4, marginBottom: 16 }}>
            {error}
          </div>
        )}

        {success && (
          <div style={{ background: "#d4edda", color: "#155724", padding: 12, borderRadius: 4, marginBottom: 16 }}>
            {success}
          </div>
        )}

        {/* Upload Section */}
        <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16, marginBottom: 24 }}>
          <h3 style={{ marginTop: 0 }}>Upload New Examples</h3>
          
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
            <input
              type="text"
              placeholder="Title (optional)"
              value={uploadMeta.title}
              onChange={(e) => setUploadMeta(prev => ({ ...prev, title: e.target.value }))}
              style={{ padding: 8, border: "1px solid #ddd", borderRadius: 4 }}
            />
            <input
              type="text"
              placeholder="Client Type (e.g., DoD, Commercial)"
              value={uploadMeta.client_type}
              onChange={(e) => setUploadMeta(prev => ({ ...prev, client_type: e.target.value }))}
              style={{ padding: 8, border: "1px solid #ddd", borderRadius: 4 }}
            />
            <input
              type="text"
              placeholder="Domain (e.g., Cybersecurity, IT)"
              value={uploadMeta.domain}
              onChange={(e) => setUploadMeta(prev => ({ ...prev, domain: e.target.value }))}
              style={{ padding: 8, border: "1px solid #ddd", borderRadius: 4 }}
            />
            <input
              type="text"
              placeholder="Contract Vehicle (e.g., SEWP, GSA)"
              value={uploadMeta.contract_vehicle}
              onChange={(e) => setUploadMeta(prev => ({ ...prev, contract_vehicle: e.target.value }))}
              style={{ padding: 8, border: "1px solid #ddd", borderRadius: 4 }}
            />
            <select
              value={uploadMeta.complexity_tier}
              onChange={(e) => setUploadMeta(prev => ({ ...prev, complexity_tier: e.target.value }))}
              style={{ padding: 8, border: "1px solid #ddd", borderRadius: 4 }}
            >
              <option value="">Select Complexity Tier</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          <div style={{ marginBottom: 16 }}>
            <input
              type="file"
              multiple
              accept=".pdf,.docx,.doc"
              onChange={handleFileSelect}
              style={{ marginBottom: 8 }}
            />
            {selectedFiles.length > 0 && (
              <div style={{ fontSize: "14px", color: "#666" }}>
                Selected: {selectedFiles.map(f => f.name).join(", ")}
              </div>
            )}
          </div>

          <button
            onClick={uploadExamples}
            disabled={uploading || !selectedFiles.length}
            style={{
              padding: "10px 20px",
              background: uploading ? "#6c757d" : "#007bff",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: uploading ? "not-allowed" : "pointer"
            }}
          >
            {uploading ? "Uploading..." : "Upload Examples"}
          </button>
        </div>

        {/* Examples List */}
        <div>
          <h3>Existing Examples ({examples.length})</h3>
          
          {loading ? (
            <div style={{ textAlign: "center", padding: 40 }}>Loading examples...</div>
          ) : examples.length === 0 ? (
            <div style={{ textAlign: "center", padding: 40, color: "#666" }}>
              No examples uploaded yet. Upload some examples to get started.
            </div>
          ) : (
            <div style={{ display: "grid", gap: 12 }}>
              {examples.map((example) => (
                <div key={example.id} style={{
                  border: "1px solid #ddd",
                  borderRadius: 8,
                  padding: 16,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center"
                }}>
                  <div>
                    <h4 style={{ margin: "0 0 8px 0" }}>{example.title}</h4>
                    <div style={{ fontSize: "14px", color: "#666" }}>
                      <span>Client: {example.client_type || "—"}</span> • 
                      <span> Domain: {example.domain || "—"}</span> • 
                      <span> Vehicle: {example.contract_vehicle || "—"}</span> • 
                      <span> Tier: {example.complexity_tier || "—"}</span>
                    </div>
                    <div style={{ fontSize: "12px", color: "#999", marginTop: 4 }}>
                      {example.sections_count} sections • Status: {example.ingest_status} • 
                      Created: {example.created_at ? new Date(example.created_at).toLocaleDateString() : "—"}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      onClick={() => deleteExample(example.id)}
                      style={{
                        padding: "6px 12px",
                        background: "#dc3545",
                        color: "white",
                        border: "none",
                        borderRadius: 4,
                        cursor: "pointer"
                      }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
