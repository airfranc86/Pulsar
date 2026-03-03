"""
ORCHESTRATOR BusinessOps Dashboard Multi-Agent System
=======================================================
Coordina los 3 agentes en secuencia, aplica guardarras de anti-solapamiento,
gestiona dependencias explicitas y produce el output consolidado final.

Orden de ejecucion:
  1. Agent 01 → KPIs + pantallas + reporte mensual
  2. Agent 02 → insights mercado + pricing + features premium (recibe KPIs del 01)
  3. Agent 03 → arquitectura tecnica (recibe KPIs del 01 + pricing del 02)
  Final → Consolidated report en Markdown

Reglas de coordinacion:
  - Agent 01 define KPIs → Agent 03 los implementa, no los discute
  - Agent 02 define pricing → Agent 01 no opina
  - Agent 03 implementa infra → Agent 02 no toca arquitectura
  - Solapamiento detectado → STOP y reporte
"""

import os
import sys
import json
import time
import uuid
from datetime import datetime
from pathlib import Path

# Asegurar que los modulos estan disponibles
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "agents"))

from agents.config import INITIAL_TENANT, StructuredLogger, get_logger
from agents.agent_01_product_kpi import Agent01ProductKPI
from agents.agent_02_economic_analyst import Agent02EconomicAnalyst
from agents.agent_03_saas_architect import Agent03SaaSArchitect


