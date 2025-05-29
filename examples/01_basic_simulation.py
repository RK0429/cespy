#!/usr/bin/env python3
"""
Basic Simulation Examples - Getting Started with CESPy

This example demonstrates the fundamental simulation workflows using different
SPICE simulators supported by CESPy.
"""

import os
import sys
from pathlib import Path

# Add the cespy package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cespy import LTspice, NGspiceSimulator, Qspice, XyceSimulator
from cespy import SimRunner, RawRead
from cespy.editor import SpiceEditor


def example_ltspice_simulation():
    """Basic LTSpice simulation example."""
    print("=== LTSpice Simulation Example ===")
    
    # Create a simple RC circuit netlist
    netlist_content = """
Version 4
SHEET 1 880 680
WIRE 176 80 80 80
WIRE 304 80 176 80
WIRE 80 128 80 80
WIRE 176 128 176 80
WIRE 304 128 304 80
WIRE 80 240 80 208
WIRE 176 240 176 208
WIRE 176 240 80 240
WIRE 304 240 304 208
WIRE 304 240 176 240
WIRE 304 240 304 240
FLAG 304 240 0
SYMBOL voltage 80 112 R0
WINDOW 123 0 0 Left 0
WINDOW 39 0 0 Left 0
SYMATTR InstName V1
SYMATTR Value SINE(0 1 1k)
SYMBOL res 160 112 R0
SYMATTR InstName R1
SYMATTR Value 1k
SYMBOL cap 288 112 R0
SYMATTR InstName C1
SYMATTR Value 1u
TEXT 56 264 Left 2 !.tran 0 10m 0 10u
"""
    
    # Create temporary netlist file
    netlist_path = Path("temp_rc_circuit.asc")
    with open(netlist_path, 'w') as f:
        f.write(netlist_content)
    
    try:
        # Initialize LTSpice simulator
        simulator = LTspice()
        
        # Run simulation using SimRunner
        runner = SimRunner()
        runner.simulator = simulator
        
        # Configure simulation
        runner.set_circuit(str(netlist_path))
        
        # Run the simulation
        print("Running LTSpice simulation...")
        result = runner.run()
        
        if result:
            print("✓ Simulation completed successfully")
            
            # Read raw data if available
            raw_file = netlist_path.with_suffix('.raw')
            if raw_file.exists():
                raw_reader = RawRead(str(raw_file))
                traces = raw_reader.get_trace_names()
                print(f"Available traces: {traces}")
            else:
                print("No raw data file found")
        else:
            print("✗ Simulation failed")
            
    except Exception as e:
        print(f"Error running LTSpice simulation: {e}")
    finally:
        # Cleanup
        if netlist_path.exists():
            netlist_path.unlink()


def example_ngspice_simulation():
    """Basic NGSpice simulation example."""
    print("\n=== NGSpice Simulation Example ===")
    
    # Create a simple voltage divider netlist
    netlist_content = """
* Simple voltage divider circuit
V1 vin 0 DC 5
R1 vin vout 1k
R2 vout 0 2k
.op
.print dc v(vout)
.end
"""
    
    # Create temporary netlist file
    netlist_path = Path("temp_divider.net")
    with open(netlist_path, 'w') as f:
        f.write(netlist_content)
    
    try:
        # Initialize NGSpice simulator
        simulator = NGspiceSimulator()
        
        # Run simulation
        runner = SimRunner()
        runner.simulator = simulator
        runner.set_circuit(str(netlist_path))
        
        print("Running NGSpice simulation...")
        result = runner.run()
        
        if result:
            print("✓ NGSpice simulation completed successfully")
        else:
            print("✗ NGSpice simulation failed")
            
    except Exception as e:
        print(f"Error running NGSpice simulation: {e}")
    finally:
        # Cleanup
        if netlist_path.exists():
            netlist_path.unlink()


def example_qspice_simulation():
    """Basic QSpice simulation example."""
    print("\n=== QSpice Simulation Example ===")
    
    try:
        # Initialize QSpice simulator
        simulator = Qspice()
        
        # Create a simple RC circuit
        netlist_content = """
* RC Low-pass filter
V1 in 0 AC 1 0
R1 in out 1k
C1 out 0 1n
.ac dec 10 1 100meg
.end
"""
        
        netlist_path = Path("temp_rc_filter.net")
        with open(netlist_path, 'w') as f:
            f.write(netlist_content)
        
        runner = SimRunner()
        runner.simulator = simulator
        runner.set_circuit(str(netlist_path))
        
        print("Running QSpice simulation...")
        result = runner.run()
        
        if result:
            print("✓ QSpice simulation completed successfully")
        else:
            print("✗ QSpice simulation failed")
            
    except Exception as e:
        print(f"Error running QSpice simulation: {e}")
    finally:
        if 'netlist_path' in locals() and netlist_path.exists():
            netlist_path.unlink()


