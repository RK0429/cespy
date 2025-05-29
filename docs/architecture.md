# Cespy Architecture Documentation

## Overview

Cespy is a unified Python toolkit for automating SPICE circuit simulators (LTSpice, NGSpice, QSpice, Xyce). The architecture has been comprehensively refactored to improve modularity, cross-platform compatibility, and maintainability while preserving all existing functionality.

## Core Architecture Principles

### 1. Layered Architecture
The codebase follows a layered architecture pattern:

```
┌─────────────────────────────────────────┐
│           User Interface Layer          │
│        (CLI tools, Python API)         │
├─────────────────────────────────────────┤
│         Application Layer               │
│    (Analysis toolkit, Batch runners)   │
├─────────────────────────────────────────┤
│         Domain Layer                    │
│   (Simulators, Editors, Raw parsers)   │
├─────────────────────────────────────────┤
│       Infrastructure Layer             │
│  (Core utilities, Platform management) │
└─────────────────────────────────────────┘
```

### 2. Dependency Injection
Components use dependency injection for loose coupling:
- Simulators are injected into runners
- Runners are injected into analysis classes
- Platform-specific implementations are selected at runtime

### 3. Factory Pattern
Factory classes handle object creation and configuration:
- `SimulatorFactory` for simulator instantiation
- `ComponentFactory` for circuit component creation
- `TaskQueue` for simulation task management

### 4. Observer Pattern
Progress reporting and callback management:
- `ProgressReporter` for standardized progress tracking
- `CallbackManager` for flexible event handling
- Performance monitoring with `PerformanceMonitor`

## Module Structure

### Core Infrastructure (`cespy.core`)

The core module provides foundational utilities used across the entire codebase:

#### `patterns.py` - Regex Pattern Library
```python
# Centralized regex patterns for SPICE parsing
SPICE_PATTERNS = {
    'component': r'([RLCVIJKXM]\w*)\s+(.*)',
    'parameter': r'\.param\s+(\w+)\s*=\s*(.+)',
    'measurement': r'\.meas\s+(\w+)\s+(\w+)\s+(.*)',
    # ... 50+ patterns
}
```

#### `constants.py` - Shared Constants
```python
class Simulators:
    LTSPICE = "LTSpice"
    NGSPICE = "NGSpice"
    QSPICE = "QSpice"
    XYCE = "Xyce"

class FileExtensions:
    ASC = ".asc"    # LTSpice schematic
    NET = ".net"    # SPICE netlist
    RAW = ".raw"    # Raw simulation data
    # ... more extensions
```

#### `platform.py` - Cross-Platform Management
```python
class PlatformManager:
    """Handles OS-specific logic and optimizations"""
    
    def get_simulator_search_paths(self, simulator: str) -> List[Path]
    def get_optimal_process_count(self, memory_intensive: bool = False) -> int
    def setup_process_environment(self, wine_mode: bool = False) -> Dict[str, str]
```

#### `performance.py` - Performance Optimization
```python
@profile_performance(include_memory=True)
def expensive_function():
    """Automatically tracked performance function"""
    pass

with performance_timer("operation_name"):
    # Timed code block
    pass
```

#### `api_consistency.py` - API Standardization
```python
@deprecated(version="2.0", replacement="new_method")
def old_method():
    """Deprecated method with automatic warnings"""
    pass

@standardize_parameters({'old_param': 'new_param'})
def standardized_function(new_param):
    """Function with parameter migration"""
    pass
```

### Simulator Abstraction (`cespy.simulators`)

#### Enhanced Simulator Interface
```python
class ISimulator(ABC):
    """Abstract interface for all simulators"""
    
    @abstractmethod
    def validate_installation(self) -> SimulatorInfo
    
    @abstractmethod
    def prepare_command(self, netlist_path: Path, **options) -> SimulationCommand
    
    @abstractmethod
    def parse_arguments(self, args: List[str]) -> Dict[str, Any]
```

#### Simulator Factory and Locator
```python
class SimulatorFactory:
    """Factory for creating simulator instances"""
    
    @classmethod
    def create(cls, simulator_type: str, **options) -> ISimulator
    
    @classmethod
    def detect_all(cls) -> Dict[str, SimulatorInfo]

class SimulatorLocator:
    """Locates simulator installations across platforms"""
    
    def find_simulator(self, name: str) -> Optional[Path]
    def get_version(self, path: Path) -> Optional[str]
```

