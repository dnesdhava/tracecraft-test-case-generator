# Skills Reference: AI-Powered Test Case Generator

## Purpose of This Document

This document defines the technical and domain skills required to design, build, test, operate, and maintain the AI-Powered Test Case Generator. For each skill it states the purpose, why it is required by this project specifically, the expected competency level, and where in the codebase or workflow the skill is applied.

**Competency levels used in this document:**

| Level | Definition |
|---|---|
| Working knowledge | Understands core concepts; can follow and extend established patterns in the codebase without detailed guidance |
| Proficient | Can design and implement independently; can make trade-off decisions; can review others' work |
| Advanced | Can architect the component; can evaluate alternatives; can define standards; can mentor |

**Phase notation:**

| Tag | Meaning |
|---|---|
| `MVP` | Required for the initial mandatory baseline as defined in `prd.md` |
| `FUTURE` | Not required for MVP; needed when a future enhancement from `prd.md §27` is built |
| `MVP / FUTURE` | Core skill is MVP; a deeper specialization within it is a future requirement |

Skills marked `MVP` must be present on the team before the baseline is considered implementable. A team missing a mandatory skill must either hire, train, or acquire it before beginning that component.

---

## 1. Python Development

### 1.1 Python 3.x (version 3.11 or later)

**Purpose:** The entire application is written in Python. Language version 3.11 or later is required because the specification relies on `typing.Protocol` with `@runtime_checkable`, frozen dataclasses, improved `tomllib` support, and the `ExceptionGroup` construct for batch-processing error aggregation.

**Why required:** Every component — parsers, extractors, normalizer, AI adapters, validators, exporters, CLI — is a Python module. A developer who does not know Python at a working level cannot contribute to any layer of the codebase.

**Expected competency:** Proficient. Developers must be comfortable with the standard library (`pathlib`, `dataclasses`, `logging`, `typing`, `enum`, `uuid`, `hashlib`, `re`, `json`, `csv`, `os`, `io`, `datetime`), virtual environments, and the `pyproject.toml` project structure.

**Where used in the project:**

- Every module in `src/tcg/` uses Python 3.11+ features.
- `tcg.domain.models` uses `@dataclass(frozen=True)` for immutable domain objects.
- `tcg.domain.ports` uses `typing.Protocol` for all dependency-inversion boundaries.
- `tcg.config.settings` uses Pydantic v2 which requires Python 3.11+.
- All use cases in `tcg.application.use_cases` rely on standard-library typing and dataclass patterns.

**Phase:** `MVP`

---

### 1.2 Object-Oriented Programming

**Purpose:** Enables the clean-architecture layering, SOLID component design, and the protocol-based dependency inversion described in `spec.md §2`.

**Why required:** The entire system is organized as a set of cohesive classes with single responsibilities and replaceable interfaces. Without sound OOP design, the separation between domain, application, and infrastructure layers will collapse, making components untestable and making future integrations impossible without rewriting core logic.

**Expected competency:** Proficient. Must understand classes, inheritance (used sparingly), composition, encapsulation, abstract base classes, protocols, and the difference between value objects and entities. Must understand why mutable global state is prohibited in this codebase.

**Where used in the project:**

- `tcg.domain.ports`: All six port protocols (`ISourceParser`, `IAIProvider`, `IRunStorage`, `IAuditWriter`, `IExporter`, `ISensitiveDataScanner`) are defined as `Protocol` classes.
- `tcg.infrastructure.parsers`: Each parser is a class implementing `ISourceParser` with no shared mutable state.
- `tcg.domain.services`: `TraceabilityService`, `CoverageService`, `DeduplicationService` are stateless service classes.
- `tcg.infrastructure.ai`: `ContextAssembler`, `PromptBuilder`, and `AIResponseParser` are collaborating classes injected into `GenerateTestCasesUseCase`.
- `tcg.interfaces.cli.main`: The composition root instantiates all infrastructure adapters and injects them into use-case constructors.

**Phase:** `MVP`

---

### 1.3 Type Hints

**Purpose:** Enforces explicit data contracts at every public boundary, enables static analysis with `mypy --strict`, and makes the specification's interface definitions directly verifiable in code.

**Why required:** The specification (`spec.md §17`) defines all six port protocols using typed signatures. The `TestCase` schema has 16 required typed fields. Any untyped boundary is an unverified contract. `mypy --strict` is a mandatory code-quality gate before merge.

**Expected competency:** Proficient. Must be comfortable with `TypeVar`, `Generic`, `Protocol`, `Literal`, `Final`, `TypedDict`, `Union` and `X | Y` shorthand, `Optional`, `Sequence`, `Mapping`, `dataclass` field types, and `overload`. Must understand why `Any` is prohibited in public interfaces.

**Where used in the project:**

- `tcg.domain.models`: Every field in every frozen dataclass is typed, including `list[str]`, `dict[str, str]`, and `SourceLocation | None`.
- `tcg.domain.ports`: All protocol method signatures are fully typed.
- `tcg.application.use_cases`: Every use-case `__init__` parameter and `execute` return type is typed.
- `tcg.infrastructure`: All parser `extract()` methods return `ProcessingResult[ExtractionResult]` generics.
- `pyproject.toml`: `mypy` configuration enforces `strict = true`.

**Phase:** `MVP`

---

### 1.4 Exception Handling

**Purpose:** Implements the exception hierarchy defined in `spec.md §20.1` and the `ProcessingResult[T]` contract, ensuring that failures are explicit, partial progress is preserved, and sensitive content never appears in error messages.

**Why required:** The application processes untrusted, potentially malformed, partially readable, and adversarially crafted files. Every failure path must produce a non-sensitive diagnostic, preserve successful artifacts, and provide a recovery action. Silent swallowing of exceptions or raw `Exception` catches that obscure the failure stage are explicitly prohibited by the constitution.

**Expected competency:** Proficient. Must understand the difference between programmer errors (bugs, raised as exceptions) and expected processing failures (returned as `ProcessingResult`). Must know when to catch, when to re-raise, and when to wrap with a domain exception. Must never include file content, source text, AI responses, or credentials in exception messages.

**Where used in the project:**

- `tcg.domain.models.result`: `ProcessingResult[T]` is the return type for all fallible infrastructure operations.
- `tcg.infrastructure.parsers`: Each parser catches library-specific exceptions and wraps them as `ParserError` with a source ID and stage label, never with raw content.
- `tcg.infrastructure.ai.openai_adapter`: Rate-limit and timeout responses are caught and returned as `AIProviderRateLimitError` or `AIProviderTimeoutError` with `is_retryable: True`.
- `tcg.application.use_cases.generate_test_cases`: Iterates over requirements using the batch partial-success pattern; accumulates errors without aborting the batch.
- `tcg.infrastructure.audit.file_audit_writer`: An audit write failure logs `CRITICAL` and continues; it does not crash the application.

**Phase:** `MVP`

---

### 1.5 File Processing

**Purpose:** Enables safe, bounded reading of BRD documents, JIRA export files, and flow-diagram PDFs from the local file system.

**Why required:** The application's entire input surface is files. Every file must be opened safely — respecting size limits, checking magic bytes before trusting content, handling encoding errors, and never following symbolic links outside the authorized workspace.

**Expected competency:** Working knowledge. Must understand `pathlib.Path` operations, binary vs. text mode, `with` statements for safe file handles, `io.BytesIO` for in-memory byte streams, and how to read file headers without loading an entire large file.

**Where used in the project:**

- `tcg.infrastructure.security.file_validator`: Reads the first N bytes for magic-byte detection before passing the file to any parser.
- `tcg.infrastructure.parsers.brd.docx_parser`: Opens the DOCX ZIP archive using `zipfile` in read-only mode.
- `tcg.infrastructure.parsers.brd.pdf_brd_parser`: Opens the PDF using an approved library in read-only mode; does not evaluate embedded scripts.
- `tcg.infrastructure.storage.file_storage`: Reads and writes JSON run state files using `pathlib.Path` and `json`.
- `tcg.infrastructure.audit.file_audit_writer`: Appends newline-delimited JSON audit records to a configured file path.

**Phase:** `MVP`

---

### 1.6 Package Management

**Purpose:** Ensures the project has a reproducible, auditable, and security-scanned dependency set.

**Why required:** The application depends on third-party libraries for PDF parsing, DOCX reading, AI API clients, Pydantic, and test tooling. Any unaudited or unpinned dependency is a supply-chain risk. The `pip-audit` gate in the CI pipeline requires a clean lock file.

**Expected competency:** Working knowledge. Must understand `pyproject.toml` dependency specification, `pip install -e .`, virtual environments, lock files (`pip-tools` or `uv`), dependency groups (runtime vs. dev), and how to run `pip-audit`.