def example_xyce_simulation():
    """Basic Xyce simulation example."""
    print("\n=== Xyce Simulation Example ===")
    
    try:
        # Initialize Xyce simulator
        simulator = XyceSimulator()
        
        # Create a simple diode circuit
        netlist_content = """
* Simple diode circuit
V1 in 0 DC 2.5
R1 in cathode 1k
D1 cathode 0 DMOD
.model DMOD D()
.dc V1 0 5 0.1
.print dc v(cathode) i(V1)
.end
"""
        
        netlist_path = Path("temp_diode.net")
        with open(netlist_path, 'w') as f:
            f.write(netlist_content)
        
        runner = SimRunner()
        runner.simulator = simulator
        runner.set_circuit(str(netlist_path))
        
        print("Running Xyce simulation...")
        result = runner.run()
        
        if result:
            print("✓ Xyce simulation completed successfully")
        else:
            print("✗ Xyce simulation failed")
            
    except Exception as e:
        print(f"Error running Xyce simulation: {e}")
    finally:
        if 'netlist_path' in locals() and netlist_path.exists():
            netlist_path.unlink()


def example_parameter_sweep():
    """Example of parameter sweep simulation."""
    print("\n=== Parameter Sweep Example ===")
    
    try:
        # Create circuit with parameter to sweep
        netlist_content = """
Version 4
SHEET 1 880 680
WIRE 176 80 80 80
WIRE 304 80 176 80
WIRE 80 128 80 80
WIRE 176 128 176 80
WIRE 304 128 304 80
WIRE 80 240 80 208
WIRE 176 240 176 208
WIRE 176 240 80 240
WIRE 304 240 304 208
WIRE 304 240 176 240
FLAG 304 240 0
SYMBOL voltage 80 112 R0
SYMATTR InstName V1
SYMATTR Value 5
SYMBOL res 160 112 R0
SYMATTR InstName R1
SYMATTR Value {R}
SYMBOL cap 288 112 R0
SYMATTR InstName C1
SYMATTR Value 1u
TEXT 56 264 Left 2 !.step param R 100 10k 100
TEXT 56 288 Left 2 !.op
"""
        
        netlist_path = Path("temp_sweep.asc")
        with open(netlist_path, 'w') as f:
            f.write(netlist_content)
        
        # Use SpiceEditor to modify parameters
        editor = SpiceEditor(str(netlist_path))
        
        # Run simulation with different parameters
        simulator = LTspice()
        runner = SimRunner()
        runner.simulator = simulator
        
        print("Running parameter sweep simulation...")
        
        # Sweep resistance values
        resistance_values = [100, 1000, 10000]
        
        for r_val in resistance_values:
            print(f"  Simulating with R = {r_val} ohms")
            
            # Modify the parameter
            editor.set_parameter('R', str(r_val))
            editor.save_netlist()
            
            runner.set_circuit(str(netlist_path))
            result = runner.run()
            
            if result:
                print(f"    ✓ R={r_val} simulation completed")
            else:
                print(f"    ✗ R={r_val} simulation failed")
        
        print("✓ Parameter sweep completed")
        
    except Exception as e:
        print(f"Error in parameter sweep: {e}")
    finally:
        if 'netlist_path' in locals() and netlist_path.exists():
            netlist_path.unlink()


def main():
    """Run all basic simulation examples."""
    print("CESPy Basic Simulation Examples")
    print("=" * 40)
    
    # Run examples for each simulator
    example_ltspice_simulation()
    example_ngspice_simulation()
    example_qspice_simulation()
    example_xyce_simulation()
    
    # Advanced example
    example_parameter_sweep()
    
    print("\n" + "=" * 40)
    print("Basic simulation examples completed!")
    print("\nNext steps:")
    print("- See circuit editing examples (02_circuit_editing.py)")
    print("- See analysis toolkit examples (03_analysis_toolkit.py)")
    print("- See data processing examples (04_data_processing.py)")


if __name__ == "__main__":
    main()