### Simulation Orchestration (`cespy.sim`)

#### Modular SimRunner Architecture
The monolithic SimRunner has been decomposed into specialized components:

```python
class SimRunnerRefactored:
    """Refactored SimRunner using composition"""
    
    def __init__(self):
        self.task_queue = TaskQueue()
        self.process_manager = ProcessManager()
        self.result_collector = ResultCollector()
        self.callback_manager = CallbackManager()
```

#### Task Management
```python
class TaskQueue:
    """Priority-based task queue with dependency tracking"""
    
    def submit(self, task: RunTask, priority: TaskPriority = TaskPriority.NORMAL,
              dependencies: Set[str] = None) -> str
    
    def get_next_ready_task(self) -> Optional[RunTask]
```

#### Process Management
```python
class ProcessManager:
    """Manages subprocess execution with resource limits"""
    
    def execute(self, command: SimulationCommand, 
               timeout: Optional[float] = None,
               resource_limits: Optional[ResourceLimits] = None) -> ProcessResult
```

### Editor System (`cespy.editor`)

#### Enhanced Editor Pattern
```python
class BaseEditorEnhanced(BaseEditor):
    """Enhanced editor with undo/redo and validation"""
    
    def __init__(self):
        self.command_history: List[EditorCommand] = []
        self.validator = CircuitValidator()
        self.differ = SchematicDiffer()
    
    def undo(self) -> bool
    def redo(self) -> bool
    def begin_batch(self, name: str = "Batch Operation") -> None
```

#### Component Factory
```python
class ComponentFactory:
    """Factory for creating circuit components"""
    
    def create_component(self, component_type: ComponentType, 
                        name: str = None, **attributes) -> BaseComponent
    
    def create_from_spice_line(self, line: str) -> BaseComponent
```

#### Circuit Validation
```python
class CircuitValidator:
    """Validates circuit integrity and common issues"""
    
    def validate(self, circuit: Circuit) -> ValidationReport
    def check_connectivity(self) -> List[ValidationIssue]
    def check_component_values(self) -> List[ValidationIssue]
```

### Raw Data Processing (`cespy.raw`)

#### Lazy Loading and Streaming
```python
class RawReadLazy(RawRead):
    """Lazy loading implementation for large files"""
    
    def get_wave(self, trace_name: str, step: int = 0) -> NDArray
    def get_waves_async(self, trace_names: List[str]) -> Iterator[NDArray]

class RawFileStreamer:
    """Streaming API for memory-efficient processing"""
    
    def stream_data(self, chunk_size: int = 1024) -> Iterator[RawDataChunk]
    def process_with(self, processor: DataProcessor) -> Any
```

#### Optimized Parsing
```python
class OptimizedBinaryParser:
    """Numpy-optimized binary data parsing"""
    
    def parse_bulk(self, data: bytes, format_spec: FormatSpec) -> NDArray
    def auto_detect_format(self, header: bytes) -> DataFormat
```

### Analysis Toolkit (`cespy.sim.toolkit`)

#### Base Analysis Classes
```python
class BaseAnalysis(SimAnalysis):
    """Enhanced base class with parallel execution"""
    
    def __init__(self, parallel: bool = False, max_workers: int = None):
        self.progress_reporter = ProgressReporter()
        self.results: List[AnalysisResult] = []
    
    def run_analysis(self) -> List[AnalysisResult]

class StatisticalAnalysis(BaseAnalysis):
    """Base for Monte Carlo and statistical analyses"""
    
    def calculate_statistics(self, measurement: str) -> Dict[str, float]
    def get_histogram_data(self, measurement: str) -> Tuple[NDArray, NDArray]
    def get_correlation_matrix(self, measurements: List[str]) -> NDArray
```

#### Visualization System
```python
class AnalysisVisualizer:
    """Comprehensive plotting utilities"""
    
    def plot_histogram(self, analysis: StatisticalAnalysis, measurement: str) -> Figure
    def plot_scatter_matrix(self, analysis: StatisticalAnalysis, measurements: List[str]) -> Figure
    def create_analysis_report(self, analysis: StatisticalAnalysis, output_dir: Path) -> Path
```

## Design Patterns Used

### 1. Factory Pattern
Used throughout for object creation:
- `SimulatorFactory` for simulator instances
- `ComponentFactory` for circuit components
- `TaskQueue` for simulation tasks

