#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: ./iperf_logger.sh <distance_in_meters>"
    exit 1
fi

DISTANCE=$1
LAPTOP_IP="172.20.10.2"

TCP_LOGFILE="iperf_tcp_${DISTANCE}m.csv"
UDP_LOGFILE="iperf_udp_${DISTANCE}m.csv"

# Convert iperf bitrate (value + unit) to Mbps (numeric)
to_mbps() {
    local v="$1"
    local u="$2"
    awk -v v="$v" -v u="$u" 'BEGIN{
        if(u=="bits/sec")      m=v/1000000;
        else if(u=="Kbits/sec") m=v/1000;
        else if(u=="Mbits/sec") m=v;
        else if(u=="Gbits/sec") m=v*1000;
        else if(u=="Tbits/sec") m=v*1000000;
        else                    m=v;
        printf "%.6f", m;
    }'
}

# Extract sender bitrate as Mbps (numeric) from iperf3 output
extract_sender_mbps() {
    local out="$1"
    local line
    line=$(echo "$out" | grep "sender" | grep "bits/sec" | tail -n 1)
    if [[ -z "$line" ]]; then
        echo "0"
        return
    fi

    local val unit
    val=$(echo "$line" | awk '{for(i=1;i<=NF;i++) if($i ~ /bits\/sec$/){print $(i-1); exit}}')
    unit=$(echo "$line" | awk '{for(i=1;i<=NF;i++) if($i ~ /bits\/sec$/){print $i; exit}}')

    if [[ -z "$val" || -z "$unit" ]]; then
        echo "0"
        return
    fi

    to_mbps "$val" "$unit"
}

# Extract packet loss percent (numeric) from UDP sender line
extract_loss_pct() {
    local out="$1"
    local line
    line=$(echo "$out" | grep "sender" | tail -n 1)
    if [[ -z "$line" ]]; then
        echo "100"
        return
    fi

    echo "$line" | awk '{
        for(i=1;i<=NF;i++){
            if($i ~ /^\([0-9.]+%\)$/){
                gsub(/[()%]/,"",$i);
                print $i;
                exit
            }
        }
    }'
}

# Write CSV headers (if files don't exist)
if [ ! -f "$TCP_LOGFILE" ]; then
    echo "Distance,Run1,Run2,Run3,Run4,Run5,Avg" > "$TCP_LOGFILE"
fi

if [ ! -f "$UDP_LOGFILE" ]; then
    echo "Distance,Run1,Run2,Run3,Run4,Run5,Avg,PacketLoss1,PacketLoss2,PacketLoss3,PacketLoss4,PacketLoss5,Avg_PacketLoss" > "$UDP_LOGFILE"
fi

echo "============================================="
echo " Running iPerf tests at $DISTANCE meters..."
echo "============================================="

echo "---------------------------------------------"
echo "Starting TCP Tests..."
echo "---------------------------------------------"

TCP_RESULTS=()

for i in {1..5}; do
    echo "TCP Run $i..."

    tcp_output=$(iperf3 -c "$LAPTOP_IP" -t 10 2>/dev/null)
    tcp_result=$(extract_sender_mbps "$tcp_output")

    if [[ -z "$tcp_result" ]]; then
        echo "Error: iPerf3 failed. Logging 0."
        tcp_result="0"
    fi

    echo "TCP Sender Throughput (Run $i): $tcp_result Mbps"
    TCP_RESULTS+=("$tcp_result")
    sleep 1
done

TCP_AVG=$(echo "${TCP_RESULTS[@]}" | awk '{sum=0; for (i=1; i<=NF; i++) sum+=$i; print sum/NF}')

tcp_csv=$(IFS=','; echo "${TCP_RESULTS[*]}")
echo "$DISTANCE,$tcp_csv,$TCP_AVG" >> "$TCP_LOGFILE"

echo "---------------------------------------------"
echo "TCP Tests Completed"
echo "TCP Results (Mbps): ${TCP_RESULTS[@]}"
echo "TCP Average: $TCP_AVG Mbps"
echo "Results logged in $TCP_LOGFILE"
echo "---------------------------------------------"

sleep 2

echo "Starting UDP Tests..."
echo "---------------------------------------------"

UDP_RESULTS=()
PACKET_LOSS=()

for i in {1..5}; do
    echo "UDP Run $i..."

    udp_output=$(iperf3 -c "$LAPTOP_IP" -u -b 10M -t 10 2>/dev/null)
    udp_result=$(extract_sender_mbps "$udp_output")
    packet_loss=$(extract_loss_pct "$udp_output")

    if [[ -z "$udp_result" ]]; then
        echo "Error: iPerf3 failed. Logging 0 throughput and 100% loss."
        udp_result="0"
        packet_loss="100"
    fi

    echo "UDP Sender Throughput (Run $i): $udp_result Mbps"
    echo "UDP Packet Loss (Run $i): $packet_loss %"

    UDP_RESULTS+=("$udp_result")
    PACKET_LOSS+=("$packet_loss")
    sleep 1
done

UDP_AVG=$(echo "${UDP_RESULTS[@]}" | awk '{sum=0; for (i=1; i<=NF; i++) sum+=$i; print sum/NF}')
PKT_LOSS_AVG=$(echo "${PACKET_LOSS[@]}" | awk '{sum=0; for (i=1; i<=NF; i++) sum+=$i; print sum/NF}')

udp_csv=$(IFS=','; echo "${UDP_RESULTS[*]}")
loss_csv=$(IFS=','; echo "${PACKET_LOSS[*]}")
echo "$DISTANCE,$udp_csv,$UDP_AVG,$loss_csv,$PKT_LOSS_AVG" >> "$UDP_LOGFILE"

echo "---------------------------------------------"
echo "UDP Tests Completed"
echo "UDP Results (Mbps): ${UDP_RESULTS[@]}"
echo "UDP Average: $UDP_AVG Mbps"
echo "Packet Loss (%): ${PACKET_LOSS[@]}"
echo "Packet Loss Average: $PKT_LOSS_AVG %"
echo "Results logged in $UDP_LOGFILE"
echo "---------------------------------------------"

echo "Logging completed. Data saved in $TCP_LOGFILE and $UDP_LOGFILE."
