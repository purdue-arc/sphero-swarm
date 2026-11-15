import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

df = pd.read_csv("distance_mapping/distance_mapping_test_data/test_01.csv")

durations = np.array(df['durations'])
distances = np.array(df['distances'])


coeffs = np.polyfit(durations, distances, 4)
inverse_coeffs = np.polyfit(distances, durations, 4)
print(coeffs)
print(inverse_coeffs)

poly_func = np.poly1d(coeffs)

# Create a smooth line of 200 x-values so the curve isn't jagged
x_smooth = np.linspace(durations.min(), durations.max(), 200)
y_smooth = poly_func(x_smooth)

# Plot the original points and the fitted curve
plt.figure(figsize=(8, 5))
plt.scatter(durations, distances, color="black", alpha=0.7, label="Actual Data")
plt.plot(
    x_smooth, y_smooth, color="royalblue", linewidth=2, label="Degree-4 Fit"
)

plt.title("Distance vs. Duration (Degree-4 Polynomial Fit)")
plt.xlabel("Duration")
plt.ylabel("Distance")
plt.legend()
plt.grid(True, linestyle="--", alpha=0.5)
plt.show()