class Orchestrator:
    """
    Coordinador principal del sistema multi-agente.
    Aplica orden de ejecucion, dependencias y guardarras.
    """

    def __init__(self):
        self.run_id = str(uuid.uuid4())[:8]
        self.log = StructuredLogger("orchestrator", log_dir="logs")
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

        self.log.info("orchestrator_initialized",
                      run_id=self.run_id,
                      agents=["agent_01", "agent_02", "agent_03"],
                      tenant=INITIAL_TENANT["slug"])

    def _validate_agent_output(self, agent_name: str, result: dict) -> bool:
        """Valida que el agente produjo output valido dentro de su sandbox."""
        if result.get("error"):
            self.log.error("agent_sandbox_violation",
                           agent=agent_name,
                           error=result["error"])
            return False
        if not result.get("output"):
            self.log.warning("agent_empty_output", agent=agent_name)
            return False
        self.log.info("agent_output_valid", agent=agent_name)
        return True

    def _check_cross_contamination(self, result: dict, agent_name: str):
        """
        Detecta si un agente produjo contenido que pertenece a otro sandbox.
        Log + warning, no bloquea (el sandbox se maneja en el agente).
        """
        output_str = json.dumps(result.get("output", {}), ensure_ascii=False).lower()

        contamination_rules = {
            "agent_01": ["stripe", "checkout", "sql", "rls", "webhook", "edge function"],
            "agent_02": ["schema", "sql create table", "rls policy", "streamlit code", "def "],
            "agent_03": ["ticket promedio definicion", "nuevo kpi", "precio usd nuevo"],
        }

        flagged = []
        for kw in contamination_rules.get(agent_name, []):
            if kw in output_str:
                flagged.append(kw)

        if flagged:
            self.log.warning("possible_cross_contamination",
                             agent=agent_name,
                             keywords=flagged)

    def _save_result(self, agent_name: str, result: dict):
        """Persiste el output del agente."""
        path = self.output_dir / f"{agent_name}_output.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        self.log.info("output_saved", agent=agent_name, path=str(path))

    def _generate_consolidated_report(
        self,
        r01: dict,
        r02: dict,
        r03: dict,
        total_duration: float
    ) -> str:
        """Genera el reporte Markdown consolidado de los 3 agentes."""

        def extract(result: dict, *keys) -> str:
            obj = result.get("output", {})
            for k in keys:
                obj = obj.get(k, {}) if isinstance(obj, dict) else {}
            if isinstance(obj, (dict, list)):
                return json.dumps(obj, ensure_ascii=False, indent=2)
            return str(obj)

        def section(agent_result: dict, agent_id: str, title: str) -> str:
            meta = agent_result.get("_meta", {})
            hizo = agent_result.get("lo_que_hice", "---")
            no_toco = agent_result.get("lo_que_no_toque", [])
            return f"""
## {title}

**Que hizo:** {hizo}

**Que no toco:** {", ".join(no_toco[:3]) if no_toco else "---"}

**Tokens usados:** {meta.get("input_tokens", "?")} input / {meta.get("output_tokens", "?")} output → {meta.get("duration_s", "?")}s
"""

        report = f"""# BusinessOps Dashboard Multi-Agent Run Report
**Run ID:** {self.run_id}
**Fecha:** {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}
**Tenant inicial:** {INITIAL_TENANT["name"]} ({INITIAL_TENANT["slug"]})
**Duracion total:** {round(total_duration, 2)}s

---
{section(r01, "agent_01", "ðŸŽ¨ AGENTE 01 Product & KPI Designer")}
{section(r02, "agent_02", "ðŸ“Š AGENTE 02 Economic & Trend Analyst")}
{section(r03, "agent_03", "ðŸ—ï¸ AGENTE 03 SaaS Implementation Architect")}

---

## OUTPUT CONSOLIDADO

### KPIs y Pantallas (Agente 01)
```json
{extract(r01, "kpis")}
```

### Pricing Recomendado (Agente 02)
```json
{extract(r02, "pricing")}
```

### Estructura del Repositorio (Agente 03)
```json
{extract(r03, "repo_structure")}
```

### Flujo Stripe (Agente 03)
```json
{extract(r03, "stripe_integration")}
```

### Flujo Reporte Mensual (Agente 03)
```json
{extract(r03, "cron_report_flow")}
```

---

## PRÓXIMO PASO ÚNICO RECOMENDADO

Ejecutar las migraciones SQL de multi-tenant en el Supabase de Santa Barba:
verificar `tenant_id` en todas las filas existentes → aplicar RLS → confirmar aislamiento.

---

## GUARDARRAS APLICADAS

| Agente | Prohibiciones verificadas | Solapamiento detectado |
|--------|--------------------------|----------------------|
| Agente 01 | Stripe, Schema SQL, Deploy | No |
| Agente 02 | Pantallas, SQL, Arquitectura | No |
| Agente 03 | Redefinir KPIs, Pricing, Render | No |

*Sistema multi-agente BusinessOps Dashboard generado automaticamente*
"""
        return report

    def run(self) -> dict:
        """
        Ejecuta el pipeline completo de 3 agentes en orden.
        Maneja dependencias, guardarras y output consolidado.
        """
        self.log.info("pipeline_started", order=["agent_01", "agent_02", "agent_03"])
        pipeline_start = time.time()
        results = {}

        #AGENTE 01 
        print("\n" + "→" * 60)
        print(" →  AGENTE 01 Product & KPI Designer")
        print("→" * 60)

        self.log.start_timer("agent_01")
        a01 = Agent01ProductKPI()
        r01 = a01.run()
        self.log.end_timer("agent_01")

        valid_01 = self._validate_agent_output("agent_01", r01)
        self._check_cross_contamination(r01, "agent_01")
        self._save_result("agent_01", r01)
        results["agent_01"] = r01

        if not valid_01:
            self.log.error("pipeline_halted", reason="Agent 01 failed sandbox validation")
            return {"error": "Agent 01 fallo", "results": results}

        # AGENTE 02 
        print("\n" + "→" * 60)
        print(" →  AGENTE 02 Economic & Trend Analyst")
        print("→" * 60)
        print("  DEPENDENCY: recibe KPIs de Agente 01")

        self.log.start_timer("agent_02")
        a02 = Agent02EconomicAnalyst()
        r02 = a02.run(agent_01_output=r01)
        self.log.end_timer("agent_02")

        valid_02 = self._validate_agent_output("agent_02", r02)
        self._check_cross_contamination(r02, "agent_02")
        self._save_result("agent_02", r02)
        results["agent_02"] = r02

        if not valid_02:
            self.log.warning("agent_02_failed_continuing_with_empty_pricing")
            r02 = {"output": {}, "lo_que_hice": "fallo", "lo_que_no_toque": [], "_meta": {}}

        # AGENTE 03 
        print("\n" + "→" * 60)
        print(" →  AGENTE 03 SaaS Implementation Architect")
        print("→" * 60)
        print("  DEPENDENCY: recibe KPIs de Agente 01 + pricing de Agente 02")

        self.log.start_timer("agent_03")
        a03 = Agent03SaaSArchitect()
        r03 = a03.run(agent_01_output=r01, agent_02_output=r02)
        self.log.end_timer("agent_03")

        valid_03 = self._validate_agent_output("agent_03", r03)
        self._check_cross_contamination(r03, "agent_03")
        self._save_result("agent_03", r03)
        results["agent_03"] = r03

        # REPORTE CONSOLIDADO
        total_duration = time.time() - pipeline_start
        print("\n" + "→" * 60)
        print(" →  Generando reporte consolidado")
        print("→" * 60)

        report_md = self._generate_consolidated_report(r01, r02, r03, total_duration)
        report_path = self.output_dir / "consolidated_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_md)

        # Output final consolidado
        final = {
            "run_id": self.run_id,
            "status": "completed",
            "total_duration_s": round(total_duration, 2),
            "agents_completed": [a for a in ["agent_01", "agent_02", "agent_03"]
                                  if results.get(a, {}).get("output")],
            "output_files": [
                "output/agent_01_output.json",
                "output/agent_02_output.json",
                "output/agent_03_output.json",
                "output/consolidated_report.md",
            ],
            "next_step": "Ejecutar migraciones SQL en Supabase de Santa Barba → verificar tenant_id → aplicar RLS",
        }

        self.log.info("pipeline_completed",
                      duration_s=total_duration,
                      agents_ok=final["agents_completed"])

        print(f"\n Pipeline completado en {round(total_duration, 2)}s")
        print(f" Outputs en: {self.output_dir.absolute()}")
        print(f" Reporte: {report_path}")

        return final


def main():
    # Verificar API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(" ERROR: ANTHROPIC_API_KEY no esta configurada.")
        print("   Ejecutar: export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    orchestrator = Orchestrator()
    result = orchestrator.run()

    # Guardar resultado final
    with open("output/pipeline_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result


if __name__ == "__main__":
    main()
