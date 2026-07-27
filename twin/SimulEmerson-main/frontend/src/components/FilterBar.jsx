import React from "react";
import { parseNum } from "@/calculations";
import { WELLS_LIST, PAIRS_LIST } from "@/lib/constants";

export default function FilterBar({ input, setInput, onRun }) {
  const upd = (k, v) => setInput((s) => ({ ...s, [k]: v }));
  return (
    <section className="filter-bar panel" data-testid="filter-bar">
      <div className="field">
        <label htmlFor="well">Campo / Poço</label>
        <select id="well" data-testid="input-well" value={input.well} onChange={(e) => upd("well", e.target.value)}>
          {WELLS_LIST.map((w) => <option key={w}>{w}</option>)}
        </select>
      </div>
      <div className="field wide">
        <label htmlFor="windowLabel">Janela</label>
        <input id="windowLabel" data-testid="input-windowLabel" value={input.windowLabel} onChange={(e) => upd("windowLabel", e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="pressure">P (barg)</label>
        <input id="pressure" data-testid="input-pressure" inputMode="decimal" value={String(input.pressure).replace(".", ",")} onChange={(e) => upd("pressure", parseNum(e.target.value))} />
      </div>
      <div className="field">
        <label htmlFor="temperature">T (°C)</label>
        <input id="temperature" data-testid="input-temperature" inputMode="decimal" value={String(input.temperature).replace(".", ",")} onChange={(e) => upd("temperature", parseNum(e.target.value))} />
      </div>
      <div className="field">
        <label htmlFor="qo">Qo (m³/d)</label>
        <input id="qo" data-testid="input-qo" inputMode="decimal" value={String(input.qo).replace(".", ",")} onChange={(e) => upd("qo", parseNum(e.target.value))} />
      </div>
      <div className="field">
        <label htmlFor="qw">Qw (m³/d)</label>
        <input id="qw" data-testid="input-qw" inputMode="decimal" value={String(input.qw).replace(".", ",")} onChange={(e) => upd("qw", parseNum(e.target.value))} />
      </div>
      <div className="field">
        <label htmlFor="qg">Qg (Sm³/d)</label>
        <input id="qg" data-testid="input-qg" inputMode="decimal" value={String(input.qg).replace(".", ",")} onChange={(e) => upd("qg", parseNum(e.target.value))} />
      </div>
      <div className="field">
        <label htmlFor="gasLift">Gas Lift (Sm³/d)</label>
        <input id="gasLift" data-testid="input-gasLift" inputMode="decimal" value={String(input.gasLift).replace(".", ",")} onChange={(e) => upd("gasLift", parseNum(e.target.value))} />
      </div>
      <div className="field">
        <label htmlFor="comparisonPair">Par de comparação</label>
        <select id="comparisonPair" data-testid="input-comparisonPair" value={input.comparisonPair} onChange={(e) => upd("comparisonPair", e.target.value)}>
          {PAIRS_LIST.map((p) => <option key={p}>{p}</option>)}
        </select>
      </div>
      <button type="button" className="primary-button" data-testid="run-analysis" onClick={onRun}>
        ↻ Atualizar Análise
      </button>
    </section>
  );
}
