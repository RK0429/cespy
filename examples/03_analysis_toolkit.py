#!/usr/bin/env python3
"""
Analysis Toolkit Examples

This example demonstrates advanced analysis capabilities including Monte Carlo,
worst-case analysis, sensitivity analysis, and other statistical techniques.
"""

import os
import sys
import numpy as np
from pathlib import Path

# Add the cespy package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cespy.sim.toolkit import (
    MonteCarloAnalysis, WorstCaseAnalysis, FastWorstCaseAnalysis,
    SensitivityAnalysis, ToleranceDeviations, FailureMode
)
from cespy import SimRunner, LTspice
from cespy.editor import SpiceEditor


def example_monte_carlo_analysis():
    """Demonstrate Monte Carlo statistical analysis."""
    print("=== Monte Carlo Analysis Example ===")
    
    # Create a circuit with component tolerances
    netlist_content = """* Voltage Divider with Component Tolerances
* For Monte Carlo Analysis

.param R1_nom=10k
.param R2_nom=10k
.param R1_tol=0.05    ; 5% tolerance
.param R2_tol=0.05    ; 5% tolerance

V1 vin 0 DC 5
R1 vin vout {R1_nom*(1+R1_tol*AGAUSS(0,1,1))}
R2 vout 0 {R2_nom*(1+R2_tol*AGAUSS(0,1,1))}

.op
.step param run 1 100 1
.end
"""
    
    netlist_path = Path("temp_mc_circuit.net")
    with open(netlist_path, 'w') as f:
        f.write(netlist_content)
    
    try:
        # Initialize Monte Carlo analysis
        mc_analysis = MonteCarloAnalysis()
        
        print("Configuring Monte Carlo analysis...")
        
        # Configure analysis parameters
        mc_analysis.set_circuit(str(netlist_path))
        mc_analysis.set_num_runs(100)
        mc_analysis.set_output_variable('v(vout)')
        
        # Define component variations
        component_variations = {
            'R1': {'nominal': 10000, 'tolerance': 0.05, 'distribution': 'gaussian'},
            'R2': {'nominal': 10000, 'tolerance': 0.05, 'distribution': 'gaussian'},
        }
        
        for comp, params in component_variations.items():
            mc_analysis.add_component_variation(
                component=comp,
                nominal_value=params['nominal'],
                tolerance=params['tolerance'],
                distribution=params['distribution']
            )
        
        print("Running Monte Carlo simulation...")
        results = mc_analysis.run_analysis()
        
        if results:
            print("✓ Monte Carlo analysis completed")
            
            # Analyze results
            statistics = mc_analysis.get_statistics()
            print(f"Output voltage statistics:")
            print(f"  Mean: {statistics['mean']:.3f} V")
            print(f"  Std Dev: {statistics['std_dev']:.3f} V")
            print(f"  Min: {statistics['min']:.3f} V")
            print(f"  Max: {statistics['max']:.3f} V")
            
            # Yield analysis
            yield_info = mc_analysis.calculate_yield(
                lower_limit=2.3,  # 2.3V minimum
                upper_limit=2.7   # 2.7V maximum
            )
            print(f"  Yield (2.3V-2.7V): {yield_info['yield']:.1f}%")
            
        else:
            print("✗ Monte Carlo analysis failed")
            
    except Exception as e:
        print(f"Error in Monte Carlo analysis: {e}")
    finally:
        if netlist_path.exists():
            netlist_path.unlink()


