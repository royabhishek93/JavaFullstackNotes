# SimHash: Near-Duplicate Detection at Web Scale — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE

## HOOK (0:00–0:30)

Picture this. You're running a web crawler at Google scale. You've just pulled down **8 billion pages**. A huge chunk of them are near-identical — the same news article syndicated across 40 mirror sites, the same product page with a different sidebar, the same blog post with one banner ad swapped out.

So you do the "obvious" thing. You hash every page with SHA-256, and drop anything you've already seen. Ship it, right?

Wrong. Here's the number that should terrify you: change **one single character** — fix a typo, update a timestamp in the footer — and SHA-256 gives you a hash that shares **zero relationship** with the original. Not "slightly different." Completely, mathematically unrelated. You just built a duplicate detector that can't detect duplicates.

[Screen cue: Show a document with one character highlighted red, an arrow into a "SHA-256" box, and two wildly different-looking hash strings popping out in red, with a big "NO CORRELATION" stamp.]

## THE PROBLEM (0:30–2:00)

So why does this happen? It's not a bug — it's a *feature* of cryptographic hashes. They're built with something called the **avalanche effect**: flip one bit of input, and on average half the output bits flip. That's exactly what you want for integrity checks — you want a tampered file to look completely different. But it's exactly the opposite of what you want for similarity detection.

Think about what you actually need here. You don't want "identical or unrelated." You want a spectrum. You want a hash function where **similar documents produce similar-looking hashes**, so you can literally measure "how close are these two things" just by comparing two short fingerprints — without ever touching the original text again.

That idea has a name: **locality-sensitive hashing**, or LSH. And the most famous implementation of it — the one Google actually built and published — is called **SimHash**, invented by Moses Charikar.

[Screen cue: Draw two boxes labeled "Cryptographic Hash" and "Locality-Sensitive Hash." Under crypto hash: "similar in → totally different out." Under LSH: "similar in → similar out." Draw a spectrum bar under LSH going from 0% different to 100% different.]

## THE SOLUTION (2:00–5:00)

Here's how SimHash actually works, step by step.

**Step one: stop hashing the whole document.** Instead, break it into features — usually overlapping word sequences called shingles. "The cat sat" becomes shingles like "the cat sat," "cat sat on," "sat on the." Each shingle gets its own frequency-weighted score — how many times does it show up in the doc.

**Step two: hash each feature independently** into a fixed-width vector — in production, a 64-bit MurmurHash3 value per shingle.

**Step three — this is the clever part — weighted bit voting.** For every single one of the 64 bit positions, look across every feature's hash. If that feature's bit is a 1, it votes *positive* its weight. If it's a 0, it votes *negative* its weight. Sum all the votes at that bit position, across every feature in the whole document.

**Step four: sign becomes bit.** If the sum for a position is positive, the final fingerprint gets a 1 there. If it's negative or zero, it gets a 0. Do that for all 64 positions, and you've collapsed an entire document — could be 10,000 words — into one 64-bit number.

Why does this work? Because two documents sharing most of their features will have nearly identical vote totals at nearly every position — only the handful of differing features can flip a few bits. Two unrelated documents share almost no features, so their votes at each position are basically independent coin flips — on average, **half the 64 bits differ**. That's a Hamming distance around 32. Near-duplicates, by contrast, typically land at Hamming distance **0 to 3**.

Let's prove it with real numbers from the source material. Take "the cat sat on the mat" and swap one word: "the cat sat on the rug." One word changed out of six. Their fingerprints differ by **1 bit** out of 8 in the toy example — 12.5%. Now compare that to a totally unrelated sentence about quantum physics — it differs by **4 bits out of 8**, 50%, exactly what you'd expect from random chance. At production 64-bit width, that same ratio holds: near-dupes cluster at 0–5% bit difference, unrelated docs average 50%.

But here's the scaling problem: how do you check a new fingerprint against 8 billion existing ones without doing a linear scan? Google's answer, from their WWW 2007 paper: **table-splitting**, using the pigeonhole principle. Split the 64-bit fingerprint into 6 blocks. If two fingerprints differ by at most 3 bits total, then mathematically, **at least 3 of those 6 blocks must be bit-for-bit identical** — 3 differing bits simply can't poison more than 3 blocks. So Google builds around **20 to 24 sorted permutation tables**, each one designed so some specific combination of blocks sits at the front of the sort key. A query becomes: binary search each of the ~20 tables for matching leading blocks, union the tiny candidate lists — usually under 100 fingerprints — and only *then* compute exact Hamming distance. An 8-billion-row lookup becomes 20 binary searches plus a few hundred XOR-and-popcount operations. Single-digit milliseconds. Per page. Against the entire historical web.

[Screen cue: Live-draw the 64-bit fingerprint as a row of boxes, split into 6 colored blocks. Show two fingerprints stacked, differing bits highlighted in only 3 boxes, with the other 3 blocks glowing green as "identical — guaranteed match." Then draw 20 mini-tables branching off with a binary-search magnifying glass.]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

