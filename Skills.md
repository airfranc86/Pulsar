# Skills – Catálogo general

Referencia de skills para agentes de IA (Cursor, Claude Code, etc.) en el monorepo. Incluye las instaladas, las usadas en flujos y dónde buscar más.

---

## 1. Skills instaladas

| Skill | Origen | Descripción |
|-------|--------|-------------|
| **ui-ux-pro-max** | nextlevelbuilder | Guía de diseño para web y móvil: estilos, paletas, tipografía, UX/UI y reglas por stack (React, Tailwind, Next.js, etc.). |
| **brainstorming** | obra/superpowers | Convierte ideas en diseños y especificaciones estructuradas mediante diálogo colaborativo; preguntas paso a paso antes de proponer arquitectura. |
| **frontend-design** | anthropics | Interfaces frontend distintivas y listas para producción; evita diseños genéricos o "AI slop". |
| **fastapi-python** | mindrally | Experto FastAPI/Python: programación funcional y declarativa, modularización, patrón RORO. |
| **fastapi-templates** | wshobson | Estructuras y plantillas FastAPI listas para producción: async, inyección de dependencias, BD (PostgreSQL, MongoDB), testing. |
| **find-skills** | Vercel Labs | Meta-skill: busca e instala otras skills desde el catálogo cuando el agente detecta que las necesitas. |
| **skill-creator** | (oficial) | Automatización y validación para crear skills propias desde cero: plantilla base y metadatos. |
|  |  |  | <!-- Deja este campo vacío para cargar skills nuevas manualmente -->
---

## 2. Skills secundarias (flujos de trabajo)

Mencionadas en planes y flujos; no necesariamente instaladas en el entorno.

| Skill | Uso |
|-------|-----|
| **writing-plans** | Obligatoria después de brainstorming para generar un plan de desarrollo detallado. |
| **elements-of-style:writing-clearly-and-concisely** | Documentación clara y concisa (diseño, técnico, RFC). |
| **mcp-builder** | Construcción e implementación de servidores MCP (Model Context Protocol). |

---

## 3. Comandos de instalación

### Skills instaladas

```bash
# UI/UX
npx skills add https://github.com/nextlevelbuilder/ui-ux-pro-max-skill --skill ui-ux-pro-max

# Clarificación y planificación
npx skills add https://github.com/obra/superpowers --skill brainstorming

# Frontend
npx skills add https://github.com/anthropics/skills --skill frontend-design

# Backend FastAPI
npx skills add https://github.com/mindrally/skills --skill fastapi-python
npx skills add https://github.com/wshobson/agents --skill fastapi-templates

# Meta-skills
# find-skills: buscar e instalar otras skills (consultar documentación del paquete)
# skill-creator: npx skills init nombre-de-tu-skill
```

### Búsqueda e inicialización

```bash
# Buscar skills en el catálogo
npx skills find [query]

# Crear una skill nueva
npx skills init nombre-de-tu-skill
```

---

## 4. Colecciones y repositorios

| Recurso | Descripción |
|---------|-------------|
| **Anthropic Skills** (anthropics/skills) | Catálogo oficial: diseño, desarrollo, comunicación, etc. |
| **awesome-claude-skills** (ComposioHQ) | Directorio curado de skills Claude (investigación, escritura, optimización, etc.). |
| **OpenAI Skills** (openai/skills) | Catálogo OpenAI para capacidades extensibles (p. ej. Codex). |
| **claude-skills** (alirezarezvani/claude-skills) | Colección comunitaria: comandos, sub-agentes, casos de uso reales. |

---

## 5. Uso en el proyecto

- **Diseño y frontend:** ui-ux-pro-max + frontend-design (Fase 3 del ciclo de desarrollo).
- **Clarificación y planificación:** brainstorming → writing-plans.
- **Backend:** fastapi-templates + fastapi-python.
- **Extensión:** find-skills para descubrir skills; skill-creator para crear propias; mcp-builder si se implementan servidores MCP.

Detalle de fases y flujo en: `UX Pro Max - Design Intelligence.md`.