**Where used in the project:**

- `pyproject.toml`: Declares all runtime and development dependencies with minimum version pins and upper-bound guards for volatile libraries.
- `.env.example`: Documents required environment variables; ensures credentials are never in dependency files.
- CI pipeline: Runs `pip-audit` on every push to detect known CVEs in dependencies.

**Phase:** `MVP`

---

### 1.7 Unit Testing with pytest

**Purpose:** Provides deterministic, isolated tests for all domain logic, parsers, validators, extractors, security controls, and use-case orchestration.

**Why required:** The specification (`spec.md §23`) mandates unit tests for domain logic, parsers, validators, access controls, redaction, and failure paths. The code-quality gate requires ≥ 85% line coverage on domain and application layers. AI-generated test cases are recommendations; the only reliable quality control over the generator itself is a comprehensive, fixture-based test suite.

**Expected competency:** Proficient. Must understand `pytest` fixtures (`tmp_path`, `monkeypatch`, `caplog`), parameterized tests, `conftest.py` shared fixtures, test doubles (stubs, fakes, mocks via `unittest.mock` or `pytest-mock`), and how to write tests that are deterministic, isolated, and independent of external services.

**Where used in the project:**

- `tests/unit/domain/`: Tests for `TraceabilityService`, `CoverageService`, `DeduplicationService`, and `DomainValidationService` using in-memory data.
- `tests/unit/infrastructure/parsers/`: Tests each parser against fixture files in `tests/fixtures/`.
- `tests/unit/infrastructure/`: Tests `Redactor`, `SensitiveDataScanner`, `FileValidator`, `ContextAssembler`, `PromptBuilder`, and `AIResponseParser` with synthetic inputs.
- `tests/unit/application/`: Tests each use case by injecting in-memory test doubles for all ports.
- `tests/integration/`: Tests the full pipeline from source file to validated `TestCase` using sanitized fixture documents.

**Phase:** `MVP`

---

## 2. Document Processing

### 2.1 PDF Parsing

**Purpose:** Enables extraction of text, layout structure, and graphical elements from BRD PDFs and E2E flow-diagram PDFs.

**Why required:** PDF is a primary source format for both BRDs and flow diagrams. PDFs are not structured documents — they describe visual placement of content, not semantic meaning. Extracting usable, ordered, provenance-tagged text from PDFs requires understanding content streams, text operators, page dictionaries, and the difference between text-native and image-only PDFs.

**Expected competency:** Proficient. Must understand the PDF content model (pages, content streams, text operators, coordinate spaces), the difference between text-native and image-only PDFs, how to detect password protection, and how to extract page-level text without evaluating JavaScript or macros. Must be able to select and integrate an appropriate Python PDF library (e.g. `pdfplumber`, `pypdf`, `pymupdf`) and understand each library's extraction behaviour and limitations.

**Where used in the project:**

- `tcg.infrastructure.parsers.brd.pdf_brd_parser`: Full text extraction, page-level ordering, boilerplate detection for BRD PDFs.
- `tcg.infrastructure.parsers.flow.pdf_flow_parser`: Shape, connector, label, and annotation extraction for flow-diagram PDFs.
- `tcg.infrastructure.extraction.text_extractor`: Text-block ordering and reconstruction using bounding-box coordinates from the PDF library.
- `tcg.infrastructure.security.file_validator`: Magic-byte validation (`%PDF-`) and password-protection detection before parsing begins.

**Phase:** `MVP`

---

### 2.2 DOCX Processing

**Purpose:** Enables structured extraction of text, headings, lists, tables, and document metadata from Microsoft Word DOCX files used as BRDs.

**Why required:** DOCX is the most common format for business requirements documents. Unlike PDFs, DOCX files have a defined semantic structure (OOXML XML), making it possible to reliably extract heading levels, paragraph styles, table row/column relationships, and document properties. Reliable heading extraction is essential for producing accurate section-path provenance on every requirement.

**Expected competency:** Working knowledge. Must understand the OOXML structure (ZIP archive, `word/document.xml`, paragraph styles, table elements), how to traverse the element tree in document order, and how to extract styled text without losing heading hierarchy. Experience with `python-docx` is expected.

**Where used in the project:**

- `tcg.infrastructure.parsers.brd.docx_parser`: Traverses the OOXML element tree; extracts headings with level and breadcrumb, paragraphs with parent heading path, numbered lists, and tables with row/column fidelity.
- `tcg.infrastructure.extraction.table_extractor`: Handles merged cells and complex table structures from DOCX tables.
- `tcg.infrastructure.security.file_validator`: Validates the DOCX ZIP structure integrity before parsing.

**Phase:** `MVP`

---

### 2.3 Text Extraction

**Purpose:** Provides a format-agnostic layer that converts raw parser output into ordered, typed, provenanced `TextBlock` objects consumed by the normalization layer.

**Why required:** BRD parsers produce format-specific objects (OOXML elements, PDF text objects). The normalization and requirement-identification logic must not depend on format-specific representations. The `TextExtractor` bridges parsers and domain logic, preserving the original text alongside a normalized form and tagging every block with its extraction method and confidence.

**Expected competency:** Working knowledge. Must understand text encoding (UTF-8, Unicode normalization), whitespace normalization, line reconstruction from PDF bounding boxes, and the difference between extracted, reconstructed, and OCR-derived text.

**Where used in the project:**

- `tcg.infrastructure.extraction.text_extractor`: Used by both BRD parsers and the flow diagram processor to produce `TextBlock` lists.
- `tcg.infrastructure.normalization.requirement_normalizer`: Consumes `TextBlock` lists; applies the normalization pipeline (Step 1 through Step 5 in `spec.md §8.2`).
- `tcg.infrastructure.ai.context_assembler`: Selects relevant text blocks for inclusion in the AI evidence package, subject to the token budget.

**Phase:** `MVP`

---

### 2.4 Structured Document Processing

**Purpose:** Enables hierarchical interpretation of BRD documents — recognizing that a requirement under heading §3.2.1 has a different scope than one under §5 — and preserving that structure as `section_path` provenance on every extracted item.

**Why required:** Requirement traceability (`spec.md §9.2`) requires that every `SourceReference` be specific enough for a reviewer to locate the evidence. A reference that says only "page 12" is insufficient; one that says "§3.2.1 – Payment Rules, paragraph 4, page 12" is verifiable. Reconstructing this requires understanding how heading levels nest and how paragraphs and tables belong to sections.

**Expected competency:** Working knowledge. Must understand document outline models, heading-level trees, and how to maintain a section-breadcrumb as a document is traversed in order.

**Where used in the project:**

- `tcg.infrastructure.parsers.brd.docx_parser`: Maintains a running `section_path` stack updated as each heading element is encountered.
- `tcg.infrastructure.parsers.brd.pdf_brd_parser`: Infers section boundaries from font size, bold style, and numbering patterns in PDF text.
- `tcg.domain.models.source`: `SourceLocation.section_path` field carries the reconstructed hierarchy for every extracted item.

**Phase:** `MVP`

---

### 2.5 Table Extraction

**Purpose:** Preserves the row-and-column relationships of business-rule tables, data-definition tables, and acceptance-criteria tables in BRD documents.

**Why required:** BRDs routinely define business rules, data ranges, and error codes in tables. A table that specifies "transfer limit: min £1, max £50,000" cannot be correctly understood if the row and column relationships are lost by naïve flat-text extraction. The `TableExtractor` must preserve these relationships so the normalization layer can identify boundary values and validation rules.

**Expected competency:** Working knowledge. Must understand how DOCX table elements map to rows and cells (including `gridSpan` and `rowSpan` for merged cells), and how PDF table-like layouts can be reconstructed from bounding-box grouping. Must be able to represent a table as a `list[list[TableCell]]` structure and handle merged-cell spans without data loss.

**Where used in the project:**

- `tcg.infrastructure.extraction.table_extractor`: Core extraction class; handles merged cells with a `merged_from` reference.
- `tcg.infrastructure.parsers.brd.docx_parser`: Delegates table elements to `TableExtractor`.
- `tcg.infrastructure.parsers.brd.pdf_brd_parser`: Uses bounding-box clustering to reconstruct grid layout from PDF text objects.
- `tcg.domain.services.domain_validator`: Uses table-extracted boundary values to assess whether `BOUNDARY` scenario class is applicable.

**Phase:** `MVP`

---

### 2.6 PDF Flow and Diagram Interpretation

**Purpose:** Converts a graphical end-to-end workflow diagram in PDF form into a machine-readable directed graph of nodes, edges, and paths that the test case generation engine can reason over.

