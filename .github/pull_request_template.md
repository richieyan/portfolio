## Summary
- 

## Checklist (required)
- [ ] I read [docs/PRD.md](docs/PRD.md) and [/.github/copilot-instructions.md](.github/copilot-instructions.md) for this change.
- [ ] Data fetches use the Tushare Python SDK (e.g., `import tushare as ts` with token set); no MCP CLI paths were added.
- [ ] Local-first: reads go to SQLite first; TTL/refresh respected; dedup via unique keys per PRD.
- [ ] Changes are minimal and avoid unrelated refactors or reformatting.
- [ ] Migrations/schema/index changes are documented and safe for existing data files.
- [ ] I avoided overwriting existing logic; risky edits were checked twice.
- [ ] Logging/error handling follows existing patterns.

## Tests
- [ ] Not needed (explain why): 
- [ ] Added/updated tests: 
