# 01 — Bootstrap the installable skill and diagnostic CLI

**What to build:** Deliver a self-contained `inspect-powerpoint-natively` skill and an installable `powerpoint-native-render` CLI whose diagnostic command tells an agent whether the local machine can attempt the native render gate. The result must be machine-readable and useful before any presentation is opened.

**Blocked by:** None — can start immediately

**Status:** resolved

- [x] Installing the CLI from the skill directory exposes the documented command without depending on repository-root files.
- [x] The diagnostic command emits one versioned JSON object, uses stable success and failure exit codes, and reports platform, PowerPoint, Python, PDF runtime, and automation prerequisites without opening a presentation.
- [x] macOS, Windows, Linux, missing-PowerPoint, and missing-dependency outcomes are covered through black-box or adapter-level tests.
- [x] The skill frontmatter passes validation and advertises the five approved invocation branches without duplicating synonyms.

## Answer

Added the independently installable `inspect-powerpoint-natively` skill and its skill-local `powerpoint-native-render` Python package. The `doctor` command now emits schema-versioned JSON with stable exit behavior, platform-specific discovery, actionable repair guidance, and an explicit `unverified` state for automation permission that a non-invasive diagnostic cannot prove. The package discovers PowerPoint through COM registration on Windows and standard or Spotlight-discovered application locations on macOS without opening a presentation.

Validated the result with 11 unit and black-box tests, Python 3.9 mypy, bytecode compilation, the standard skill validator, and a live diagnostic on macOS. Ticket 02 is now the next unblocked implementation frontier.
