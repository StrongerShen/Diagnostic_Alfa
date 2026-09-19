# Gemini Agy CLI 指南 (GEMINI.md)

本專案遵循統一的 AI Coding Agent 規範。詳細架構、雙網卡隔離原則、臺灣正體中文規範與開發指令，請參閱：
👉 **[AGENTS.md](./AGENTS.md)**

### 快速注意事項 (Gemini Agy CLI)
1. **語言規範**：100% 臺灣正體中文（zh-TW），嚴禁中國大陸用語。
2. **網路安全**：主力對外網卡 `wlxd03745e1db0d` 絕不可更動；ALFA 網卡為 `wlx00c0cabb0b45`。
3. **隱私政策**：去識別化，禁止提交真實密碼、私有 SSID 或硬體 MAC。
4. **專屬技能**：專案技能存放於 `.agents/skills/`，可自動發現或直接引用。
