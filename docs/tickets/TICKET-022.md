# TICKET-022 — Extract nested definitions in tree-sitter chunker

**id:** TICKET-022
**title:** Extract nested definitions in tree-sitter chunker
**status:** OPEN
**priority:** P2
**category:** Parsing/Chunking
**effort:** M
**depends_on:** TICKET-007

## Goal

Walk tree-sitter AST beyond root-level children to extract methods inside classes as individual chunks, improving retrieval precision for class-heavy codebases.

## Acceptance Criteria

- Class methods extracted as individual chunks, not bundled into parent class chunk
- Each method chunk includes context: file_path, language, parent class name, method name
- Class-level code (class body excluding methods) preserved as separate chunk
- Nested classes handled to at least 2 levels deep
- Languages tested: Python, JavaScript/TypeScript, Java, Go
- Existing chunking tests updated; new tests for nested extraction added

## Implementation Notes

Location: `src/airag/chunking/code.py`.

Current behavior: only root-level AST children walked — `class Foo` with 10 methods produces one large chunk, often exceeding token limit.

Approach: recursive walk with depth limit (3–4 levels). For each class/struct/impl node, descend into children and extract function/method nodes.

Context header for method chunks: `file_path | language | class: ClassName | method: method_name`.

Risk: deep nesting in some languages (Rust impl blocks, JS module patterns) — depth limit prevents runaway recursion.

Token budget unchanged: method chunk capped at 1024 tokens; if method exceeds, apply existing sub-splitting logic.

## Completion Notes

<!-- Fill when status → DONE -->
<!-- What was delivered, any gaps, date completed -->
