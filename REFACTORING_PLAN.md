# Grok4Git Refactoring Plan

## Executive Summary

This refactoring plan addresses architectural issues, code organization problems, and maintainability concerns in the Grok4Git codebase. The primary goals are to improve separation of concerns, reduce coupling, enhance testability, and establish clear domain boundaries.

## Current State Analysis

### Critical Issues

1. **Monolithic Files**
   - `tools.py`: 2,089 lines - contains all GitHub operations
   - `chat.py`: 1,079 lines - handles UI, commands, AI interaction, tool execution
   - Both violate Single Responsibility Principle

2. **Mixed Responsibilities**
   - Chat interface mixes UI rendering, command parsing, AI interaction, and tool execution
   - Tools module mixes all GitHub domain operations without clear boundaries
   - Configuration has complex lazy initialization pattern

3. **Tight Coupling**
   - Direct imports between modules
   - Global state (config proxy, github_api singleton)
   - Hard to test individual components

4. **Code Organization**
   - No clear domain boundaries (repos, files, PRs, issues, commits all mixed)
   - No service layer - business logic in tool functions
   - Inconsistent error handling patterns
   - Missing type hints in many places

## Refactoring Strategy

### Phase 1: Domain Separation (Tools Module)

**Goal**: Split `tools.py` into domain-specific modules

**Structure**:
```
grok4git/
  services/
    __init__.py
    repositories.py      # Repository operations
    files.py            # File operations
    pull_requests.py    # PR operations
    issues.py           # Issue operations
    commits.py          # Commit operations
    search.py           # Search operations
  tools/
    __init__.py         # Tool registry and definitions
    registry.py         # Tool registration system
```

**Actions**:
1. Create `services/` directory for domain operations
2. Extract repository operations to `services/repositories.py`
3. Extract file operations to `services/files.py`
4. Extract PR operations to `services/pull_requests.py`
5. Extract issue operations to `services/issues.py`
6. Extract commit operations to `services/commits.py`
7. Extract search operations to `services/search.py`
8. Create `tools/registry.py` for tool definitions and registration
9. Update `tools/__init__.py` to export tools from registry
10. Update imports throughout codebase

**Benefits**:
- Clear domain boundaries
- Easier to locate functionality
- Better testability
- Reduced file size (each ~200-400 lines)

### Phase 2: Chat Interface Refactoring

**Goal**: Separate UI, command handling, and AI interaction

**Structure**:
```
grok4git/
  chat/
    __init__.py
    interface.py        # Main chat interface (orchestration)
    ai_client.py        # AI interaction logic
    command_handlers.py # Slash command handlers
    ui/
      __init__.py
      display.py        # UI rendering (Rich components)
      prompts.py         # User input handling
      formatters.py     # Response formatting
```

**Actions**:
1. Create `chat/` directory structure
2. Extract AI client logic to `chat/ai_client.py`
3. Extract command handlers to `chat/command_handlers.py`
4. Extract UI components to `chat/ui/display.py`
5. Extract prompt handling to `chat/ui/prompts.py`
6. Extract formatters to `chat/ui/formatters.py`
7. Refactor `chat/interface.py` to orchestrate components
8. Update `main.py` to use new structure

**Benefits**:
- Clear separation of concerns
- Easier to test UI components separately
- Better maintainability
- Reduced complexity per file

### Phase 3: Service Layer Introduction

**Goal**: Create proper service layer for business logic

**Structure**:
```
grok4git/
  services/
    base.py             # Base service class
    repositories.py     # Repository service
    files.py            # File service
    pull_requests.py    # PR service
    issues.py           # Issue service
    commits.py          # Commit service
    search.py           # Search service
```

**Actions**:
1. Create `services/base.py` with base service class
2. Refactor each domain service to inherit from base
3. Move business logic from tools to services
4. Keep tools as thin wrappers calling services
5. Add proper error handling in services
6. Add logging in services

