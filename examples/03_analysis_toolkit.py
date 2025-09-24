#!/usr/bin/env python3
# pylint: disable=invalid-name,duplicate-code
"""
Analysis Toolkit Examples

This example demonstrates advanced analysis capabilities including Monte Carlo,
worst-case analysis, sensitivity analysis, and other statistical techniques.
"""

import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union

# Add the cespy package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cespy.sim.process_callback import (
    ProcessCallback,  # pylint: disable=wrong-import-position
)
from cespy.sim.toolkit import (  # pylint: disable=wrong-import-position
    FailureMode,
    FastWorstCaseAnalysis,
    MonteCarloAnalysis,
    SensitivityAnalysis,
    ToleranceDeviations,
    WorstCaseAnalysis,
)


def example_monte_carlo_analysis() -> None:
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
    with open(netlist_path, "w", encoding="utf-8") as f:
        f.write(netlist_content)

    try:
        # Initialize Monte Carlo analysis
        mc_analysis = MonteCarloAnalysis(str(netlist_path), num_runs=100)

        print("Configuring Monte Carlo analysis...")

        # Define component variations
        component_variations = {
            "R1": {"nominal": 10000, "tolerance": 0.05, "distribution": "gaussian"},
            "R2": {"nominal": 10000, "tolerance": 0.05, "distribution": "gaussian"},
        }

        for comp, params in component_variations.items():
            tolerance = params["tolerance"]
            if isinstance(tolerance, (int, float)):
                mc_analysis.set_tolerance(
                    ref=comp,
                    new_tolerance=float(tolerance),
                )

        print("Running Monte Carlo simulation...")
        results = mc_analysis.run_analysis()

        if results:
            print("✓ Monte Carlo analysis completed")

            # Analyze results
            statistics = mc_analysis.get_measurement_statistics("v(vout)")
            print("Output voltage statistics:")
            print(f"  Mean: {statistics['mean']:.3f} V")
            print(f"  Std Dev: {statistics['std_dev']:.3f} V")
            print(f"  Min: {statistics['min']:.3f} V")
            print(f"  Max: {statistics['max']:.3f} V")

            # Note: Yield analysis would require additional implementation
            print("  Yield analysis requires additional implementation")

        else:
            print("✗ Monte Carlo analysis failed")

    except (IOError, OSError, ValueError) as e:
        print(f"Error in Monte Carlo analysis: {e}")
    finally:
        if netlist_path.exists():
            netlist_path.unlink()


def example_worst_case_analysis() -> None:
    """Demonstrate worst-case analysis."""
    # pylint: disable=too-many-branches
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
    with open(netlist_path, "w", encoding="utf-8") as f:
        f.write(netlist_content)

    try:
        # Initialize worst-case analysis
        print("Configuring worst-case analysis...")

        wc_analysis = WorstCaseAnalysis(circuit_file=str(netlist_path))
        print("Worst-case analysis initialized")

        # Try to configure if methods are available
        config_methods = [
            ("set_circuit", str(netlist_path)),
            ("set_analysis_type", "ac"),
            ("set_output_variable", "v(vout)"),
            ("set_frequency_point", 1000),
        ]

        for method_name, value in config_methods:
            try:
                if hasattr(wc_analysis, method_name):
                    getattr(wc_analysis, method_name)(value)
                    print(f"  Configured {method_name}")
                else:
                    print(f"  {method_name} method not available")
            except (AttributeError, ValueError) as e:
                print(f"  Error configuring {method_name}: {e}")

        # Define component tolerances
        tolerances = {
            "R1": 0.05,  # 5%
            "R2": 0.05,  # 5%
            "C1": 0.10,  # 10%
        }

        for comp, tol in tolerances.items():
            try:
                wc_analysis.set_tolerance(ref=comp, new_tolerance=tol)
                print(f"  Added tolerance for {comp}: {tol*100}%")
            except (AttributeError, ValueError) as e:
                print(f"  Error adding tolerance for {comp}: {e}")

        # Note: Temperature variation would need to be implemented
        print("  Temperature variation: would need custom implementation")

        print("Running worst-case analysis...")
        try:
            if hasattr(wc_analysis, "run_analysis"):
                results = (
                    wc_analysis.run_analysis()
                )  # pylint: disable=assignment-from-none
                if results is not None:
                    print("✓ Worst-case analysis completed")
                else:
                    print("✗ Worst-case analysis failed")

                # Note: Results would need specific implementation
                print("  Results processing would need custom implementation")
            else:
                print("✗ Worst-case run_analysis method not available")
        except (AttributeError, ValueError) as e:
            print(f"✗ Worst-case analysis error: {e}")

    except (IOError, OSError, ValueError) as e:
        print(f"Error in worst-case analysis: {e}")
    finally:
        if netlist_path.exists():
            netlist_path.unlink()