**Why required:** Flow diagrams are a primary source for E2E scenario coverage. Without interpreting the diagram structure, the generator cannot identify complete paths, alternate branches, decision conditions, or exception paths. This is the most technically challenging extraction task in the application because PDF does not encode semantic graph structure.

**Expected competency:** Advanced. Must understand PDF vector-graphics content streams (path operators, transformation matrices, annotation objects), shape-proximity analysis, connector-endpoint assignment, and directed-graph construction. Must understand the limitations of heuristic shape classification and be able to model ambiguity explicitly. Must design the extraction so that every uncertain element is flagged rather than silently resolved.

**Where used in the project:**

- `tcg.infrastructure.parsers.flow.pdf_flow_parser`: Reads PDF page content streams; applies shape-type vocabulary; builds `FlowNode`, `FlowEdge`, and `FlowPath` objects.
- `tcg.infrastructure.extraction.diagram_extractor`: Performs connector-endpoint assignment, ambiguity detection, `DANGLING_NODE` and `INCOMPLETE_DECISION` identification, and depth-limited path enumeration.
- `tcg.domain.models.flow`: `FlowDiagram`, `FlowNode`, `FlowEdge`, `FlowPath`, and `AmbiguityWarning` are the output models.
- `tcg.application.use_cases.process_source`: Delegates to the flow parser and records all ambiguities for reviewer inspection.
- `tcg.domain.services.traceability_service`: Links flow paths to requirements and to generated E2E test cases.

**Phase:** `MVP`

---

## 3. JIRA Integration

### 3.1 JIRA REST API Concepts

**Purpose:** Provides the conceptual foundation for understanding how JIRA structures project data, which fields are stable identifiers, and how the JSON export format maps to the internal domain model.

**Why required:** Although the baseline uses a structured JSON import rather than a live API, the field names, data types, and relationships in the import file are JIRA API constructs (e.g. `fields.customfield_*`, ADF document format, `issuelinks` structure). Understanding these prevents field-mapping errors that would corrupt requirement traceability.

**Expected competency:** Working knowledge. Must understand JIRA issue types, field structure, the Atlassian Document Format (ADF) used in descriptions and comments, `issuelinks` relationship types, and how JIRA Cloud exports differ from JIRA Server exports.

**Where used in the project:**

- `tcg.infrastructure.parsers.jira.json_import_parser`: Maps JIRA JSON fields to `JiraStory` model fields; handles ADF-to-plain-text conversion for descriptions and acceptance criteria.
- `tcg.config.settings`: The `jira.acceptance_criteria_field` setting names the configurable custom field key, informed by JIRA's custom field conventions.
- `docs/adr/`: Decisions about field-mapping and ADF handling should be recorded as Architecture Decision Records.

**Phase:** `MVP`  
*(Live JIRA API connector:* `FUTURE`*)*

---

### 3.2 User Stories

**Purpose:** Enables correct identification, extraction, and modelling of JIRA user stories as first-class evidence units in the traceability graph.

**Why required:** User stories are a primary source for test-case generation. Their story key is a stable, business-owned identifier that must be preserved through normalization, traceability linking, and export. A team member who does not understand the user-story format may incorrectly treat the summary as the full requirement or fail to recognize that the description often contains additional business rules beyond the summary.

**Expected competency:** Working knowledge. Must understand the "As a … I want … So that …" convention, when story descriptions contain additional rules, the relationship between stories and epics, and the significance of story status and priority for risk-based coverage.

**Where used in the project:**

- `tcg.infrastructure.parsers.jira.json_import_parser`: Maps `summary`, `description`, and `issue_type` fields; preserves the story key as `business_id` with `id_origin: BUSINESS`.
- `tcg.domain.models.requirement`: `NormalizedRequirement.jira_story_id` links every derived requirement back to its source story.
- `tcg.domain.models.test_case`: `TestCase.jira_story_id` is a mandatory schema field; a case without a traceable story ID must use the documented N/A value with a reason.

**Phase:** `MVP`

---

### 3.3 Acceptance Criteria

**Purpose:** Treats acceptance criteria as the primary evidence for expected behavior in generated test cases, as established by the constitution and PRD.

**Why required:** Acceptance criteria are the most precise, testable statement of expected behavior in a JIRA story. The specification requires that every acceptance criterion receive an internal criterion ID, that criterion-to-case traceability is maintained, and that conflicts between a story description and its criteria are surfaced rather than resolved silently. Mishandling criteria leads to generated cases whose expected results cannot be verified.

**Expected competency:** Proficient. Must understand how acceptance criteria are expressed in BDD (Given/When/Then), numbered-list, and free-prose styles; how to split them into discrete, traceable units; and how to assign internal IDs when none are provided. Must understand the difference between an acceptance criterion and a test step.

**Where used in the project:**

- `tcg.infrastructure.parsers.jira.json_import_parser`: Splits raw criteria text into individual `AcceptanceCriterion` objects; assigns `{story_key}-AC-{n}` internal IDs.
- `tcg.domain.models.requirement`: `NormalizedRequirement.acceptance_criteria` is a `list[AcceptanceCriterion]`.
- `tcg.domain.services.traceability_service`: Maintains criterion-to-case `TraceLink` objects; reports criteria with no associated test case as coverage gaps.
- `tcg.infrastructure.ai.context_assembler`: Includes relevant acceptance criteria in the evidence package sent to the AI model.

**Phase:** `MVP`

---

### 3.4 Issue Metadata

**Purpose:** Enables preservation and use of JIRA metadata fields — priority, labels, components, linked issues, status — for risk-based prioritization and traceability.

**Why required:** Test-case priority is derived from source-supported evidence (`spec.md §10.5`). JIRA story priority, severity labels, and epic/parent relationships are legitimate sources for this evidence. Without correctly extracting and preserving these fields, the generator must default all cases to `Priority.UNKNOWN`, reducing the usefulness of the coverage and quality reports.

**Expected competency:** Working knowledge. Must understand which JIRA fields are reliable priority signals, which are project-specific, and which must be preserved for access-policy reasons (reporter, assignee, timestamps) even when they are not directly used in generation.

**Where used in the project:**

- `tcg.infrastructure.parsers.jira.json_import_parser`: Extracts `priority.name`, `labels`, `components`, `status.name`, and `issuelinks` into the `JiraStory` model.
- `tcg.infrastructure.normalization.requirement_normalizer`: Uses story priority as a candidate `Priority` value for generated cases when no BRD-level priority is found.
- `tcg.domain.models.requirement`: `NormalizedRequirement` carries story priority and labels as optional context for the scenario engine.

**Phase:** `MVP`

---

### 3.5 Requirement Extraction from JIRA Stories

**Purpose:** Bridges the gap between a JIRA user story (a delivery unit) and a normalized requirement (a testable behavior unit), which are not the same thing.

**Why required:** A single JIRA story may contain multiple discrete testable behaviors in its description and acceptance criteria. Conversely, a single behavior may be described across a parent epic and several child stories. The normalization layer must decompose stories into individual testable units without losing the story identity that links back to the original source.

**Expected competency:** Proficient. Must understand how to identify discrete testable behaviors within story text, how to handle ambiguous language ("the system should…" vs. "the system must…"), and how to flag behaviors that require clarification rather than inventing expected outcomes.

**Where used in the project:**

- `tcg.infrastructure.normalization.requirement_normalizer`: Step 1 (identifier assignment) and Step 4 (cross-source linking) are directly concerned with decomposing and linking JIRA-sourced requirements.
- `tcg.domain.services.domain_validator`: Applies rules to detect stories whose description contains testable behavior not captured in acceptance criteria.
- `tcg.application.use_cases.process_source`: Calls the normalizer for JIRA extraction results and surfaces `NormalizationIssue` objects for reviewer action.

**Phase:** `MVP`

---

## 4. AI and LLM Skills

### 4.1 Prompt Engineering

**Purpose:** Designs the versioned, structured prompts used by `PromptBuilder` to instruct the AI model to produce evidence-grounded, schema-conformant test cases.

**Why required:** The quality of generated test cases is directly governed by prompt design. The constitution's prohibition on invented behavior, the requirement to separate source-supported facts from assumptions, and the demand for structured output in a defined JSON schema all depend on how the prompt is constructed. A poorly designed prompt produces fluent but inaccurate or hallucinated cases that fail the evidence gate.

**Expected competency:** Advanced. Must understand zero-shot vs. few-shot prompting, chain-of-thought elicitation, structured output via JSON mode or constrained generation, system vs. user message roles, the effect of token budget on context quality, and prompt versioning practices. Must understand the attack surface of prompt injection from untrusted source documents and how structural delimiters and instruction hardening mitigate it.

**Where used in the project:**

