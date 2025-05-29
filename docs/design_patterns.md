# Design Patterns Guide for Cespy

This document explains the design patterns used throughout the cespy codebase and provides guidance for contributors on when and how to use them.

## Factory Pattern

### Overview
The Factory pattern is used extensively to create objects without specifying their exact classes, allowing for flexible object creation based on configuration or runtime conditions.

### Implementations

#### SimulatorFactory
**Location**: `cespy.sim.simulator_interface.SimulatorFactory`

**Purpose**: Creates appropriate simulator instances based on type and configuration.

```python
# Usage
simulator = SimulatorFactory.create("LTSpice", executable_path="/custom/path")

# Auto-detection
available_sims = SimulatorFactory.detect_all()
```

**Benefits**:
- Centralizes simulator creation logic
- Handles platform-specific instantiation
- Supports automatic detection and configuration

#### ComponentFactory
**Location**: `cespy.editor.component_factory.ComponentFactory`

**Purpose**: Creates circuit component objects from specifications or SPICE lines.

```python
# Create from type
resistor = ComponentFactory.create_component(ComponentType.RESISTOR, 
                                           name="R1", value="1k", nodes=["net1", "net2"])

# Parse from SPICE line
component = ComponentFactory.create_from_spice_line("R1 net1 net2 1k")
```

**When to Use**:
- Creating circuit components programmatically
- Parsing netlists into object representations
- Supporting multiple component formats

### Guidelines for New Factories

1. **Single Responsibility**: Each factory should create one type of object
2. **Configuration**: Support both explicit and automatic configuration
3. **Validation**: Validate inputs before object creation
4. **Error Handling**: Provide clear error messages for invalid inputs

```python
class MyObjectFactory:
    """Template for new factory classes"""
    
    @classmethod
    def create(cls, object_type: str, **options) -> MyObject:
        """Create object with validation and error handling"""
        if object_type not in cls.SUPPORTED_TYPES:
            raise ValueError(f"Unsupported type: {object_type}")
        
        # Validation logic
        cls._validate_options(options)
        
        # Object creation
        return cls._create_object(object_type, options)
```

## Strategy Pattern

### Overview
The Strategy pattern allows selecting algorithms at runtime, providing flexibility in behavior without changing client code.

### Implementations

#### Cache Eviction Policies
**Location**: `cespy.raw.raw_data_cache.py`

**Purpose**: Different strategies for cache management based on usage patterns.

```python
class CachePolicy(ABC):
    @abstractmethod
    def evict(self, cache: Dict[str, Any], max_size: int) -> None:
        pass

class LRUPolicy(CachePolicy):
    def evict(self, cache: Dict[str, Any], max_size: int) -> None:
        # Least Recently Used eviction logic
        pass

class LFUPolicy(CachePolicy):
    def evict(self, cache: Dict[str, Any], max_size: int) -> None:
        # Least Frequently Used eviction logic
        pass

# Usage
cache = RawDataCache(policy=LRUPolicy())
```

#### Optimization Strategies
**Location**: `cespy.core.performance.PerformanceOptimizer`

**Purpose**: Different optimization approaches based on data characteristics.

```python
def optimize_for_size(size_mb: float, operation: str) -> Dict[str, Any]:
    if size_mb < 10:
        return {"strategy": "load_full", "cache": True}
    elif size_mb < 100:
        return {"strategy": "chunked", "chunk_size": "10MB"}
    else:
        return {"strategy": "streaming", "memory_map": True}
```

### When to Use Strategy Pattern

1. **Multiple Algorithms**: When you have multiple ways to perform the same task
2. **Runtime Selection**: When the choice of algorithm depends on runtime conditions
3. **Extensibility**: When you want to easily add new algorithms without changing existing code

### Implementation Template

```python
class AlgorithmStrategy(ABC):
    @abstractmethod
    def execute(self, data: Any) -> Any:
        pass

class ConcreteStrategyA(AlgorithmStrategy):
    def execute(self, data: Any) -> Any:
        # Implementation A
        pass

class Context:
    def __init__(self, strategy: AlgorithmStrategy):
        self.strategy = strategy
    
    def set_strategy(self, strategy: AlgorithmStrategy):
        self.strategy = strategy
    
    def process(self, data: Any) -> Any:
        return self.strategy.execute(data)
```

## Observer Pattern

