# Cespy Refactoring Plan

## Executive Summary

This document outlines a comprehensive refactoring plan for cespy, a unified Python toolkit for automating SPICE circuit simulators. The refactoring aims to improve code quality, maintainability, and extensibility while preserving all existing functionality from the merged kupicelib and kuPyLTSpice projects.

## Current State Assessment

### Strengths

- Well-organized module structure with clear separation of concerns
- Good use of abstract base classes for extensibility
- Comprehensive type hints in critical modules
- Strong test infrastructure with CI/CD pipeline
- Multi-simulator support with unified interface

### Areas for Improvement

- Code duplication across modules (22 files with TODO comments)
- Tight coupling between SimRunner and simulator implementations
- Inconsistent error handling and exception hierarchy
- Mixed responsibilities in some classes
- Platform-specific path handling scattered throughout codebase
- Magic strings and regex patterns not centralized

## Refactoring Goals

1. **Reduce Code Duplication**: Extract common patterns and utilities
2. **Improve Modularity**: Break down large classes and separate concerns
3. **Enhance Consistency**: Standardize interfaces and naming conventions
4. **Simplify Extension**: Make it easier to add new simulators and features
5. **Better Error Handling**: Create a comprehensive exception hierarchy
6. **Performance Optimization**: Identify and optimize bottlenecks

## Detailed Refactoring Plan

### Phase 1: Foundation Improvements (Weeks 1-2)

#### 1.1 Centralize Common Patterns

**Priority**: High  
**Effort**: Medium

- Create `cespy/core/` package for shared utilities
- Extract regex patterns to `cespy/core/patterns.py`:

  ```python
  # Component patterns
  COMPONENT_VALUE_PATTERN = re.compile(r'value=([^"\s]+)')
  COMPONENT_REF_PATTERN = re.compile(r'^[RLCVIJKEFHG]\w+')
  
  # Parameter patterns
  PARAM_PATTERN = re.compile(r'.param\s+(\w+)\s*=\s*(.+)', re.IGNORECASE)
  ```

- Create `cespy/core/constants.py` for magic strings and configuration
- Move path utilities to `cespy/core/paths.py`

#### 1.2 Establish Exception Hierarchy

**Priority**: High  
**Effort**: Low

Create `cespy/exceptions.py`:

```python
class CespyError(Exception):
    """Base exception for all cespy errors"""

class SimulatorError(CespyError):
    """Errors related to simulator execution"""

class FileFormatError(CespyError):
    """Errors in file parsing or generation"""

class ComponentNotFoundError(CespyError):
    """Component reference not found in circuit"""

class SimulationTimeoutError(SimulatorError):
    """Simulation exceeded timeout"""
```

#### 1.3 Standardize Configuration

**Priority**: Medium  
**Effort**: Medium

- Create `cespy/config.py` for global configuration management
- Move all default values and settings to configuration
- Support configuration via environment variables and config files
- Example structure:

  ```python
  @dataclass
  class CespyConfig:
      default_timeout: int = 600
      parallel_sims: int = 4
      encoding: str = 'utf-8'
      log_level: str = 'INFO'
  ```

### Phase 2: Core Module Refactoring (Weeks 3-4)

#### 2.1 Refactor Simulator Interface

**Priority**: High  
**Effort**: High

- Standardize the `Simulator` abstract base class:

  ```python
  class Simulator(ABC):
      @abstractmethod
      def validate_installation(self) -> bool:
          """Verify simulator is properly installed"""
      
      @abstractmethod
      def get_version(self) -> str:
          """Get simulator version information"""
      
      @abstractmethod
      def prepare_command(self, netlist: Path) -> List[str]:
          """Prepare command line for execution"""
  ```

- Extract path resolution to a separate `SimulatorLocator` class
- Create `SimulatorFactory` for instantiation logic
- Implement consistent parameter handling across all simulators

#### 2.2 Simplify SimRunner Architecture

**Priority**: High  
**Effort**: High

Break down SimRunner into focused components:

- `TaskQueue`: Manages simulation tasks and priorities
- `ProcessManager`: Handles subprocess execution and monitoring
- `ResultCollector`: Aggregates and processes simulation results
- `CallbackManager`: Manages and executes callbacks
- Keep `SimRunner` as a facade that orchestrates these components

#### 2.3 Enhance Editor Pattern

**Priority**: Medium  
**Effort**: Medium