- `tcg.infrastructure.ai.prompt_builder`: Builds every `GenerationPrompt` from a versioned template stored in `config/prompt_templates/`.
- `config/prompt_templates/generate_v1.0.txt`: The versioned prompt template; any change increments the version and requires re-evaluation against test fixtures.
- `tcg.infrastructure.ai.context_assembler`: Works with the prompt engineer to define what evidence is included and how it is labelled in the evidence section.
- `tcg.infrastructure.security.file_validator` and `context_assembler`: Prompt injection mitigation patterns are designed by the prompt engineer in collaboration with the security skill owner.

**Phase:** `MVP`

---

### 4.2 Requirement Understanding

**Purpose:** Enables the system to correctly identify which parts of source documents represent discrete testable behaviors, actors, preconditions, outcomes, and constraints.

**Why required:** The AI model cannot reliably distinguish a business rule from a project objective from a constraint from a delivery note without well-designed identification logic in the normalizer and well-structured evidence in the prompt. A team member with this skill understands how requirements are written in practice — including ambiguous, compound, and conflicting requirements — and designs the extraction rules and prompt instructions accordingly.

**Expected competency:** Proficient. Must understand requirement quality characteristics (unambiguous, verifiable, atomic, consistent, traceable), common BRD writing patterns, and how to represent partial or conflicting requirements without inventing missing information.

**Where used in the project:**

- `tcg.infrastructure.normalization.requirement_normalizer`: The requirement-pattern configuration, cross-source linking rules, and conflict detection logic reflect this skill.
- `tcg.infrastructure.ai.context_assembler`: The `behavior_statement` field in `NormalizedRequirement` is constructed to give the model a clear, focused description of what needs to be tested.
- `tcg.domain.services.domain_validator`: Rules for identifying ambiguous requirements and gap conditions.
- `tcg.application.use_cases.generate_test_cases`: Decides which `NormalizedRequirement` objects have sufficient evidence to proceed to generation.

**Phase:** `MVP`

---

### 4.3 Test Scenario Generation

**Purpose:** Applies testing theory to the AI generation step — ensuring that the prompt and scenario-planning logic consider all applicable scenario classes for each requirement.

**Why required:** Without this skill, the generator defaults to happy-path cases. The scenario engine (`spec.md §10.2`) applies applicability rules for all seven scenario classes. Designing these rules correctly, and writing the prompt instructions that guide the model to consider each class, requires someone who understands why each scenario type adds coverage value and how to derive it from source evidence rather than generic testing heuristics.

**Expected competency:** Proficient. Must understand all seven scenario classes (positive, negative, boundary, validation, exception, integration, E2E), the difference between source-supported and invented scenarios, and how to write applicability rules that correctly classify evidence from BRDs, user stories, and flow diagrams.

**Where used in the project:**

- `tcg.domain.services` and `tcg.application.use_cases.generate_test_cases`: `ScenarioPlan` construction and the seven-class applicability rules.
- `tcg.infrastructure.ai.prompt_builder`: Prompt instructions guide the model through each applicable scenario class.
- `tcg.infrastructure.ai.response_parser`: Validates that the model's output includes the required `test_type` field using a controlled enumeration.

**Phase:** `MVP`

---

### 4.4 Structured Output Generation

**Purpose:** Constrains the AI model to produce JSON output conforming to the test-case schema defined in `spec.md §13.3`, enabling deterministic downstream validation.

**Why required:** Free-form AI text output cannot be reliably validated, parsed, or used as a structured test case. The entire validation pipeline depends on the model's output being parseable JSON with all required fields in the correct types and controlled values. This skill governs how JSON mode or constrained generation is used, how the output schema is embedded in the prompt, and how the response parser handles deviations.

**Expected competency:** Proficient. Must understand JSON schema constraints, how to specify them in a prompt, how to use provider-specific JSON mode or function-calling features to enforce structure, and how to handle malformed or truncated JSON without silently accepting incomplete output.

**Where used in the project:**

- `tcg.infrastructure.ai.prompt_builder`: The output contract section of the prompt embeds the required JSON schema and controlled enumeration values.
- `tcg.infrastructure.ai.response_parser`: Validates the raw response against the output contract schema before mapping to domain objects.
- `tcg.config.schema_registry`: Maintains the versioned JSON schema that both the prompt and the response parser use.
- `tcg.infrastructure.export.json_exporter`: The final export uses the same schema version as the generation prompt.

**Phase:** `MVP`

---

### 4.5 Context Management

**Purpose:** Manages the selection, trimming, and ordering of source evidence included in the AI prompt to stay within the token budget while maximizing generation quality.

**Why required:** AI providers have context-window limits. Sending too much source text increases cost and may cause truncation; sending too little produces unsupported or vague test cases. The `ContextAssembler` must apply a priority-based trimming strategy that removes less-critical evidence before critical evidence and records what was omitted for the audit record.

**Expected competency:** Proficient. Must understand token counting (approximation for different model families), context-window limits for approved models, retrieval-augmented generation (RAG) patterns for selecting relevant evidence, and the evidence-budget configuration in `spec.md §11.2`.

**Where used in the project:**

- `tcg.infrastructure.ai.context_assembler`: Core implementation of context selection, priority trimming, and omission recording.
- `tcg.config.settings`: `ai.context_budget_per_requirement` configuration value.
- `tcg.domain.models.scenario`: `EvidencePackage.omitted_refs` records what was excluded from the context.
- `tcg.domain.models.test_case`: `GenerationMetadata.evidence_budget_used` and `evidence_items_omitted` are recorded per case.

**Phase:** `MVP`  
*(Advanced RAG with vector retrieval:* `FUTURE`*)*

---

### 4.6 Hallucination Prevention

**Purpose:** Designs the architectural and prompt-level controls that prevent the AI model from inventing requirements, business rules, error messages, or expected behaviors not present in the supplied sources.

**Why required:** The constitution's most fundamental rule is that AI-generated output must not invent unsupported behavior. Hallucination prevention is not a single technique but a set of layered controls: evidence grounding in the prompt, explicit instructions to cite evidence, the evidence gate in the validation engine, the prohibition on unverified citations, and the human review requirement. A developer with this skill understands where each control sits and how to test its effectiveness.

**Expected competency:** Advanced. Must understand why LLMs hallucinate, which prompt patterns reduce hallucination rates, how to construct evaluation fixtures that expose hallucination, and how the evidence gate (`spec.md §12.3`) detects unverified citations in the response parser output.

**Where used in the project:**

- `tcg.infrastructure.ai.prompt_builder`: Prompt instructions explicitly prohibit invention of behavior and require citing each claim to the evidence section.
- `tcg.infrastructure.ai.context_assembler`: Grounding strategy — only verified, provenanced evidence is included in the context.
- `tcg.infrastructure.ai.response_parser`: Tags model-cited references as `UNVERIFIED_CITATION` when they do not match the supplied evidence package.
- `tcg.application.use_cases.validate_test_cases`: The evidence gate blocks cases with unverified citations.
- `tests/fixtures/ai_responses/unverified_citation_response.json`: Test fixture covering this failure mode.

**Phase:** `MVP`

---

### 4.7 AI Response Validation

**Purpose:** Implements deterministic post-generation checks that verify the model's output meets structural, traceability, and security requirements before a case is shown to a reviewer.

**Why required:** AI model output cannot be trusted without validation. The response may be malformed JSON, truncated, a refusal, or structurally valid but containing unsupported claims, placeholder text, or sensitive content. The validation engine applies twelve ordered gates; none of these gates can be designed or tested without understanding what can go wrong in AI responses.

**Expected competency:** Proficient. Must understand common AI response failure modes (truncation, refusal, hallucinated citations, placeholder text, prompt echo), how to test each mode with pre-recorded fixture responses, and how to design gate logic that rejects failures without exposing the raw model output in logs.

**Where used in the project:**

- `tcg.infrastructure.ai.response_parser`: Parses and structurally validates the raw AI response.
- `tcg.application.use_cases.validate_test_cases`: Applies all twelve validation gates in the specified order.
- `tcg.domain.services.domain_validator`: Domain-level validation rules applied as part of the schema and evidence gates.
- `tests/fixtures/ai_responses/`: All five response failure fixture types exercise the validation logic.

**Phase:** `MVP`

---

## 5. Testing Skills

### 5.1 Functional Testing

**Purpose:** Verifies that the application correctly generates test cases that match the stated requirements, acceptance criteria, and flow steps in the source documents.

**Why required:** The application itself must be tested to confirm that a given BRD section produces the correct `NormalizedRequirement`, that a given requirement produces an applicable scenario plan, and that the generated cases accurately represent the source evidence. Functional testing of the generator requires the same skills the generator is trying to automate for the target banking system.