### Overview
The Observer pattern defines a one-to-many dependency between objects, allowing multiple observers to be notified of state changes.

### Implementations

#### Progress Reporting
**Location**: `cespy.sim.toolkit.base_analysis.ProgressReporter`

**Purpose**: Notify multiple listeners about analysis progress.

```python
class ProgressReporter:
    def __init__(self, callback: Optional[Callable[[int, int, str], None]] = None):
        self.callback = callback
    
    def report(self, current: int, total: int, message: str = "") -> None:
        # Calculate metrics and format message
        if self.callback:
            self.callback(current, total, formatted_message)

# Usage
def progress_callback(current, total, message):
    print(f"Progress: {current}/{total} - {message}")

analysis = MonteCarloAnalysis("circuit.asc", progress_callback=progress_callback)
```

#### Performance Monitoring
**Location**: `cespy.core.performance.PerformanceMonitor`

**Purpose**: Collect and report performance metrics to multiple observers.

```python
@profile_performance(log_calls=True)
def monitored_function():
    # Function automatically reports metrics to PerformanceMonitor
    pass
```

### Implementation Guidelines

1. **Weak References**: Use weak references to prevent memory leaks
2. **Error Handling**: Don't let observer errors affect the subject
3. **Async Notifications**: Consider async notifications for expensive observers

```python
class Subject:
    def __init__(self):
        self._observers: List[Observer] = []
    
    def attach(self, observer: Observer) -> None:
        self._observers.append(observer)
    
    def detach(self, observer: Observer) -> None:
        self._observers.remove(observer)
    
    def notify(self, event: Event) -> None:
        for observer in self._observers[:]:  # Copy to avoid modification issues
            try:
                observer.update(event)
            except Exception as e:
                # Log error but continue with other observers
                logger.warning("Observer failed: %s", e)
```

## Command Pattern

### Overview
The Command pattern encapsulates requests as objects, allowing you to parameterize clients with different requests, queue operations, and support undo functionality.

### Implementations

#### Editor Undo/Redo
**Location**: `cespy.editor.base_editor_enhanced.py`

**Purpose**: Implement undo/redo functionality for circuit editing operations.

```python
class EditorCommand(ABC):
    @abstractmethod
    def execute(self) -> None:
        pass
    
    @abstractmethod
    def undo(self) -> None:
        pass

class SetComponentValueCommand(EditorCommand):
    def __init__(self, editor: BaseEditor, component: str, old_value: str, new_value: str):
        self.editor = editor
        self.component = component
        self.old_value = old_value
        self.new_value = new_value
    
    def execute(self) -> None:
        self.editor.set_component_value(self.component, self.new_value)
    
    def undo(self) -> None:
        self.editor.set_component_value(self.component, self.old_value)

# Usage in editor
class BaseEditorEnhanced:
    def __init__(self):
        self.command_history: List[EditorCommand] = []
        self.current_command = -1
    
    def execute_command(self, command: EditorCommand) -> None:
        command.execute()
        # Remove any commands after current position (for redo)
        self.command_history = self.command_history[:self.current_command + 1]
        self.command_history.append(command)
        self.current_command += 1
    
    def undo(self) -> bool:
        if self.current_command >= 0:
            self.command_history[self.current_command].undo()
            self.current_command -= 1
            return True
        return False
```

#### Batch Operations
**Location**: `cespy.editor.base_editor_enhanced.py`

**Purpose**: Group multiple operations into a single undoable command.

```python
class BatchCommand(EditorCommand):
    def __init__(self, commands: List[EditorCommand], name: str = "Batch Operation"):
        self.commands = commands
        self.name = name
    
    def execute(self) -> None:
        for command in self.commands:
            command.execute()
    
    def undo(self) -> None:
        # Undo in reverse order
        for command in reversed(self.commands):
            command.undo()

# Usage
with editor.batch_operation("Replace all resistors"):
    for resistor in resistors:
        editor.set_component_value(resistor, new_value)
```

### When to Use Command Pattern

1. **Undo/Redo**: When you need to support undo/redo operations
2. **Queuing**: When you want to queue, log, or schedule operations
3. **Macro Recording**: When you need to record and replay sequences of operations

## Adapter Pattern

### Overview
The Adapter pattern allows incompatible interfaces to work together by providing a wrapper that translates one interface to another.

### Implementations

