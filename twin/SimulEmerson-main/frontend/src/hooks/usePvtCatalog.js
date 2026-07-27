import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

/** Hook que encapsula listagem e criação de amostras PVT. */
export function usePvtCatalog() {
  const [catalog, setCatalog] = useState([]);

  const load = useCallback(() => {
    api.listPVT().then(setCatalog).catch(() => {});
  }, []);

  const create = useCallback(async (payload) => {
    await api.createPVT(payload);
    load();
  }, [load]);

  useEffect(() => { load(); }, [load]);

  return { catalog, load, create };
}
