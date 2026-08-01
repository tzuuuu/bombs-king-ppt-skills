# 01 — Bootstrap the installable skill and diagnostic CLI

**What to build:** Deliver a self-contained `inspect-powerpoint-natively` skill and an installable `powerpoint-native-render` CLI whose diagnostic command tells an agent whether the local machine can attempt the native render gate. The result must be machine-readable and useful before any presentation is opened.

**Blocked by:** None — can start immediately

**Status:** claimed

- [ ] Installing the CLI from the skill directory exposes the documented command without depending on repository-root files.
- [ ] The diagnostic command emits one versioned JSON object, uses stable success and failure exit codes, and reports platform, PowerPoint, Python, PDF runtime, and automation prerequisites without opening a presentation.
- [ ] macOS, Windows, Linux, missing-PowerPoint, and missing-dependency outcomes are covered through black-box or adapter-level tests.
- [ ] The skill frontmatter passes validation and advertises the five approved invocation branches without duplicating synonyms.