def example_worst_case_analysis():
    """Demonstrate worst-case analysis."""
    print("\n=== Worst-Case Analysis Example ===")
    
    # Create an amplifier circuit for worst-case analysis
    netlist_content = """* Operational Amplifier Circuit
* For Worst-Case Analysis

.param R1_nom=10k R1_tol=0.05
.param R2_nom=100k R2_tol=0.05
.param C1_nom=1n C1_tol=0.1
.param temp_nom=25

V1 vin 0 AC 1 0
R1 vin n1 {R1_nom}
R2 n1 vout {R2_nom}
C1 n1 vout {C1_nom}
XU1 0 n1 vcc vee vout OPAMP
V_VCC vcc 0 DC 15
V_VEE vee 0 DC -15

.subckt OPAMP in+ in- vcc vee out
Rin in+ in- 1meg
E1 out 0 in+ in- 100000
Rout out 0 100
.ends

.ac dec 10 10 100k
.temp {temp_nom}
.end
"""
    
    netlist_path = Path("temp_wc_circuit.net")
    with open(netlist_path, 'w') as f:
        f.write(netlist_content)
    
    try:
        # Initialize worst-case analysis
        wc_analysis = WorstCaseAnalysis()
        
        print("Configuring worst-case analysis...")
        
        wc_analysis.set_circuit(str(netlist_path))
        wc_analysis.set_analysis_type('ac')
        wc_analysis.set_output_variable('v(vout)')
        wc_analysis.set_frequency_point(1000)  # Analyze at 1kHz
        
        # Define component tolerances
        tolerances = {
            'R1': 0.05,  # 5%
            'R2': 0.05,  # 5%
            'C1': 0.10,  # 10%
        }
        
        for comp, tol in tolerances.items():
            wc_analysis.add_component_tolerance(comp, tol)
        
        # Add temperature variation
        wc_analysis.add_temperature_variation(min_temp=-40, max_temp=85)
        
        print("Running worst-case analysis...")
        results = wc_analysis.run_analysis()
        
        if results:
            print("✓ Worst-case analysis completed")
            
            wc_results = wc_analysis.get_worst_case_results()
            print(f"Worst-case results at 1kHz:")
            print(f"  Maximum gain: {wc_results['max_gain']:.2f} dB")
            print(f"  Minimum gain: {wc_results['min_gain']:.2f} dB")
            print(f"  Gain variation: {wc_results['gain_variation']:.2f} dB")
            
            # Get the worst-case combinations
            worst_combinations = wc_analysis.get_worst_combinations()
            print(f"  Worst-case high combination: {worst_combinations['high']}")
            print(f"  Worst-case low combination: {worst_combinations['low']}")
            
        else:
            print("✗ Worst-case analysis failed")
            
    except Exception as e:
        print(f"Error in worst-case analysis: {e}")
    finally:
        if netlist_path.exists():
            netlist_path.unlink()


def example_fast_worst_case():
    """Demonstrate fast worst-case analysis using linearization."""
    print("\n=== Fast Worst-Case Analysis Example ===")
    
    # Create a filter circuit
    netlist_content = """* Second-order filter for fast worst-case
.param R1_nom=1k R1_tol=0.05
.param R2_nom=1k R2_tol=0.05  
.param C1_nom=100n C1_tol=0.1
.param C2_nom=47n C2_tol=0.1

V1 vin 0 AC 1 0
R1 vin n1 {R1_nom}
C1 n1 0 {C1_nom}
R2 n1 vout {R2_nom}
C2 vout 0 {C2_nom}

.ac dec 20 10 10k
.end
"""
    
    netlist_path = Path("temp_fast_wc.net")
    with open(netlist_path, 'w') as f:
        f.write(netlist_content)
    
    try:
        # Initialize fast worst-case analysis
        fast_wc = FastWorstCaseAnalysis()
        
        print("Configuring fast worst-case analysis...")
        
        fast_wc.set_circuit(str(netlist_path))
        fast_wc.set_analysis_frequency_range(10, 10000)
        fast_wc.set_output_variable('v(vout)')
        
        # Add component sensitivities
        components = ['R1', 'R2', 'C1', 'C2']
        tolerances = [0.05, 0.05, 0.1, 0.1]
        
        for comp, tol in zip(components, tolerances):
            fast_wc.add_component_tolerance(comp, tol)
        
        print("Running fast worst-case analysis...")
        results = fast_wc.run_analysis()
        
        if results:
            print("✓ Fast worst-case analysis completed")
            
            # Get sensitivity information
            sensitivities = fast_wc.get_sensitivities()
            print("Component sensitivities:")
            for comp, sens in sensitivities.items():
                print(f"  {comp}: {sens:.3f} dB/%")
            
            # Get frequency response bounds
            bounds = fast_wc.get_frequency_bounds()
            print(f"Frequency response bounds:")
            print(f"  Corner frequency range: {bounds['fc_min']:.1f} - {bounds['fc_max']:.1f} Hz")
            print(f"  Peak gain range: {bounds['gain_min']:.2f} - {bounds['gain_max']:.2f} dB")
            
        else:
            print("✗ Fast worst-case analysis failed")
            
    except Exception as e:
        print(f"Error in fast worst-case analysis: {e}")
    finally:
        if netlist_path.exists():
            netlist_path.unlink()


