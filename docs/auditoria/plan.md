# Plan de Auditoría Técnica — JinxAS

## 1. Alcance
Auditoría técnica independiente del proyecto JinxAS v0.5.0 en modo A
(auditoría + pruebas + remediación).

**Sistema auditado:** Asistente de voz local para Windows.
**Hash base:** `a197ee99de2aa8b4e3d65ceb7994c7fa896a6e62`
**Rama de trabajo:** `auditoria-profunda` (desde main)

## 2. Criterios de evaluación
- C1: Documentación del proyecto (README, CHANGELOG, ARQUITECTURA, BASELINE, TROUBLESHOOTING)
- C2: ISO/IEC 25010 (funcionalidad, eficiencia, usabilidad, fiabilidad, seguridad, mantenibilidad, portabilidad)
- C3: OWASP Top 10 for LLM Applications con mapeo CWE
- C4: Empaquetado Python (PEP 517/621)
- C5: Criterios de aceptación propios (BASELINE.md)

## 3. Entorno de ejecución
- SO: Windows NT 10.0.26300.0
- Python: 3.12.10
- Rama: `auditoria-profunda`
- venv existente con 92 paquetes instalados

## 4. Herramientas de análisis
- pytest 9.1.1 + pytest-cov 7.1.0
- ruff 0.16.10
- bandit 1.9.4
- vulture 2.16
- pip-audit 2.10.1
- python -m build 1.6.1

## 5. Limitaciones
- No se verifican medianas de latencia en vivo (requiere sesión de voz)
- No se verifica la calidad de modelos de terceros
- No se ejecuta eval_tools.py (requiere Ollama activo)
- Edge-TTS depende de red y no se prueba
- No se lee ni modifica `.env`, bóveda ni `logs/`

## 6. Zona protegida
- `percepcion.py`: `esperar_palabra_activacion()`, `coincide_wakeword()`,
  umbral de fuzzy matching y `VARIANTES_WAKEWORD` son de solo lectura.