**Expected competency:** Proficient. Must design test scenarios that verify correct extraction, correct normalization, correct scenario-class selection, and correct case schema for a given input. Must be able to distinguish a case that is wrong because the parser failed from one that is wrong because the prompt is inadequate.

**Where used in the project:**

- `tests/integration/test_brd_to_requirements.py`: Functional verification of the BRD parsing-to-normalization pipeline.
- `tests/integration/test_generation_pipeline.py`: Functional verification that a known set of requirements produces cases covering expected scenario classes.
- Review workflow: QA team members performing human review apply functional testing judgment to decide whether cases are correct and complete.

**Phase:** `MVP`

---

### 5.2 Regression Testing

**Purpose:** Detects when a change to a parser, normalizer, prompt template, or validation rule causes previously passing outputs to fail or degrade.

**Why required:** Prompt templates, parser configurations, validation rules, and schema versions are all versioned because changes to any of them can affect output. The change-impact analysis in `spec.md §9.5` detects affected test cases at runtime; the regression test suite detects affected application behavior at the code level.

**Expected competency:** Working knowledge. Must understand how to write tests that record a known-good output from a fixture input and assert it does not regress. Must understand the difference between expected changes (schema additions, new scenario classes) and unintended regressions.

**Where used in the project:**

- `tests/unit/infrastructure/parsers/`: Parser tests against stable fixture files serve as regression guards.
- `tests/integration/`: Integration tests run on every pull request to prevent pipeline-level regressions.
- CI pipeline: `pytest` runs all tests on every push; a test failure blocks the merge.
- `tcg.domain.services.traceability_service`: Change-impact detection at run time is the runtime equivalent of regression testing for source changes.

**Phase:** `MVP`

---

### 5.3 Integration Testing

**Purpose:** Verifies that multiple components — parser to extractor to normalizer, normalizer to traceability to generator, generator to validator to exporter — work correctly together.

**Why required:** Clean architecture creates component boundaries that are individually testable but whose composition must also be verified. An integration test confirms that the `JiraStory` produced by the parser flows correctly through normalization and emerges as a correctly linked `NormalizedRequirement` with the right `TraceLink` objects.

**Expected competency:** Working knowledge. Must design tests that cover component-to-component contracts using real or fixture-backed implementations (not mocks) for the components under integration, while still using test doubles for external services (AI providers, external APIs).

**Where used in the project:**

- `tests/integration/test_brd_to_requirements.py`, `test_jira_to_requirements.py`, `test_flow_to_paths.py`: Component-integration tests.
- `tests/integration/test_generation_pipeline.py`: Normalizer → scenario engine → generation engine → validator integration.
- `tests/integration/test_export_pipeline.py`: Validator → formatter → exporter integration.
- `tests/integration/test_audit_trail.py`: Verifies that audit events are emitted correctly at each pipeline stage.

**Phase:** `MVP`

---

### 5.4 End-to-End Testing

**Purpose:** Generates test cases that cover complete workflows from start to end, as represented by fully resolved flow diagram paths.

**Why required:** E2E scenario class (`TestType.END_TO_END`) is one of the seven mandatory scenario classes. Generating an E2E case requires understanding a complete flow path — all actors, decisions, data handoffs, and termination — which is more complex than a single-requirement case. The team must be able to evaluate whether a generated E2E case correctly covers the intended workflow.

**Expected competency:** Working knowledge. Must understand how multi-step business workflows are structured, what actors and data states are involved, and how to evaluate whether a test case step sequence correctly represents a start-to-finish path.

**Where used in the project:**

- `tcg.infrastructure.extraction.diagram_extractor`: Path enumeration logic; `FlowPath` with `PathType.MAIN` and `PathType.ALTERNATE`.
- `tcg.domain.services.coverage_service`: Tracks whether each complete flow path has at least one associated E2E test case.
- `tcg.infrastructure.ai.prompt_builder`: E2E prompt instructions guide the model to include all relevant actors, decision labels, and termination states from the selected flow path.
- `tests/fixtures/flow/branching_flow.pdf`: Fixture exercising E2E case generation from a multi-branch flow.

**Phase:** `MVP`

---

### 5.5 Negative Testing

**Purpose:** Ensures the generator produces test cases that cover invalid inputs, unauthorized actions, and rejection conditions — not only happy-path scenarios.

**Why required:** Negative scenarios are the second most commonly missed test class after boundary cases. The scenario engine applies applicability rules that require explicit source evidence of a rejection condition before generating a negative case. Without this skill, the rules for negative-class applicability will be either too permissive (inventing rejection behavior) or too restrictive (missing real negative scenarios).

**Expected competency:** Working knowledge. Must understand the difference between a negative test (system correctly rejects invalid input) and an error-handling test (system correctly handles a failure condition), and how to identify negative test evidence in BRDs and acceptance criteria.

**Where used in the project:**

- `tcg.domain.services.domain_validator`: Applies `TestType.NEGATIVE` applicability rules.
- `tcg.infrastructure.ai.prompt_builder`: Negative scenario prompt instructions.
- `tests/unit/domain/test_domain_validator.py`: Tests negative-class applicability rules with fixture requirements.

**Phase:** `MVP`

---

### 5.6 Boundary Value Analysis

**Purpose:** Enables identification of numeric, length, date, count, and threshold boundaries stated in source documents, and generates test cases at, just inside, and just outside those limits.

**Why required:** Boundary defects are among the most common bugs in banking and payment systems (e.g. transfer limits, transaction thresholds, timeout values). The scenario engine identifies boundary values from BRD tables and requirement text. Without a team member skilled in boundary analysis, these identification rules will miss real limits or incorrectly flag non-limit values as boundaries.

**Expected competency:** Working knowledge. Must understand the boundary value analysis technique (on-point, off-point, just-inside, just-outside), how to extract limit values from textual and tabular sources, and how to construct meaningful boundary test data without inventing limits.

**Where used in the project:**

- `tcg.domain.models.scenario`: `BoundaryValue` is extracted from source evidence and included in the `ScenarioPlan`.
- `tcg.domain.services.domain_validator`: Rules that apply `TestType.BOUNDARY` only when an explicit limit is found in the source.
- `tcg.infrastructure.ai.context_assembler`: `BoundaryValue` objects are passed as structured data to the model, not as free-form text.
- `tests/unit/domain/test_domain_validator.py`: Parameterized tests for boundary-detection rules with multiple table formats.

**Phase:** `MVP`

---

### 5.7 Equivalence Partitioning

**Purpose:** Groups valid and invalid inputs into equivalence classes so that test data in generated cases is representative rather than arbitrary.

**Why required:** Generated test data guidance (`TestDataItem`) must advise the tester on meaningful data values and characteristics, not random examples. Equivalence partitioning principles inform how the context assembler and prompt instructions frame test-data guidance for each scenario class.

**Expected competency:** Working knowledge. Must understand equivalence partitioning, how to identify valid and invalid input classes from requirement text, and how to express data characteristics rather than specific production values in test-data fields.

**Where used in the project:**

- `tcg.infrastructure.ai.prompt_builder`: Prompt instructions guide the model to describe data characteristics (valid class, invalid class, boundary value) rather than specific live data values.
- `tcg.domain.models.test_case`: `TestDataItem.description` carries the data characteristic; `TestDataItem.value` may be a masked or synthetic example.
- Validation gate — consistency check: Verifies that test data descriptions are substantive rather than placeholder text.

**Phase:** `MVP`

---

### 5.8 Requirement Traceability

**Purpose:** Establishes and maintains verifiable links between requirements, acceptance criteria, flow steps, and generated test cases across the entire project lifecycle.

**Why required:** Requirement traceability is the central governing principle of this application (constitution §1). Every component — from the normalizer to the traceability engine to the validation gates to the export — exists to serve this principle. A team member who does not understand why traceability matters and how to verify it cannot correctly implement or evaluate any part of the system.

**Expected competency:** Proficient. Must understand bidirectional traceability, coverage matrices, orphan requirements, impact analysis, and the difference between a resolvable source reference and a broken link. Must be able to evaluate whether a `SourceReference` is specific enough for a reviewer to locate the evidence.

**Where used in the project:**

- `tcg.domain.services.traceability_service`: Core implementation of the traceability graph and source-reference resolution.
- `tcg.application.use_cases.validate_test_cases`: The traceability gate (`spec.md §12.3`) blocks cases with broken or missing references.
- `tcg.application.use_cases.generate_report`: Produces the traceability matrix, coverage report, and change-impact report.
- `tcg.infrastructure.export`: Exports preserve all source references and their resolution status.

**Phase:** `MVP`

---

## 6. Banking and Payment Domain Skills

### 6.1 Fund Transfers

**Purpose:** Provides domain context for understanding BRD requirements and JIRA stories that describe internal and external fund-transfer workflows.

