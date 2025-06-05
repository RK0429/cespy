#!/usr/bin/env python3
"""
Batch and Distributed Simulation Examples

This example demonstrates batch processing, distributed simulation,
client-server architecture, and performance optimization techniques.
"""

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

# Add the cespy package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cespy import LTspice  # noqa: E402
from cespy.client_server import ServerSimRunner, SimClient, SimServer  # noqa: E402
from cespy.editor import SpiceEditor  # noqa: E402
from cespy.sim import SimBatch, SimRunner  # noqa: E402


def example_basic_batch_simulation():
    """Demonstrate basic batch simulation capabilities."""
    print("=== Basic Batch Simulation Example ===")

    # Create a base circuit for batch simulation
    base_netlist = """* RC Filter for Batch Simulation
.param R_val=1k
.param C_val=1n
.param freq=1k

V1 vin 0 AC 1 0
R1 vin vout {R_val}
C1 vout 0 {C_val}

.ac dec 10 1 100k
.end
"""

    base_path = Path("batch_base_circuit.net")
    with open(base_path, "w") as f:
        f.write(base_netlist)

    try:
        print("Setting up batch simulation...")

        # Initialize batch simulator
        batch_sim = SimBatch()

        # Configure batch parameters
        batch_sim.set_base_circuit(str(base_path))
        batch_sim.set_simulator(LTspice())

        # Define parameter variations
        resistance_values = [100, 500, 1000, 2200, 4700, 10000]  # ohms
        capacitance_values = [100e-12, 470e-12, 1e-9, 2.2e-9, 4.7e-9]  # farads

        # Generate all combinations
        simulation_jobs = []
        job_id = 0

        for r_val in resistance_values:
            for c_val in capacitance_values:
                job_params = {
                    "R_val": str(r_val),
                    "C_val": f"{c_val:.2e}",
                    "job_id": job_id,
                }
                simulation_jobs.append(job_params)
                job_id += 1

        print(f"Generated {len(simulation_jobs)} simulation jobs")

        # Add jobs to batch
        for job in simulation_jobs[:10]:  # Limit to first 10 for demo
            batch_sim.add_job(
                job_id=job["job_id"],
                parameters=job,
                output_file=f"batch_result_{job['job_id']}.raw",
            )

        print("Running batch simulation...")
        start_time = time.time()

        # Run batch with progress callback
        def progress_callback(completed, total, current_job):
            progress = (completed / total) * 100
            print(f"  Progress: {progress:.1f}% (Job {current_job})")

        batch_sim.set_progress_callback(progress_callback)
        results = batch_sim.run_batch()

        elapsed_time = time.time() - start_time
        print(f"✓ Batch simulation completed in {elapsed_time:.2f} seconds")

        # Analyze batch results
        successful_jobs = [job for job in results if job["status"] == "success"]
        failed_jobs = [job for job in results if job["status"] == "failed"]

        print("Results summary:")
        print(f"  Successful: {len(successful_jobs)}")
        print(f"  Failed: {len(failed_jobs)}")
        print(f"  Success rate: {len(successful_jobs)/len(results)*100:.1f}%")

        # Extract key metrics from successful jobs
        if successful_jobs:
            print("Sample results:")
            for job in successful_jobs[:3]:  # Show first 3
                job_params: dict[str, object] = job["parameters"]
                print(
                    f"  Job {job['job_id']}: R={job_params['R_val']}, "
                    f"C={job_params['C_val']}"
                )

    except Exception as e:
        print(f"Error in batch simulation: {e}")
    finally:
        # Cleanup
        if base_path.exists():
            base_path.unlink()

        # Clean up result files
        for i in range(10):
            result_file = Path(f"batch_result_{i}.raw")
            if result_file.exists():
                result_file.unlink()


