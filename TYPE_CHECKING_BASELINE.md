# Type Checking Baseline

This document tracks the baseline Mypy type checking errors. These errors are expected and will be addressed incrementally.

**Current Status**: 23 errors across 6 files

## Error Summary by Category

### 1. Anthropic SDK Type Issues (6 errors)
**Files**: `ai_generator.py`
- Line 92, 112: No overload variant matches `dict[str, object]` for `messages` parameter
- Line 96, 113: Returning `Any` from function declared to return `str`
- Line 105: Dict entry has incompatible type for tool results

**Root Cause**: The Anthropic SDK has strict type hints, but our dynamic message construction doesn't match the expected `MessageParam` type.

**Resolution Strategy**:
- Use TypedDict or Pydantic models for message construction
- Add proper type annotations to message builders
- Estimated effort: 1-2 hours

### 2. Missing Type Annotations (5 errors)
**Files**: `document_processor.py` (2), `search_tools.py` (3)
- document_processor.py:43 - `current_chunk` needs type annotation
- document_processor.py:147 - `lesson_content` needs type annotation
- search_tools.py:27, 141 - `last_sources` needs type annotation

**Root Cause**: Empty list initialization without explicit type hints.

**Resolution Strategy**:
- Add explicit type annotations: `current_chunk: list[str] = []`
- Estimated effort: 15 minutes

### 3. ChromaDB Embedding Function Mismatch (1 error)
**File**: `vector_store.py:61`
- `SentenceTransformerEmbeddingFunction` doesn't match expected protocol

**Root Cause**: ChromaDB's type stubs expect a more general embedding function type.

**Resolution Strategy**:
- Add `# type: ignore[arg-type]` with explanatory comment
- This is a third-party library type stub issue, not our code
- Estimated effort: 5 minutes

### 4. Returning Any from Functions (6 errors)
**Files**: `vector_store.py` (4), `search_tools.py` (2)
- Methods returning untyped values from ChromaDB/JSON operations

**Root Cause**: ChromaDB and JSON operations return `Any`, which propagates through our code.

**Resolution Strategy**:
- Add explicit type casts or assertions at ChromaDB boundaries
- Use TypeGuard functions for runtime type validation
- Estimated effort: 1 hour

### 5. Missing Return Statement (1 error)
**File**: `vector_store.py:250`
- `get_course_link` method doesn't return in all code paths

**Root Cause**: Logic flow doesn't guarantee return in all branches.

**Resolution Strategy**:
- Add explicit `return None` at the end
- Estimated effort: 2 minutes

### 6. Incompatible Type Arguments (3 errors)
**Files**: `document_processor.py` (2), `app.py` (1)
- document_processor.py:170, 218 - `title` type is `str | Any | None` but expects `str`
- app.py:73 - `sources` type is `list[str]` but expects `list[dict[str, str | None]]`

**Root Cause**: Type narrowing needed for optional values.

**Resolution Strategy**:
- Add type guards or assertions before object construction
- Fix `sources` type inconsistency in API response model
- Estimated effort: 30 minutes

### 7. Method Override Signature Mismatch (2 errors)
**File**: `search_tools.py:54, 159`
- `execute` method signatures don't match base `Tool` class

**Root Cause**: Base class uses `**kwargs: Any`, subclasses use explicit parameters.

**Resolution Strategy**:
- Keep explicit parameters (better for type safety)
- Add `# type: ignore[override]` with comment explaining design choice
- Alternative: Use Protocol instead of inheritance
- Estimated effort: 15 minutes

### 8. Incompatible Return Type (1 error)
**File**: `rag_system.py:55`
- Returns `tuple[None, int]` but expects `tuple[Course, int]`

**Root Cause**: Error handling path returns `None` for course.

**Resolution Strategy**:
- Change return type to `tuple[Course | None, int]`
- Update callers to handle `None` case
- Estimated effort: 20 minutes

## Priority for Fixes

**High Priority** (Quick wins, ~1 hour total):
1. Missing type annotations (#2)
2. Missing return statement (#5)
3. ChromaDB ignore comment (#3)

**Medium Priority** (Moderate effort, ~2 hours total):
4. Method override mismatches (#7)
5. Incompatible type arguments (#6)
6. Incompatible return type (#8)

**Low Priority** (Larger refactoring, ~3 hours total):
7. Anthropic SDK type issues (#1)
8. Returning Any from functions (#4)

## Testing After Fixes

After addressing each category:
1. Run `./scripts/typecheck.sh` to verify error count decreases
2. Run `./scripts/test.sh` to ensure no regressions
3. Update this document with new baseline

## Future Improvements

Once baseline is cleared:
- Enable stricter Mypy checks: `disallow_any_generics`, `disallow_untyped_defs`
- Add type checking to CI/CD pipeline
- Enforce no new type errors in code reviews
