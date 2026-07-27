import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

/** Encapsula a integração com a API: health check inicial e
 *  execução/persistência de análises do consultor. */
export function useApiConnection() {
  const [status, setStatus] = useState("API: verificando");
  const [lastAnalysisId, setLastAnalysisId] = useState(null);

  useEffect(() => {
    api.health()
      .then((d) => setStatus(`API: ${d.status} • v${d.version}`))
      .catch(() => setStatus("API: offline/local"));
  }, []);

  const runAnalysis = useCallback(async (payload) => {
    try {
      const data = await api.analyze({ ...payload, persist: true });
      const aid = data.analysis_id || null;
      setLastAnalysisId(aid);
      setStatus(`API: ok • análise #${aid ? aid.slice(0, 8) : "-"}`);
      return data;
    } catch (err) {
      setStatus("API: offline/local");
      if (process.env.NODE_ENV !== "production") {
        // dev-only: ajuda no debug de integração; nunca chega à produção
        console.warn("Falha ao persistir análise:", err);
      }
      return null;
    }
  }, []);

  return { status, lastAnalysisId, runAnalysis };
}
