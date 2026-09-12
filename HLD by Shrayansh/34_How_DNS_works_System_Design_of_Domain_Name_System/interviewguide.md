# Interview Guide: How DNS Works

## 🗣️ The Interview Scenario

> "When I type `www.concept-and-coding.com` into my browser and hit enter, walk me through — in full technical detail — every single step that happens before the page starts loading. Don't skip the parts about caching, root servers, or how your ISP even knows where to send the request."

This is one of the most classic "explain it from first principles" HLD questions. It's deceptively simple-sounding but separates candidates who've memorized "DNS translates domain names to IPs" from those who can actually trace the full recursive resolution chain, explain record types, and reason about scaling authoritative servers via zones.

## 🏗️ Architect's Explanation (For a New Developer)

Every device on the internet has a unique numerical address — an **IP address** (like `172.32.4.8`) — similar to how every house has a unique street address. But nobody wants to memorize numbers to visit their favorite website, so we invented **domain names** (like `google.com`) — human-friendly, readable names.

**DNS (Domain Name System)** is the **mediator/phonebook** that translates domain names into IP addresses, because the internet's actual routing machinery only understands IP addresses — nothing understands "google.com" directly.

The clever part isn't the concept — it's *how* that translation actually happens without a single giant global database holding every domain name in the world. Instead, DNS is a **hierarchical, distributed system**, where different organizations each manage one small piece of the puzzle, and your query gets progressively routed to whichever organization holds the answer for the piece you're asking about.

## 📊 Visualize It

**Domain name hierarchy (read right to left):**

```
        www  .  concept-and-coding  .  com  .  (implicit trailing dot = root)
         |            |                |              |
     Subdomain    Second-Level      Top-Level        Root
                  Domain (SLD)      Domain (TLD)
     
     Full chain (subdomain -> root) = FQDN (Fully Qualified Domain Name)
     "concept-and-coding.com" alone = the Domain Name
```

**Recursive DNS resolution — the full journey:**

```
Browser/OS (Stub Resolver)
   | 1. Check local cache -> MISS
   v
DNS Resolver (from ISP, or custom e.g. 8.8.8.8)
   | 2. Check its own cache -> MISS
   |
   | 3. Ask a ROOT server (one of 13: A-M, e.g. run by Verisign/NASA/etc.)
   v
ROOT server: "I don't have the IP, but here's the .com TLD server"
   |
   | 4. Ask the .com TLD server
   v
TLD server: "I don't have the IP, but concept-and-coding.com's
             authoritative server is at GoDaddy: ns3/ns4.domaincontrol.com"
   |
   | 5. Ask the Authoritative Name Server (GoDaddy)
   v
Authoritative server: "Here's the actual A record IP address!"
   |
   v
DNS Resolver caches the answer, returns it to the Stub Resolver
   |
   v
Browser now has the IP -> makes the actual HTTP(S) connection
```
*(This whole chain = ONE request/response from the client's perspective — but the DNS Resolver made several recursive hops on the client's behalf. That's why it's called the "recursive" approach.)*

**Iterative approach (for comparison — client does the hopping itself):**

```
DNS Client -> Resolver: "no cache? give me SOMETHING"
Resolver -> Client: "Here's the root server's IP, YOU ask it"
Client -> Root: "What's the IP for concept-and-coding.com?"
Root -> Client: "Here's the .com TLD server, YOU ask it"
Client -> TLD: "..."
TLD -> Client: "Here's the authoritative server, YOU ask it"
Client -> Authoritative server -> gets final IP directly
```

## 🔧 Deep Dive: How It Actually Works

### Foundational Definitions

- **IP address** — a unique numerical label assigned to each device connected to the internet (IPv4/IPv6), used for locating devices.
- **Domain name** — a human-readable, friendly name used to identify a device on the internet.
- **DNS** — the system that translates domain names into IP addresses, since the internet's routing infrastructure only understands IP addresses.

### The Domain Name Hierarchy

Reading `www.concept-and-coding.com.` (note the implicit trailing dot) from right to left:
- **Root** — the topmost level (the trailing dot, often invisible in everyday typing).
- **TLD (Top-Level Domain)** — e.g., `.com`.
- **SLD (Second-Level Domain)** — e.g., `concept-and-coding`.
- **Subdomain** — e.g., `www` (you can have many: `mail.`, `blog.`, `admin.`, `cdn.image.media.`, etc. — there's no fixed limit on subdomain depth).
- **Domain Name** — the SLD + TLD combined (e.g., `concept-and-coding.com`).
- **FQDN (Fully Qualified Domain Name)** — the complete chain from subdomain all the way to root.

### Key DNS Record Types

Each DNS record has (among other fields) a **record name**, a **type**, and associated data:

- **A Record (Address Record)** — type `1`. Maps a record name directly to an **IP address**. This is where the actual IP lives.
- **CNAME Record (Canonical Name)** — type `5`. Used to create an **alias**, mapping one domain/subdomain to another domain name (not directly to an IP). Example: `www.google.com` → CNAME → `google.com`, and `blog.google.com` → CNAME → `google.com` — both ultimately resolve through `google.com`'s own A record. CNAME is typically only used at the **subdomain level** (you wouldn't alias one entirely different top-level domain to another).
- Resolving a CNAME may require an **additional lookup**: the resolver sees "this is a CNAME pointing to X," then has to separately query for X's actual A record to get the real IP — CNAME chains can even be multiple hops long.
- **NS Records (Name Server / Authoritative records)** — identify which servers are authoritative for a given (sub)domain.