#### Simulator Compatibility
**Location**: `cespy.sim.simulator_interface.SimulatorAdapter`

**Purpose**: Adapt legacy simulator classes to the new ISimulator interface.

```python
class SimulatorAdapter(ISimulator):
    """Adapts legacy simulator classes to new interface"""
    
    def __init__(self, legacy_simulator):
        self.legacy_simulator = legacy_simulator
    
    def validate_installation(self) -> SimulatorInfo:
        # Adapt legacy check method to new interface
        if hasattr(self.legacy_simulator, 'check_installation'):
            is_valid = self.legacy_simulator.check_installation()
            return SimulatorInfo(
                name=self.legacy_simulator.__class__.__name__,
                version="unknown",
                path=getattr(self.legacy_simulator, 'executable_path', None),
                is_available=is_valid
            )
        return SimulatorInfo(name="unknown", version="unknown", is_available=False)
    
    def prepare_command(self, netlist_path: Path, **options) -> SimulationCommand:
        # Adapt legacy command preparation
        if hasattr(self.legacy_simulator, 'build_command'):
            cmd_parts = self.legacy_simulator.build_command(str(netlist_path), **options)
            return SimulationCommand(
                executable=cmd_parts[0],
                arguments=cmd_parts[1:],
                working_directory=netlist_path.parent
            )
        raise NotImplementedError("Legacy simulator doesn't support command building")
```

#### API Migration
**Location**: `cespy.core.api_consistency.py`

**Purpose**: Provide compatibility wrappers for renamed or restructured APIs.

```python
def create_compatibility_wrapper(old_name: str, new_name: str, version: str, module_dict: Dict[str, Any]) -> None:
    """Create a compatibility wrapper for renamed functions/classes"""
    if new_name in module_dict:
        original = module_dict[new_name]
        
        @deprecated(version=version, reason=f"Name changed from {old_name} to {new_name}", replacement=new_name)
        def wrapper(*args, **kwargs):
            return original(*args, **kwargs)
        
        wrapper.__name__ = old_name
        module_dict[old_name] = wrapper

# Usage in module initialization
create_compatibility_wrapper("MontecarloAnalysis", "MonteCarloAnalysis", "2.0", globals())
```

### Guidelines for Adapters

1. **Minimal Interface**: Adapters should provide only the necessary interface translation
2. **Error Handling**: Handle cases where legacy objects don't support required operations
3. **Performance**: Avoid unnecessary data conversion in adapters
4. **Documentation**: Clearly document what functionality is adapted vs. not supported

## Singleton Pattern

### Overview
The Singleton pattern ensures a class has only one instance and provides global access to it.

### Implementations

#### Platform Manager
**Location**: `cespy.core.platform.PlatformManager`

**Purpose**: Provide global access to platform-specific information and utilities.

```python
class PlatformManager:
    _instance: Optional['PlatformManager'] = None
    
    def __new__(cls) -> 'PlatformManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._detect_platform()

# Global instance
platform_manager = PlatformManager()

# Usage
from cespy.core.platform import platform_manager
info = platform_manager.info
```

#### Performance Monitor
**Location**: `cespy.core.performance.PerformanceMonitor`

**Purpose**: Centralized performance metrics collection.

```python
# Global instance for performance monitoring
performance_monitor = PerformanceMonitor()

@profile_performance()
def my_function():
    # Automatically reports to global monitor
    pass
```

### When to Use Singleton

1. **Global State**: When you need truly global state (use sparingly)
2. **Resource Management**: For expensive-to-create objects that should be shared
3. **Configuration**: For application-wide configuration objects

### Singleton Alternatives

Consider these alternatives before using Singleton:

1. **Dependency Injection**: Pass instances explicitly
2. **Module-level Variables**: Use module globals for simple cases
3. **Context Managers**: For scoped resource management

```python
# Alternative: Dependency injection
class MyClass:
    def __init__(self, platform_manager: PlatformManager):
        self.platform_manager = platform_manager

# Alternative: Context manager
@contextmanager
def performance_context():
    monitor = PerformanceMonitor()
    try:
        yield monitor
    finally:
        monitor.generate_report()
```

## Decorator Pattern

### Overview
The Decorator pattern allows adding new functionality to objects dynamically without altering their structure.

### Implementations

#### Performance Profiling
**Location**: `cespy.core.performance.profile_performance`

**Purpose**: Add performance monitoring to any function without modifying its code.