Now let's talk about where this bites people in production — because SimHash has two very real failure modes that the paper is upfront about.

**Trap number one: bag-of-words blindness.** If you use single words — unigrams — as your features, then "dog bites man" and "man bites dog" produce the *exact same set* of features: {dog, bites, man}. Same features means same fingerprint. Hamming distance **zero** — SimHash reports "certain duplicate" — even though the meaning is completely inverted. That's not a rare edge case; that's any sentence where word order carries the meaning. The fix: use **word-level shingles**, n-grams of 3 or more words, not single words. "dog bites man" becomes the single feature "dog bites man" — a completely different feature from "man bites dog" — and now the fingerprints diverge sharply.

**Trap number two: threshold ambiguity right at the cutoff.** Two *legitimately different* articles that both quote the same 200-word press release verbatim can land at Hamming distance 2 to 3 — a false positive, wrongly merged as duplicates. Meanwhile, two *legitimately near-identical* articles — same core content, but one has 200 extra words of navigation and ad boilerplate baked into the extracted text — can land at Hamming distance 6 to 8, a false negative, wrongly kept as distinct. The threshold isn't a hard wall; it's a fuzzy zone, and content near it will fool you in both directions.

The mitigation for both: **strip boilerplate before feature extraction** — nav bars, footers, ad slots — and never treat SimHash as a final verdict. Treat it as a **candidate generator**. Anything that lands near your threshold gets a cheap second check — like Jaccard similarity over the actual shingle sets — before you auto-merge or auto-reject anything.

And here's a subtlety a lot of engineers miss when picking between similarity techniques entirely: SimHash is *lexical* — it catches near-identical wording. It does **not** catch semantic similarity — two documents that say the same thing in completely different words will NOT get similar fingerprints. If you need "these mean the same thing," you need embeddings and an ANN index like HNSW, not SimHash. And if your corpus is small — a few thousand docs — don't even bother with SimHash's infrastructure; direct Jaccard or edit-distance comparison is simpler and more precise at that scale.

[Screen cue: Split-screen comparison. Left: "dog bites man" vs "man bites dog" with unigram feature sets highlighted identical, red "FALSE POSITIVE" stamp. Right: a Hamming-distance number line from 0 to 64, a shaded "danger zone" around 3, with two document icons landing inside it from opposite directions — one merging in wrongly, one staying out wrongly.]

## REAL WORLD (8:00–9:30)

The canonical real-world number here is Google's own paper: **8 billion** web page fingerprints, 64-bit width, similarity threshold Hamming distance ≤ 3, roughly **20 to 24 permutation tables**, memory footprint in the **hundreds of gigabytes**, sharded across many machines with tables held fully in RAM. That's the reference architecture everyone building this copies from.

Now bring it closer to home. Think about a company like **Flipkart**, running a product catalog with tens of millions of SKUs across thousands of third-party sellers. Two sellers list "iPhone 14 128GB Blue" with slightly different descriptions, different bullet formatting, a different warranty blurb pasted in. A SimHash-style fingerprint over the product description shingles, checked against roughly 50 million existing listings, catches that near-duplicate listing in single-digit milliseconds and flags it for catalog dedup — instead of showing the buyer ten near-identical listings with ten different prices.

Or picture **Zomato or Swiggy** running spam and review-abuse detection across tens of millions of restaurant reviews. Someone copy-pastes their glowing 5-star review across 200 different restaurant pages, changing only the restaurant name and one adjective each time. Exact-hash dedup misses every single one of those 200 copies. A SimHash fingerprint over 4-word shingles catches all 200 as near-duplicates of each other, at a scale of tens of thousands of new reviews landing per day, without ever running a full text-diff against the historical review corpus.

[Screen cue: Google logo with "8B pages / 64-bit / ≤3 Hamming / ~20 tables / 100s of GB RAM." Then Flipkart logo with "50M SKUs / few ms per check." Then Zomato/Swiggy logo with "10Ks of reviews/day / 200-copy spam pattern caught."]

## OUTRO + NEXT EPISODE (9:30–10:00)

So next time someone on your team says "just hash it and compare," ask them: exact duplicate, or near-duplicate? Because those are two completely different problems, and SimHash — feature shingling, weighted bit voting, Hamming distance, table-splitting for scale — is the tool built specifically for the second one.

If this kind of "how do real systems actually solve impossible-looking scale problems" content is useful to you, hit subscribe — there's a whole series like this.

Next episode, we're staying in the same neighborhood: **Bloom filters and HyperLogLog** — how you check "have I seen this before" and "how many unique things have I seen" across billions of items, using structures that are wrong on purpose to stay small. See you there.

[Screen cue: End card with video thumbnail for "Bloom Filter & HyperLogLog" and a subscribe button animation.]