- Create `ComponentFactory` for creating component objects
- Implement `CircuitValidator` for validation logic
- Add `SchematicDiffer` for tracking changes
- Standardize component manipulation interface:

  ```python
  class ComponentInterface(Protocol):
      def set_value(self, value: Union[str, float]) -> None
      def get_attributes(self) -> Dict[str, Any]
      def validate(self) -> List[str]  # Return validation errors
  ```

### Phase 3: Module-Specific Improvements (Weeks 5-6)

#### 3.1 Editor Module Enhancements

**Priority**: Medium  
**Effort**: Medium

- Extract common editing operations to `BaseEditor`
- Implement undo/redo functionality
- Add circuit validation and linting
- Create `NetlistOptimizer` for performance improvements

#### 3.2 Raw Data Processing Optimization

**Priority**: Medium  
**Effort**: High

- Implement lazy loading for large raw files
- Add streaming API for memory-efficient processing
- Create `RawDataCache` for frequently accessed data
- Optimize binary parsing with numpy operations

#### 3.3 Analysis Toolkit Improvements

**Priority**: Low  
**Effort**: Medium

- Extract common analysis patterns to base classes
- Implement parallel execution for Monte Carlo
- Add progress reporting interface
- Create visualization helpers for analysis results

### Phase 4: Platform and Integration (Weeks 7-8)

#### 4.1 Cross-Platform Improvements

**Priority**: High  
**Effort**: Medium

- Create `PlatformManager` for OS-specific logic
- Standardize path handling across Windows/Linux/macOS
- Implement automatic simulator detection
- Add platform-specific optimization hints

#### 4.2 API Consistency

**Priority**: Medium  
**Effort**: Low

- Standardize method naming conventions
- Ensure consistent parameter ordering
- Add deprecation warnings for old APIs
- Create API migration guide

#### 4.3 Performance Optimization

**Priority**: Low  
**Effort**: High

- Profile critical paths and identify bottlenecks
- Implement caching for repeated operations
- Optimize regex compilation and reuse
- Add performance benchmarks to test suite

### Phase 5: Documentation and Testing (Weeks 9-10)

#### 5.1 Documentation Updates

**Priority**: High  
**Effort**: Medium

- Update all docstrings to reflect refactoring
- Create architecture documentation
- Add design patterns guide
- Write performance tuning guide

#### 5.2 Test Suite Enhancement

**Priority**: High  
**Effort**: Medium

- Add tests for all new components
- Increase coverage to >90%
- Add integration tests for refactored modules
- Create performance regression tests

#### 5.3 Migration Support

**Priority**: Medium  
**Effort**: Low

- Create automated migration scripts
- Document breaking changes
- Provide compatibility layer for critical APIs
- Add migration validation tests

## Implementation Strategy

### Development Approach

1. **Branch Strategy**: Create feature branches for each phase
2. **Review Process**: Code review after each major component
3. **Testing**: Maintain test coverage throughout refactoring
4. **Documentation**: Update docs alongside code changes

### Risk Mitigation

1. **Backward Compatibility**: Maintain old APIs with deprecation warnings
2. **Incremental Changes**: Small, focused PRs for easier review
3. **Feature Flags**: Allow toggling between old and new implementations
4. **Rollback Plan**: Tag stable versions before major changes

### Success Metrics

- Reduce code duplication by 50%
- Improve test coverage to >90%
- Reduce average method complexity by 30%
- Achieve 100% type hint coverage
- Zero regression in functionality

## Priority Matrix

| Component | Priority | Effort | Impact | Risk |
|-----------|----------|--------|---------|------|
| Exception Hierarchy | High | Low | High | Low |
| Common Patterns | High | Medium | High | Low |
| Simulator Interface | High | High | High | Medium |
| SimRunner Refactor | High | High | High | High |
| Platform Manager | High | Medium | Medium | Low |
| Performance Opt | Low | High | Medium | Low |
| Analysis Toolkit | Low | Medium | Low | Low |

## Timeline

- **Weeks 1-2**: Foundation improvements
- **Weeks 3-4**: Core module refactoring
- **Weeks 5-6**: Module-specific improvements
- **Weeks 7-8**: Platform and integration
- **Weeks 9-10**: Documentation and testing
- **Week 11**: Final review and release preparation
- **Week 12**: Buffer for unexpected issues

## Conclusion

This refactoring plan addresses the key architectural issues in cespy while preserving its functionality and improving its maintainability. The phased approach allows for incremental improvements with minimal disruption to users. By focusing on code quality, consistency, and extensibility, cespy will be better positioned for future enhancements and community contributions.
