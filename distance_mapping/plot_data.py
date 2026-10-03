import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

df = pd.read_csv("distance_mapping/distance_mapping.csv")

durations = np.array(df['durations'])
distances = np.array(df['distances'])
dtdx = (durations / distances).mean()
print(dtdx)

plt.plot(durations, distances)
plt.plot(distances*dtdx, distances, color="green")
plt.plot(durations, durations/dtdx, color="red")
plt.xlabel("duration")
plt.ylabel("distance (in)")
plt.show()