# Technical Specification: AI-Powered Test Case Generator

**Document status:** Draft technical specification  
**Governed by:** `constitution.md` and `prd.md`  
**Language:** Python (≥ 3.11)  
**Architecture:** Clean Architecture with SOLID principles  
**Notation:** This document uses interface and type signatures to describe contracts. These are specifications, not executable code. Implementations must honour every contract described here but may choose libraries and patterns that satisfy the interface.

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Component Architecture](#2-component-architecture)
3. [Input Processing Layer](#3-input-processing-layer)
4. [BRD Document Parser](#4-brd-document-parser)
5. [JIRA User Story Parser](#5-jira-user-story-parser)
6. [PDF and Flow Diagram Processor](#6-pdf-and-flow-diagram-processor)
7. [Text Extraction Layer](#7-text-extraction-layer)
8. [Requirement Normalization Layer](#8-requirement-normalization-layer)
9. [Requirement Traceability Engine](#9-requirement-traceability-engine)
10. [Test Scenario Generation Engine](#10-test-scenario-generation-engine)
11. [Test Case Generation Engine](#11-test-case-generation-engine)
12. [Test Case Validation Engine](#12-test-case-validation-engine)
13. [Output Formatting Layer](#13-output-formatting-layer)
14. [Reporting and Export Layer](#14-reporting-and-export-layer)
15. [Logging and Audit Layer](#15-logging-and-audit-layer)
16. [Data Models](#16-data-models)
17. [Interfaces and Protocols](#17-interfaces-and-protocols)
18. [Configuration Management](#18-configuration-management)
19. [Security Controls](#19-security-controls)
20. [Error Handling](#20-error-handling)
21. [Performance Expectations](#21-performance-expectations)
22. [Scalability Considerations](#22-scalability-considerations)
23. [Testing Approach](#23-testing-approach)
24. [Project Folder Structure](#24-project-folder-structure)

---

## 1. System Architecture

### 1.1 Architectural Style

The application follows **Clean Architecture**. Domain rules are at the centre and have no dependency on infrastructure, AI providers, file formats, or delivery mechanisms. Infrastructure and interface layers depend inward on domain contracts; the domain never depends outward.

```
┌──────────────────────────────────────────────────────────────┐
│  Interfaces Layer  (CLI / future REST API)                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Application Layer  (Use Cases / Orchestration)        │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │  Domain Layer                                    │  │  │
│  │  │  Models · Ports (Protocols) · Domain Services   │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
         ↑ depends inward only
┌──────────────────────────────────────────────────────────────┐
│  Infrastructure Layer                                        │
│  Parsers · Extractors · AI Adapters · Storage · Audit ·     │
│  Exporters · Security · Normalization                        │
└──────────────────────────────────────────────────────────────┘
```

**Dependency rule:** No module in the domain or application layer may import from `infrastructure` or `interfaces`. All cross-boundary calls pass through domain `Port` protocols resolved by dependency injection at composition root.

### 1.2 Layer Responsibilities

| Layer | Package | Responsibilities |
|---|---|---|
| Domain | `tcg.domain` | Immutable data models, port protocols, domain validation rules, traceability logic, coverage logic |
| Application | `tcg.application` | Orchestrate use cases, coordinate domain services, manage run lifecycle, enforce business workflow |
| Infrastructure | `tcg.infrastructure` | Parse files, extract content, call AI providers, persist state, write audit records, export outputs |
| Interfaces | `tcg.interfaces` | Accept user input (CLI commands), present status and results, delegate to use cases |
| Configuration | `tcg.config` | Load, validate, and distribute typed configuration; schema registry |

### 1.3 High-Level Data Flow

```
[User / CLI]
     │
     ▼
[Use Case: IngestSource]
     │  preflight + register metadata
     ▼
[Input Processing Layer]  →  [Source Registry]
     │  parser selection + execution
     ▼
[Parser: BRD | JIRA | Flow PDF]
     │  raw parse result
     ▼
[Text Extraction Layer]
     │  structured extracted content + provenance
     ▼
[Requirement Normalization Layer]
     │  NormalizedRequirement list
     ▼
[Requirement Traceability Engine]
     │  TraceabilityGraph + gap report
     ▼
[Use Case: GenerateTestCases]
     │  scoped evidence package
     ▼
[Test Scenario Generation Engine]
     │  scenario plan per requirement
     ▼
[Test Case Generation Engine]
     │  AI prompt → raw AI response → parsed drafts
     ▼
[Test Case Validation Engine]
     │  validated TestCase list + ValidationReport
     ▼
[Review Workflow]
     │  human edits / approvals / rejections
     ▼
[Reporting and Export Layer]
     │  traceability matrix · coverage report · quality report
     ▼
[Exporter: JSON | CSV]
     │
[Audit Layer]  ←─ every stage emits AuditEvent
```

### 1.4 Deployment Model (Baseline)

The initial baseline is a **local command-line application** with file-system persistence. All components run in a single Python process on an authorized workstation or controlled server. Sensitive source documents never leave the authorized execution environment except when an explicitly approved AI provider call is made, subject to the data-classification and provider-policy controls in Section 19.

No network services, databases, or live external system connectors are assumed for the baseline.

---

## 2. Component Architecture

### 2.1 SOLID Principles Applied

| Principle | Applied as |
|---|---|
| Single Responsibility | Each class and module owns one concept. `BRDParser` parses; `TextExtractor` extracts; `RequirementNormalizer` normalizes. No class crosses more than one layer boundary. |
| Open/Closed | New source types are added by implementing `ISourceParser` without modifying existing parsers or the application layer. New exporters implement `IExporter`. New AI providers implement `IAIProvider`. |
| Liskov Substitution | Every `ISourceParser` implementation is a drop-in replacement. All domain services that accept protocol types accept any conforming implementation. |
| Interface Segregation | Ports are narrowly scoped. `ISourceParser` handles parsing only. `IExporter` handles export only. No god-protocol aggregates unrelated concerns. |
| Dependency Inversion | Use cases receive their dependencies (storage, AI provider, audit writer, parsers) via constructor injection. The composition root in `tcg.interfaces.cli.main` wires concrete implementations to port interfaces. |

### 2.2 Composition Root

The CLI entry point is the only place where infrastructure adapters are instantiated and injected into use cases. Use cases are constructed with the resolved concrete implementations of each required port. This makes all use cases independently testable with in-memory or fixture implementations of each port.

### 2.3 Key Component Map

```
tcg.domain
├── models/
│   source           SourceDocument, SourceMetadata, SourceLocation, ExtractionMethod
│   requirement      NormalizedRequirement, AcceptanceCriterion, RequirementConflict
│   flow             FlowDiagram, FlowNode, FlowEdge, FlowPath
│   test_case        TestCase, TestStep, TestDataItem, SourceReference
│   traceability     TraceLink, TraceabilityGraph, CoverageRecord
│   run              GenerationRun, RunConfig, RunStatus
│   audit            AuditEvent, AuditEventType
│   result           ProcessingResult, ValidationFinding, ValidationReport
│   enums            SourceType, ProcessingStatus, ReviewStatus, TestType, Priority ...
├── ports/
│   source_parser    ISourceParser
│   ai_provider      IAIProvider
│   run_storage      IRunStorage
│   audit_writer     IAuditWriter
│   exporter         IExporter
│   sensitive_scanner ISensitiveDataScanner
└── services/
    traceability     TraceabilityService
    coverage         CoverageService
    deduplication    DeduplicationService
    domain_validator DomainValidationService

tcg.application
└── use_cases/
    create_run        CreateRunUseCase
    ingest_source     IngestSourceUseCase
    process_source    ProcessSourceUseCase
    generate          GenerateTestCasesUseCase
    validate          ValidateTestCasesUseCase
    review            ReviewTestCaseUseCase
    export            ExportResultsUseCase
    report            GenerateReportUseCase

tcg.infrastructure
├── parsers/
│   brd/             DocxBRDParser, PdfBRDParser
│   jira/            JiraJsonImportParser
│   flow/            PdfFlowDiagramParser
├── extraction/
│   text_extractor   TextExtractor
│   table_extractor  TableExtractor
│   diagram_extractor DiagramExtractor
│   ocr_processor    OCRProcessor (approved path only)
├── normalization/
│   normalizer       RequirementNormalizer
├── ai/
│   context_assembler ContextAssembler
│   prompt_builder    PromptBuilder
│   response_parser   AIResponseParser
│   openai_adapter    OpenAIAdapter (implements IAIProvider)
├── storage/
│   file_storage      FileRunStorage (implements IRunStorage)
├── security/
│   redactor          Redactor
│   scanner           SensitiveDataScanner (implements ISensitiveDataScanner)
│   access_control    AccessController
│   file_validator    FileValidator
├── audit/
│   file_audit_writer FileAuditWriter (implements IAuditWriter)
└── export/
    json_exporter     JSONExporter (implements IExporter)
    csv_exporter      CSVExporter (implements IExporter)

tcg.interfaces
└── cli/
    main              composition root and entry point
    commands/         run, ingest, process, generate, validate, review, export, report
```

---

## 3. Input Processing Layer

### 3.1 Responsibilities

- Receive a file path or structured data reference with its declared source type and project association.
- Validate authorization before any content is read.
- Run preflight checks before committing to full parsing.
- Select and delegate to the appropriate parser implementation.
- Register source metadata and processing status in run storage.
- Emit audit events at each stage transition.
- Return a `ProcessingResult` without surfacing any sensitive content in error messages.

### 3.2 Preflight Validation Sequence

The following checks run in this order before parsing begins. Any blocking failure stops the sequence and records the outcome.

1. **Authorization check** — confirm the requesting principal is authorized for the project and the declared data classification.
2. **File existence and access** — confirm the path is readable without trusting the filename or extension alone.
3. **File size check** — compare against the configured `max_file_size_bytes` for the declared source type. Reject and report when over the limit.
4. **Magic-byte and MIME detection** — determine the actual content type from file bytes; reject when it does not match the declared type.
5. **Supported-format check** — confirm the detected type is in the configured supported-format list.
6. **Integrity check** — compute SHA-256 checksum; compare with the supplied checksum when provided.
7. **Duplicate identity check** — verify no source with the same checksum already exists in this run; block silent re-ingestion.
8. **Password protection detection** — detect encrypted or password-protected content and reject with an actionable message.
9. **Corruption detection** — attempt minimal structural validation (e.g. PDF header, ZIP for DOCX) and reject clearly corrupt files.
10. **Language detection** — attempt language identification on a text sample; flag non-English content per the baseline language constraint.
11. **Required metadata check** — confirm that the structured JIRA import contains required fields (story key, summary) before accepting.

### 3.3 `ISourceParser` Selection

`InputProcessingLayer` maintains an ordered registry of `ISourceParser` implementations. Selection calls `parser.accepts(source_metadata)` in registry order and uses the first accepting parser. Parsers are registered at application startup via dependency injection and must not be hard-coded into the intake layer.

### 3.4 Parser Dispatch Interface

```
InputProcessingLayer.ingest(
    source_path: Path,
    declared_type: SourceType,
    project_id: str,
    uploader: str,
    data_classification: DataClassification,
    run_id: str,
    config: IntakeConfig,
) -> ProcessingResult[SourceMetadata]
```

On success returns the registered `SourceMetadata`. On failure returns a `ProcessingResult` with status `FAILED` and a non-sensitive diagnostic message.

### 3.5 Supported Input Formats

| Source type | Baseline supported formats | Not supported (baseline) |
|---|---|---|
| BRD document | `.docx` (OOXML), `.pdf` (text-native or searchable) | `.doc` (legacy binary), `.xls`, `.xlsx`, spreadsheet-only documents |
| JIRA export | `.json` (structured JIRA Cloud export) | Live JIRA REST API (FUTURE) |
| Acceptance criteria | Embedded in JIRA JSON export, or `.json` standalone list | Inline plain-text files without structure |
| E2E flow diagram | `.pdf` (text-native vector, or image-based with approved OCR path) | `.vsdx`, `.drawio`, `.png` standalone image files |

The supported-format list and the file size limits per type are configurable and must be reviewed before production deployment.

---

## 4. BRD Document Parser

### 4.1 Responsibilities

- Accept a validated BRD file path and source metadata.
- Extract all document structure: headings, paragraphs, numbered lists, tables, footnotes, and appendix references.
- Identify explicit requirement identifiers using configured pattern rules.
- Extract business rules, actors, roles, preconditions, constraints, data definitions, and acceptance expectations where present.
- Assign extraction confidence to each element.
- Return a `BRDExtractionResult` that preserves original provenance and an original-fidelity text representation.
- Never modify or write to the source file.

### 4.2 DOCX Parser Design

The DOCX parser uses the OOXML structure (ZIP archive containing `word/document.xml`). It processes the document element tree in document order.

**Extraction targets:**

| Element | Extracted data |
|---|---|
| Paragraph with `Heading` style | Heading level, heading text, ordinal within the document |
| Normal paragraph | Text content, parent heading path (breadcrumb), paragraph index |
| Numbered list item | Item text, list level, parent heading path |
| Table | Table index, caption (if present), all row/cell content with row and column positions |
| Inline text with bold or specific character style | Candidate for business-rule or actor identification (configurable) |
| Core properties | Document title, author, revision number, last modified date |

**Requirement pattern matching:**

The parser applies a configurable list of requirement identifier patterns (regular expressions) against paragraph text. When a match is found, the paragraph is tagged as a candidate requirement with the identifier captured. The pattern list is configured externally and must not be hard-coded. When no patterns match, the paragraph is still extracted; the normalizer decides whether it contains testable behavior.

**Table extraction:**

Tables are extracted as a list of `TableRow` objects each containing `TableCell` objects with their column index and span. The parser must not flatten a table into a single string without preserving row/column structure.

### 4.3 PDF BRD Parser Design

The PDF BRD parser handles text-native and searchable PDFs. It uses a PDF content-stream reader that does not evaluate JavaScript or execute embedded content.

**Detection sequence:**

1. Confirm the PDF version and structure are parseable.
2. Detect whether the PDF is text-native (has readable text content streams) or image-only.
3. For image-only PDFs: if OCR is enabled and approved, delegate to `OCRProcessor`; otherwise mark as `REQUIRES_MANUAL_REVIEW` and do not proceed.
4. For text-native PDFs: extract page-by-page, preserving page number and approximate text ordering.

**Text ordering:**

PDF text extraction does not guarantee reading order. The parser must apply a configurable line-merging strategy (based on bounding-box coordinates) to reconstruct paragraph-level text. Merged text that cannot be reliably ordered must be marked `ORDERING_UNCERTAIN`.

**Boilerplate detection:**

The parser applies configurable rules to identify and tag (but not silently delete) repeated header, footer, page-number, and watermark content. Tagged content is excluded from the normalized requirement pass by default but remains accessible in the raw extraction.

### 4.4 `BRDExtractionResult` structure

```
BRDExtractionResult
  source_id: str
  parse_method: ParseMethod          # DOCX | PDF_TEXT | PDF_OCR
  page_count: int
  extraction_status: ProcessingStatus
  extracted_sections: list[DocumentSection]
  extracted_tables: list[ExtractedTable]
  candidate_requirements: list[CandidateRequirement]
  boilerplate_regions: list[SourceLocation]
  unreadable_regions: list[UnreadableRegion]
  warnings: list[str]
  overall_confidence: float
```

### 4.5 Error Handling

| Condition | Behavior |
|---|---|
| File is not a valid ZIP (DOCX) | Raise `ParserError` with source ID and stage; do not propagate file content |
| PDF has no readable text layers | Return status `REQUIRES_OCR_OR_MANUAL_REVIEW`; do not generate cases |
| Requirement pattern match produces unexpected overlap | Log as warning; keep all matches, flag as ambiguous |
| Table has merged cells that cannot be resolved | Extract available cells; mark table as `PARTIALLY_EXTRACTED` |
| Document exceeds page limit | Extract up to the limit; mark remaining pages as `LIMIT_REACHED` |

---

## 5. JIRA User Story Parser

### 5.1 Responsibilities

- Accept a validated structured JIRA export file (`.json`) or equivalent structured record.
- Extract every story with its stable key, summary, description, acceptance criteria, priority, labels, components, linked issues, and supplied metadata.
- Assign internal criterion IDs when criteria lack explicit identifiers.
- Flag missing required fields, stories with no acceptance criteria, and stories whose description and acceptance criteria conflict.
- Return a `JiraExtractionResult` preserving the original field values.

### 5.2 JIRA JSON Export Format

The parser handles the structured export format produced by the JIRA Cloud project export or an equivalent field-mapped export. The following fields are required; their absence is a validation warning.

| JSON path | Required | Mapped to |
|---|---|---|
| `issues[].key` | Yes | `JiraStory.story_key` |
| `issues[].fields.summary` | Yes | `JiraStory.summary` |
| `issues[].fields.description` | No | `JiraStory.description` |
| `issues[].fields.issuetype.name` | Yes | `JiraStory.issue_type` |
| `issues[].fields.priority.name` | No | `JiraStory.priority` |
| `issues[].fields.status.name` | No | `JiraStory.status` |
| `issues[].fields.labels` | No | `JiraStory.labels` |
| `issues[].fields.components[].name` | No | `JiraStory.components` |
| `issues[].fields.customfield_acceptance_criteria` | No | `JiraStory.raw_acceptance_criteria` |
| `issues[].fields.issuelinks` | No | `JiraStory.linked_issues` |
| `issues[].fields.parent.key` | No | `JiraStory.parent_key` |
| `issues[].fields.created` / `updated` | No | `JiraStory.retrieval_metadata` |

**Custom field mapping:** The field name for acceptance criteria varies between JIRA configurations. The actual field key is configurable (`jira_acceptance_criteria_field`) and defaults to `customfield_acceptance_criteria`. The parser must not hard-code this field name.

### 5.3 Acceptance Criteria Parsing

Raw acceptance criteria text may be in:

- Atlassian Document Format (ADF) JSON — the parser must extract plain text from all inline and block text nodes.
- Plain text or Markdown — the parser splits on numbered list markers, blank lines between Given/When/Then blocks, or bullet characters.
- Structured list — each list item becomes one `AcceptanceCriterion`.

Each criterion receives an internal criterion ID in the format `{story_key}-AC-{ordinal}` when no explicit ID is found in the text. The internal ID is labeled `id_origin: SYSTEM_GENERATED` and the parent story key is always retained.

**Conflict detection:** When a criterion directly contradicts a phrase in the story description (detected by configurable semantic or keyword rules), the parser creates a `RequirementConflict` referencing both locations.

### 5.4 `JiraExtractionResult` structure

```
JiraExtractionResult
  source_id: str
  story_count: int
  stories: list[JiraStory]
  stories_without_criteria: list[str]   # story keys
  stories_with_conflicts: list[str]     # story keys
  missing_required_fields: list[FieldWarning]
  extraction_status: ProcessingStatus
  warnings: list[str]
```

### 5.5 Standalone Acceptance Criteria Import

When acceptance criteria are provided as a separate `.json` file (not embedded in a JIRA export), the file must include for each criterion: a `story_key` linking it to a known story, an optional `criterion_id`, and the `criterion_text`. The parser validates that every criterion references a known story key in the current run; orphan criteria are reported as warnings.

---

## 6. PDF and Flow Diagram Processor

### 6.1 Responsibilities

- Distinguish a flow-diagram PDF from a BRD PDF at the processing level (BRD parser handles text-narrative PDFs; the flow parser handles diagram-bearing PDFs).
- Extract diagram structural elements: nodes, edges, labels, actors, and annotations.
- Reconstruct directed-graph paths including main, alternate, exception, and loop paths.
- Assign confidence scores to every extracted element and path.
- Identify and report ambiguous, disconnected, or missing elements.
- Preserve page, coordinate, and bounding-region provenance for every element.
- Support both text-native vector diagrams and approved OCR-processed image diagrams.

### 6.2 Diagram Detection Heuristic

A PDF page is classified as diagram-bearing when:

- The ratio of vector-path objects to text characters exceeds a configurable threshold, or
- Text content is sparse relative to page area, or
- The page contains recognized shape annotations matching flowchart conventions.

Pages not meeting the diagram threshold within a flow-diagram PDF are reported as warnings (they may contain a legend or notes).

### 6.3 Element Extraction

**For text-native vector PDFs:**

The processor reads PDF annotation objects and path/text objects grouped by proximity. Shape classification uses a configurable shape-type vocabulary (rounded rectangles → activity, diamonds → decision, ovals → start/end, parallelograms → I/O). Shape classification must be treated as a heuristic, never as confirmed semantic meaning. Every classified shape is tagged `is_inferred: true` unless a legend explicitly confirms the convention.

**For image-based PDFs (approved OCR path):**

The page is rendered to an image at a configured DPI, sent to the approved `OCRProcessor`, and the returned text boxes are combined with spatial analysis to infer shapes and connectors. All extracted content from OCR is tagged `extraction_method: OCR` with the OCR engine name and version. Image-based extraction has lower confidence and is always surfaced to the reviewer.

### 6.4 Graph Reconstruction

After element extraction, the `DiagramExtractor` builds a directed graph:

- **Nodes** are extracted shape elements.
- **Directed edges** are drawn from the source shape of each connector to its destination shape, using connector endpoint proximity.
- **Edge labels** are assigned when a text element is positioned adjacent to and associated with a connector.

**Ambiguity rules:**

- A connector whose endpoints cannot be unambiguously assigned to two specific nodes is marked `is_ambiguous: true` and creates an `AmbiguityWarning`.
- A node with no outgoing connector and no `END` classification is marked `DANGLING_NODE`.
- A decision node with fewer than two labeled outgoing edges is marked `INCOMPLETE_DECISION`.

**Path enumeration:**

Paths are enumerated from each `START` node to each `END` node using a depth-limited search (configurable `max_path_depth`). Loops are detected and represented as `LOOP` path type with the repeating edge identified; the loop body is not unrolled to prevent explosion. Paths exceeding the depth limit are truncated and marked `PATH_TRUNCATED`.

### 6.5 `FlowExtractionResult` structure

```
FlowExtractionResult
  source_id: str
  page_count: int
  diagram_count: int
  nodes: list[FlowNode]
  edges: list[FlowEdge]
  paths: list[FlowPath]
  ambiguities: list[AmbiguityWarning]
  incomplete_elements: list[str]         # node or edge IDs
  unreadable_pages: list[int]
  overall_confidence: float
  extraction_status: ProcessingStatus
  warnings: list[str]
```

---

## 7. Text Extraction Layer

### 7.1 Responsibilities

- Provide format-agnostic services used by all parsers: plain-text extraction, table extraction, OCR orchestration, and language detection.
- Maintain separation between raw extraction and semantic interpretation.
- Record extraction method, library name, library version, and confidence for every operation.
- Expose no business-domain logic; serve only as extraction utilities.

### 7.2 `TextExtractor`

Inputs: raw file bytes or a parsed document object from a lower-level library.

Outputs: ordered list of `TextBlock` objects, each with:

```
TextBlock
  block_id: str
  text: str                     # extracted text content
  block_type: BlockType         # HEADING | PARAGRAPH | LIST_ITEM | CAPTION | OTHER
  page_number: int | None
  section_path: list[str]       # e.g. ["3", "3.1", "3.1.2"]
  bounding_box: BoundingBox | None
  extraction_method: ExtractionMethod
  is_reconstructed: bool        # True when ordering was inferred
  confidence: float
  original_style: str | None    # style name from DOCX, for diagnostic use
```

### 7.3 `TableExtractor`

Extracts tables as a `Table` object:

```
Table
  table_id: str
  source_location: SourceLocation
  caption: str | None
  headers: list[str]             # first row or header row if detected
  rows: list[list[TableCell]]
  has_merged_cells: bool
  is_partially_extracted: bool
  confidence: float
```

`TableCell` carries the cell text, row index, column index, row span, and column span. Merged cells are represented by a `TableCell` at the top-left position carrying the full span; downstream cells covered by the merge are represented as empty cells with a `merged_from` reference.

### 7.4 `OCRProcessor`

The `OCRProcessor` is an optional infrastructure component that must be explicitly enabled in configuration (`ocr.enabled: true`) and must name the approved OCR provider (`ocr.provider`). It wraps a single approved OCR library or API and must not fall back to a different engine silently.

Inputs: image bytes (PNG or TIFF at configured DPI) and a page reference.

Outputs: list of `OCRTextRegion` objects with bounding-box coordinates, text content, and per-region confidence scores.

**Safety constraints:**

- Maximum image size per page is configured and enforced before calling the OCR provider.
- OCR output is always tagged `extraction_method: OCR`.
- Any API call to a remote OCR provider is subject to the same data-classification controls as AI provider calls.

### 7.5 Language Detection

The `TextExtractor` applies language detection (configurable library, e.g. `langdetect`) on a sample of the first N characters of the document. The result is stored in `SourceMetadata.language_detected`. When the detected language is not English and the configuration `language.enforce_english: true`, extraction proceeds but the source is flagged `LANGUAGE_WARNING` and a human review item is created. No content is discarded solely because of the language flag.

---

## 8. Requirement Normalization Layer

### 8.1 Responsibilities

- Accept `BRDExtractionResult`, `JiraExtractionResult`, and `FlowExtractionResult` outputs from all parsers in a run.
- Produce a canonical list of `NormalizedRequirement` objects with stable internal IDs.
- Preserve original source representations alongside normalized ones.
- Assign an `IDOrigin` to distinguish business-owned identifiers from system-generated ones.
- Detect and record duplicate, superseded, conflicting, and near-identical requirements across sources.
- Link requirements to their acceptance criteria and to related flow nodes when evidence supports the link.
- Report all gaps, conflicts, and ambiguities as `NormalizationIssue` objects rather than resolving them silently.

### 8.2 Normalization Steps

**Step 1 — Identifier assignment:**

For each candidate requirement or story:
- If an explicit business identifier is found (BRD requirement ID, JIRA story key, or acceptance-criterion ID), use it as `business_id`.
- If no explicit identifier exists, generate a deterministic internal ID: `{source_id}-REQ-{sha256_of_normalized_text[:8]}`. Tag `id_origin: SYSTEM_GENERATED` and retain the source location.
- Store the internal `requirement_id` as a stable UUID separate from `business_id`.

**Step 2 — Text normalization:**

- Strip leading/trailing whitespace and normalize internal whitespace.
- Convert Unicode curly quotes, en dashes, and similar to ASCII equivalents for comparison purposes only.
- Store the normalized text in `normalized_text`; the original text is preserved in `original_text`.
- Do not alter domain-specific terminology; normalization is for comparison and indexing, not rewriting.

**Step 3 — Deduplication:**

Compare normalized text across sources using configurable similarity rules:
- Exact match on normalized text → mark the later-dated or lower-priority source as `SUPERSEDED` with a reference to the primary.
- Similarity above a configurable threshold (e.g. 0.85 cosine similarity over TF-IDF vectors) → flag as `NEAR_DUPLICATE` and create a `NormalizationIssue` for human review.
- Do not consolidate automatically; preserve both and require human decision.

**Step 4 — Cross-source linking:**

Attempt to link:
- A BRD requirement to a JIRA story when the story's summary or acceptance criteria text references the BRD requirement identifier.
- A JIRA story to a flow node when the story summary or description mentions a flow step label or actor.
- An acceptance criterion to a flow decision branch when the criterion text matches a branch label.

Links are recorded as `TraceLink` objects with a `link_confidence` and `link_evidence` field. Links with confidence below the configurable threshold are created as `CANDIDATE` links requiring human confirmation.

**Step 5 — Gap identification:**

- BRD requirements with no corresponding JIRA story → `GAP: BRD_NO_STORY`.
- JIRA stories with no acceptance criteria → `GAP: STORY_NO_CRITERIA`.
- Acceptance criteria with no supporting BRD requirement → `GAP: CRITERIA_NO_BRD`.
- Flow path nodes with no linked requirement → `GAP: FLOW_NO_REQUIREMENT`.

### 8.3 `NormalizedRequirement` structure (full)

```
NormalizedRequirement
  requirement_id: str                    # stable internal UUID
  business_id: str | None               # explicit BRD or JIRA identifier
  id_origin: IDOrigin                    # BUSINESS | SYSTEM_GENERATED
  source_id: str
  source_type: SourceType
  source_location: SourceLocation
  requirement_type: RequirementType      # FUNCTIONAL | BUSINESS_RULE | ACTOR |
                                         # CONSTRAINT | DATA | ACCEPTANCE_CRITERION
  original_text: str
  normalized_text: str
  behavior_statement: str                # AI-assist or rule-based extraction of
                                         # the core testable behavior
  actors: list[str]
  preconditions: list[str]
  expected_outcomes: list[str]
  constraints: list[str]
  dependencies: list[str]                # referenced systems or services
  acceptance_criteria: list[AcceptanceCriterion]
  related_requirement_ids: list[str]     # linked by cross-source evidence
  flow_node_ids: list[str]
  unresolved_questions: list[str]
  conflicts: list[RequirementConflict]
  extraction_confidence: float
  normalization_status: ProcessingStatus
```

### 8.4 `RequirementNormalizer` interface

```
RequirementNormalizer.normalize(
    brd_results: list[BRDExtractionResult],
    jira_result: JiraExtractionResult | None,
    flow_results: list[FlowExtractionResult],
    config: NormalizationConfig,
) -> NormalizationResult

NormalizationResult
  requirements: list[NormalizedRequirement]
  issues: list[NormalizationIssue]    # gaps, conflicts, near-duplicates
  trace_links: list[TraceLink]
```

---

## 9. Requirement Traceability Engine

### 9.1 Responsibilities

- Build and maintain a `TraceabilityGraph` representing all many-to-many relationships between sources, requirements, acceptance criteria, flow elements, test scenarios, test cases, and exported artifacts.
- Resolve and validate source references attached to generated test cases.
- Detect and report orphan requirements, untested branches, and weak or missing links.
- Compute coverage metrics for each requirement, story, criterion, and flow path.
- Detect when a source-version change affects existing test-case traceability.
- Support change-impact queries: given a changed source item, return all affected test cases.

### 9.2 TraceabilityGraph Model

The graph is a directed, labelled, weighted multigraph stored as an adjacency list of `TraceLink` objects.

```
TraceLink
  link_id: str
  from_entity_id: str              # requirement_id, criterion_id, node_id, case_id ...
  from_entity_type: EntityType
  to_entity_id: str
  to_entity_type: EntityType
  link_type: LinkType              # REQUIREMENT_TO_STORY | STORY_TO_CRITERION |
                                   # REQUIREMENT_TO_CASE | CASE_TO_SOURCE |
                                   # CRITERION_TO_CASE | FLOW_PATH_TO_CASE | ...
  link_confidence: float
  link_evidence: str               # non-sensitive description of the matching evidence
  link_status: LinkStatus          # CONFIRMED | CANDIDATE | BROKEN | EXCLUDED
  created_by: str                  # NORMALIZER | USER | GENERATOR
  created_at: datetime
```

**Confirmed links** are established by the normalizer when evidence is unambiguous or by a user explicitly.
**Candidate links** are created when confidence is below the threshold and require user confirmation.
**Broken links** result from a source update that removes or changes the referenced element.

### 9.3 Source Reference Resolution

When a `SourceReference` is attached to a test case, the `TraceabilityService` resolves it:

1. Look up the `source_id` in the run's source registry.
2. Confirm the source version in the reference matches the stored source version.
3. Confirm the `location` (page, section, node ID) exists in the corresponding extraction result.
4. If the resolution succeeds, mark the reference `RESOLVED`.
5. If the source has been updated since the case was generated, mark the reference `STALE` and add the case to the re-review queue.
6. If the source ID is not found or the location does not exist, mark the reference `BROKEN` — this is a blocking validation failure.

### 9.4 Coverage Computation

```
CoverageRecord
  entity_id: str
  entity_type: EntityType
  total_applicable_scenario_classes: list[TestType]
  covered_scenario_classes: list[TestType]
  excluded_scenario_classes: list[tuple[TestType, str]]  # (type, reason)
  unresolved_scenario_classes: list[TestType]
  linked_case_ids: list[str]
  coverage_percentage: float    # covered / (covered + uncovered applicable)
  has_approved_case: bool
  orphan: bool                  # no linked case of any status
```

### 9.5 Change-Impact Analysis

When a source document is replaced or updated:

1. Compute the new checksum and detect the version change.
2. Find all `TraceLink` objects referencing elements from the old version.
3. Attempt to re-resolve each reference in the new version by location.
4. References that no longer resolve → marked `BROKEN`; affected test cases → `NEEDS_REREVIEW`.
5. References that resolve to content with changed text → marked `STALE`; affected test cases → `NEEDS_REREVIEW`.
6. Emit an audit event recording the source ID, old and new checksums, and the count of affected test cases.

---

## 10. Test Scenario Generation Engine

### 10.1 Responsibilities

- Accept a scoped set of `NormalizedRequirement` objects, a `TraceabilityGraph`, and a generation scope configuration.
- Produce a `ScenarioPlan` for each requirement listing the applicable scenario classes and the source-evidence rationale for each.
- Record explicitly when a scenario class is not applicable and why.
- Never create scenario-class slots for behaviors not supported by the evidence.
- Pass the `ScenarioPlan` to the Test Case Generation Engine; it is not the final output but the structured evidence assembly for AI consumption.

### 10.2 Scenario Classification Logic

For each `NormalizedRequirement`, the engine evaluates each of the seven mandatory scenario classes:

| Class | Applicability rule | Evidence required |
|---|---|---|
| Positive | Always applicable when any testable behavior exists | A described success path in the source |
| Negative | Applicable when the source describes disallowed inputs, unauthorized actions, or rejection conditions | Explicit rejection, error, or disallowed state described in the source |
| Boundary | Applicable only when the source specifies a numeric, length, date, count, rate, or state limit | Explicit limit value in a requirement, acceptance criterion, or table |
| Validation | Applicable when the source describes required fields, formats, types, or business-rule constraints | Explicit validation rule or requiredness statement |
| Exception | Applicable when the source describes a failure, timeout, retry, unavailable dependency, or recovery | Explicit error-handling or recovery behavior described in the source |
| Integration | Applicable when the source references an external system, service, data store, or integration contract | Explicit system name or interface reference in the source |
| End-to-End | Applicable when a complete flow path from start to end is sufficiently resolved in the flow diagram | A `FlowPath` with `is_complete: true` and `path_type: MAIN or ALTERNATE` |

When a class is not applicable, the engine records `ScenarioApplicability(class, EXCLUDED, reason)`.
When applicability cannot be determined from the evidence alone, the engine records `ScenarioApplicability(class, UNRESOLVED, question)`.
When a class is applicable, it records `ScenarioApplicability(class, APPLICABLE, evidence_summary)`.

### 10.3 `ScenarioPlan` structure

```
ScenarioPlan
  plan_id: str
  requirement_id: str
  source_references: list[SourceReference]
  scenario_applicabilities: list[ScenarioApplicability]
  boundary_values: list[BoundaryValue]      # extracted from source
  validation_rules: list[ValidationRule]    # extracted from source
  integration_points: list[IntegrationPoint]
  flow_paths: list[FlowPath]                # applicable flow paths
  open_questions: list[str]
  created_at: datetime

ScenarioApplicability
  scenario_class: TestType
  status: ApplicabilityStatus   # APPLICABLE | EXCLUDED | UNRESOLVED
  rationale: str
  evidence_refs: list[SourceReference]
```

### 10.4 Evidence Budget

The scenario engine also computes an `EvidenceBudget` per requirement: the maximum number of source-text tokens that should be included in the AI prompt context for this requirement, based on the configured `ai.context_budget_per_requirement` limit. This budget prevents unnecessary source content from being sent to the AI provider.

---

## 11. Test Case Generation Engine

### 11.1 Responsibilities

- Accept one or more `ScenarioPlan` objects.
- Assemble a minimal `EvidencePackage` per plan using `ContextAssembler`.
- Build a versioned, structured `GenerationPrompt` using `PromptBuilder`.
- Call the `IAIProvider` implementation.
- Parse and structurally validate the AI response using `AIResponseParser`.
- Map parsed drafts to `TestCase` domain objects.
- Attach generation metadata to every case.
- Return cases in status `DRAFT` for the validation engine.
- Handle all AI provider errors without surfacing sensitive context in error messages.

### 11.2 `ContextAssembler`

Assembles the evidence sent to the AI model. Must apply data minimization.

**Assembly rules:**

1. Start with the `ScenarioPlan`'s requirement text (normalized, not original confidential text unless the plan explicitly permits original text under the active data-classification policy).
2. Include acceptance criteria text up to the configured budget.
3. Include relevant flow-path step labels (not raw PDF content, only extracted labels).
4. Include boundary values and validation rules as structured data, not free-form source text.
5. Include only the source location references (section, page, story key) as provenance identifiers; do not include surrounding document paragraphs beyond what is necessary.
6. Apply the `Redactor` to the assembled context before use; any redacted item is recorded in the `EvidencePackage.redacted_items` field.
7. Record every included item with its source reference so the response parser can attach accurate traceability.

The assembled context must not exceed the configured token budget. If evidence exceeds the budget, the assembler trims less-critical elements in a documented priority order and records what was omitted in `EvidencePackage.omitted_refs`.

### 11.3 `PromptBuilder`

Builds the structured prompt from versioned prompt templates.

**Prompt structure (logical, not literal):**

- **System/instructions section:** versioned instruction set identifier, schema version, output format specification (JSON), constraints (no invented behavior, cite evidence, flag assumptions, use controlled values), prohibited behaviors.
- **Evidence section:** the assembled `EvidencePackage` content.
- **Output contract section:** explicit JSON schema defining required fields and controlled value enumerations.
- **Separation marker:** a clear boundary between the instructions and the evidence to reduce prompt injection risk.

**Versioning:** The prompt template name and version are recorded in `GenerationMetadata.prompt_version`. A change to any prompt template or instruction set must increment the version and triggers re-evaluation against the test fixture suite before production use.

**Prompt injection mitigation:** The evidence section is clearly delimited and the instructions explicitly state that evidence content cannot override instructions. The `ContextAssembler` applies a configurable blocklist of instruction-like phrases in source text (e.g. "ignore previous instructions") and replaces them with a placeholder before assembly.

### 11.4 `IAIProvider` and `AIProviderConfig`

The `IAIProvider` protocol defines a single operation:

```
IAIProvider.generate(
    prompt: GenerationPrompt,
    config: AIProviderConfig,
) -> AIRawResponse

AIProviderConfig
  provider_name: str              # e.g. "openai"
  model_name: str                 # e.g. "gpt-4o"
  api_key_env_var: str            # name of the env var holding the key (NOT the key)
  max_tokens: int
  temperature: float              # 0.0 for deterministic; low values preferred
  timeout_seconds: int
  retry_policy: RetryPolicy
  data_classification_approved: DataClassification
  region_restriction: str | None
```

The API key is read from the environment variable at call time using `os.environ.get(config.api_key_env_var)`. It is never stored in configuration files, logged, or included in audit records.

**Baseline provider:** `OpenAIAdapter` implementing `IAIProvider` for OpenAI-compatible APIs. Additional providers are added by implementing the protocol.

### 11.5 `AIResponseParser`

Parses the raw AI response string into structured `TestCaseDraft` objects.

**Parsing rules:**

1. Attempt to parse the response as JSON against the output contract schema.
2. If JSON parsing fails: record `AIResponseParseError`, set case status to `GENERATION_FAILED`, and do not silently repair the output.
3. For each parsed case draft: validate that all required fields are present and controlled values are valid.
4. Tag every field with `content_origin: AI_GENERATED`.
5. Extract `source_references` from the model's citations and cross-check each against the `EvidencePackage`. A model-cited reference that does not appear in the evidence package is tagged `UNVERIFIED_CITATION` and triggers an evidence-gate warning.
6. Extract `assumptions` and `open_questions` from designated response fields; these must not be merged into steps or expected results.
7. Truncated responses (incomplete JSON) → mark as `GENERATION_FAILED`.
8. Refused responses → mark as `GENERATION_REFUSED` with the refusal reason; do not create a usable case.

### 11.6 `GenerationMetadata`

```
GenerationMetadata
  run_id: str
  generation_timestamp: datetime
  provider_name: str
  model_name: str
  prompt_version: str
  schema_version: str
  source_versions: dict[str, str]   # source_id → checksum
  retrieval_config_version: str | None
  validation_rule_version: str
  token_count_input: int | None     # if available from provider
  token_count_output: int | None
  evidence_budget_used: int
  evidence_items_omitted: int
```

---

## 12. Test Case Validation Engine

### 12.1 Responsibilities

- Apply all mandatory validation gates from Section 19 of the PRD to every `TestCaseDraft` or `TestCase`.
- Produce a `ValidationReport` per case and per run.
- Enforce that no case with a blocking gate failure is treated as usable or exportable without an explicit override recorded by an authorized user.
- Block sensitive-data leakage before cases are stored or surfaced for review.

### 12.2 Gate Execution Order

Gates run in this order. A blocking gate stops further gate execution for the affected case.

```
1. Input gate         (runs at intake, before parsing)
2. Extraction gate    (after parsing, before normalization)
3. Identity gate      (after normalization)
4. Security gate      (before schema gate — must block sensitive data first)
5. Schema gate
6. Traceability gate
7. Evidence gate
8. Coverage gate
9. Consistency gate
10. Duplication gate
11. Audit gate
12. Review gate       (applied on state transitions, not on generation)
```

### 12.3 Gate Specifications

**Identity gate:**
- `test_case_id` is a non-empty stable UUID.
- `requirement_id` resolves to a known `NormalizedRequirement` in the run.
- `jira_story_id`, when present, resolves to a known story key in the run.
- `schema_version` is a known version in the schema registry.
- **Failure type:** BLOCKING

**Security gate:**
- Run `ISensitiveDataScanner.scan(test_case)` against the full case including all text fields.
- If a secret pattern (API key, password, bearer token), card number pattern, or prohibited PII pattern is found: mark the case `SECURITY_BLOCKED`, redact or quarantine, and emit a security audit event without logging the matched value.
- **Failure type:** BLOCKING

**Schema gate:**
- All required fields are present and non-empty (or explicitly set to the documented not-applicable value with a reason).
- `test_type` is a value from the controlled `TestType` enumeration.
- `review_status` is a value from the controlled `ReviewStatus` enumeration.
- `priority` is a value from the controlled `Priority` enumeration or the documented UNKNOWN value with a rationale.
- `test_steps` contains at least one step with a non-empty action.
- `expected_results` contains at least one non-empty value.
- **Failure type:** BLOCKING

**Traceability gate:**
- At least one `SourceReference` is present.
- Every reference has a non-empty `source_id` and `location`.
- Every reference resolves when passed to `TraceabilityService.resolve_reference()`.
- No reference is marked `BROKEN`.
- **Failure type:** BLOCKING for broken references; WARNING for `STALE` references.

**Evidence gate:**
- No step or expected result contains text flagged by the AI response parser as `UNVERIFIED_CITATION`.
- Assumptions are in the `assumptions` field, not embedded in steps or expected results.
- `open_questions` are separated from expected results.
- No expected result is a placeholder string (configurable pattern list).
- **Failure type:** BLOCKING for unverified citations and placeholders; WARNING for unresolved questions.

**Coverage gate:**
- The case has a `test_type` value that corresponds to a scenario class marked `APPLICABLE` in the associated `ScenarioPlan`.
- The `ScenarioPlan` records whether all applicable classes are addressed or excluded with a reason.
- Unapplied applicable classes are reported as coverage warnings, not blocking failures for individual cases.
- **Failure type:** WARNING

**Consistency gate:**
- `test_steps` reference entities (actors, data fields, system names) that appear in the source evidence or preconditions; unrecognized entities are flagged as warnings.
- The first step's precondition alignment is checked: actors mentioned in the preconditions should be recognizable in the first step.
- The number of expected results at case level is consistent with the narrative structure (multi-step workflows may have multiple expected results).
- **Failure type:** WARNING

**Duplication gate:**
- Compute a case fingerprint: hash of normalized scenario text + test type + primary requirement ID.
- Compare with fingerprints of all cases in the run.
- Exact fingerprint match → `DUPLICATE`; consolidate or record distinct rationale.
- High similarity (configurable threshold) → `NEAR_DUPLICATE` warning.
- **Failure type:** WARNING (blocking only if consolidation policy is configured as strict).

**Audit gate:**
- `GenerationMetadata.run_id` is present and matches the active run.
- `GenerationMetadata.generation_timestamp` is a valid ISO 8601 datetime.
- `GenerationMetadata.schema_version` is registered.
- **Failure type:** BLOCKING

### 12.4 `ValidationReport` structure

```
ValidationReport
  run_id: str
  report_timestamp: datetime
  cases_validated: int
  cases_passed: int
  cases_warning: int
  cases_failed: int
  cases_blocked: int
  gate_summaries: list[GateSummary]

GateSummary
  gate_name: str
  gate_type: GateType        # BLOCKING | WARNING
  cases_passed: int
  cases_failed: int
  representative_findings: list[ValidationFinding]   # de-identified

ValidationFinding
  finding_id: str
  case_id: str
  gate: str
  severity: FindingSeverity  # BLOCKING | WARNING | INFO
  message: str               # non-sensitive diagnostic
  affected_field: str | None
```

---

## 13. Output Formatting Layer

### 13.1 Responsibilities

- Accept validated `TestCase` objects and produce both a machine-readable structured representation and a human-readable representation.
- Apply the configured export policy (approved-only, all with status labels, etc.) before any content leaves the validation pipeline.
- Apply data minimization and the `ISensitiveDataScanner` before formatting output.
- Preserve schema version, source references, review status, and validation status in every output representation.
- Support a review-oriented view that presents evidence excerpts inline, subject to access policy.

### 13.2 Human-Readable Review View

The review view is a structured document (default Markdown with YAML front matter) intended for testers and reviewers. Each test case section includes:

```
## TC-{id}: {scenario}

| Field             | Value                    |
|-------------------|--------------------------|
| Requirement ID    | {requirement_id}         |
| JIRA Story        | {jira_story_id}          |
| Test Type         | {test_type}              |
| Priority          | {priority}               |
| Review Status     | {review_status}          |
| Validation Status | {validation_status}      |
| Schema Version    | {schema_version}         |

### Preconditions
{preconditions as numbered list}

### Test Data
{test_data items as table}

### Test Steps
{steps as numbered table: Step | Action | Expected Result}

### Expected Result (Case Level)
{expected_results}

### Source Evidence
{source_references as formatted list with display_reference}

### Assumptions and Open Questions
{assumptions and open_questions}

### Warnings
{validation_findings with severity WARNING or INFO}
```

The review view must clearly distinguish source-supported content from assumptions and open questions. It must never display raw source text that violates the active data classification without an authorized access check.

### 13.3 Machine-Readable Schema (JSON)

The canonical structured output schema is versioned in the schema registry. Version `1.0` is defined as:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "tcg-test-case-schema-v1.0",
  "type": "object",
  "required": [
    "test_case_id", "schema_version", "requirement_id", "scenario",
    "preconditions", "test_data", "test_steps", "expected_results",
    "priority", "test_type", "source_references", "review_status",
    "validation_status", "generation_metadata"
  ],
  "properties": {
    "test_case_id":        { "type": "string", "format": "uuid" },
    "schema_version":      { "type": "string", "pattern": "^\\d+\\.\\d+$" },
    "requirement_id":      { "type": "string" },
    "jira_story_id":       { "type": ["string", "null"] },
    "jira_story_id_na_reason": { "type": ["string", "null"] },
    "scenario":            { "type": "string", "minLength": 10 },
    "preconditions":       { "type": "array", "items": { "type": "string" } },
    "test_data":           { "type": "array", "items": { "$ref": "#/$defs/TestDataItem" } },
    "test_steps":          { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/TestStep" } },
    "expected_results":    { "type": "array", "minItems": 1, "items": { "type": "string" } },
    "priority":            { "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"] },
    "priority_rationale":  { "type": ["string", "null"] },
    "test_type":           { "enum": ["POSITIVE", "NEGATIVE", "BOUNDARY", "VALIDATION",
                                       "EXCEPTION", "INTEGRATION", "END_TO_END"] },
    "additional_test_types": { "type": "array", "items": { "enum": ["POSITIVE", "NEGATIVE",
                                       "BOUNDARY", "VALIDATION", "EXCEPTION",
                                       "INTEGRATION", "END_TO_END"] } },
    "source_references":   { "type": "array", "minItems": 1,
                             "items": { "$ref": "#/$defs/SourceReference" } },
    "review_status":       { "enum": ["DRAFT", "NEEDS_REVIEW", "NEEDS_CLARIFICATION",
                                       "REJECTED", "APPROVED"] },
    "review_history":      { "type": "array", "items": { "$ref": "#/$defs/ReviewEvent" } },
    "assumptions":         { "type": "array", "items": { "type": "string" } },
    "open_questions":      { "type": "array", "items": { "type": "string" } },
    "validation_status":   { "enum": ["PASSED", "WARNING", "FAILED", "BLOCKED"] },
    "validation_findings": { "type": "array", "items": { "$ref": "#/$defs/ValidationFinding" } },
    "generation_metadata": { "$ref": "#/$defs/GenerationMetadata" },
    "is_superseded_by":    { "type": ["string", "null"] },
    "created_at":          { "type": "string", "format": "date-time" },
    "updated_at":          { "type": "string", "format": "date-time" }
  },
  "$defs": {
    "TestStep": {
      "type": "object",
      "required": ["step_number", "action"],
      "properties": {
        "step_number":     { "type": "integer", "minimum": 1 },
        "action":          { "type": "string", "minLength": 5 },
        "expected_result": { "type": ["string", "null"] }
      }
    },
    "TestDataItem": {
      "type": "object",
      "required": ["description"],
      "properties": {
        "description": { "type": "string" },
        "value":       { "type": ["string", "null"] },
        "is_masked":   { "type": "boolean" },
        "data_type":   { "type": ["string", "null"] }
      }
    },
    "SourceReference": {
      "type": "object",
      "required": ["source_id", "source_type", "display_reference", "confidence"],
      "properties": {
        "source_id":          { "type": "string" },
        "source_type":        { "type": "string" },
        "display_reference":  { "type": "string" },
        "excerpt_hash":       { "type": ["string", "null"] },
        "confidence":         { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "resolution_status":  { "enum": ["RESOLVED", "STALE", "BROKEN", "CANDIDATE"] }
      }
    },
    "ReviewEvent": {
      "type": "object",
      "required": ["event_id", "reviewer", "action", "timestamp"],
      "properties": {
        "event_id":    { "type": "string" },
        "reviewer":    { "type": "string" },
        "action":      { "enum": ["APPROVED", "REJECTED", "EDITED", "COMMENTED",
                                   "REQUESTED_CLARIFICATION", "RE_REVIEWED"] },
        "reason":      { "type": ["string", "null"] },
        "timestamp":   { "type": "string", "format": "date-time" },
        "field_diffs": { "type": "array", "items": { "$ref": "#/$defs/FieldDiff" } }
      }
    },
    "FieldDiff": {
      "type": "object",
      "required": ["field_name", "old_value", "new_value"],
      "properties": {
        "field_name": { "type": "string" },
        "old_value":  {},
        "new_value":  {}
      }
    },
    "ValidationFinding": {
      "type": "object",
      "required": ["finding_id", "gate", "severity", "message"],
      "properties": {
        "finding_id":     { "type": "string" },
        "gate":           { "type": "string" },
        "severity":       { "enum": ["BLOCKING", "WARNING", "INFO"] },
        "message":        { "type": "string" },
        "affected_field": { "type": ["string", "null"] }
      }
    },
    "GenerationMetadata": {
      "type": "object",
      "required": ["run_id", "generation_timestamp", "schema_version", "prompt_version"],
      "properties": {
        "run_id":                    { "type": "string" },
        "generation_timestamp":      { "type": "string", "format": "date-time" },
        "provider_name":             { "type": "string" },
        "model_name":                { "type": "string" },
        "prompt_version":            { "type": "string" },
        "schema_version":            { "type": "string" },
        "source_versions":           { "type": "object" },
        "validation_rule_version":   { "type": "string" },
        "token_count_input":         { "type": ["integer", "null"] },
        "token_count_output":        { "type": ["integer", "null"] }
      }
    }
  }
}
```

### 13.4 CSV Schema

The CSV export maps each `TestCase` to one row. Multi-value fields (test steps, source references, preconditions) are serialized as JSON-encoded strings within their column. Required columns and their exact header names are defined in the schema registry alongside the JSON schema.

| Column header | Source field | Notes |
|---|---|---|
| `test_case_id` | `test_case_id` | UUID |
| `schema_version` | `schema_version` | |
| `requirement_id` | `requirement_id` | |
| `jira_story_id` | `jira_story_id` | Empty string when N/A |
| `scenario` | `scenario` | |
| `preconditions` | `preconditions` | JSON array string |
| `test_data` | `test_data` | JSON array string |
| `test_steps` | `test_steps` | JSON array string |
| `expected_results` | `expected_results` | JSON array string |
| `priority` | `priority` | |
| `test_type` | `test_type` | |
| `source_references` | `source_references[*].display_reference` | Pipe-separated |
| `review_status` | `review_status` | |
| `validation_status` | `validation_status` | |
| `assumptions` | `assumptions` | JSON array string |
| `open_questions` | `open_questions` | JSON array string |
| `generation_run_id` | `generation_metadata.run_id` | |
| `generated_at` | `generation_metadata.generation_timestamp` | |

---

## 14. Reporting and Export Layer

### 14.1 Responsibilities

- Generate all mandatory reports defined in PRD Section 23.
- Apply access control, export policy, data minimization, and sensitive-data scanning before any output is produced.
- Support filter-based export scoping.
- Preserve stable IDs, schema version, and traceability through export.

### 14.2 Mandatory Report Types

**Generation Summary Report:**

```
GenerationSummaryReport
  run_id: str
  run_timestamp: datetime
  project_id: str
  source_count: int
  source_statuses: dict[ProcessingStatus, int]
  requirements_identified: int
  stories_identified: int
  criteria_identified: int
  flow_nodes_identified: int
  flow_paths_identified: int
  cases_generated: int
  cases_by_test_type: dict[TestType, int]
  cases_by_priority: dict[Priority, int]
  cases_by_validation_status: dict[ValidationStatus, int]
  warnings_count: int
  failures_count: int
  unresolved_questions_count: int
  run_duration_seconds: float
  schema_version: str
  model_name: str
  prompt_version: str
```

**Traceability Matrix:**

Tabular mapping of every requirement, story, and acceptance criterion to all associated test cases and their review status. Orphan requirements (no associated case) are listed separately. Produced as a structured JSON object and a human-readable Markdown table.

**Coverage Report:**

Per-requirement, per-story, per-criterion, and per-flow-path coverage record listing applicable scenario classes, which are covered, which are excluded with reasons, and which are unresolved.

**Quality Report:**

Gate-by-gate summary with counts of passed, warned, failed, and blocked cases. Lists representative non-sensitive findings per gate. Does not include full test-case content.

**Review Report:**

Counts of cases by review status. Lists cases awaiting clarification. Counts of approvals and rejections with timestamps and reviewers.

**Change Impact Report:**

Lists test cases whose source references are `STALE` or `BROKEN` following a source update. Groups by affected source and change type.

### 14.3 `IExporter` Protocol

```
IExporter.accepts(format: ExportFormat) -> bool
IExporter.export(
    cases: list[TestCase],
    config: ExportConfig,
    scanner: ISensitiveDataScanner,
) -> ExportResult

ExportConfig
  format: ExportFormat               # JSON | CSV
  output_path: Path
  include_review_statuses: set[ReviewStatus]
  include_validation_statuses: set[ValidationStatus]
  require_approved: bool             # if True, only APPROVED cases
  redact_source_excerpts: bool
  schema_version: str

ExportResult
  output_path: Path
  case_count: int
  redacted_field_count: int
  blocked_case_count: int
  export_timestamp: datetime
  schema_version: str
```

### 14.4 Export Policy Enforcement

Before writing any case to the export:

1. Apply the access policy: confirm the requesting principal is authorized to export from this project.
2. Apply the review-status filter from `ExportConfig`.
3. If `require_approved: true`, exclude any non-APPROVED case. If `require_approved: false`, label non-approved cases with their review status in the export.
4. Run `ISensitiveDataScanner.scan(case)` on every case. Block cases that fail the security gate.
5. Apply redaction to source-excerpt fields when `redact_source_excerpts: true`.
6. Emit an audit event recording the export: requester, run ID, filter config, case count, blocked count, format, destination path hash (not the path itself if it is sensitive).

---

## 15. Logging and Audit Layer

### 15.1 Operational Logging

**Logger hierarchy:**

```
tcg                         # root logger
tcg.intake                  # intake and preflight
tcg.parsing                 # all parsers
tcg.extraction              # text and diagram extraction
tcg.normalization           # requirement normalizer
tcg.traceability            # traceability engine
tcg.generation              # scenario and test case generation
tcg.validation              # validation engine
tcg.review                  # review workflow
tcg.export                  # export and report
tcg.security                # security events (separate handler recommended)
tcg.ai                      # AI provider interactions
```

**Log record fields:**

Every log record must include at minimum:

```
timestamp    ISO 8601 UTC
level        DEBUG | INFO | WARNING | ERROR | CRITICAL
logger       logger name from the hierarchy
run_id       correlation identifier (empty string if no active run)
source_id    relevant source ID (empty string if not applicable)
message      non-sensitive diagnostic message
```

For structured (JSON) logging, add:

```
component    module path
event_type   short event label for filtering
```

**Prohibited log content:** API keys, bearer tokens, passwords, file contents, raw source text, raw AI prompts, raw AI responses, payment card data, personal identifiers beyond those required for auditability, internal file paths that expose sensitive information.

**Log levels:** Use `DEBUG` for trace-level diagnostic detail that is never enabled in production by default. Use `INFO` for normal state transitions. Use `WARNING` for recoverable non-fatal issues. Use `ERROR` for failures that affect processing. Use `CRITICAL` for security events and unrecoverable failures.

### 15.2 Audit Records

Audit records are immutable append-only records distinct from operational logs. They are written by all components via `IAuditWriter` and must not be modified after the fact.

**`AuditEvent` structure:**

```
AuditEvent
  event_id: str              # UUID
  event_type: AuditEventType
  run_id: str
  actor: str                 # principal name or service identifier
  target_type: str           # e.g. "source", "test_case", "run"
  target_id: str             # the entity being acted upon
  action: str                # e.g. "APPROVED", "EXPORTED", "REJECTED"
  outcome: str               # SUCCESS | FAILURE | PARTIAL
  reason: str | None         # non-sensitive reason
  metadata: dict[str, str]   # non-sensitive key-value pairs (versions, counts)
  timestamp: datetime
```

**`AuditEventType` enumeration:**

```
RUN_CREATED | RUN_CONFIGURED | RUN_STATUS_CHANGED
SOURCE_REGISTERED | SOURCE_PREFLIGHT | SOURCE_PARSED | SOURCE_EXCLUDED | SOURCE_DELETED
EXTRACTION_COMPLETED | EXTRACTION_WARNING | EXTRACTION_FAILED
NORMALIZATION_COMPLETED | CONFLICT_DETECTED | GAP_IDENTIFIED
GENERATION_REQUESTED | GENERATION_COMPLETED | GENERATION_FAILED | GENERATION_RETRIED
VALIDATION_GATE_PASSED | VALIDATION_GATE_FAILED | VALIDATION_OVERRIDDEN
CASE_CREATED | CASE_EDITED | CASE_APPROVED | CASE_REJECTED | CASE_CLARIFICATION_REQUESTED
CASE_REREVIEW_TRIGGERED | CASE_SUPERSEDED
EXPORT_CREATED | EXPORT_BLOCKED | EXPORT_COMPLETED | EXPORT_FAILED
REPORT_GENERATED
SECURITY_EVENT | SENSITIVE_DATA_DETECTED | REDACTION_APPLIED
ACCESS_DENIED | POLICY_CHANGED | ADMIN_ACTION
RETENTION_EXPIRY | ARTIFACT_DELETED
```

**`IAuditWriter` implementations:**

- `FileAuditWriter` (baseline): writes newline-delimited JSON records to a configured audit log file. The file path is separate from the operational log path. File permissions must restrict write access to the application and read access to authorized users only.

**Audit integrity:** Audit records must not be modifiable by the application after they are written. Deletion of audit records must itself generate an audit event if the deletion is permitted. The audit file must not be truncated or overwritten.

### 15.3 Security Event Logging

Security-relevant events (access denied, sensitive data detected, redaction applied, provider policy violation) are written to both the operational `tcg.security` logger and as `AuditEventType.SECURITY_EVENT` records. The security audit path should be separate from the general audit log and protected by stricter access controls.

Security log records must never include the sensitive value that triggered the event. They record: the event type, the source or field where the detection occurred (as an ID or label, not content), the action taken, and the timestamp.

---

## 16. Data Models

### 16.1 Enumeration Definitions

```
SourceType: BRD_DOCX | BRD_PDF | JIRA_EXPORT | ACCEPTANCE_CRITERIA | FLOW_DIAGRAM_PDF

DataClassification: PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED

ProcessingStatus:
  QUEUED | PROCESSING | COMPLETED | COMPLETED_WITH_WARNINGS |
  FAILED | BLOCKED | REQUIRES_OCR_OR_MANUAL_REVIEW |
  LANGUAGE_WARNING | LIMIT_REACHED | EXCLUDED

ExtractionMethod: DOCX_PARSER | PDF_TEXT | PDF_OCR | JIRA_STRUCTURED | MANUAL

IDOrigin: BUSINESS | SYSTEM_GENERATED

RequirementType: FUNCTIONAL | BUSINESS_RULE | ACTOR | CONSTRAINT | DATA | ACCEPTANCE_CRITERION

NodeType: START | END | ACTIVITY | DECISION | MERGE | ANNOTATION | UNKNOWN

EdgeType: NORMAL | ALTERNATE | EXCEPTION | LOOP | UNKNOWN

PathType: MAIN | ALTERNATE | EXCEPTION | LOOP

LinkType:
  REQUIREMENT_TO_STORY | STORY_TO_CRITERION | REQUIREMENT_TO_CASE |
  CRITERION_TO_CASE | FLOW_PATH_TO_CASE | CASE_TO_SOURCE

LinkStatus: CONFIRMED | CANDIDATE | BROKEN | EXCLUDED

EntityType: REQUIREMENT | STORY | CRITERION | FLOW_NODE | FLOW_PATH | TEST_CASE | SOURCE

ApplicabilityStatus: APPLICABLE | EXCLUDED | UNRESOLVED

TestType: POSITIVE | NEGATIVE | BOUNDARY | VALIDATION | EXCEPTION | INTEGRATION | END_TO_END

Priority: CRITICAL | HIGH | MEDIUM | LOW | UNKNOWN

ReviewStatus: DRAFT | NEEDS_REVIEW | NEEDS_CLARIFICATION | REJECTED | APPROVED

ValidationStatus: PASSED | WARNING | FAILED | BLOCKED

FindingSeverity: BLOCKING | WARNING | INFO

GateType: BLOCKING | WARNING

ExportFormat: JSON | CSV

AuditEventType: (see Section 15.2)
```

### 16.2 `SourceLocation`

```
SourceLocation
  source_id: str
  page_number: int | None
  section_path: list[str]    # hierarchical section breadcrumb
  paragraph_index: int | None
  table_index: int | None
  row_index: int | None
  column_index: int | None
  node_id: str | None
  edge_id: str | None
  path_id: str | None
  bounding_box: BoundingBox | None

BoundingBox
  x0: float
  y0: float
  x1: float
  y1: float
  coordinate_space: str      # "pdf_points" or "normalized_0_1"
```

### 16.3 `GenerationRun`

```
GenerationRun
  run_id: str                # UUID
  project_id: str
  project_name: str
  feature_context: str | None
  data_classification: DataClassification
  owner: str                 # principal
  reviewers: list[str]
  status: RunStatus          # CREATED | PROCESSING | AWAITING_REVIEW | COMPLETED | FAILED
  created_at: datetime
  updated_at: datetime
  source_ids: list[str]
  generation_config: GenerationConfig
  schema_version: str
  validation_rule_version: str
```

### 16.4 `RetryPolicy`

```
RetryPolicy
  max_attempts: int          # default: 3
  backoff_seconds: float     # base delay for exponential backoff
  max_backoff_seconds: float
  retryable_status_codes: list[int]   # e.g. [429, 503, 504]
```

---

## 17. Interfaces and Protocols

All protocols are defined using `typing.Protocol` with `@runtime_checkable` where interface checks are needed. No concrete implementation may be imported by use cases; all dependency injection is through the protocol type.

### 17.1 `ISourceParser`

```
class ISourceParser(Protocol):
    def accepts(self, metadata: SourceMetadata) -> bool:
        """Return True if this parser can handle the given source type and format."""

    def preflight(
        self, source_path: Path, metadata: SourceMetadata, config: ParserConfig
    ) -> PreflightResult:
        """Run preflight checks without full parsing.
        Returns PreflightResult with status and any blocking issues."""

    def extract(
        self, source_path: Path, metadata: SourceMetadata, config: ParserConfig
    ) -> ProcessingResult[ExtractionResult]:
        """Execute full extraction. Must not modify the source file.
        Returns ProcessingResult with the extraction result or error details."""
```

### 17.2 `IAIProvider`

```
class IAIProvider(Protocol):
    def generate(
        self, prompt: GenerationPrompt, config: AIProviderConfig
    ) -> ProcessingResult[AIRawResponse]:
        """Send a generation prompt to the AI provider.
        Must not log the prompt contents. Returns a ProcessingResult.
        On rate limit or timeout, returns FAILED with a retryable indicator."""

    def get_provider_metadata(self) -> ProviderMetadata:
        """Return provider name, model name, and API version for audit metadata."""
```

### 17.3 `IRunStorage`

```
class IRunStorage(Protocol):
    def create_run(self, run: GenerationRun) -> None: ...
    def load_run(self, run_id: str) -> GenerationRun: ...
    def update_run_status(self, run_id: str, status: RunStatus) -> None: ...

    def register_source(self, run_id: str, metadata: SourceMetadata) -> None: ...
    def load_source_metadata(self, run_id: str, source_id: str) -> SourceMetadata: ...
    def list_sources(self, run_id: str) -> list[SourceMetadata]: ...

    def save_extraction_result(
        self, run_id: str, source_id: str, result: ExtractionResult
    ) -> None: ...
    def load_extraction_result(
        self, run_id: str, source_id: str
    ) -> ExtractionResult | None: ...

    def save_test_case(self, run_id: str, case: TestCase) -> None: ...
    def load_test_case(self, run_id: str, case_id: str) -> TestCase: ...
    def update_test_case(self, run_id: str, case: TestCase) -> None: ...
    def list_test_cases(
        self, run_id: str, filters: TestCaseFilter | None = None
    ) -> list[TestCase]: ...

    def save_traceability_graph(
        self, run_id: str, graph: TraceabilityGraph
    ) -> None: ...
    def load_traceability_graph(self, run_id: str) -> TraceabilityGraph | None: ...
```

### 17.4 `IAuditWriter`

```
class IAuditWriter(Protocol):
    def record(self, event: AuditEvent) -> None:
        """Write an immutable audit record. Must not raise on transient failure;
        must log a CRITICAL operational error and continue if audit write fails."""
```

### 17.5 `IExporter`

```
class IExporter(Protocol):
    def accepts(self, fmt: ExportFormat) -> bool: ...

    def export(
        self,
        cases: list[TestCase],
        config: ExportConfig,
        scanner: ISensitiveDataScanner,
    ) -> ExportResult:
        """Serialize cases to the target format. Must apply scanner before writing.
        Must not write cases that fail the security scan."""
```

### 17.6 `ISensitiveDataScanner`

```
class ISensitiveDataScanner(Protocol):
    def scan(self, obj: Any) -> ScanResult:
        """Scan any serializable object for sensitive data patterns.
        Returns ScanResult with a list of ScanMatch objects.
        Must not log the matched values."""

    def redact(self, text: str) -> tuple[str, int]:
        """Apply redaction to a text string. Returns the redacted string
        and the count of redacted items."""

ScanResult
  has_findings: bool
  findings: list[ScanMatch]   # finding type and field path only, not matched value

ScanMatch
  pattern_name: str           # e.g. "api_key", "card_number"
  field_path: str             # e.g. "test_steps[2].action"
  severity: FindingSeverity
```

---

## 18. Configuration Management

### 18.1 Configuration Layers

Configuration is loaded in this precedence order (highest wins):

1. **Environment variables** (e.g. `TCG_AI_MODEL_NAME`) — required for secrets and deployment-specific values.
2. **User configuration file** (`~/.tcg/config.yaml` or path from `TCG_CONFIG_PATH`) — user-scoped overrides.
3. **Project configuration file** (`.tcg/project.yaml` in the run workspace) — project-scoped overrides.
4. **Built-in defaults** (`tcg/config/defaults.yaml`) — all keys with safe defaults; never includes secrets.

### 18.2 Configuration Schema

The configuration is validated at application startup using a typed settings class (Pydantic BaseSettings recommended). Missing required values that have no default cause a `ConfigurationError` at startup, not at runtime.

```
TCGSettings
  ├── storage: StorageConfig
  │     base_dir: Path                # root directory for run storage
  │     audit_log_path: Path
  │     security_audit_log_path: Path
  │     max_storage_size_bytes: int
  │
  ├── intake: IntakeConfig
  │     max_file_size_brd_bytes: int
  │     max_file_size_flow_bytes: int
  │     max_file_size_jira_bytes: int
  │     supported_brd_formats: list[str]
  │     supported_flow_formats: list[str]
  │     supported_jira_formats: list[str]
  │
  ├── parsers: ParserConfig
  │     brd:
  │       max_pages: int
  │       requirement_id_patterns: list[str]    # regex list
  │       boilerplate_detection_enabled: bool
  │     jira:
  │       acceptance_criteria_field: str
  │     flow:
  │       max_pages: int
  │       max_path_depth: int
  │       diagram_heuristic_threshold: float
  │       shape_type_vocabulary: dict[str, str] # shape → NodeType
  │
  ├── ocr: OCRConfig
  │     enabled: bool
  │     provider: str                 # name only; credentials in env
  │     render_dpi: int
  │     max_image_size_bytes: int
  │
  ├── normalization: NormalizationConfig
  │     similarity_threshold: float
  │     link_confidence_threshold: float
  │
  ├── ai: AIConfig
  │     provider: str                 # "openai" or other registered name
  │     model_name: str               # from env preferred: TCG_AI_MODEL_NAME
  │     api_key_env_var: str          # default: "TCG_AI_API_KEY"
  │     max_tokens: int
  │     temperature: float
  │     timeout_seconds: int
  │     context_budget_per_requirement: int
  │     retry_policy: RetryPolicy
  │     data_classification_approved: DataClassification
  │     region_restriction: str | None
  │
  ├── validation: ValidationConfig
  │     duplication_similarity_threshold: float
  │     duplication_policy: str       # "warn" | "block"
  │     rule_version: str
  │
  ├── export: ExportConfig
  │     default_format: ExportFormat
  │     require_approved_for_export: bool
  │     redact_source_excerpts: bool
  │
  ├── security: SecurityConfig
  │     sensitive_patterns: list[str] # additional regex patterns for scanner
  │     prompt_injection_blocklist: list[str]
  │
  ├── logging: LoggingConfig
  │     level: str                    # "INFO" default
  │     format: str                   # "json" | "text"
  │     log_path: Path | None
  │
  └── language: LanguageConfig
        enforce_english: bool
        detection_sample_chars: int
```

### 18.3 Secret Handling

- API keys, tokens, and provider credentials are read exclusively from environment variables.
- No secret may appear in any YAML, JSON, or TOML configuration file.
- The `.env.example` file must document required environment variable names with placeholder values; it must never contain real secrets.
- The `settings.py` module must refuse to start if a required credential environment variable is empty and there is no default.
- All configuration file paths must be checked for world-readability permissions on startup; a warning is emitted if permissions are too permissive.

### 18.4 Schema Registry

The `SchemaRegistry` class (in `tcg.config.schema_registry`) maintains a mapping of schema version strings to their JSON Schema definitions and CSV column maps. It exposes:

```
SchemaRegistry.get_schema(version: str) -> dict
SchemaRegistry.get_csv_columns(version: str) -> list[CSVColumnDef]
SchemaRegistry.is_known_version(version: str) -> bool
SchemaRegistry.current_version() -> str
```

Adding a new schema version requires adding its definition to the registry and updating the `current_version`. Old versions must remain available for re-validation of existing exports.

---

## 19. Security Controls

### 19.1 File Validation

`FileValidator` performs the following before any file is opened for parsing:

- Read and verify the file magic bytes against a configurable MIME-to-magic-bytes map.
- Enforce the configured size limit per source type before reading.
- For DOCX: verify the ZIP structure is well-formed before expanding.
- For PDF: verify the PDF header signature (`%PDF-`) and that the file is not password-protected (attempt to open without a password; if a password prompt is required, reject with `PASSWORD_PROTECTED` status).
- Never evaluate JavaScript in PDFs.
- Never follow hyperlinks or external references in BRD documents.
- Never execute macros or embedded code of any kind.

### 19.2 Access Control

`AccessController` is called by every use case at the start of execution. It evaluates:

```
AccessController.authorize(
    principal: str,
    action: str,
    resource_type: str,
    resource_id: str | None,
    project_id: str,
) -> AuthorizationResult
```

The authorization model is **role-based** with **project isolation**. A principal may have different roles in different projects. The following built-in roles are defined; their precise permissions are documented in the project configuration.

| Role | Permitted actions |
|---|---|
| `viewer` | Read approved cases and reports for the assigned project |
| `analyst` | Create runs, ingest sources, generate cases, review and approve cases within the assigned project |
| `qa_lead` | All analyst permissions plus configure review rules, release exports, trigger re-review |
| `admin` | All qa_lead permissions plus configure policies, manage access, view audit logs |

A resource in one project must never be accessed by a principal whose authorization is for a different project. `AccessController` must be called even for read operations when the resource is classified above `PUBLIC`.

### 19.3 Redactor

`Redactor` applies pattern-based redaction to text strings. Patterns include:

- Standard configurable patterns for bearer tokens, API keys (common prefixes), password fields, and card numbers.
- Configurable additional patterns per project or data classification.
- The redacted replacement text is a fixed token like `[REDACTED]` that does not embed the original length or character class.
- A `redact()` call returns the redacted string and a count of replacements.
- The original value is never logged; only the count of redactions and the pattern name are recorded.

### 19.4 `SensitiveDataScanner`

Before any case is stored, exported, or surfaced for review, `SensitiveDataScanner.scan()` traverses all string fields in the `TestCase`. It checks:

- Secrets (API key patterns, bearer token patterns, configurable enterprise patterns).
- Payment card number patterns (PAN-like sequences).
- Configurable PII patterns (e.g. SSN-like sequences, email addresses, phone numbers) based on the active data classification.

A case with a `BLOCKING` scan finding is moved to `SECURITY_BLOCKED` status. The matched value is never recorded; only the finding type and field path are logged in the security audit channel.

### 19.5 Prompt Injection Mitigation

Before the `ContextAssembler` includes any source text in a prompt:

1. Apply the `prompt_injection_blocklist` (configurable list of instruction-like phrases).
2. Replace any match with the token `[CONTENT_REDACTED_INJECTION_RISK]`.
3. Record the count of replacements in `EvidencePackage.injection_mitigations`.
4. The `PromptBuilder` uses a clear structural separator between the instructions section and the evidence section.
5. The instructions explicitly state that the evidence section is untrusted source material and cannot override instructions.

---

## 20. Error Handling

### 20.1 Exception Hierarchy

```
TCGError                          # base; all application exceptions
├── ConfigurationError            # invalid or missing config at startup
├── AuthorizationError            # access denied (non-revealing)
├── SourceIngestionError          # intake-phase failures
│   ├── FileTooLargeError
│   ├── UnsupportedFormatError
│   ├── PasswordProtectedError
│   ├── CorruptedFileError
│   └── DuplicateSourceError
├── ParserError                   # parsing-phase failures
│   ├── ExtractionError
│   └── OCRError
├── NormalizationError
├── TraceabilityError
├── GenerationError               # generation-phase failures
│   ├── AIProviderError
│   │   ├── AIProviderUnavailableError
│   │   ├── AIProviderRateLimitError
│   │   └── AIProviderTimeoutError
│   └── AIResponseParseError
├── ValidationError               # gate failures
│   └── SecurityGateError
├── ExportError
├── StorageError
└── AuditError                    # audit write failure (logged at CRITICAL)
```

### 20.2 `ProcessingResult[T]`

All public methods in the infrastructure and application layers that can fail gracefully return a `ProcessingResult[T]` rather than raising an exception directly (exceptions are reserved for programming errors or unrecoverable failures):

```
ProcessingResult[T]
  status: ProcessingStatus
  value: T | None
  errors: list[ProcessingError]
  warnings: list[str]

ProcessingError
  error_code: str
  message: str         # non-sensitive diagnostic
  stage: str
  source_id: str | None
  is_retryable: bool
```

Callers check `result.status` before accessing `result.value`. A FAILED status with `is_retryable: True` may be retried under the retry policy; `is_retryable: False` requires a new run or user intervention.

### 20.3 Partial Success Preservation

When processing a batch of sources or generating cases for a set of requirements:

- Succeed-fast approach: process all items; accumulate errors without aborting the batch.
- Return a `BatchProcessingResult` with per-item results.
- Never discard successfully processed items because of a failure in another item.
- Clearly mark the run as `COMPLETED_WITH_WARNINGS` rather than `COMPLETED` when any item has an error.

### 20.4 Retry Behavior

AI provider calls and external service calls follow the `RetryPolicy`. Before each retry:

1. Log the retry attempt at `WARNING` level with the attempt number and retryable error code (not the error message if it could contain sensitive content).
2. Apply exponential backoff with jitter.
3. Emit an `AuditEvent` of type `GENERATION_RETRIED`.
4. Do not create a new case identity on retry; the same case draft is retried with the same `test_case_id`.
5. After exhausting retries, return `ProcessingResult.FAILED` with `is_retryable: False`.

---

## 21. Performance Expectations

Performance targets apply to the baseline single-process deployment using approved hardware. Targets must be formally validated against an agreed representative corpus before any production release. Until validated, they are design targets only.

| Operation | Input | Design target |
|---|---|---|
| Preflight (all checks) | Any single source file | ≤ 5 seconds |
| DOCX BRD parse | Up to 50 pages | ≤ 30 seconds |
| PDF BRD parse (text-native) | Up to 50 pages | ≤ 60 seconds |
| PDF BRD parse (OCR path) | Up to 20 pages | ≤ 180 seconds |
| JIRA export import | Up to 100 stories | ≤ 15 seconds |
| Flow diagram parse (text-native) | Up to 20 pages | ≤ 60 seconds |
| Flow diagram parse (OCR path) | Up to 10 pages | ≤ 120 seconds |
| Normalization + traceability | Up to 200 requirements | ≤ 60 seconds |
| Test case generation (excl. AI latency) | Up to 50 requirements | ≤ 30 seconds |
| AI provider round-trip | Single generation request | Governed by provider SLA and timeout config |
| Validation (all gates) | Up to 500 cases | ≤ 30 seconds |
| JSON export | Up to 500 cases | ≤ 10 seconds |
| CSV export | Up to 500 cases | ≤ 10 seconds |
| Traceability matrix report | Up to 200 requirements × 500 cases | ≤ 20 seconds |

**Progress reporting:** Any operation expected to take longer than 10 seconds must emit progress events at regular intervals. The CLI must display or log these events so users can observe progress without terminating a legitimate long-running operation.

**Token budget enforcement:** The `ContextAssembler` must enforce the configured `context_budget_per_requirement` and emit a WARNING log when evidence is trimmed, preventing unbounded AI API costs.

---

## 22. Scalability Considerations

### 22.1 Baseline Design Decisions Supporting Future Scale

- **Stateless domain services:** `TraceabilityService`, `CoverageService`, `DeduplicationService`, and `DomainValidationService` are pure functions of their inputs. They hold no mutable process state and can be called in parallel.
- **Pluggable storage port:** `IRunStorage` is the only persistence boundary. Replacing `FileRunStorage` with a database-backed implementation does not require changes to any use case.
- **Pluggable AI provider port:** `IAIProvider` allows substitution of any AI provider, batching strategy, or local model without changing generation orchestration.
- **Scoped generation:** The `GenerateTestCasesUseCase` accepts a generation scope (full run, selected requirement set, selected story, selected flow path). This supports incremental processing and later distribution across workers.
- **Immutable audit events:** Audit events are append-only and can be streamed to any destination (file, queue, database) by replacing the `IAuditWriter` implementation.

### 22.2 Identified Scaling Boundaries

| Component | Current limit | Future scaling path |
|---|---|---|
| `FileRunStorage` | Single-machine file system | Replace with database-backed `IRunStorage` (FUTURE) |
| Serial source processing | N sources processed sequentially | Parallelize with `concurrent.futures.ProcessPoolExecutor` bounded by CPU count |
| Single AI provider call per requirement | Can be slow for large requirement sets | Batch with controlled concurrency; respect provider rate limits |
| In-memory traceability graph | Bounded by available RAM | Serialize graph to storage between stages; lazy-load nodes on demand |
| Single-process execution | One run at a time on one machine | Queue-based run dispatch with worker processes (FUTURE) |

### 22.3 Large-Document Handling

When a source exceeds the configured page limit:

1. Process up to the configured limit.
2. Record `LIMIT_REACHED` in the source processing status.
3. Report the unprocessed page range to the user.
4. Do not generate cases from unprocessed pages.
5. Offer a documented approach to split the source into parts and process each with a linked source set.

---

## 23. Testing Approach

### 23.1 Test Categories

| Category | Target | Tooling |
|---|---|---|
| Unit tests | Domain models, domain services, parser logic, validation gates, redactor, file validator, normalization rules | `pytest`, deterministic fixtures |
| Integration tests | Source-to-extraction, normalization-to-traceability, generation-to-validation, export pipeline | `pytest`, sanitized fixture files |
| Contract tests | `ISourceParser`, `IAIProvider`, `IRunStorage`, `IExporter` implementations against protocol | `pytest` with mock and real adapters |
| Security tests | File validator, sensitive-data scanner, redactor, access control, prompt injection handling | `pytest` with adversarial fixtures |
| Fixture-based AI tests | AI response parser against pre-recorded model responses | `pytest` with recorded fixture responses (no live calls in CI) |
| CLI smoke tests | End-to-end CLI commands with sanitized fixture inputs | `pytest` subprocess or click testing |

### 23.2 Fixture Requirements

- All fixtures must use synthetic or masked data; no production or real customer data.
- BRD fixtures must cover: normal multi-section document, document with explicit requirement IDs, document with tables, document with no identifiable requirements, DOCX with embedded image, scanned PDF (image-only).
- JIRA fixtures must cover: stories with acceptance criteria, stories without acceptance criteria, stories with ADF description, stories with description/criteria conflict, export with missing required fields.
- Flow-diagram fixtures must cover: simple linear flow, branching decision flow, loop, multi-page diagram, image-only PDF, ambiguous connectors, missing start/end nodes.
- Validation fixtures must cover: all-fields-valid case, each blocking gate failure, each warning gate trigger, duplicate case pair, security gate trigger (synthetic secret pattern).
- AI response fixtures must cover: valid JSON response, malformed JSON, truncated response, refused response, response with unverified citations, response with injection-like content.

### 23.3 Test Isolation

- No unit test may call an external AI provider, file system outside `tmp_path`, or live network service.
- All infrastructure adapters used in unit tests must be replaced by in-memory or fixture-backed test doubles.
- Integration tests may use the file system but must clean up via `pytest` fixtures.
- Test doubles for `IAIProvider` return pre-recorded fixture responses.
- The `FileRunStorage` base path in tests points to a `tmp_path` fixture.

### 23.4 Code Quality Gates

Every pull request must pass before merge:

- `mypy --strict` (or equivalent type checker) on the `tcg` package.
- `ruff` (or equivalent linter) with no suppressed errors beyond documented exceptions.
- `pytest` with all unit and integration tests passing.
- `pytest-cov` minimum coverage threshold (target ≥ 85% line coverage for domain and application layers; ≥ 70% overall).
- `pip-audit` (or equivalent) with no known critical vulnerabilities in dependencies.

---

## 24. Project Folder Structure

```
testcasegenerator/
│
├── src/
│   └── tcg/                                   # main package
│       ├── __init__.py
│       │
│       ├── domain/                            # pure domain — no infrastructure imports
│       │   ├── __init__.py
│       │   ├── models/
│       │   │   ├── __init__.py
│       │   │   ├── enums.py                   # all Enum definitions
│       │   │   ├── source.py                  # SourceDocument, SourceMetadata,
│       │   │   │                              #   SourceLocation, BoundingBox
│       │   │   ├── requirement.py             # NormalizedRequirement,
│       │   │   │                              #   AcceptanceCriterion,
│       │   │   │                              #   RequirementConflict, NormalizationIssue
│       │   │   ├── flow.py                    # FlowDiagram, FlowNode, FlowEdge,
│       │   │   │                              #   FlowPath, AmbiguityWarning
│       │   │   ├── test_case.py               # TestCase, TestStep, TestDataItem,
│       │   │   │                              #   SourceReference, ReviewEvent
│       │   │   ├── traceability.py            # TraceLink, TraceabilityGraph,
│       │   │   │                              #   CoverageRecord
│       │   │   ├── run.py                     # GenerationRun, RunConfig,
│       │   │   │                              #   GenerationConfig
│       │   │   ├── result.py                  # ProcessingResult, ProcessingError,
│       │   │   │                              #   ValidationFinding, ValidationReport
│       │   │   ├── audit.py                   # AuditEvent, AuditEventType
│       │   │   └── scenario.py                # ScenarioPlan, ScenarioApplicability,
│       │   │                                  #   BoundaryValue, EvidencePackage
│       │   │
│       │   ├── ports/                         # Protocol definitions only
│       │   │   ├── __init__.py
│       │   │   ├── source_parser.py           # ISourceParser
│       │   │   ├── ai_provider.py             # IAIProvider
│       │   │   ├── run_storage.py             # IRunStorage
│       │   │   ├── audit_writer.py            # IAuditWriter
│       │   │   ├── exporter.py                # IExporter
│       │   │   └── sensitive_scanner.py       # ISensitiveDataScanner
│       │   │
│       │   └── services/                      # pure domain logic
│       │       ├── __init__.py
│       │       ├── traceability_service.py    # TraceabilityService
│       │       ├── coverage_service.py        # CoverageService
│       │       ├── deduplication_service.py   # DeduplicationService
│       │       └── domain_validator.py        # DomainValidationService
│       │
│       ├── application/                       # orchestration — depends on domain only
│       │   ├── __init__.py
│       │   └── use_cases/
│       │       ├── __init__.py
│       │       ├── create_run.py              # CreateRunUseCase
│       │       ├── ingest_source.py           # IngestSourceUseCase
│       │       ├── process_source.py          # ProcessSourceUseCase
│       │       ├── generate_test_cases.py     # GenerateTestCasesUseCase
│       │       ├── validate_test_cases.py     # ValidateTestCasesUseCase
│       │       ├── review_test_case.py        # ReviewTestCaseUseCase
│       │       ├── export_results.py          # ExportResultsUseCase
│       │       └── generate_report.py         # GenerateReportUseCase
│       │
│       ├── infrastructure/                    # concrete implementations
│       │   ├── __init__.py
│       │   │
│       │   ├── parsers/
│       │   │   ├── __init__.py
│       │   │   ├── brd/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── docx_parser.py         # DocxBRDParser (ISourceParser)
│       │   │   │   └── pdf_brd_parser.py      # PdfBRDParser (ISourceParser)
│       │   │   ├── jira/
│       │   │   │   ├── __init__.py
│       │   │   │   └── json_import_parser.py  # JiraJsonImportParser (ISourceParser)
│       │   │   └── flow/
│       │   │       ├── __init__.py
│       │   │       └── pdf_flow_parser.py     # PdfFlowDiagramParser (ISourceParser)
│       │   │
│       │   ├── extraction/
│       │   │   ├── __init__.py
│       │   │   ├── text_extractor.py          # TextExtractor
│       │   │   ├── table_extractor.py         # TableExtractor
│       │   │   ├── diagram_extractor.py       # DiagramExtractor
│       │   │   └── ocr_processor.py           # OCRProcessor
│       │   │
│       │   ├── normalization/
│       │   │   ├── __init__.py
│       │   │   └── requirement_normalizer.py  # RequirementNormalizer
│       │   │
│       │   ├── ai/
│       │   │   ├── __init__.py
│       │   │   ├── context_assembler.py       # ContextAssembler
│       │   │   ├── prompt_builder.py          # PromptBuilder
│       │   │   ├── response_parser.py         # AIResponseParser
│       │   │   └── openai_adapter.py          # OpenAIAdapter (IAIProvider)
│       │   │
│       │   ├── storage/
│       │   │   ├── __init__.py
│       │   │   └── file_storage.py            # FileRunStorage (IRunStorage)
│       │   │
│       │   ├── security/
│       │   │   ├── __init__.py
│       │   │   ├── file_validator.py          # FileValidator
│       │   │   ├── access_control.py          # AccessController
│       │   │   ├── redactor.py                # Redactor
│       │   │   └── sensitive_scanner.py       # SensitiveDataScanner (ISensitiveDataScanner)
│       │   │
│       │   ├── audit/
│       │   │   ├── __init__.py
│       │   │   └── file_audit_writer.py       # FileAuditWriter (IAuditWriter)
│       │   │
│       │   └── export/
│       │       ├── __init__.py
│       │       ├── json_exporter.py           # JSONExporter (IExporter)
│       │       └── csv_exporter.py            # CSVExporter (IExporter)
│       │
│       ├── interfaces/
│       │   ├── __init__.py
│       │   └── cli/
│       │       ├── __init__.py
│       │       ├── main.py                    # composition root; entry point
│       │       └── commands/
│       │           ├── __init__.py
│       │           ├── run_cmd.py             # tcg run create / run status
│       │           ├── ingest_cmd.py          # tcg ingest
│       │           ├── process_cmd.py         # tcg process
│       │           ├── generate_cmd.py        # tcg generate
│       │           ├── validate_cmd.py        # tcg validate
│       │           ├── review_cmd.py          # tcg review
│       │           ├── export_cmd.py          # tcg export
│       │           └── report_cmd.py          # tcg report
│       │
│       └── config/
│           ├── __init__.py
│           ├── settings.py                    # TCGSettings (Pydantic BaseSettings)
│           ├── schema_registry.py             # SchemaRegistry
│           └── defaults.yaml                  # built-in defaults (no secrets)
│
├── tests/
│   ├── conftest.py                            # shared fixtures, tmp_path, test doubles
│   │
│   ├── unit/
│   │   ├── domain/
│   │   │   ├── test_traceability_service.py
│   │   │   ├── test_coverage_service.py
│   │   │   ├── test_deduplication_service.py
│   │   │   └── test_domain_validator.py
│   │   ├── infrastructure/
│   │   │   ├── parsers/
│   │   │   │   ├── test_docx_parser.py
│   │   │   │   ├── test_pdf_brd_parser.py
│   │   │   │   ├── test_jira_json_parser.py
│   │   │   │   └── test_pdf_flow_parser.py
│   │   │   ├── test_requirement_normalizer.py
│   │   │   ├── test_context_assembler.py
│   │   │   ├── test_prompt_builder.py
│   │   │   ├── test_response_parser.py
│   │   │   ├── test_file_validator.py
│   │   │   ├── test_redactor.py
│   │   │   └── test_sensitive_scanner.py
│   │   └── application/
│   │       ├── test_ingest_source.py
│   │       ├── test_generate_test_cases.py
│   │       ├── test_validate_test_cases.py
│   │       └── test_review_test_case.py
│   │
│   ├── integration/
│   │   ├── test_brd_to_requirements.py        # BRD parse → normalize → traceability
│   │   ├── test_jira_to_requirements.py
│   │   ├── test_flow_to_paths.py
│   │   ├── test_generation_pipeline.py        # normalize → generate → validate
│   │   ├── test_export_pipeline.py            # validate → export
│   │   └── test_audit_trail.py
│   │
│   └── fixtures/
│       ├── brd/
│       │   ├── sample_brd_with_ids.docx       # sanitized
│       │   ├── sample_brd_tables.docx
│       │   ├── sample_brd_text_native.pdf
│       │   ├── sample_brd_image_only.pdf
│       │   └── sample_brd_no_requirements.docx
│       ├── jira/
│       │   ├── stories_with_criteria.json
│       │   ├── stories_without_criteria.json
│       │   ├── stories_with_conflict.json
│       │   └── stories_missing_fields.json
│       ├── flow/
│       │   ├── simple_linear_flow.pdf
│       │   ├── branching_flow.pdf
│       │   ├── loop_flow.pdf
│       │   ├── multipage_flow.pdf
│       │   ├── image_only_flow.pdf
│       │   └── ambiguous_connectors_flow.pdf
│       └── ai_responses/
│           ├── valid_response.json
│           ├── malformed_json_response.txt
│           ├── truncated_response.txt
│           ├── refused_response.json
│           └── unverified_citation_response.json
│
├── docs/
│   ├── constitution.md
│   ├── prd.md
│   ├── spec.md
│   └── adr/                                   # Architecture Decision Records
│       └── 0001-clean-architecture.md
│
├── config/
│   ├── schema_v1.0.json                       # JSON Schema for test case output v1.0
│   └── prompt_templates/
│       └── generate_v1.0.txt                  # versioned prompt template
│
├── pyproject.toml                             # build metadata, dependencies,
│                                              #   tool config (mypy, ruff, pytest, coverage)
├── .env.example                               # env variable names with placeholder values
└── README.md
```

---

## Cross-Cutting Conventions

### Type Annotations

All public functions and methods must declare full type annotations for parameters and return types. `Any` is not permitted in public interfaces. `dict[str, Any]` in public positions must be replaced with a typed dataclass or TypedDict. Type stubs must be supplied or selected for all third-party dependencies.

### Immutability

Domain model objects (`NormalizedRequirement`, `TestCase`, `TraceLink`, etc.) are defined as frozen dataclasses or equivalent immutable structures. Mutations to a test case (review edits, status changes) must produce a new version of the object; the old version is preserved in `review_history`.

### Correlation Identifiers

Every operation within a run propagates `run_id` as a correlation identifier. It must appear in every log record, audit event, and error result related to that run. When an operation spans multiple sources or cases, individual `source_id` or `case_id` values are added to the correlation context but do not replace `run_id`.

### Dependency Versions

`pyproject.toml` must pin the minimum required version for every dependency and specify an upper bound for dependencies that have a history of breaking changes. A `requirements.lock` or equivalent lock file must be committed and kept up to date. Dependency audits (`pip-audit` or equivalent) must run as part of the CI pipeline.

### Architecture Decision Records

Significant design decisions must be recorded as Architecture Decision Records (ADRs) in `docs/adr/`. Each ADR documents the decision, the context that drove it, the options considered, the consequences, and any superseded decisions. `spec.md` references ADRs for decisions that warrant extended justification.