def example_parallel_simulation() -> None:
    """Demonstrate parallel simulation using threading and multiprocessing."""
    print("\n=== Parallel Simulation Example ===")

    # Create multiple circuit variants
    circuits = []
    for i in range(6):
        circuit_content = f"""* Parallel Simulation Circuit {i}
.param gain={10 + i * 5}
.param freq={1000 * (i + 1)}

V1 vin 0 SINE(0 1 {{freq}})
R1 vin n1 1k
R2 n1 vout {{gain}}k
C1 vout 0 1n

.tran 0 5m 0 10u
.end
"""
        circuit_path = Path(f"parallel_circuit_{i}.net")
        with open(circuit_path, "w") as f:
            f.write(circuit_content)
        circuits.append(circuit_path)

    try:
        print(f"Created {len(circuits)} circuits for parallel simulation")

        # Sequential simulation for comparison
        print("Running sequential simulations...")
        start_time = time.time()

        sequential_results = []
        for i, circuit_path in enumerate(circuits):
            runner = SimRunner(simulator=LTspice)
            result = runner.run(str(circuit_path))
            sequential_results.append(
                {"circuit": i, "success": result, "time": time.time()}
            )

        sequential_time = time.time() - start_time
        print(f"Sequential time: {sequential_time:.2f} seconds")

        # Parallel simulation using ThreadPoolExecutor
        print("Running parallel simulations (threading)...")

        def run_single_simulation(circuit_info):
            circuit_id, circuit_path = circuit_info
            runner = SimRunner(simulator=LTspice)

            start = time.time()
            result = runner.run(str(circuit_path))
            end = time.time()

            return {"circuit": circuit_id, "success": result, "time": end - start}

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=3) as executor:
            circuit_info = [(i, path) for i, path in enumerate(circuits)]
            threaded_results = list(executor.map(run_single_simulation, circuit_info))

        threaded_time = time.time() - start_time
        print(f"Threaded time: {threaded_time:.2f} seconds")

        # Calculate speedup
        speedup = sequential_time / threaded_time
        print(f"Threading speedup: {speedup:.2f}x")

        # Parallel simulation using ProcessPoolExecutor
        print("Running parallel simulations (multiprocessing)...")

        start_time = time.time()

        # Note: Process-based parallelism may have overhead for small simulations
        with ProcessPoolExecutor(max_workers=2) as executor:
            circuit_info = [
                (i, path) for i, path in enumerate(circuits[:4])
            ]  # Limit for demo
            process_results = list(executor.map(run_single_simulation, circuit_info))

        process_time = time.time() - start_time
        print(f"Process-based time: {process_time:.2f} seconds")

        # Results summary
        successful_sequential = sum(1 for r in sequential_results if r["success"])
        successful_threaded = sum(1 for r in threaded_results if r["success"])
        successful_process = sum(1 for r in process_results if r["success"])

        print("Success rates:")
        print(f"  Sequential: {successful_sequential}/{len(sequential_results)}")
        print(f"  Threaded: {successful_threaded}/{len(threaded_results)}")
        print(f"  Process-based: {successful_process}/{len(process_results)}")

    except Exception as e:
        print(f"Error in parallel simulation: {e}")
    finally:
        # Cleanup
        for circuit_path in circuits:
            if circuit_path.exists():
                circuit_path.unlink()


