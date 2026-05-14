# Changelog

## [0.99.0] - 2026-05-14

- Added "Conexões IA" dialog to connect/configure ChatGPT/OpenAI and Claude from the GUI.
- The "Configuração mínima recomendada" card is now actionable: inline fix buttons,
  "Configurar ChatGPT/OpenAI", "Configurar Claude", "Testar conexão" and "Abrir diagnóstico".
- "Concluir configuração" now requires the mandatory items to be OK.
- Added AIConnectionService, EnvConfigService (backed-up .env writes + .gitignore guard),
  ClaudeExecutorDetector and OpenAIConnectionTester.
- Build version label shown in the About screen and window title.
- Fixed cross-platform pytest temp handling (macOS/Windows).

## [0.2.0] - 2026-04-14

- Release foundation for the desktop product lifecycle.
- Added unified version and update configuration flow.
- Added About and Updates surfaces in the desktop UX.
- Added release packaging, installer scaffolding and delivery documentation.

## [0.1.0] - 2026-04-13

- Initial desktop workflow with Command Center, runs, checkpoints and onboarding.