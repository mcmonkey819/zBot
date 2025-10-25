# -*- coding: utf-8 -*-
"""
Test runner for pinned race state persistence feature.
Runs all tests related to the pinned race state functionality.
"""
import os
import subprocess
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows compatibility
os.environ['PYTHONIOENCODING'] = 'utf-8'


def run_pinned_race_state_tests():
    """Run all pinned race state related tests."""
    test_files = [
        "test/unit/test_pinned_race_state_helpers.py",
        "test/unit/test_pinned_race_state_model.py", 
        "test/integration/test_pinned_race_state_ui.py",
        "test/integration/test_pinned_race_state_commands.py"
    ]
    
    print("Running Pinned Race State Persistence Tests")
    print("=" * 50)
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_file in test_files:
        print(f"\nRunning {test_file}...")
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"
            ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
            
            if result.returncode == 0:
                print(f"[PASS] {test_file} - PASSED")
                # Count tests from output
                lines = result.stdout.split('\n')
                for line in lines:
                    if '::' in line and 'PASSED' in line:
                        passed_tests += 1
                        total_tests += 1
            else:
                print(f"[FAIL] {test_file} - FAILED")
                print(result.stdout)
                print(result.stderr)
                # Count failed tests
                lines = result.stdout.split('\n')
                for line in lines:
                    if '::' in line and ('FAILED' in line or 'ERROR' in line):
                        failed_tests += 1
                        total_tests += 1
                        
        except Exception as e:
            print(f"[ERROR] Error running {test_file}: {e}")
            failed_tests += 1
            total_tests += 1
    
    print("\n" + "=" * 50)
    print(f"Test Summary:")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "No tests run")
    
    return failed_tests == 0


def run_specific_test_category(category):
    """Run tests for a specific category."""
    if category == "unit":
        test_files = [
            "test/unit/test_pinned_race_state_helpers.py",
            "test/unit/test_pinned_race_state_model.py"
        ]
    elif category == "integration":
        test_files = [
            "test/integration/test_pinned_race_state_ui.py",
            "test/integration/test_pinned_race_state_commands.py"
        ]
    else:
        print(f"Unknown category: {category}")
        return False
    
    print(f"Running {category} tests for pinned race state feature...")
    
    for test_file in test_files:
        print(f"\nRunning {test_file}...")
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"
            ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
            
            if result.returncode == 0:
                print(f"[PASS] {test_file} - PASSED")
            else:
                print(f"[FAIL] {test_file} - FAILED")
                print(result.stdout)
                print(result.stderr)
                return False
        except Exception as e:
            print(f"[ERROR] Error running {test_file}: {e}")
            return False
    
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        category = sys.argv[1]
        success = run_specific_test_category(category)
    else:
        success = run_pinned_race_state_tests()
    
    sys.exit(0 if success else 1)