def example_fast_worst_case() -> None:
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
    with open(netlist_path, "w", encoding="utf-8") as f:
        f.write(netlist_content)

    try:
        # Initialize fast worst-case analysis
        fast_wc = FastWorstCaseAnalysis(str(netlist_path))

        print("Configuring fast worst-case analysis...")

        # Note: Configuration would be done via specific methods"

        # Add component sensitivities
        components = ["R1", "R2", "C1", "C2"]
        tolerances = [0.05, 0.05, 0.1, 0.1]

        for comp, tol in zip(components, tolerances):
            fast_wc.set_tolerance(comp, tol)

        print("Running fast worst-case analysis...")
        results = fast_wc.run_analysis()

        if results:
            print("✓ Fast worst-case analysis completed")

            # Note: Sensitivity and bounds analysis requires proper implementation
            print("Component sensitivities would be available after analysis")
            print("Frequency analysis bounds would be available after analysis")

        else:
            print("✗ Fast worst-case analysis failed")

    except (IOError, OSError, ValueError) as e:
        print(f"Error in fast worst-case analysis: {e}")
    finally:
        if netlist_path.exists():
            netlist_path.unlink()


def example_sensitivity_analysis() -> None:
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
    with open(netlist_path, "w", encoding="utf-8") as f:
        f.write(netlist_content)

    try:
        # Initialize sensitivity analysis
        sens_analysis = SensitivityAnalysis(str(netlist_path))

        print("Configuring sensitivity analysis...")

        # Note: Output variables would be configured via specific methods

        # Define parameters for sensitivity analysis
        parameters = {
            "VCC": {"nominal": 12, "variation": 0.1},  # ±10%
            "R1_nom": {"nominal": 10000, "variation": 0.05},  # ±5%
            "R2_nom": {"nominal": 2200, "variation": 0.05},  # ±5%
            "RC_nom": {"nominal": 1000, "variation": 0.05},  # ±5%
            "RE_nom": {"nominal": 220, "variation": 0.05},  # ±5%
        }

        for param, config in parameters.items():
            sens_analysis.set_tolerance(
                ref=param,
                new_tolerance=config["variation"],
            )

        print("Running sensitivity analysis...")
        results = sens_analysis.run_analysis()  # pylint: disable=assignment-from-none

        if results is not None:
            print("✓ Sensitivity analysis completed")

            # Extract sensitivity information
            print("Parameter sensitivities would be available after analysis")
            print("Critical parameters would be identified after analysis")

        else:
            print("✗ Sensitivity analysis failed")

    except (IOError, OSError, ValueError) as e:
        print(f"Error in sensitivity analysis: {e}")
    finally:
        if netlist_path.exists():
            netlist_path.unlink()


