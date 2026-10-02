# Papeles de Trabajo — Auditoría JinxAS

## Registro cronológico

### 2026-10-01 22:50 — Fase 1: Planeación
- `git rev-parse HEAD` → `a197ee99de2aa8b4e3d65ceb7994c7fa896a6e62` (exit 0)
- `git remote -v` → origin https://github.com/DAHL13/JinxAS.git (exit 0)
- `python --version` → Python 3.12.10 (exit 0)
- SO: Microsoft Windows NT 10.0.26300.0
- `git checkout -b auditoria-profunda` → OK (exit 0)
- pip freeze: 92 paquetes instalados

### 2026-10-01 22:54 — Fase 3.1: Pruebas automáticas
- `pytest -q -m "not integration"` → **188 passed** en 0.89s (exit 0)
- `ruff check .` → All checks passed (exit 0)
- `ruff check . --select E402,E741,F401,F841,F541` → **59 errores** (exit 1)
  - F401 (imports no usados): 10 ocurrencias en tests
  - F841 (variables no usadas): 5 en tests
  - E402 (imports no al inicio): 5 en tests
  - E741 (nombres ambiguos): 3 en test_f5_seguridad.py
- `python -m build --wheel` → jinxas-0.5.0-py3-none-any.whl (exit 0)
  - **ui/panel.html NO incluido** → H-001
- `pip check` → No broken requirements found (exit 0)
- `bandit -r jinxas/ -q` → 1 High (SHA1 B324), 14 Low (exit 1)
- `vulture jinxas/ --min-confidence 80` → 4 resultados: 3 imports no usados, 1 variable (exit 1)
- `pip-audit` → 15 vulnerabilidades en pip 25.0.1 y urllib3 2.7.0 (exit 1)
- Búsqueda de secretos en código y git history → **Nada encontrado** (exit 0)

### 2026-10-01 22:57 — Fase 5: Remediación
- H-001 (CRÍTICO): Corregido — ui/panel.html movido a jinxas/ui/
- H-002 (ALTO): Corregido — pywebview fijado, thefuzz añadido
- H-003 (ALTO): Corregido — sys.path eliminado de __init__.py
- H-004 (MEDIO): Corregido — sha1 usedforsecurity=False
- H-005 (MEDIO): Corregido — imports muertos eliminados
- H-006 (MEDIO): Corregido — parámetros de escuchar_y_transcribir
- H-007 (BAJO): Corregido — Python 3.11+ → 3.12+ en BASELINE.md
- H-008 (BAJO): Corregido — num_ctx: 4096 → 2048 en BASELINE.md
- H-013 (BAJO): Corregido — formato de licencia en pyproject.toml
- H-014 (COBERTURA): 16 pruebas nuevas añadidas

### 2026-10-02 08:52 — Fase 6: Reprueba
- `pytest -q -m "not integration"` → **205 passed** en 1.89s (exit 0)
- `ruff check .` → All checks passed (exit 0)
- `python -m build --wheel` → wheel ahora incluye jinxas/ui/panel.html ✅
- `git status` → Limpio (exit 0)
