import React, { useState } from "react";

export default function InstructionEditor({ instruction, onSave, onCancel }) {
  const [editedInstruction, setEditedInstruction] = useState({
    purpose: instruction?.purpose || "",
    micro_outline: instruction?.micro_outline || [],
    must_include: instruction?.must_include || [],
    tone_rules: instruction?.tone_rules || [],
    compliance_items: instruction?.compliance_items || []
  });

  const handleSave = () => {
    onSave(editedInstruction);
  };

  const updateField = (field, value) => {
    setEditedInstruction(prev => ({ ...prev, [field]: value }));
  };

  const updateArrayField = (field, index, value) => {
    setEditedInstruction(prev => ({
      ...prev,
      [field]: prev[field].map((item, i) => i === index ? value : item)
    }));
  };

  const addArrayItem = (field) => {
    setEditedInstruction(prev => ({
      ...prev,
      [field]: [...prev[field], ""]
    }));
  };

  const removeArrayItem = (field, index) => {
    setEditedInstruction(prev => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== index)
    }));
  };

  const renderArrayField = (field, label, placeholder) => (
    <div style={{ marginBottom: 16 }}>
      <label style={{ display: "block", fontWeight: "bold", marginBottom: 8 }}>{label}</label>
      {editedInstruction[field].map((item, index) => (
        <div key={index} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <input
            type="text"
            value={item}
            onChange={(e) => updateArrayField(field, index, e.target.value)}
            placeholder={placeholder}
            style={{ 
              flex: 1, 
              padding: 8, 
              border: "1px solid #ddd", 
              borderRadius: 4 
            }}
          />
          <button
            onClick={() => removeArrayItem(field, index)}
            style={{ 
              padding: "4px 8px", 
              background: "#dc3545", 
              color: "white", 
              border: "none", 
              borderRadius: 4 
            }}
          >
            Remove
          </button>
        </div>
      ))}
      <button
        onClick={() => addArrayItem(field)}
        style={{ 
          padding: "6px 12px", 
          background: "#28a745", 
          color: "white", 
          border: "none", 
          borderRadius: 4 
        }}
      >
        Add {label.slice(0, -1)}
      </button>
    </div>
  );

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
        width: "min(800px, 95vw)",
        maxHeight: "90vh",
        overflow: "auto",
        borderRadius: 10,
        padding: 24
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <h2 style={{ margin: 0 }}>Edit Instruction Sheet</h2>
          <button onClick={onCancel} style={{ padding: "8px 16px" }}>Cancel</button>
        </div>

        <div style={{ display: "grid", gap: 16 }}>
          {/* Purpose */}
          <div>
            <label style={{ display: "block", fontWeight: "bold", marginBottom: 8 }}>Purpose</label>
            <textarea
              value={editedInstruction.purpose}
              onChange={(e) => updateField("purpose", e.target.value)}
              placeholder="What is the purpose of this section?"
              style={{
                width: "100%",
                minHeight: 80,
                padding: 8,
                border: "1px solid #ddd",
                borderRadius: 4,
                resize: "vertical"
              }}
            />
          </div>

          {/* Micro Outline */}
          {renderArrayField("micro_outline", "Micro Outline", "Add outline item...")}

          {/* Must Include */}
          {renderArrayField("must_include", "Must Include", "Add required item...")}

          {/* Tone Rules */}
          {renderArrayField("tone_rules", "Tone Rules", "Add tone rule...")}

          {/* Compliance Items */}
          {renderArrayField("compliance_items", "Compliance Items", "Add compliance item...")}
        </div>

        <div style={{ display: "flex", gap: 12, marginTop: 24, justifyContent: "flex-end" }}>
          <button
            onClick={onCancel}
            style={{
              padding: "10px 20px",
              background: "#6c757d",
              color: "white",
              border: "none",
              borderRadius: 4
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            style={{
              padding: "10px 20px",
              background: "#007bff",
              color: "white",
              border: "none",
              borderRadius: 4
            }}
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}
