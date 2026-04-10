#!/bin/bash

echo "🚀 Monitoring HLD Document Creation Progress..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

while true; do
    clear
    echo "╔════════════════════════════════════════════════╗"
    echo "║   HLD Document Creation - Live Progress       ║"
    echo "╚════════════════════════════════════════════════╝"
    echo ""
    
    total=$(ls -1 *-hld.md 2>/dev/null | wc -l | tr -d ' ')
    target=33
    percentage=$((total * 100 / target))
    
    echo "📊 Progress: $total / $target files ($percentage%)"
    echo ""
    
    # Progress bar
    filled=$((percentage / 3))
    empty=$((33 - filled))
    printf "["
    for i in $(seq 1 $filled); do printf "█"; done
    for i in $(seq 1 $empty); do printf "░"; done
    printf "] $percentage%%\n"
    echo ""
    
    echo "📄 Recently Created Files:"
    ls -lht *-hld.md 2>/dev/null | head -5 | awk '{printf "   %-40s %s\n", $9, $5}'
    echo ""
    
    if [ $total -ge $target ]; then
        echo "✅ ALL DONE! $total HLD documents created!"
        break
    fi
    
    echo "⏳ Agent is working... (Press Ctrl+C to stop monitoring)"
    sleep 15
done