def example_sensitivity_analysis():
    """Demonstrate sensitivity analysis."""
    print("\n=== Sensitivity Analysis Example ===")
    
    # Create a bias circuit for sensitivity analysis
    netlist_content = """* BJT Bias Circuit for Sensitivity Analysis
.param VCC=12
.param R1_nom=10k
.param R2_nom=2.2k  
.param RC_nom=1k
.param RE_nom=220

VCC vcc 0 DC {VCC}
R1 vcc base {R1_nom}
R2 base 0 {R2_nom}
RC vcc coll {RC_nom}
RE emit 0 {RE_nom}
Q1 coll base emit BJT_MODEL

.model BJT_MODEL NPN(BF=100 IS=1e-14)
.op
.end
"""
    
    netlist_path = Path("temp_sensitivity.net")
    with open(netlist_path, 'w') as f:
        f.write(netlist_content)
    
    try:
        # Initialize sensitivity analysis
        sens_analysis = SensitivityAnalysis()
        
        print("Configuring sensitivity analysis...")
        
        sens_analysis.set_circuit(str(netlist_path))
        sens_analysis.set_output_variables(['v(coll)', 'v(emit)', 'i(VCC)'])
        
        # Define parameters for sensitivity analysis
        parameters = {
            'VCC': {'nominal': 12, 'variation': 0.1},      # ±10%
            'R1_nom': {'nominal': 10000, 'variation': 0.05}, # ±5%
            'R2_nom': {'nominal': 2200, 'variation': 0.05},  # ±5%
            'RC_nom': {'nominal': 1000, 'variation': 0.05},  # ±5%
            'RE_nom': {'nominal': 220, 'variation': 0.05},   # ±5%
        }
        
        for param, config in parameters.items():
            sens_analysis.add_parameter(
                name=param,
                nominal_value=config['nominal'],
                variation=config['variation']
            )
        
        print("Running sensitivity analysis...")
        results = sens_analysis.run_analysis()
        
        if results:
            print("✓ Sensitivity analysis completed")
            
            # Get sensitivity results
            sensitivities = sens_analysis.get_sensitivities()
            
            print("Parameter sensitivities:")
            for output_var in ['v(coll)', 'v(emit)', 'i(VCC)']:
                print(f"\n  {output_var}:")
                for param, sens in sensitivities[output_var].items():
                    print(f"    {param}: {sens:.3f} %/%")
            
            # Get most sensitive parameters
            critical_params = sens_analysis.get_critical_parameters(threshold=0.1)
            print(f"\nCritical parameters (sensitivity > 0.1 %/%):")
            for output_var, params in critical_params.items():
                print(f"  {output_var}: {params}")
            
        else:
            print("✗ Sensitivity analysis failed")
            
    except Exception as e:
        print(f"Error in sensitivity analysis: {e}")
    finally:
        if netlist_path.exists():
            netlist_path.unlink()


def example_tolerance_analysis():
    """Demonstrate tolerance and deviation analysis."""
    print("\n=== Tolerance Analysis Example ===")
    
    # Create a precision voltage reference
    netlist_content = """* Precision Voltage Reference
* For tolerance analysis

.param R1_nom=10k R1_tol=0.01
.param R2_nom=10k R2_tol=0.01
.param R3_nom=1k R3_tol=0.05
.param VREF_nom=2.5 VREF_tol=0.002

VREF vref 0 DC {VREF_nom}
R1 vref n1 {R1_nom}
R2 n1 vout {R2_nom}
R3 vout 0 {R3_nom}

.op
.end
"""
    
    netlist_path = Path("temp_tolerance.net")
    with open(netlist_path, 'w') as f:
        f.write(netlist_content)
    
    try:
        # Initialize tolerance analysis
        tol_analysis = ToleranceDeviations()
        
        print("Configuring tolerance analysis...")
        
        tol_analysis.set_circuit(str(netlist_path))
        tol_analysis.set_output_variable('v(vout)')
        
        # Define component tolerances with different distributions
        components = [
            {'name': 'R1_nom', 'nominal': 10000, 'tolerance': 0.01, 'distribution': 'uniform'},
            {'name': 'R2_nom', 'nominal': 10000, 'tolerance': 0.01, 'distribution': 'uniform'},
            {'name': 'R3_nom', 'nominal': 1000, 'tolerance': 0.05, 'distribution': 'gaussian'},
            {'name': 'VREF_nom', 'nominal': 2.5, 'tolerance': 0.002, 'distribution': 'gaussian'},
        ]
        
        for comp in components:
            tol_analysis.add_component(
                name=comp['name'],
                nominal_value=comp['nominal'],
                tolerance=comp['tolerance'],
                distribution=comp['distribution']
            )
        
        print("Running tolerance analysis...")
        results = tol_analysis.run_analysis()
        
        if results:
            print("✓ Tolerance analysis completed")
            
            # Get tolerance budget
            budget = tol_analysis.get_tolerance_budget()
            print("Tolerance budget breakdown:")
            total_contribution = 0
            for comp, contribution in budget.items():
                print(f"  {comp}: {contribution:.1f}% contribution")
                total_contribution += contribution
            
            print(f"  Total: {total_contribution:.1f}%")
            
            # Get RSS (Root Sum of Squares) analysis
            rss_result = tol_analysis.get_rss_analysis()
            print(f"\nRSS Analysis:")
            print(f"  Worst-case (arithmetic): ±{rss_result['worst_case']:.3f}")
            print(f"  RSS estimate: ±{rss_result['rss']:.3f}")
            print(f"  Improvement factor: {rss_result['improvement_factor']:.1f}x")
            
        else:
            print("✗ Tolerance analysis failed")
            
    except Exception as e:
        print(f"Error in tolerance analysis: {e}")
    finally:
        if netlist_path.exists():
            netlist_path.unlink()