def example_client_server_simulation() -> None:
    """Demonstrate client-server distributed simulation."""
    print("\n=== Client-Server Simulation Example ===")

    try:
        print("Setting up client-server simulation...")

        # Create a circuit for distributed simulation
        server_circuit = """* Distributed Simulation Circuit
.param R1_val=1k
.param R2_val=10k
.param C1_val=1n

V1 vin 0 AC 1 0
R1 vin n1 {R1_val}
R2 n1 vout {R2_val}
C1 vout 0 {C1_val}

.ac dec 10 1 100k
.end
"""

        circuit_path = Path("server_circuit.net")
        with open(circuit_path, "w") as f:
            f.write(server_circuit)

        # Configure server
        server_config = {
            "host": "localhost",
            "port": 9090,
            "max_workers": 3,
            "simulator": LTspice(),
        }

        # Simulate server setup (in real usage, server runs in separate process)
        print("Configuring simulation server...")
        server = SimServer(**server_config)

        # Note: In actual usage, you would start the server:
        # server.start()

        print("Setting up simulation clients...")

        # Create multiple clients for distributed work
        client_jobs = []

        # Define different parameter sets for clients
        parameter_sets = [
            {"R1_val": "500", "R2_val": "5k", "C1_val": "2n"},
            {"R1_val": "1k", "R2_val": "10k", "C1_val": "1n"},
            {"R1_val": "2k", "R2_val": "20k", "C1_val": "500p"},
            {"R1_val": "4.7k", "R2_val": "47k", "C1_val": "470p"},
        ]

        # Simulate client requests
        print("Simulating distributed simulation requests...")

        for i, params in enumerate(parameter_sets):
            # Create client
            client = SimClient(host="localhost", port=9090)

            # Prepare job
            job_request = {
                "job_id": f"client_job_{i}",
                "circuit_file": str(circuit_path),
                "parameters": params,
                "analysis_type": "ac",
                "priority": "normal",
            }

            client_jobs.append({"client": client, "request": job_request, "job_id": i})

        print(f"Created {len(client_jobs)} client jobs")

        # Simulate job execution (normally done by server)
        print("Executing distributed jobs...")

        job_results = []
        for job in client_jobs:
            # Simulate job processing
            print(f"  Processing job {job['job_id']}...")

            # In real implementation, this would be handled by the server
            runner = ServerSimRunner()
            runner.set_circuit(job["request"]["circuit_file"])
            runner.set_parameters(job["request"]["parameters"])

            start_time = time.time()
            result = runner.run()
            execution_time = time.time() - start_time

            job_results.append(
                {
                    "job_id": job["job_id"],
                    "success": result,
                    "execution_time": execution_time,
                    "parameters": job["request"]["parameters"],
                }
            )

            print(f"    Job {job['job_id']} completed in {execution_time:.3f}s")

        # Results analysis
        print("Distributed simulation results:")
        total_jobs = len(job_results)
        successful_jobs = sum(1 for r in job_results if r["success"])
        total_time = sum(r["execution_time"] for r in job_results)

        print(f"  Total jobs: {total_jobs}")
        print(f"  Successful: {successful_jobs}")
        print(f"  Success rate: {successful_jobs/total_jobs*100:.1f}%")
        print(f"  Total execution time: {total_time:.3f}s")
        print(f"  Average time per job: {total_time/total_jobs:.3f}s")

        # Show job details
        print("Job details:")
        for result in job_results:
            status = "✓" if result["success"] else "✗"
            print(f"  {status} Job {result['job_id']}: {result['execution_time']:.3f}s")

    except Exception as e:
        print(f"Error in client-server simulation: {e}")
    finally:
        if "circuit_path" in locals() and circuit_path.exists():
            circuit_path.unlink()


