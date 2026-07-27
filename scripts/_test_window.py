"""Quick unit test for test_window_horas feature in calcular_24h."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from recon_engine import calcular_24h, CalcHoraResult, MPFMHoraInput, PVTParams

pvt = PVTParams(bank='B08', tag='MPB-08', fe=1.0, rs=50.0,
                rho_oleo_std=840.0, rho_gas_std=1.2, rho_agua_std=1020.0)

resultados_all_valid   = [CalcHoraResult(hora=h, hora_valida=True)  for h in range(24)]
resultados_2_inv       = [CalcHoraResult(hora=h, hora_valida=(h not in [8, 10])) for h in range(24)]
mpfm_horas             = [MPFMHoraInput(hora=h, oleo_corr_t=8.4, gas_corr_t=1.2, agua_corr_t=0.5) for h in range(24)]

# Test 1 — full 24h, no window param (backward compat)
r1 = calcular_24h(resultados_all_valid, mpfm_horas, pvt)
assert r1.horas_janela == 24,          f"T1 horas_janela: {r1.horas_janela}"
assert r1.horas_validas == 24,         f"T1 horas_validas: {r1.horas_validas}"
assert r1.consolidado_completo == True, f"T1 consolidado: {r1.consolidado_completo}"
assert r1.cobertura_pct == 100.0,      f"T1 cobertura: {r1.cobertura_pct}"
print("PASS Test1 (full 24h, default)      janela=%d validas=%d completo=%s cobertura=%.1f%%" %
      (r1.horas_janela, r1.horas_validas, r1.consolidado_completo, r1.cobertura_pct))

# Test 2 — 8h window (hours 6-13), all valid
r2 = calcular_24h(resultados_all_valid, mpfm_horas, pvt, test_window_horas=list(range(6, 14)))
assert r2.horas_janela == 8,           f"T2 horas_janela: {r2.horas_janela}"
assert r2.horas_validas == 8,          f"T2 horas_validas: {r2.horas_validas}"
assert r2.consolidado_completo == True, f"T2 consolidado: {r2.consolidado_completo}"
assert r2.cobertura_pct == 100.0,      f"T2 cobertura: {r2.cobertura_pct}"
print("PASS Test2 (8h window, all valid)   janela=%d validas=%d completo=%s cobertura=%.1f%%" %
      (r2.horas_janela, r2.horas_validas, r2.consolidado_completo, r2.cobertura_pct))

# Test 3 — 8h window with 2 invalid hours inside (8 and 10)
r3 = calcular_24h(resultados_2_inv, mpfm_horas, pvt, test_window_horas=list(range(6, 14)))
assert r3.horas_janela == 8,            f"T3 horas_janela: {r3.horas_janela}"
assert r3.horas_validas == 6,           f"T3 horas_validas: {r3.horas_validas}"
assert r3.consolidado_completo == False, f"T3 consolidado: {r3.consolidado_completo}"
assert r3.cobertura_pct == 75.0,        f"T3 cobertura: {r3.cobertura_pct}"
qa_cob = [f for f in r3.qa_flags_consolidados if 'cobertura' in f]
assert qa_cob, f"T3 no qa_cobertura flag: {r3.qa_flags_consolidados}"
print("PASS Test3 (8h window, 2 invalid)  janela=%d validas=%d completo=%s cobertura=%.1f%%  qa=%s" %
      (r3.horas_janela, r3.horas_validas, r3.consolidado_completo, r3.cobertura_pct, qa_cob))

# Test 4
window_midnight = list(range(22, 24)) + list(range(0, 6))  # [22,23,0,1,2,3,4,5]
r4 = calcular_24h(resultados_all_valid, mpfm_horas, pvt, test_window_horas=window_midnight)
assert r4.horas_janela == 8,           f"T4 horas_janela: {r4.horas_janela}"
assert r4.horas_validas == 8,          f"T4 horas_validas: {r4.horas_validas}"
assert r4.consolidado_completo == True, f"T4 consolidado: {r4.consolidado_completo}"
print("PASS Test4 (midnight-cross 22→5)   janela=%d validas=%d completo=%s cobertura=%.1f%%" %
      (r4.horas_janela, r4.horas_validas, r4.consolidado_completo, r4.cobertura_pct))

print("\nAll tests PASSED.")
