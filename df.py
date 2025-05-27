import sys
import numpy as np

def apply_differential_privacy(true_count: int, epsilon: float, clamp_min: int = 0) -> int:
    if epsilon <= 0:
        raise ValueError("Epsilon must be > 0")
    noise = np.random.laplace(loc=0.0, scale=1/epsilon)
    noisy_count = round(true_count + noise)
    return max(noisy_count, clamp_min)

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 df.py <true_count> <epsilon>")
        sys.exit(1)
    try:
        true_count = int(sys.argv[1])
        epsilon = float(sys.argv[2])
    except ValueError:
        print("Error: true_count must be int, epsilon must be float")
        sys.exit(1)

    noisy_count = apply_differential_privacy(true_count, epsilon)
    print(f"Differentially private count: {noisy_count}")

if __name__ == "__main__":
    main()