**Benefits**:
- Business logic separated from API calls
- Consistent error handling
- Better testability (mock services)
- Reusable logic

### Phase 4: Domain Models

**Goal**: Replace raw dicts with proper domain models

**Structure**:
```
grok4git/
  models/
    __init__.py
    repository.py       # Repository model
    file.py             # File model
    pull_request.py     # PR model
    issue.py            # Issue model
    commit.py           # Commit model
    branch.py           # Branch model
```

**Actions**:
1. Create `models/` directory
2. Define dataclasses for each domain entity
3. Add validation and helper methods
4. Replace dict returns with model instances
5. Add serialization methods (to_dict, to_json)
6. Update services to return models
7. Update tools to convert models to JSON for AI

**Benefits**:
- Type safety
- Better IDE support
- Clearer contracts
- Validation at boundaries

### Phase 5: Configuration Simplification

**Goal**: Simplify configuration management

**Actions**:
1. Remove lazy initialization proxy pattern
2. Use standard singleton pattern or dependency injection
3. Simplify environment variable loading
4. Add configuration validation
5. Create configuration schema/documentation

**Benefits**:
- Simpler code
- Easier to understand
- Better error messages
- Clearer dependencies

### Phase 6: Error Handling Standardization

**Goal**: Consistent error handling across codebase

**Structure**:
```
grok4git/
  exceptions.py         # Custom exceptions
```

**Actions**:
1. Create custom exception hierarchy
2. Replace generic exceptions with domain-specific ones
3. Add error context to exceptions
4. Standardize error messages
5. Add error recovery strategies

**Benefits**:
- Better error messages
- Easier debugging
- Consistent error handling
- Better user experience

## Detailed Implementation Plan

### Phase 1: Domain Separation (Priority: High)

#### Step 1.1: Create Services Directory Structure
- Create `grok4git/services/` directory
- Create `__init__.py` with exports
- Create base service class

#### Step 1.2: Extract Repository Operations
**File**: `services/repositories.py`
**Functions to extract**:
- `list_github_repos`
- `get_repo_info`
- `create_repository`
- `search_github_repos`

**Dependencies**: `github_api`, `config`

#### Step 1.3: Extract File Operations
**File**: `services/files.py`
**Functions to extract**:
- `get_file_content`
- `get_bulk_file_content`
- `get_bulk_codebase_overview`
- `list_directory_contents`
- `recursive_list_directory`
- `delete_file`
- `_get_large_file_summary`

**Dependencies**: `github_api`, `config`, `base64`

#### Step 1.4: Extract Pull Request Operations
**File**: `services/pull_requests.py`
**Functions to extract**:
- `create_pull_request`
- `merge_pull_request`
- `_create_files_in_empty_repo`
- `review_pull_request`
- `approve_pull_request`
- `request_pr_changes`
- `iterate_pull_request`

**Dependencies**: `github_api`, `config`, `peer_review`

#### Step 1.5: Extract Issue Operations
**File**: `services/issues.py`
**Functions to extract**:
- `manage_issues`
- `add_issue_comment`

**Dependencies**: `github_api`, `config`

#### Step 1.6: Extract Commit Operations
**File**: `services/commits.py`
**Functions to extract**:
- `get_commit_history`
- `get_commit_details`
- `get_commit_diff`
- `compare_commits`

**Dependencies**: `github_api`, `config`

#### Step 1.7: Extract Search Operations
**File**: `services/search.py`
**Functions to extract**:
- `search_github_repos`

**Dependencies**: `github_api`, `config`

#### Step 1.8: Create Tool Registry
**File**: `tools/registry.py`
- Define tool schemas
- Register tools from services
- Export TOOLS and TOOL_FUNCTIONS

#### Step 1.9: Update Imports
- Update `chat.py` imports
- Update `peer_review.py` imports
- Update `main.py` imports
- Update test files

### Phase 2: Chat Interface Refactoring (Priority: High)