**Why required:** The application targets banking BRDs. A developer or tester who does not understand fund-transfer mechanics — initiation, authorization, settlement, confirmation, reconciliation, and reversal — will produce test cases with inaccurate preconditions, missing actors (maker-checker), and incorrect expected results. This domain knowledge improves the quality of the normalization rules and prompt instructions for banking-specific content.

**Expected competency:** Working knowledge. Must understand the core stages of a fund transfer, the role of debit/credit account validation, authorization rules (limits, dual approval), cut-off times, settlement states, and the difference between immediate and batch settlement.

**Where used in the project:**

- Normalization rules in `tcg.infrastructure.normalization.requirement_normalizer`: Identifying transfer-specific actors (initiator, authorizer, beneficiary), preconditions (account status, balance availability), and outcomes (debit/credit confirmation, reference number).
- Prompt design in `tcg.infrastructure.ai.prompt_builder`: Accurate prompt instructions for banking-context requirement understanding.
- Review workflow: Reviewers from the banking domain verify that generated cases reflect real transfer behavior.

**Phase:** `FUTURE` *(domain templates for banking workflows)*  
Working knowledge is recommended for the MVP team but is not a blocking dependency for baseline technical implementation.

---

### 6.2 Payment Processing

**Purpose:** Provides understanding of end-to-end payment processing lifecycles — initiation, validation, routing, processing, settlement, confirmation, and exception handling — as used in BRDs for payment features.

**Why required:** Payment features are among the most requirement-dense areas of banking systems. Understanding payment processing sequences helps identify which flow diagram nodes represent which payment stages, which BRD requirements relate to which stages, and what exception paths (insufficient funds, rejected payment, cut-off breach) are likely to be present but perhaps only partially documented.

**Expected competency:** Working knowledge. Must understand payment lifecycle stages, status codes, retry and reversal mechanics, and the role of payment schemas in defining valid inputs and outcomes.

**Where used in the project:**

- Flow diagram interpretation: Identifying payment-stage nodes and decision points in `tcg.infrastructure.parsers.flow.pdf_flow_parser`.
- Normalization: Correctly mapping payment-lifecycle requirements to `RequirementType.FUNCTIONAL` vs. `RequirementType.BUSINESS_RULE`.
- Scenario planning: Identifying applicable exception and integration classes for payment workflows.

**Phase:** `FUTURE`  
Recommended for the team reviewing generated payment-feature test cases.

---

### 6.3 SWIFT, NEFT, and RTGS

**Purpose:** Provides understanding of specific interbank and cross-border payment channels, their format requirements, timing rules, and regulatory obligations.

**Why required:** BRDs for payment features in international banking often reference SWIFT message types (MT103, MT202), NEFT batch windows, and RTGS real-time settlement rules. A team member who does not understand these references will generate test cases that misidentify timing constraints, cut-off times, and format validation requirements.

**Expected competency:** Working knowledge. Must understand the basic characteristics of each channel (SWIFT for international, NEFT for India batch, RTGS for high-value real-time), their key timing and amount thresholds, and the format identifiers used in requirement text.

**Where used in the project:**

- Normalization rules: Recognizing SWIFT message type identifiers, NEFT/RTGS amount thresholds, and cut-off time references as boundary values.
- Test data guidance: Generating meaningful synthetic test data characteristics for each channel type.
- Review: Domain reviewers verify generated cases against channel-specific rules.

**Phase:** `FUTURE`  
Relevant when the application is used on cross-border or interbank payment BRDs.

---

### 6.4 Card Payments

**Purpose:** Provides understanding of card payment flows — authorization, capture, clearing, settlement, chargeback, and reversal — and the data types and validation rules specific to card payment requirements.

**Why required:** Card payment requirements are highly sensitive (PAN, CVV, expiry) and highly regulated (PCI DSS). The `SensitiveDataScanner` must detect card-number patterns; the `Redactor` must mask them. A team member who does not understand PAN format, the Luhn algorithm, and what constitutes card data will not correctly configure these security controls.

**Expected competency:** Working knowledge (security-focused). Must understand what constitutes cardholder data (PAN, CVV, expiry, cardholder name), why this data must be masked in test cases and logs, how to write test data guidance that references card-data characteristics without including real card numbers, and the basic card authorization flow.

**Where used in the project:**

- `tcg.infrastructure.security.sensitive_scanner`: Card-number detection pattern (PAN-like sequences, Luhn-valid patterns).
- `tcg.infrastructure.security.redactor`: Card masking configuration.
- `tcg.domain.models.test_case`: `TestDataItem.is_masked: true` for any card-related test data item.
- Test data guidance in generated cases: Must describe card data characteristics (e.g. "a Visa card number in the test card range") rather than real or valid card numbers.

**Phase:** `MVP` *(security-focused card-data handling)*  
*(Full card payment test-case generation expertise:* `FUTURE`*)*

---

### 6.5 Payment Gateways

**Purpose:** Provides understanding of the integration contract between an application and an external payment gateway, including request/response structures, error codes, timeout behavior, and reconciliation.

**Why required:** Payment gateway requirements typically generate integration and exception scenario test cases. Understanding the gateway integration model helps correctly identify integration scenario applicability, what the expected responses are for various error conditions, and what reconciliation checks are testable.

**Expected competency:** Working knowledge. Must understand the typical request/response pattern for a payment gateway (authorize, capture, void, refund), common error-code categories (declined, timeout, network error), and the reconciliation obligation.

**Where used in the project:**

- Scenario planning: `TestType.INTEGRATION` and `TestType.EXCEPTION` applicability for payment gateway requirements.
- Prompt design: Providing accurate context about integration patterns when gateway-related requirements are in the evidence package.

**Phase:** `FUTURE`

---

### 6.6 Validation and Exception Handling in Banking

**Purpose:** Enables identification of the domain-specific validation rules (amount limits, account status checks, beneficiary validation, duplicate detection) and exception paths (reversal, rejection, hold) present in banking BRDs.

**Why required:** Banking validation rules are complex, domain-specific, and often expressed in BRD tables or notes rather than in named requirements. Without domain knowledge, the normalizer may miss these rules, and the scenario engine may not identify the corresponding validation and exception scenario classes.

**Expected competency:** Working knowledge. Must understand common banking validation rules (balance check, beneficiary account status, duplicate transaction detection, amount threshold checks) and common exception flows (payment hold, rejection notification, reversal initiation).

**Where used in the project:**

- `tcg.infrastructure.normalization.requirement_normalizer`: Recognition of banking validation patterns from BRD table content.
- `tcg.domain.services.domain_validator`: `TestType.VALIDATION` and `TestType.EXCEPTION` applicability rules informed by banking domain knowledge.

**Phase:** `MVP / FUTURE` *(basic validation recognition: MVP; deep domain-specific rules: FUTURE)*

---

### 6.7 Regulatory and Compliance Considerations

**Purpose:** Ensures that generated test cases for regulated banking features reflect the compliance obligations relevant to the feature under test (AML, KYC, PCI DSS, RBI guidelines, etc.).

**Why required:** Banking features are subject to regulatory requirements that may not always be explicitly called out in every BRD but are implied by the type of transaction. An advisor with regulatory knowledge can flag when a generated test case is missing a compliance check that regulators would expect, and can identify when a requirement gap represents a regulatory risk.

**Expected competency:** Working knowledge. Must understand the categories of banking regulation relevant to the features being tested (AML transaction monitoring thresholds, KYC verification requirements, PCI DSS data handling obligations), and be able to identify when a BRD is missing regulatory coverage.

**Where used in the project:**

- Review workflow: Domain reviewers with regulatory knowledge inspect generated cases for missing compliance checks.
- Future prompt templates for regulated features: May include compliance-check scenario class guidance.
- `tcg.infrastructure.security.sensitive_scanner`: PCI DSS card-data patterns and AML-related PII patterns are informed by regulatory knowledge.

**Phase:** `FUTURE` *(formal compliance template guidance)*  
Working knowledge of PCI DSS data handling is recommended for the MVP security role.

---

## 7. Software Engineering

### 7.1 Clean Architecture

**Purpose:** Structures the codebase so that domain rules are independent of infrastructure, delivery mechanisms, AI providers, file formats, and external services.

**Why required:** The constitution requires that domain behavior not depend on any single provider, library, or deployment environment. The specification (`spec.md §1.1`) defines the layering explicitly: domain → application → infrastructure, with the dependency rule strictly enforced. Violating this rule makes the codebase fragile, untestable without live services, and impossible to extend cleanly with future integrations.

**Expected competency:** Advanced. Must be able to identify the correct layer for any new component, enforce the dependency rule in code review, design port protocols that are genuinely replaceable, and explain to team members why an infrastructure import in a domain class is a violation that must be corrected.

