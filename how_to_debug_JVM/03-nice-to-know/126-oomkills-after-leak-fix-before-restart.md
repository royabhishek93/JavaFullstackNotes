# #126 — Service OOMKills After Memory Leak Fix But Before Restart

> **Category:** JVM Tuning Production Playbook | **Type:** Scenario Q&A | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"We found a memory leak, the fix is ready, but deployment is in 2 hours due to change freeze. The pod will OOMKill before then. What do you do operationally?"

## 😊 Explain It Simply (for anyone)
Picture a boat with a slow leak (the memory leak) — you've already patched the hole in the workshop (the fix is coded and ready), but company policy says you can't put the boat back in the water for two more hours (the change freeze), and it's currently sinking. Your job right now isn't to fix the leak again — it's already fixed — your job is to keep the boat afloat for two hours using whatever temporary bailing buckets you have (bigger memory limits, manual restarts on your own schedule, temporarily reducing load). The golden rule: none of these buckets are the actual fix, and you should never let "just keep bailing" become the permanent plan once the boat is finally allowed back in dry dock.

## 📊 Visualize It
```
 Leak detected      Fix ready       Deploy window (2h away)
      │                 │                    │
      ▼                 ▼                    ▼
 ──────────────────────────────────────────────────► time
      Memory grows steadily, pod nears OOMKill threshold
      Options: ↑ pod memory limit | manual restart | heap dump first
```

## 🏭 The Real Production Answer (15-YOE Level)
> "This is an incident response question as much as a JVM question. Options in order:
>
> 1. Increase pod memory limit temporarily (if you have access):
>    kubectl set resources deployment/myservice --limits=memory=4Gi
>    Buys time, doesn't fix root cause. Document why.
>
> 2. Increase JVM heap headroom if Max < Limit:
>    Check: if limits.memory=4Gi but -Xmx=2g, bump -Xmx=3g via env var, rolling restart
>    This is already a restart, but it's your restart on your schedule, not K8s killing pods randomly
>
> 3. Implement a manual JVM heap dump before it dies:
>    jcmd <pid> GC.heap_dump /dumps/pre-oom.hprof
>    Gives you evidence even if pod dies before the fix
>
> 4. Reduce pod replica count during the window to reduce memory pressure on the cluster overall
>
> 5. If it's a scheduled leak accumulation, trigger a rolling restart just before the OOMKill threshold:
>    A cron job that does a rolling restart every hour is an engineering smell, but it's better than
>    random OOMKills affecting users. Make it explicit that this is a temporary measure.
>
> The answer to 'restart fixes memory issues' is: NO. Restart buys time. Fix eliminates the problem.
> Never let operational workarounds become the permanent solution."

## 🔑 Key Takeaway
When a fix is ready but blocked by process, buy time deliberately and visibly (limit bump, controlled restart) — never let a stopgap silently become the permanent fix.