#### Step 2.1: Create Chat Directory Structure
- Create `grok4git/chat/` directory
- Create `chat/ui/` subdirectory

#### Step 2.2: Extract AI Client
**File**: `chat/ai_client.py`
**Class**: `AIClient`
**Responsibilities**:
- OpenAI client management
- Message history management
- Tool call execution
- Response processing
- Auto-recovery logic

**Methods**:
- `__init__()`
- `send_message(user_input: str) -> str`
- `execute_tool_call(tool_call) -> str`
- `_handle_empty_response() -> None`
- `_build_recovery_context() -> str`

#### Step 2.3: Extract Command Handlers
**File**: `chat/command_handlers.py`
**Class**: `CommandHandler`
**Responsibilities**:
- Execute slash commands
- Handle command-specific logic

**Methods**:
- `execute(command_name: str, args: List[str]) -> bool`
- `_handle_help(args: List[str]) -> None`
- `_handle_clear() -> None`
- `_handle_exit() -> bool`
- `_handle_model(args: List[str]) -> None`
- `_handle_repos(args: List[str]) -> None`
- `_handle_peer_review_toggle(args: List[str]) -> None`
- `_handle_peer_review_status() -> None`
- `_handle_auto_recovery_toggle(args: List[str]) -> None`
- `_handle_auto_recovery_status() -> None`

#### Step 2.4: Extract UI Components
**File**: `chat/ui/display.py`
**Class**: `DisplayManager`
**Responsibilities**:
- Welcome message display
- Command help display
- Response formatting
- Status messages

**Methods**:
- `show_welcome() -> None`
- `show_help(command_name: Optional[str] = None) -> None`
- `show_response(content: str) -> None`
- `show_status(message: str) -> None`
- `show_error(message: str) -> None`

**File**: `chat/ui/prompts.py`
**Class**: `PromptManager`
**Responsibilities**:
- User input handling
- Command completion
- Context status display

**Methods**:
- `get_user_input() -> str`
- `_get_context_status() -> str`
- `_check_context_warnings() -> None`

**File**: `chat/ui/formatters.py`
**Functions**:
- `format_tool_result(function_name: str, result: str, args: dict) -> str`
- `format_error(error: Exception) -> str`
- `format_context_status(used: int, total: int) -> str`

#### Step 2.5: Refactor Main Interface
**File**: `chat/interface.py`
**Class**: `GrokChat`
**Responsibilities**:
- Orchestrate components
- Main chat loop
- Command routing

**Methods**:
- `__init__()`
- `run() -> None`
- `_process_user_input(user_input: str) -> None`
- `_handle_slash_command(command_name: str, args: List[str]) -> bool`
- `_handle_natural_language(user_input: str) -> None`

### Phase 3: Service Layer (Priority: Medium)

#### Step 3.1: Create Base Service
**File**: `services/base.py`
**Class**: `BaseService`
**Methods**:
- `__init__(github_api, config)`
- `_make_request(method, url, **kwargs)`
- `_handle_error(error, context)`
- `_log_operation(operation, details)`

#### Step 3.2: Refactor Services to Inherit Base
- Update each service to inherit from `BaseService`
- Move common logic to base class
- Add consistent error handling
- Add operation logging

### Phase 4: Domain Models (Priority: Medium)

#### Step 4.1: Create Models Directory
- Create `grok4git/models/` directory
- Create `__init__.py`

#### Step 4.2: Define Repository Model
**File**: `models/repository.py`
**Class**: `Repository`
**Fields**:
- `full_name: str`
- `description: Optional[str]`
- `stars: int`
- `forks: int`
- `open_issues: int`
- `default_branch: str`
- `language: Optional[str]`
- `created_at: str`
- `updated_at: str`
- `html_url: str`

**Methods**:
- `to_dict() -> dict`
- `to_json() -> str`
- `from_api_response(data: dict) -> Repository`

