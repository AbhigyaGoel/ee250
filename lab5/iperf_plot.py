import matplotlib
matplotlib.use("Agg")

import pandas as pd
import matplotlib.pyplot as plt
import sys

# Get distance from command line
distance = sys.argv[1]

# Read CSV files and take the last row (most recent run)
tcp_data = pd.read_csv(f"iperf_tcp_{distance}m.csv").tail(1)
udp_data = pd.read_csv(f"iperf_udp_{distance}m.csv").tail(1)

# Define run labels
runs = ["Run1", "Run2", "Run3", "Run4", "Run5"]

# Extract throughput values
tcp_throughput = tcp_data[runs].values[0]
udp_throughput = udp_data[runs].values[0]

# Create the plot
plt.figure(figsize=(8, 5))

plt.plot(runs, tcp_throughput, marker='o', linestyle='-', color='orange',
         linewidth=2, label="TCP Throughput (Mbps)")
plt.plot(runs, udp_throughput, marker='s', linestyle='--', color='coral',
         linewidth=2, label="UDP Throughput (Mbps)")

plt.title(f"TCP & UDP Throughput at {distance}m Distance")
plt.xlabel("Test Runs")
plt.ylabel("Throughput (Mbps)")
plt.ylim(bottom=0)
plt.legend()
plt.grid(True, linestyle=':', alpha=0.6)

plt.savefig(f"throughput_{distance}m.png")
print(f"Saved throughput_{distance}m.png")
plt.close()
