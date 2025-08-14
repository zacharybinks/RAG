import React, { useState } from "react";

export default function SectionInstructionCard({ instruction }) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (!instruction) return null;
  const {
    title, section_key, purpose, must_include = [], micro_outline = [],
    tone_rules = [], win_themes = [], evidence_prompts = [],
    compliance_checklist = [], length_hint_words = {}, acceptance_criteria = [], gaps = []
  } = instruction;

  return (
    <div style={{
      border:"1px solid #ddd",
      borderRadius:8,
      padding:16,
      marginBottom:16,
      textAlign: "left"
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <h4 style={{margin:0}}>{title} <small style={{color:"#666"}}>({section_key})</small></h4>
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          style={{
            background: "none",
            border: "1px solid #ddd",
            borderRadius: 4,
            padding: "4px 8px",
            cursor: "pointer",
            fontSize: "12px"
          }}
        >
          {isCollapsed ? "Show" : "Hide"}
        </button>
      </div>

      {!isCollapsed && (
        <div style={{ textAlign: "left" }}>
          {purpose && (<p><strong>Purpose:</strong> {purpose}</p>)}
          {!!micro_outline.length && (
            <>
              <strong>Micro-outline:</strong>
              <ul style={{ textAlign: "left", paddingLeft: 20 }}>
                {micro_outline.map((b,i)=><li key={i}>{b}</li>)}
              </ul>
            </>
          )}
          {!!must_include.length && (
            <>
              <strong>Must include:</strong>
              <ul style={{ textAlign: "left", paddingLeft: 20 }}>
                {must_include.map((b,i)=><li key={i}>{b}</li>)}
              </ul>
            </>
          )}
          {!!compliance_checklist.length && (
            <>
              <strong>Compliance checklist:</strong>
              <ul style={{ textAlign: "left", paddingLeft: 20 }}>
                {compliance_checklist.map((b,i)=><li key={i}>{b}</li>)}
              </ul>
            </>
          )}
          {!!win_themes.length && (<p><strong>Win themes:</strong> {win_themes.join(" · ")}</p>)}
          {!!tone_rules.length && (<p><strong>Tone:</strong> {tone_rules.join(", ")}</p>)}
          {!!evidence_prompts.length && (
            <p><strong>Evidence prompts:</strong> {evidence_prompts.join(" · ")}</p>
          )}
          {length_hint_words?.min && (
            <p><strong>Length hint:</strong> {length_hint_words.min}–{length_hint_words.max || "?"} words</p>
          )}
          {!!acceptance_criteria.length && (
            <>
              <strong>Acceptance criteria:</strong>
              <ul style={{ textAlign: "left", paddingLeft: 20 }}>
                {acceptance_criteria.map((b,i)=><li key={i}>{b}</li>)}
              </ul>
            </>
          )}
          {!!gaps.length && (
            <>
              <strong>Gaps/Uncertainties:</strong>
              <ul style={{ textAlign: "left", paddingLeft: 20 }}>
                {gaps.map((b,i)=><li key={i}>{b}</li>)}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}
