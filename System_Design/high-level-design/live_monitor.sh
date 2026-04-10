#!/bin/bash
clear
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   HLD Document Creation - Live Monitoring            ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

while true; do
    total=$(ls -1 *-hld.md 2>/dev/null | wc -l | tr -d ' ')
    target=33
    percentage=$((total * 100 / target))
    remaining=$((target - total))
    
    # Clear previous line
    tput cuu 4
    tput el
    
    echo "📊 Progress: $total / $target files ($percentage% complete)"
    
    # Progress bar
    filled=$((percentage / 3))
    empty=$((33 - filled))
    printf "   ["
    for i in $(seq 1 $filled 2>/dev/null); do printf "█"; done
    for i in $(seq 1 $empty 2>/dev/null); do printf "░"; done
    printf "] $percentage%%\n"
    
    echo "   Remaining: $remaining files"
    echo ""
    
    if [ $total -ge $target ]; then
        echo "✅ ALL 33 HLD DOCUMENTS COMPLETE!"
        break
    fi
    
    sleep 10
done
