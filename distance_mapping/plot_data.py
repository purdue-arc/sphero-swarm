import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

df = pd.read_csv("distance_mapping/distance_mapping_test_data/test_01.csv")

durations = np.array(df['durations'])
distances = np.array(df['distances'])

slope, intercept = np.polyfit(durations, distances, 1)
best_fit_distances = slope * durations + intercept
# dist = slope * duration + intercept
# (dist - intercept ) /slope
print(slope)
print(intercept)

plt.scatter(durations, distances, color="blue")
plt.title("Linear Regression of Sphero Distance Traveled vs. Duration")
plt.plot(durations, best_fit_distances, color="orange")
plt.xlabel("Duration (s)")
plt.ylabel("Distance (in)")
plt.show()