### Step-by-Step: The Recursive Resolution Process

1. **Stub Resolver (OS-level DNS client) checks its local cache.** Every OS maintains a local DNS cache (you can inspect it via `ipconfig /displaydns` on Windows). Cache hit → done immediately. Cache miss → proceed.

2. **Query the DNS Resolver.** Your system knows the resolver's address from your network configuration (check Wi-Fi/Ethernet settings) — by default this is provided by your **ISP**. You can override it with a public resolver like **Google's public DNS (`8.8.8.8`)**.

3. **DNS Resolver checks its own cache.** Every server in this chain independently maintains its own cache — cache hit anywhere short-circuits the remaining steps.

4. **DNS Resolver queries a Root Server.** There are exactly **13 root servers worldwide, labeled A through M**, each operated by a different organization (e.g., root server **A** is operated by Verisign; root server **E** by NASA; root server **G** by the US Department of Defense, etc.). The resolver picks whichever root server is geographically/network nearest.

5. **Root Server responds with the relevant TLD's address.** The root server doesn't know the final IP, but it knows which **TLD** (there are 1000+ TLDs today, and growing — `.com`, `.in`, `.edu`, `.io`, etc.) is responsible for resolving domains under that suffix, and returns that TLD server's address.

6. **DNS Resolver queries the TLD server.** The TLD server (e.g., the `.com` TLD registry, operated by Verisign) checks its own cache; if not cached, it consults its own records, which map each registered domain to its **authoritative name servers (NS records)**.

7. **How does the TLD know which authoritative server to point to?** When a domain (e.g., `concept-and-coding.com`) is purchased through a **registrar** (e.g., GoDaddy), that registrar communicates with the relevant **TLD registry** (e.g., Verisign for `.com`) to register which authoritative name servers should handle queries for that domain. This is why the TLD registry knows to point queries for `concept-and-coding.com` to GoDaddy's name servers (e.g., `ns3.domaincontrol.com`, `ns4.domaincontrol.com`).

8. **TLD server responds with the authoritative name server addresses**, often including **two** (a primary and a secondary, per an SOA/NS record convention) — "use the primary; if no answer, query the secondary."

