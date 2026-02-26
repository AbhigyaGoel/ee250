# Lab 5: Wireless Measurements

## Team Members

- Abhigya Goel (USC ID: 7248905335)

## Lab Question Answers

### Part 1: Signal Measurements

**Question 1:** What is dBm? What values are considered good and bad for WiFi signal strength?

dBm stands for decibel-milliwatts and is a logarithmic unit that expresses power relative to one milliwatt. Since WiFi signals are very low power, dBm values are always negative. A reading between -30 and -50 dBm represents an excellent connection, -50 to -67 dBm is adequate for most tasks, and anything weaker than -70 dBm will cause noticeable performance issues. Below -80 dBm the connection becomes essentially unusable.

**Question 2:** Why do we need to check the OS? What is the difference between the commands for each OS?

Each operating system exposes wireless adapter information through its own system utilities. Linux uses iwconfig, which reports RSSI directly in dBm. Windows uses netsh wlan show interfaces, which reports signal as a 0–100% quality score. macOS uses wdutil info, which provides RSSI in dBm. Because these tools have completely different output formats, the parsing logic must be tailored to each OS.

**Question 3:** In your own words, what is subprocess.check_output doing? What does it return?

subprocess.check_output spawns a child process that executes the given shell command and captures everything it writes to stdout. It waits for the command to finish and then returns that captured output as a bytes object. If the command exits with a non-zero return code, it raises a CalledProcessError so the caller knows something went wrong.

**Question 4:** In your own words, what is re.search doing? What does it return?

re.search scans through a string looking for the first position where a given regular expression pattern produces a match. If it finds one, it returns a Match object that lets you pull out specific captured groups (like the numeric signal value). If no match exists anywhere in the string, it returns None.

**Question 5:** In the Windows case, why do we need to convert the signal quality to dBm?

Windows reports WiFi signal as a percentage (0–100%) representing perceived quality, while Linux and macOS give raw power readings in dBm. To keep measurements consistent and comparable across platforms, we convert the Windows percentage to an approximate dBm value using the formula dBm = -100 + (quality/ 2). This mapping comes from how the Windows WLAN API internally derives the quality percentage from the actual RSSI.

**Question 6:** What is the standard deviation? Why is it useful to calculate it?

Standard deviation quantifies how spread out a set of measurements are from their average. A small standard deviation means the signal readings were tightly clustered and consistent, while a large one indicates the signal was fluctuating a lot during sampling. This matters because two locations could have the same average signal strength but very different reliability — standard deviation captures that distinction.

**Question 7:** What is a dataframe? Why is it useful to use a dataframe to store the data?

A Pandas DataFrame is a tabular data structure with labeled rows and columns, similar to a spreadsheet. It makes it easy to organize our measurements (location, mean, std dev) in a structured way, perform vectorized calculations across columns, and feed data directly into visualization libraries like Plotly without manual data wrangling.

**Question 8:** Why is it important to plot the error bars? What do they tell us?

Error bars show the range of variability in our measurements at each location. Without them, a bar chart only shows the average, which can be misleading. If one location has tight error bars, we can trust that average as representative. If another has wide error bars, the signal there is unstable, and the average alone doesn't tell the full story.

**Question 9:** What did you observe from the plot? How does the signal strength change as you move between locations? Why do you think signal strength is weaker in certain locations?

The dorm room had the strongest signal at about -39.4 dBm, which makes sense since the WiFi access point is mounted in the hallway right outside. The common room was next at -48.3 dBm, just down the hall. The hallway itself measured -53.8 dBm, likely due to interference from multiple APs overlapping. The stairwell was weaker at -63.2 dBm because of the concrete walls and metal fire doors, and the laundry room in the basement was weakest at -68.2 dBm, separated by a floor and heavy walls. Error bars were relatively tight across locations, indicating stable readings at each spot.

---

### Part 2: Network Performance

**Question 10:** How does distance affect TCP and UDP throughput?

As the Raspberry Pi moves farther from the router, the wireless signal degrades, which reduces the achievable data rate for both protocols. TCP reacts by throttling its sending rate and retransmitting dropped packets, so throughput declines gradually. UDP maintains its target sending rate regardless of conditions, so while the sender throughput stays relatively flat at shorter distances, the actual successfully-received throughput drops once the link quality can no longer support the rate, and packets simply get lost.

**Question 11:** At what distance does significant packet loss occur for UDP?

Significant packet loss started around 7 meters, where average loss reached approximately 1.2%. At 8 meters, it climbed to about 1.8%. At shorter distances (2m and 4m), loss was negligible (under 0.1%), and at 6m it was still under 0.5%. This aligns with the expected behavior of WiFi signal degradation over distance.

**Question 12:** Why does UDP experience more packet loss than TCP?

TCP has built-in reliability mechanisms: it tracks every segment with sequence numbers, waits for acknowledgments, and retransmits anything that doesn't get confirmed. So even when the wireless link drops packets, TCP recovers them. UDP provides no such guarantees — it fires packets and moves on. When the signal weakens and the physical layer starts corrupting or dropping frames, those UDP packets are gone permanently with no recovery mechanism.

**Question 13:** What happens if we increase the UDP bandwidth (-b 100M)?

Pushing the target rate to 100 Mbps forces the sender to inject far more data than the wireless link can realistically carry. The network buffers on the router and receiver fill up and start dropping the excess. The result is extremely high packet loss because the physical channel capacity is the bottleneck, and UDP has no congestion control to back off. Actual received throughput won't increase proportionally — it will plateau at whatever the link can handle, with the rest lost.

**Question 14:** Would performance be different on 5 GHz Wi-Fi vs. 2.4 GHz?

Yes. 5 GHz provides wider channels and higher maximum throughput at close range, so TCP and UDP would both achieve better speeds near the router. The tradeoff is that 5 GHz signals attenuate faster through walls and over distance, so performance would degrade more rapidly as the RPi moves away. 2.4 GHz has better range and wall penetration, so it would maintain usable throughput at greater distances, but with a lower peak speed. The choice depends on whether range or speed matters more for the use case.