#### Step 4.3: Define File Model
**File**: `models/file.py`
**Class**: `File`
**Fields**:
- `path: str`
- `content: str`
- `size: int`
- `sha: str`
- `branch: str`

**Methods**:
- `to_dict() -> dict`
- `is_binary() -> bool`
- `is_large(max_size: int) -> bool`

#### Step 4.4: Define Pull Request Model
**File**: `models/pull_request.py`
**Class**: `PullRequest`
**Fields**:
- `title: str`
- `body: str`
- `branch: str`
- `base_branch: str`
- `files: List[FileChange]`
- `commit_message: str`
- `html_url: Optional[str]`

**Methods**:
- `to_dict() -> dict`
- `validate() -> bool`

#### Step 4.5: Update Services to Return Models
- Update service methods to return model instances
- Add conversion methods in tools
- Update tests

### Phase 5: Configuration Simplification (Priority: Low)

#### Step 5.1: Simplify Config Class
- Remove proxy pattern
- Use standard singleton or module-level instance
- Simplify initialization
- Add validation

#### Step 5.2: Add Configuration Schema
- Document all configuration options
- Add validation for each option
- Provide clear error messages

### Phase 6: Error Handling (Priority: Medium)

#### Step 6.1: Create Exception Hierarchy
**File**: `exceptions.py`
**Classes**:
- `Grok4GitError` (base)
- `ConfigurationError`
- `GitHubAPIError`
- `RepositoryNotFoundError`
- `FileNotFoundError`
- `PermissionError`
- `ValidationError`

#### Step 6.2: Update Error Handling
- Replace generic exceptions with custom ones
- Add error context
- Standardize error messages
- Add recovery strategies

## Migration Strategy

### Backward Compatibility
- Maintain existing public API during refactoring
- Use deprecation warnings for old imports
- Provide migration guide

### Testing Strategy
1. Write tests for new modules before refactoring
2. Run existing tests after each phase
3. Add integration tests for new structure
4. Ensure 100% test coverage maintained

### Incremental Approach
1. Complete Phase 1 fully before moving to Phase 2
2. Test thoroughly after each phase
3. Update documentation after each phase
4. Get code review after each phase

## File Size Targets

After refactoring:
- Service files: 200-400 lines each
- Chat components: 200-300 lines each
- Model files: 100-200 lines each
- Tool registry: 300-500 lines
- Main interface: 200-300 lines

## Benefits Summary

1. **Maintainability**: Smaller, focused files easier to understand
2. **Testability**: Clear boundaries enable unit testing
3. **Extensibility**: Easy to add new domains or features
4. **Type Safety**: Models provide type checking
5. **Error Handling**: Consistent, informative errors
6. **Code Reuse**: Service layer enables reuse
7. **Documentation**: Clear structure self-documents

## Risks and Mitigation

### Risk 1: Breaking Changes
**Mitigation**: Maintain backward compatibility, use deprecation warnings

### Risk 2: Test Failures
**Mitigation**: Write tests first, run tests frequently, fix immediately

### Risk 3: Scope Creep
**Mitigation**: Strict phase boundaries, complete one phase before starting next

### Risk 4: Performance Regression
**Mitigation**: Benchmark before/after, profile critical paths

## Timeline Estimate

- Phase 1: 2-3 days
- Phase 2: 2-3 days
- Phase 3: 1-2 days
- Phase 4: 2-3 days
- Phase 5: 1 day
- Phase 6: 1-2 days

**Total**: 9-14 days

## Success Criteria

1. All existing tests pass
2. No performance regression
3. Code coverage maintained or improved
4. All files under 500 lines
5. Clear domain boundaries
6. Documentation updated
7. No breaking changes to public API

## Next Steps

1. Review and approve this plan
2. Create feature branch: `refactor/domain-separation`
3. Begin Phase 1 implementation
4. Set up CI/CD to run tests after each commit
5. Schedule code reviews after each phase