def example_failure_mode_analysis():
    """Demonstrate failure mode analysis."""
    print("\n=== Failure Mode Analysis Example ===")
    
    # Create a power supply circuit
    netlist_content = """* Linear Regulator Circuit
* For failure mode analysis

.param VIN=15
.param R1=1k
.param R2=2.2k
.param C1=100u
.param C2=10u

VIN vin 0 DC {VIN}
R1 vin reg_in {R1}
XREG reg_in 0 vout REGULATOR
R2 vout 0 {R2}
C1 vin 0 {C1}
C2 vout 0 {C2}

.subckt REGULATOR in gnd out
* Simple regulator model
R_series in n1 10
R_shunt n1 gnd 1k
E_reg out gnd n1 gnd 0.8
R_load out gnd 100
.ends

.op
.dc VIN 10 20 0.5
.end
"""
    
    netlist_path = Path("temp_failure.net")
    with open(netlist_path, 'w') as f:
        f.write(netlist_content)
    
    try:
        # Initialize failure mode analysis
        failure_analysis = FailureMode()
        
        print("Configuring failure mode analysis...")
        
        failure_analysis.set_circuit(str(netlist_path))
        failure_analysis.set_output_variable('v(vout)')
        
        # Define failure modes
        failure_modes = [
            {
                'name': 'R1_open',
                'component': 'R1',
                'failure_type': 'open_circuit',
                'probability': 1e-6  # per hour
            },
            {
                'name': 'R1_short',
                'component': 'R1', 
                'failure_type': 'short_circuit',
                'probability': 1e-7
            },
            {
                'name': 'C1_short',
                'component': 'C1',
                'failure_type': 'short_circuit',
                'probability': 1e-5
            },
            {
                'name': 'C1_open',
                'component': 'C1',
                'failure_type': 'open_circuit',
                'probability': 1e-6
            },
            {
                'name': 'regulator_fail',
                'component': 'XREG',
                'failure_type': 'parameter_drift',
                'parameters': {'gain': 0.1},  # 90% gain reduction
                'probability': 1e-4
            }
        ]
        
        for failure in failure_modes:
            failure_analysis.add_failure_mode(**failure)
        
        print("Running failure mode analysis...")
        results = failure_analysis.run_analysis()
        
        if results:
            print("✓ Failure mode analysis completed")
            
            # Get failure impact analysis
            impact_analysis = failure_analysis.get_failure_impact()
            print("Failure mode impact on output voltage:")
            
            for failure_name, impact in impact_analysis.items():
                print(f"  {failure_name}:")
                print(f"    Output change: {impact['output_change']:.3f} V")
                print(f"    Severity: {impact['severity']}")
                print(f"    Probability: {impact['probability']:.2e} per hour")
            
            # Get system reliability
            reliability = failure_analysis.get_system_reliability(time_hours=8760)  # 1 year
            print(f"\nSystem reliability (1 year): {reliability:.4f}")
            print(f"MTBF: {failure_analysis.get_mtbf():.1f} hours")
            
        else:
            print("✗ Failure mode analysis failed")
            
    except Exception as e:
        print(f"Error in failure mode analysis: {e}")
    finally:
        if netlist_path.exists():
            netlist_path.unlink()


def main():
    """Run all analysis toolkit examples."""
    print("CESPy Analysis Toolkit Examples")
    print("=" * 60)
    
    # Run all analysis examples
    example_monte_carlo_analysis()
    example_worst_case_analysis()
    example_fast_worst_case()
    example_sensitivity_analysis()
    example_tolerance_analysis()
    example_failure_mode_analysis()
    
    print("\n" + "=" * 60)
    print("Analysis toolkit examples completed!")
    print("\nAnalysis techniques demonstrated:")
    print("- Monte Carlo statistical analysis")
    print("- Worst-case corner analysis")
    print("- Fast worst-case using linearization")
    print("- Parameter sensitivity analysis")
    print("- Tolerance budget analysis")
    print("- Failure mode and reliability analysis")
    print("\nNext: See data processing examples (04_data_processing.py)")


if __name__ == "__main__":
    main()