9. **DNS Resolver queries the Authoritative Name Server** (e.g., GoDaddy's `ns3.domaincontrol.com`). This server holds the actual DNS records (A records, CNAME records, etc.) for the domain and returns the final resolved IP address.

10. **DNS Resolver returns the final answer to the Stub Resolver / client.**

**Why it's called "recursive":** from the client's perspective, it made just **one** request and got **one** answer — but the DNS Resolver internally performed multiple recursive queries (root → TLD → authoritative) on the client's behalf.

### The Iterative Approach (Contrast)

In the **iterative** model, the **DNS client itself** does the hopping (rather than delegating that work to the resolver):
1. Client checks local cache.
2. If miss, client asks the DNS resolver, which — if it also has no cached answer — responds with just the **root server's IP address** rather than doing the lookup itself.
3. Client then directly queries the root server, gets redirected to the TLD server, and directly queries that.
4. Client then directly queries the authoritative server to get the final IP.

**Key distinction:** in recursive resolution, the **resolver** takes on the responsibility of chasing down the full answer; in iterative resolution, the **client** is responsible for making each subsequent hop itself.

### DNS Zones: Why Authoritative Servers Get Split Up

**The problem:** a single authoritative server for `concept-and-coding.com` would need to hold records for **every** subdomain under it — `mail.`, `blog.`, `admin.`, `a.b.c.`, `system-design.resource.` — with no limit on how many subdomains can exist. Two issues arise:
1. **Record management burden** — one server maintaining potentially unlimited subdomain records.
2. **Traffic imbalance** — if one subdomain (e.g., `mail.concept-and-coding.com`) receives disproportionately heavy traffic, that single authoritative server becomes overloaded, even though other subdomains (e.g., `admin.concept-and-coding.com`) get comparatively little traffic.

**The solution: DNS Zones.** An authoritative server can **delegate** responsibility for specific subdomains to a *different* authoritative server, effectively creating a separate "zone." For example: the primary authoritative server (`ns3...`) keeps handling `concept-and-coding.com`, `blog.concept-and-coding.com`, `a.b.concept-and-coding.com`, etc., but delegates `mail.concept-and-coding.com` entirely to a different authoritative server (e.g., `ns5...`), which now owns that zone and handles all lookups/records for it (and anything further nested under it).

This is the exact same load-distribution principle used one level up between TLD and second-level domains — just applied recursively at the subdomain level, letting organizations **scale out** DNS management and traffic handling for their busiest subdomains independently.

## 🔥 Real Production Incident & Fix

**What broke:** A growing SaaS company hosted all of its subdomains (`www.`, `api.`, `mail.`, `cdn.`) under a single authoritative DNS zone managed by one pair of name servers. When their `api.` subdomain went viral due to a partner integration surge, DNS query volume for that one subdomain spiked massively — and because *all* subdomains shared the same authoritative name servers, resolution for the completely unrelated `www.` marketing site and `mail.` subdomain started timing out too.

**How it was detected:** Monitoring showed elevated DNS query latency and occasional `SERVFAIL` responses reported by an external DNS health-check service (e.g., Pingdom/UptimeRobot-style monitors), correlated with authoritative name server CPU/query-rate metrics showing the shared servers were saturated almost entirely by `api.` subdomain lookups, based on query-log analysis at the DNS provider.

**Root cause:** All subdomains — regardless of traffic pattern — were served by the exact same pair of authoritative name servers with no zone delegation. A traffic spike on one subdomain became a shared-infrastructure problem for every other subdomain, because there was no isolation between them at the DNS layer.

**The fix:**
1. Delegated the `api.` subdomain into its **own DNS zone**, served by a dedicated pair of authoritative name servers (following the same delegation pattern by which TLDs point to authoritative servers, applied recursively one level down).
2. Kept `www.` and `mail.` on the original authoritative servers, now insulated from `api.`'s traffic spikes.
3. Lowered the **TTL (time-to-live)** on the `api.` zone's records temporarily during high-traffic events to allow faster DNS-level failover/rebalancing if needed, while keeping longer TTLs on stable, low-churn subdomains to maximize caching efficiency and reduce unnecessary query load.

```
BEFORE:                                    AFTER:
ONE authoritative server pair serves       api. subdomain delegated to its OWN
www. + api. + mail. + everything else      dedicated authoritative server pair (its own zone)
        |                                          |
api. traffic spike overloads shared         www. + mail. remain on original servers,
server -> www. and mail. lookups fail too   fully insulated from api.'s traffic spikes
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why are there exactly 13 root servers, and is that really enough for the entire internet?**
The number 13 comes from a historical limitation of the original DNS protocol's response packet size over UDP, but in practice each of those 13 "root servers" is actually a **label** (A through M) served by a globally distributed anycast network of many physical servers worldwide, not 13 single machines — so the effective capacity and redundancy is far greater than the count of 13 suggests.

**Q2: What's the practical difference between a CNAME record and an A record, and why can't you CNAME your root/apex domain in most setups?**
An A record maps a name directly to an IP address, while a CNAME maps a name to *another domain name* which must then itself be resolved (potentially requiring an extra lookup); many DNS providers disallow CNAME at the root/apex domain (e.g., `concept-and-coding.com` itself, as opposed to a subdomain) because the apex must also typically coexist with other record types (like NS or MX records) at that same name, which conflicts with the CNAME's requirement of being the *only* record type present for that name.

**Q3: Why does DNS caching matter so much for performance, and where does caching happen along the resolution chain?**
Caching happens at every layer — the OS-level stub resolver, the ISP/public DNS resolver, and even the root/TLD/authoritative servers themselves — so that repeated queries for the same popular domain don't have to redo the full multi-hop resolution chain every time; each cached record respects a TTL (time-to-live) that determines how long it can be reused before a fresh lookup is required.

**Q4: How does a domain registrar like GoDaddy actually get a domain's authoritative name servers into the TLD's records?**
When you register a domain through a registrar, the registrar communicates with the relevant TLD registry (e.g., Verisign for `.com`) to publish which authoritative name servers should be associated with that domain; this is why changing your domain's name servers (e.g., pointing to a different DNS host) is done through your registrar's control panel, which then propagates that update to the TLD registry.

**Q5: What would happen if a domain's authoritative name servers went completely offline?**
Any DNS resolver that doesn't already have a cached (non-expired) answer would fail to resolve that domain entirely, since the TLD only points to those specific authoritative servers and has no fallback data of its own — this is why authoritative DNS is typically deployed with multiple redundant servers (primary/secondary) and often across geographically distributed anycast infrastructure to minimize this single point of failure.

**Q6: Recursive vs. iterative — which one does your home router/laptop actually use, and why?**
Client devices (laptops, phones) almost universally use the **recursive** model, delegating the entire multi-hop lookup burden to a DNS resolver (typically provided by the ISP or a public resolver like `8.8.8.8`), because doing the iterative hopping themselves would require every single device to implement and maintain the full root→TLD→authoritative query logic, whereas centralizing that logic (and its caching benefits) in a shared resolver is far more efficient at scale.

## 🔑 Key Takeaway

DNS resolution isn't a single lookup — it's a **hierarchical, cached, delegated chain** (root → TLD → authoritative server, via zones) that lets no single organization or server hold the entire internet's domain data, and understanding *why* zones and caching exist (to distribute both administrative burden and traffic load) is what separates a surface-level answer from a truly system-design-grade explanation of "how DNS works."