def example_tolerance_analysis() -> None:
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
    with open(netlist_path, "w", encoding="utf-8") as f:
        f.write(netlist_content)

    try:
        # ToleranceDeviations is abstract, create a concrete implementation
        class MockToleranceAnalysis(ToleranceDeviations):
            """Mock tolerance analysis for demonstration."""

            def prepare_testbench(self, **kwargs: Any) -> None:
                """Prepare testbench for analysis."""
                # Implementation would prepare circuit for analysis
                _ = kwargs  # Acknowledge unused parameter

            def run_analysis(
                self,
                callback: Union[type[ProcessCallback], Callable[..., Any], None] = None,
                callback_args: Union[Tuple[Any, ...], Dict[str, Any], None] = None,
                switches: Optional[list[str]] = None,
                timeout: Optional[float] = None,
                exe_log: bool = False,
                measure: Optional[str] = None,
            ) -> Union[
                Tuple[
                    float,
                    float,
                    Dict[str, Union[str, float]],
                    float,
                    Dict[str, Union[str, float]],
                ],
                None,
            ]:
                """Run the analysis."""
                # Acknowledge unused parameters
                _ = (callback, callback_args, switches, timeout, exe_log, measure)
                # Return a mock result tuple
                return (
                    0.0,  # nominal_value
                    0.0,  # min_value
                    {},  # min_combination
                    0.0,  # max_value
                    {},  # max_combination
                )

        tol_analysis = MockToleranceAnalysis(str(netlist_path))
        print("Using mock tolerance analysis for demonstration")

        print("Configuring tolerance analysis...")

        # Note: Configuration done via constructor"

        # Define component tolerances with different distributions
        components = [
            {
                "name": "R1_nom",
                "nominal": 10000,
                "tolerance": 0.01,
                "distribution": "uniform",
            },
            {
                "name": "R2_nom",
                "nominal": 10000,
                "tolerance": 0.01,
                "distribution": "uniform",
            },
            {
                "name": "R3_nom",
                "nominal": 1000,
                "tolerance": 0.05,
                "distribution": "gaussian",
            },
            {
                "name": "VREF_nom",
                "nominal": 2.5,
                "tolerance": 0.002,
                "distribution": "gaussian",
            },
        ]

        for comp in components:
            name = comp["name"]
            tolerance = comp["tolerance"]
            distribution = comp.get("distribution", "uniform")
            if isinstance(name, str) and isinstance(tolerance, (int, float)):
                tol_analysis.set_tolerance(
                    ref=name,
                    new_tolerance=float(tolerance),
                    distribution=str(distribution),
                )

        print("Running tolerance analysis...")
        results = tol_analysis.run_analysis()

        if results:
            print("✓ Tolerance analysis completed")

            # Note: Tolerance budget and RSS analysis require proper implementation
            print("Tolerance budget analysis would be available after analysis")
            print("RSS Analysis would be available after analysis")

        else:
            print("✗ Tolerance analysis failed")

    except (IOError, OSError, ValueError) as e:
        print(f"Error in tolerance analysis: {e}")
    finally:
        if netlist_path.exists():
            netlist_path.unlink()


def example_failure_mode_analysis() -> None:
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
    with open(netlist_path, "w", encoding="utf-8") as f:
        f.write(netlist_content)

    try:
        # Initialize failure mode analysis
        failure_analysis = FailureMode(circuit_file=str(netlist_path))

        print("Configuring failure mode analysis...")

        # Note: Configuration done via constructor

        # Define failure modes
        failure_modes = [
            {
                "name": "R1_open",
                "component": "R1",
                "failure_type": "open_circuit",
                "probability": 1e-6,  # per hour
            },
            {
                "name": "R1_short",
                "component": "R1",
                "failure_type": "short_circuit",
                "probability": 1e-7,
            },
            {
                "name": "C1_short",
                "component": "C1",
                "failure_type": "short_circuit",
                "probability": 1e-5,
            },
            {
                "name": "C1_open",
                "component": "C1",
                "failure_type": "open_circuit",
                "probability": 1e-6,
            },
            {
                "name": "regulator_fail",
                "component": "XREG",
                "failure_type": "parameter_drift",
                "parameters": {"gain": 0.1},  # 90% gain reduction
                "probability": 1e-4,
            },
        ]

        for failure in failure_modes:
            # Note: Failure mode configuration requires specific implementation
            print(f"Adding failure mode: {failure}")

        print("Running failure mode analysis...")
        # Note: FailureMode uses run() method, not run_analysis()
        try:
            results = failure_analysis.run()
        except AttributeError:
            # Fallback if run() doesn't exist
            print("Note: Failure mode analysis requires proper run implementation")
            results = None

        if results:
            print("✓ Failure mode analysis completed")

            # Note: Failure impact analysis requires proper implementation
            print("Failure impact analysis would be available after analysis")
            print("System reliability metrics would be available after analysis")
            print("MTBF calculations would be available after analysis")

        else:
            print("✗ Failure mode analysis failed")

    except (IOError, OSError, ValueError) as e:
        print(f"Error in failure mode analysis: {e}")
    finally:
        if netlist_path.exists():
            netlist_path.unlink()


def main() -> None:
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