### 2. Strategy Pattern
For algorithm selection:
- Different simulation strategies per simulator
- Multiple cache eviction policies
- Various optimization strategies

### 3. Observer Pattern
For event handling:
- Progress reporting callbacks
- Performance monitoring
- Result collection

### 4. Command Pattern
For undo/redo functionality:
- `EditorCommand` base class
- Command history management
- Batch operation support

### 5. Adapter Pattern
For compatibility:
- `SimulatorAdapter` for legacy simulators
- `SimRunnerCompat` for backward compatibility
- API migration wrappers

### 6. Singleton Pattern
For global state:
- `PlatformManager` for system information
- `PerformanceMonitor` for metrics collection
- `RegexCache` for pattern caching

## Data Flow Architecture

### 1. Simulation Workflow
```
User Input → Editor → Validator → SimRunner → TaskQueue → ProcessManager → ResultCollector → Analysis
```

### 2. Analysis Workflow
```
Circuit File → Analysis Setup → Parameter Generation → Parallel Execution → Result Collection → Statistics → Visualization
```

### 3. Cross-Platform Workflow
```
Platform Detection → Simulator Location → Environment Setup → Execution → Result Processing
```

## Performance Architecture

### 1. Caching Strategy
- **Regex Cache**: Compiled patterns with LRU eviction
- **File Cache**: Raw data with configurable policies
- **Result Cache**: Analysis results with TTL expiration

### 2. Parallel Execution
- **Thread Pool**: I/O-bound operations (file parsing)
- **Process Pool**: CPU-bound operations (simulations)
- **Async Processing**: Network operations (client-server)

### 3. Memory Management
- **Lazy Loading**: On-demand data loading
- **Streaming**: Chunk-based processing for large files
- **Memory Mapping**: OS-level memory management

### 4. Optimization Hints
Platform-specific optimizations:
- **Windows**: Job objects for process management
- **Linux**: Memory mapping and tmpfs usage
- **macOS**: Rosetta compatibility for x86_64 simulators

## Error Handling Architecture

### 1. Exception Hierarchy
```python
CespyError
├── SimulatorError
│   ├── SimulatorNotFoundError
│   ├── SimulatorTimeoutError
│   └── SimulatorFailedError
├── FileFormatError
│   ├── InvalidNetlistError
│   └── InvalidRawFileError
└── AnalysisError
    ├── ConvergenceError
    └── InsufficientDataError
```

### 2. Error Recovery
- Automatic retry mechanisms
- Graceful degradation
- Detailed error reporting
- Recovery strategies for common failures

## Testing Architecture

### 1. Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: Module interaction testing
- **Performance Tests**: Regression detection
- **Platform Tests**: Cross-platform compatibility

### 2. Test Infrastructure
- **Mocking**: Simulator execution mocking
- **Fixtures**: Reusable test data
- **Benchmarks**: Performance baseline tracking
- **CI/CD Integration**: Automated testing pipeline

## Extension Points

### 1. New Simulators
Implement `ISimulator` interface:
```python
class MySimulator(ISimulator):
    def validate_installation(self) -> SimulatorInfo:
        # Implementation
    
    def prepare_command(self, netlist_path: Path, **options) -> SimulationCommand:
        # Implementation
```

### 2. New Analysis Types
Extend base classes:
```python
class MyAnalysis(ParametricAnalysis):
    def prepare_runs(self) -> List[Dict[str, Any]]:
        # Implementation
    
    def apply_parameters(self, parameters: Dict[str, Any]) -> None:
        # Implementation
```

### 3. New File Formats
Implement format interfaces:
```python
class MyFormatReader(RawFileReader):
    def read_header(self) -> RawFileHeader:
        # Implementation
    
    def read_traces(self) -> Dict[str, NDArray]:
        # Implementation
```

## Migration and Compatibility

### 1. Backward Compatibility
- All existing APIs maintained
- Deprecation warnings for old methods
- Compatibility wrappers for renamed classes

### 2. Migration Path
- Automatic parameter name migration
- Legacy API bridge classes
- Comprehensive migration documentation

### 3. Version Management
- Semantic versioning
- Breaking change documentation
- Migration scripts for major versions

This architecture provides a solid foundation for future development while maintaining backward compatibility and enabling easy extension for new simulators, analysis types, and file formats.