```python
@profile_performance(include_memory=True, log_calls=True)
def expensive_function(data: List[float]) -> float:
    return sum(data) / len(data)

# The decorator automatically:
# - Measures execution time
# - Tracks memory usage
# - Logs function calls
# - Reports to PerformanceMonitor
```

#### API Deprecation
**Location**: `cespy.core.api_consistency.deprecated`

**Purpose**: Mark functions as deprecated while maintaining functionality.

```python
@deprecated(version="2.0", reason="Use new_function instead", replacement="new_function")
def old_function(x: int) -> int:
    return x * 2

# Automatically issues deprecation warnings when called
```

#### Parameter Standardization
**Location**: `cespy.core.api_consistency.standardize_parameters`

**Purpose**: Automatically migrate old parameter names to new ones.

```python
@standardize_parameters({'old_param': 'new_param', 'legacy_arg': 'current_arg'})
def updated_function(new_param: str, current_arg: int = 0) -> str:
    return f"{new_param}_{current_arg}"

# Automatically handles calls with old parameter names
updated_function(old_param="test", legacy_arg=5)  # Works with warnings
```

### Creating Custom Decorators

```python
import functools
from typing import Callable, TypeVar

F = TypeVar('F', bound=Callable[..., Any])

def my_decorator(option: str = "default") -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Pre-processing
            print(f"Calling {func.__name__} with option: {option}")
            
            try:
                result = func(*args, **kwargs)
                # Post-processing
                return result
            except Exception as e:
                # Error handling
                print(f"Error in {func.__name__}: {e}")
                raise
        
        return wrapper
    return decorator

# Usage
@my_decorator(option="custom")
def my_function(x: int) -> int:
    return x * 2
```

## Composite Pattern

### Overview
The Composite pattern allows treating individual objects and compositions of objects uniformly.

### Implementations

#### Circuit Hierarchies
**Location**: `cespy.editor.base_schematic.py`

**Purpose**: Handle nested circuit structures (subcircuits, hierarchical designs).

```python
class CircuitElement(ABC):
    @abstractmethod
    def get_nodes(self) -> List[str]:
        pass
    
    @abstractmethod
    def to_spice(self) -> str:
        pass

class Component(CircuitElement):
    def __init__(self, name: str, nodes: List[str], value: str):
        self.name = name
        self.nodes = nodes
        self.value = value
    
    def get_nodes(self) -> List[str]:
        return self.nodes
    
    def to_spice(self) -> str:
        return f"{self.name} {' '.join(self.nodes)} {self.value}"

class SubCircuit(CircuitElement):
    def __init__(self, name: str, elements: List[CircuitElement]):
        self.name = name
        self.elements = elements
    
    def get_nodes(self) -> List[str]:
        # Collect all nodes from child elements
        nodes = set()
        for element in self.elements:
            nodes.update(element.get_nodes())
        return list(nodes)
    
    def to_spice(self) -> str:
        lines = [f".subckt {self.name}"]
        for element in self.elements:
            lines.append(element.to_spice())
        lines.append(".ends")
        return "\n".join(lines)
```

### When to Use Composite Pattern

1. **Tree Structures**: When you have tree-like object structures
2. **Uniform Interface**: When you want to treat leaf and composite objects uniformly
3. **Recursive Operations**: When operations should work on both individual and grouped objects

## Best Practices

### 1. Pattern Selection
- **Don't force patterns**: Use patterns when they solve real problems
- **Start simple**: Begin with simple solutions and refactor to patterns when needed
- **Consider alternatives**: Evaluate multiple patterns for the same problem

### 2. Documentation
- **Document intent**: Explain why you chose a specific pattern
- **Provide examples**: Include usage examples in docstrings
- **Reference patterns**: Mention the pattern name in comments

### 3. Testing
- **Test interfaces**: Focus tests on the pattern interfaces
- **Mock dependencies**: Use mocking for pattern collaborators
- **Test edge cases**: Verify pattern behavior under unusual conditions

### 4. Evolution
- **Refactor gradually**: Introduce patterns incrementally
- **Maintain compatibility**: Use adapter patterns during transitions
- **Monitor performance**: Ensure patterns don't introduce performance issues

This guide provides the foundation for understanding and applying design patterns consistently throughout the cespy codebase. When contributing new features, consider which patterns apply and follow the established conventions.