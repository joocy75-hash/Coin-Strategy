#!/usr/bin/env python3
"""
Quick Moon Dev Optimization - 5 Trials for Testing
This validates the bug fix works across multiple datasets before running full 100 trials.
"""

import sys
sys.path.append('/Users/mr.joo/Desktop/전략연구소')

from optimize_adaptive_ml_moon_dev import MoonDevOptimizer

def main():
    print("=" * 80)
    print("QUICK MOON DEV OPTIMIZATION - 5 TRIALS")
    print("=" * 80)
    print("\nThis will validate the bug fix across multiple datasets.")
    print("If successful, proceed with full 100-trial optimization.\n")

    # Initialize optimizer
    optimizer = MoonDevOptimizer(
        n_trials=5,  # Quick test with just 5 trials
        n_datasets=5  # Use only 5 datasets for speed
    )

    # Run optimization
    print("Starting optimization...")
    try:
        study = optimizer.optimize()

        # Get best results
        best_score = optimizer.best_score
        best_params = optimizer.best_params

        # Summary
        print("\n" + "=" * 80)
        print("QUICK TEST RESULTS:")
        print("=" * 80)
        print(f"Best Score: {best_score:.4f}")
        print(f"Best Parameters:")
        for key, value in best_params.items():
            print(f"  {key}: {value}")

        # Validate success
        if best_score > 0:
            print("\n✅ SUCCESS: Optimization working! Trades are being executed.")
            print("   Ready to run full 100-trial optimization.")
            return 0
        else:
            print("\n❌ FAILED: Score still 0. Bug may not be fully fixed.")
            return 1

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