**Where used in the project:**

- Package structure: `tcg.domain`, `tcg.application`, `tcg.infrastructure`, `tcg.interfaces` enforce the layer boundary at the import level.
- `tcg.domain.ports`: All six port protocols define the inward-facing contracts that infrastructure implementations must satisfy.
- `tcg.interfaces.cli.main`: The composition root is the only place where infrastructure is instantiated; use cases never import concrete infrastructure.
- `docs/adr/0001-clean-architecture.md`: The architectural decision record documents the rationale and consequences.

**Phase:** `MVP`

---

### 7.2 SOLID Principles

**Purpose:** Guides class design across all layers to produce components that are independently testable, replaceable, and maintainable.

**Why required:** Each SOLID principle directly governs a specific design decision in the specification. Single Responsibility governs parser-extractor-normalizer separation. Open/Closed governs the parser and exporter registries. Dependency Inversion governs all six port protocols. Without these principles being actively applied in code review, the codebase will accumulate violations that eventually make the architecture unmaintainable.

**Expected competency:** Proficient. Must be able to identify and articulate each SOLID violation during code review; must be able to propose the correct refactoring; must understand the practical trade-offs.

**Where used in the project:**

- `tcg.infrastructure.parsers`: One class per source type; adding a new format requires a new class, not modifying existing ones.
- `tcg.infrastructure.export`: `JSONExporter` and `CSVExporter` are separate classes; a new format adds a class without changing the export use case.
- `tcg.domain.ports`: Six narrowly scoped protocols; no god-interface.
- `tcg.interfaces.cli.main`: Composition root injects concrete implementations; use cases receive protocol types.

**Phase:** `MVP`

---

### 7.3 Design Patterns

**Purpose:** Provides proven structural solutions for recurring design problems — parser selection, port registration, result composition, retry logic — without over-engineering one-off solutions.

**Why required:** The specification implies several well-known patterns: Strategy (for parser selection), Registry (for parser and exporter registration), Result (for `ProcessingResult[T]`), Chain of Responsibility (for validation gates), and Adapter (for AI and storage ports). A developer who recognizes these patterns implements them consistently; one who does not reinvents them poorly.

**Expected competency:** Working knowledge. Must recognize and apply the patterns implied by the specification. Must not apply patterns for their own sake; the goal is clarity and replaceability, not pattern count.

**Where used in the project:**

- Strategy + Registry: `ISourceParser` registry in the input processing layer; `IExporter` registry in the export layer.
- Result/Either: `ProcessingResult[T]` as the return type for fallible operations.
- Chain of Responsibility: Validation gates executed in sequence with early exit on blocking failure.
- Adapter: `OpenAIAdapter` adapts the OpenAI API to the `IAIProvider` protocol.
- Template Method: `PromptBuilder` with versioned template strings.

**Phase:** `MVP`

---

### 7.4 Git

**Purpose:** Provides version control for all source code, configuration, prompt templates, schema definitions, fixture files, and documentation.

**Why required:** The specification requires that prompt templates, schemas, and validation rules be versioned. Versioning is not meaningful without a version control system. Additionally, the audit record for a generation run must identify the prompt version and schema version that were active; this is only reliable when those artifacts are in version control with traceable tags or commit references.

**Expected competency:** Working knowledge. Must understand branching, merging, conflict resolution, `git log`, tags, and how to write meaningful commit messages. Must know how to keep secrets out of the repository (`.gitignore`, pre-commit hooks).

**Where used in the project:**

- `config/prompt_templates/`: Version-tagged prompt template files; version string embedded in file name and in `SchemaRegistry`.
- `config/schema_v1.0.json`: Versioned schema file checked into the repository.
- `.env.example`: Committed to the repository as a template; `.env` is git-ignored.
- Pre-commit hooks: Prevent secrets from being committed.

**Phase:** `MVP`

---

### 7.5 GitHub

**Purpose:** Provides the shared repository, pull-request workflow, branch-protection rules, and CI/CD trigger integration for the project.

**Why required:** The code-quality gates (`mypy`, `ruff`, `pytest`, `pip-audit`) must run automatically on every pull request. Branch protection rules must prevent direct pushes to the main branch and require passing CI before merge. These controls are GitHub-enforced and require familiarity with GitHub Actions and repository settings.

**Expected competency:** Working knowledge. Must understand pull requests, code review, branch protection rules, and GitHub Actions workflow YAML.

**Where used in the project:**

- `.github/workflows/`: CI/CD pipeline definitions running linting, type checking, tests, and dependency audit.
- Branch protection on `main`: Requires passing CI and at least one code review before merge.
- GitHub repository settings: Secrets for CI (e.g. `TCG_AI_API_KEY` for integration test environments) stored as repository secrets, not in workflow files.

**Phase:** `MVP`

---

### 7.6 CI/CD

**Purpose:** Automates the code-quality gates, test suite execution, dependency audit, and packaging on every pull request and merge to main.

**Why required:** The specification's code-quality gates (`spec.md §23.4`) must be enforced automatically, not selectively. Manual enforcement is unreliable. A CI pipeline that runs on every push prevents quality regressions from reaching the main branch and provides a verifiable quality record for each release.

**Expected competency:** Working knowledge. Must be able to write and maintain GitHub Actions workflow YAML; must understand job dependency ordering, environment variable injection from repository secrets, caching for faster runs, and how to publish test and coverage reports.

**Where used in the project:**

- `.github/workflows/ci.yml`: Runs `ruff`, `mypy`, `pytest --cov`, and `pip-audit` on every pull request and push to main.
- CI secrets: AI provider keys used in integration test environments are stored as GitHub repository secrets.
- Release workflow: Tags a release when all quality gates pass on the main branch.

**Phase:** `MVP`

---

### 7.7 Code Quality

**Purpose:** Enforces consistent formatting, linting, type safety, test coverage, and dependency hygiene across the entire codebase.

**Why required:** The constitution's coding standards require type hints, meaningful names, documented public interfaces, automated formatting and linting, and a test suite that is deterministic and isolated. Code quality tools (`ruff`, `mypy`, `pytest-cov`, `pip-audit`) operationalize these standards into automated gates that prevent violations from entering the codebase.

**Expected competency:** Working knowledge. Must be able to configure and use `ruff` (formatting and linting), `mypy --strict` (type checking), `pytest-cov` (coverage measurement), and `pip-audit` (dependency vulnerability scanning). Must understand how to suppress a rule with a documented justification rather than blanket suppression.

**Where used in the project:**

- `pyproject.toml`: Tool configuration for `ruff`, `mypy`, `pytest`, and `coverage`.
- CI pipeline: All four tools run as blocking gates on every pull request.
- Pre-commit hooks: `ruff --fix` and `mypy` run locally before commit.
- Coverage threshold: ≥ 85% line coverage for `tcg.domain` and `tcg.application`; ≥ 70% overall.

**Phase:** `MVP`

---

## 8. Security

### 8.1 Sensitive Data Handling

**Purpose:** Governs how classified source documents, extracted business requirements, payment data, and other confidential information are handled throughout the processing pipeline.

**Why required:** The application processes banking and payment BRDs that may contain business rules about transfer limits, card payment flows, customer data handling, and regulatory obligations. This content must be protected from unnecessary exposure in logs, exports, test case fields, AI prompts, and error messages. Mishandling is a regulatory and organizational risk.

**Expected competency:** Proficient. Must understand data classification categories (PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED), what constitutes confidential content in a banking context, which pipeline stages may expose content unnecessarily, and how `DataClassification` governs what may be sent to an AI provider.

**Where used in the project:**

- `tcg.domain.models.enums`: `DataClassification` enumeration applied to every `GenerationRun` and `SourceMetadata`.
- `tcg.application.use_cases.ingest_source`: Applies classification at intake; stricter classification takes precedence when sources differ.
- `tcg.infrastructure.ai.context_assembler`: Enforces that only content approved for the active `DataClassification` is sent to the AI provider.
- `tcg.infrastructure.export.json_exporter` and `csv_exporter`: Apply data minimization and the `ISensitiveDataScanner` before writing any output.
- `tcg.infrastructure.audit.file_audit_writer`: Records audit events without reproducing confidential source content.

**Phase:** `MVP`

---

### 8.2 Secrets Management

**Purpose:** Ensures that API keys, bearer tokens, provider credentials, and other secrets never appear in source code, configuration files, logs, prompts, fixtures, or exported artifacts.

**Why required:** The specification (`spec.md §18.3`) requires that all secrets be read from environment variables at runtime. A single accidental commit of a live API key to a public or internal repository creates an immediate credential-compromise risk. In a banking context, the consequences of credential exposure can extend to regulatory and financial liability.