def example_performance_optimization() -> None:
    """Demonstrate performance optimization techniques."""
    print("\n=== Performance Optimization Example ===")

    try:
        print("Demonstrating performance optimization techniques...")

        # Create a moderately complex circuit for optimization testing
        complex_circuit = """* Performance Test Circuit
.param R1=1k R2=10k R3=100k
.param C1=1n C2=100p C3=10p
.param L1=1m L2=100u

V1 vin 0 AC 1 0
R1 vin n1 {R1}
C1 n1 n2 {C1}
L1 n2 n3 {L1}
R2 n3 n4 {R2}
C2 n4 n5 {C2}
L2 n5 n6 {L2}
R3 n6 vout {R3}
C3 vout 0 {C3}

.ac dec 20 1 10meg
.end
"""

        circuit_path = Path("performance_test.net")
        with open(circuit_path, "w") as f:
            f.write(complex_circuit)

        # Test 1: Basic simulation timing
        print("Test 1: Basic simulation timing...")

        runner = SimRunner(simulator=LTspice)

        # Warm-up run
        runner.run(str(circuit_path))

        # Timed runs
        times = []
        for i in range(5):
            start_time = time.time()
            result = runner.run()
            elapsed = time.time() - start_time
            times.append(elapsed)
            print(f"  Run {i+1}: {elapsed:.3f}s")

        avg_time = sum(times) / len(times)
        print(f"  Average time: {avg_time:.3f}s")

        # Test 2: Optimized simulation settings
        print("\nTest 2: Optimized simulation settings...")

        # Configure for performance
        optimized_runner = SimRunner(simulator=LTspice)

        # Apply optimizations
        optimizations = {
            "solver": "gear",  # Faster solver for many circuits
            "reltol": "1e-3",  # Relaxed tolerance for speed
            "abstol": "1e-9",  # Relaxed tolerance
            "vntol": "1e-3",  # Relaxed voltage tolerance
            "chgtol": "1e-12",  # Relaxed charge tolerance
        }

        # Add optimization directives
        editor = SpiceEditor(str(circuit_path))
        for param, value in optimizations.items():
            if param == "solver":
                editor.add_instruction(f".options method={value}")
            else:
                editor.add_instruction(f".options {param}={value}")

        optimized_path = circuit_path.with_name("optimized_circuit.net")
        editor.save_netlist(str(optimized_path))

        # Use the optimized path

        # Measure optimized performance
        optimized_times = []
        for i in range(5):
            start_time = time.time()
            result = optimized_runner.run(str(optimized_path))
            elapsed = time.time() - start_time
            optimized_times.append(elapsed)
            print(f"  Optimized run {i+1}: {elapsed:.3f}s")

        avg_optimized_time = sum(optimized_times) / len(optimized_times)
        speedup = avg_time / avg_optimized_time

        print(f"  Average optimized time: {avg_optimized_time:.3f}s")
        print(f"  Speedup: {speedup:.2f}x")

        # Test 3: Memory usage optimization
        print("\nTest 3: Memory usage monitoring...")

        import psutil

        process = psutil.Process(os.getpid())

        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"  Baseline memory: {baseline_memory:.1f} MB")

        # Run simulation and monitor memory
        start_memory = process.memory_info().rss / 1024 / 1024
        runner.run(str(circuit_path))
        peak_memory = process.memory_info().rss / 1024 / 1024

        memory_usage = peak_memory - start_memory
        print(f"  Memory usage during simulation: {memory_usage:.1f} MB")

        # Test 4: Disk I/O optimization
        print("\nTest 4: Disk I/O optimization...")

        # Test with temporary files vs. persistent files
        import tempfile

        # Persistent file test
        start_time = time.time()
        for i in range(3):
            persistent_runner = SimRunner(simulator=LTspice)
            persistent_runner.run(str(circuit_path))
        persistent_time = time.time() - start_time

        # Temporary file test
        start_time = time.time()
        for i in range(3):
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".net", delete=False
            ) as tmp_file:
                tmp_file.write(complex_circuit)
                tmp_path = tmp_file.name

            temp_runner = SimRunner(simulator=LTspice)
            temp_runner.run(tmp_path)

            Path(tmp_path).unlink()  # Clean up

        temp_time = time.time() - start_time

        print(f"  Persistent files: {persistent_time:.3f}s")
        print(f"  Temporary files: {temp_time:.3f}s")

        if temp_time < persistent_time:
            io_speedup = persistent_time / temp_time
            print(f"  I/O speedup with temp files: {io_speedup:.2f}x")
        else:
            print("  No I/O improvement with temp files")

        # Performance summary
        print("\nPerformance optimization summary:")
        print(f"  Solver optimization speedup: {speedup:.2f}x")
        print(f"  Memory usage per simulation: {memory_usage:.1f} MB")
        print("  Recommendations:")
        print("    - Use relaxed tolerances for non-critical simulations")
        print("    - Consider temporary files for batch processing")
        print("    - Monitor memory usage for large datasets")
        print("    - Use parallel processing for independent jobs")

        # Clean up optimized file
        if optimized_path.exists():
            optimized_path.unlink()

    except Exception as e:
        print(f"Error in performance optimization: {e}")
    finally:
        if "circuit_path" in locals() and circuit_path.exists():
            circuit_path.unlink()


def main() -> None:
    """Run all batch and distributed simulation examples."""
    print("CESPy Batch and Distributed Simulation Examples")
    print("=" * 80)

    # Run all examples
    example_basic_batch_simulation()
    example_parallel_simulation()
    example_client_server_simulation()
    example_performance_optimization()

    print("\n" + "=" * 80)
    print("Batch and distributed simulation examples completed!")
    print("\nCapabilities demonstrated:")
    print("- Basic batch simulation with parameter sweeps")
    print("- Parallel simulation using threading and multiprocessing")
    print("- Client-server distributed simulation architecture")
    print("- Performance optimization techniques")
    print("- Memory and I/O usage monitoring")
    print("\nNext: See platform integration examples (06_platform_integration.py)")


if __name__ == "__main__":
    main()