**Expected competency:** Proficient. Must understand environment-variable-based secret injection, `.gitignore` and `.env.example` patterns, pre-commit secret-scanning hooks (e.g. `detect-secrets` or `gitleaks`), and how to rotate a compromised secret without downtime. Must understand why `AIProviderConfig.api_key_env_var` stores the variable name, not the value.

**Where used in the project:**

- `tcg.config.settings`: `api_key_env_var` field stores the environment variable name; the actual key is read with `os.environ.get()` at call time only.
- `.env.example`: Documents required variable names with placeholder values; never contains real secrets.
- Pre-commit hooks and CI pipeline: Secret-scanning tools check for committed credentials on every push.
- `tcg.infrastructure.ai.openai_adapter`: Reads the API key from the environment at instantiation time; never stores it as an attribute.

**Phase:** `MVP`

---

### 8.3 Secure Logging

**Purpose:** Ensures that operational logs and audit records contain enough information to diagnose failures and support accountability without reproducing confidential source text, secrets, AI prompts, raw model responses, or PII.

**Why required:** A log file that contains raw AI prompts would reproduce the confidential source text sent to the model. A log that records error details for an AI key rejection might include the key in the exception message. In a banking environment, log files are often stored and retained by infrastructure teams and may be accessible beyond the development team.

**Expected competency:** Proficient. Must understand what must never appear in logs (secrets, raw source text, full prompts, raw AI responses, card numbers, passwords), how to write diagnostic messages that identify the failure without reproducing the data, how to use structured logging (JSON log format), and how to use log levels correctly.

**Where used in the project:**

- `tcg.infrastructure`: All `logger.error()` and `logger.warning()` calls must use message templates that reference source IDs, stage names, and error codes — never raw content.
- `tcg.infrastructure.security.redactor`: Applied to any string before it is logged when there is a risk of sensitive content.
- `tcg.infrastructure.audit.file_audit_writer`: Audit records use IDs, timestamps, actions, and version metadata; never reproduce source text beyond what policy permits.
- `tcg.config.settings`: `logging.format: "json"` recommended for production to support structured log analysis.

**Phase:** `MVP`

---

### 8.4 Access Control

**Purpose:** Enforces that only authorized principals can access specific projects, sources, cases, reports, and audit records, and that a resource in one project cannot be accessed by a principal authorized only for another project.

**Why required:** The PRD requires project isolation as a non-negotiable rule. A banking application that processes multiple product BRDs from different business units must ensure that a tester working on a payments project cannot access an unrelated lending project's requirements or generated cases. Access control must be enforced at every use-case entry point, not only at the interface layer.

**Expected competency:** Proficient. Must understand role-based access control (RBAC) models, least-privilege principle, project isolation as a security boundary, and how to implement authorization checks that are called at every use-case entry point without relying on the caller to remember to call them.

**Where used in the project:**

- `tcg.infrastructure.security.access_control`: `AccessController.authorize()` is called at the start of every use case.
- `tcg.application.use_cases`: Every use case calls `access_controller.authorize()` with the principal, action, resource type, resource ID, and project ID before performing any domain operation.
- `tcg.domain.models.enums`: `Role` enumeration defines the four built-in roles and their permitted actions.
- Security tests: `tests/unit/infrastructure/test_access_control.py` verifies authorization decisions for each role and each cross-project access attempt.

**Phase:** `MVP`

---

### 8.5 Data Masking

**Purpose:** Replaces sensitive values — card numbers, account numbers, passwords, tokens, PII — with safe placeholders before content is logged, stored in test cases, or exported.

**Why required:** Test cases for banking features must reference test data. That test data must never contain real card numbers, real account numbers, real customer names, or live credentials. The `Redactor` and `SensitiveDataScanner` provide the technical controls; but these controls are only correctly designed if someone with data-masking expertise defines the patterns, the replacement tokens, and the rule for when masking is required vs. when the data should simply be excluded.

**Expected competency:** Proficient. Must understand what constitutes sensitive data in the banking context (PAN, CVV, IBAN, account number, sort code, customer reference, national ID), how to write robust detection patterns that minimize false negatives without excessive false positives, and how to represent masked test data in a way that is still useful to a tester (e.g. "a valid UK IBAN in the test IBAN range" rather than a real IBAN).

**Where used in the project:**

- `tcg.infrastructure.security.redactor`: Pattern-based masking; configurable additional patterns per project or classification.
- `tcg.infrastructure.security.sensitive_scanner`: Pre-export and pre-log scan; returns `ScanMatch` objects with field path and pattern name, never the matched value.
- `tcg.domain.models.test_case`: `TestDataItem.is_masked: true` field indicates a value has been masked or is represented by a characteristic description.
- `tcg.infrastructure.ai.context_assembler`: Applies the `Redactor` to assembled context before it is included in any AI prompt.
- `tests/unit/infrastructure/test_sensitive_scanner.py` and `test_redactor.py`: Verified against banking-specific synthetic patterns.

**Phase:** `MVP`

---

## Skills Matrix Summary

The following table summarizes the mandatory MVP skills and the future-phase skills for planning and hiring purposes.

| Category | Skill | Phase | Minimum Competency |
|---|---|---|---|
| Python Development | Python 3.11+ | MVP | Proficient |
| Python Development | Object-oriented programming | MVP | Proficient |
| Python Development | Type hints | MVP | Proficient |
| Python Development | Exception handling | MVP | Proficient |
| Python Development | File processing | MVP | Working knowledge |
| Python Development | Package management | MVP | Working knowledge |
| Python Development | Unit testing with pytest | MVP | Proficient |
| Document Processing | PDF parsing | MVP | Proficient |
| Document Processing | DOCX processing | MVP | Working knowledge |
| Document Processing | Text extraction | MVP | Working knowledge |
| Document Processing | Structured document processing | MVP | Working knowledge |
| Document Processing | Table extraction | MVP | Working knowledge |
| Document Processing | PDF flow/diagram interpretation | MVP | Advanced |
| JIRA Integration | JIRA REST API concepts | MVP | Working knowledge |
| JIRA Integration | User stories | MVP | Working knowledge |
| JIRA Integration | Acceptance criteria | MVP | Proficient |
| JIRA Integration | Issue metadata | MVP | Working knowledge |
| JIRA Integration | Requirement extraction from JIRA | MVP | Proficient |
| AI/LLM | Prompt engineering | MVP | Advanced |
| AI/LLM | Requirement understanding | MVP | Proficient |
| AI/LLM | Test scenario generation | MVP | Proficient |
| AI/LLM | Structured output generation | MVP | Proficient |
| AI/LLM | Context management | MVP | Proficient |
| AI/LLM | Hallucination prevention | MVP | Advanced |
| AI/LLM | AI response validation | MVP | Proficient |
| Testing Skills | Functional testing | MVP | Proficient |
| Testing Skills | Regression testing | MVP | Working knowledge |
| Testing Skills | Integration testing | MVP | Working knowledge |
| Testing Skills | End-to-end testing | MVP | Working knowledge |
| Testing Skills | Negative testing | MVP | Working knowledge |
| Testing Skills | Boundary value analysis | MVP | Working knowledge |
| Testing Skills | Equivalence partitioning | MVP | Working knowledge |
| Testing Skills | Requirement traceability | MVP | Proficient |
| Banking/Payment | Fund transfers | FUTURE | Working knowledge (recommended) |
| Banking/Payment | Payment processing | FUTURE | Working knowledge |
| Banking/Payment | SWIFT / NEFT / RTGS | FUTURE | Working knowledge |
| Banking/Payment | Card payments (data security) | MVP | Working knowledge |
| Banking/Payment | Payment gateways | FUTURE | Working knowledge |
| Banking/Payment | Validation and exception handling | MVP / FUTURE | Working knowledge |
| Banking/Payment | Regulatory and compliance | FUTURE | Working knowledge |
| Software Engineering | Clean architecture | MVP | Advanced |
| Software Engineering | SOLID principles | MVP | Proficient |
| Software Engineering | Design patterns | MVP | Working knowledge |
| Software Engineering | Git | MVP | Working knowledge |
| Software Engineering | GitHub | MVP | Working knowledge |
| Software Engineering | CI/CD | MVP | Working knowledge |
| Software Engineering | Code quality tooling | MVP | Working knowledge |
| Security | Sensitive data handling | MVP | Proficient |
| Security | Secrets management | MVP | Proficient |
| Security | Secure logging | MVP | Proficient |
| Security | Access control | MVP | Proficient |
| Security | Data masking | MVP | Proficient |

Skills required at **Advanced** level for MVP: PDF flow/diagram interpretation, prompt engineering, hallucination prevention, and clean architecture. These represent the highest-risk gaps for a team assembling for the first time and should be assessed early in project planning.
