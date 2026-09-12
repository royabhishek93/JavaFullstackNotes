# Senior Trap — "IIFEs Are Obsolete — ES Modules Solve Everything They Solve"
> **Topic:** IIFE | **Level:** Senior Trap | **Frequency:** High

## The Setup

A candidate dismisses a legacy codebase's IIFE patterns during a system design discussion: "IIFEs are dead. We have ES modules now — they solve all of this. Any new code using IIFEs is doing it wrong."

## The Question

How complete is this statement? In what real-world scenarios are IIFEs still the right tool, and what does confidently dismissing them reveal about the candidate's production experience?

## Model Answer (15 YOE)

ES modules do replace IIFEs for new code in controlled environments, but "obsolete" overstates the case significantly.

IIFEs are still the right output format when you need a script that runs in a browser without a module loader, works on Node.js CommonJS without a build step, and makes no assumptions about the host environment. Every major analytics SDK, most A/B testing libraries, and virtually all vendor scripts loaded via tag managers still ship as IIFEs or UMD wrappers because their operators cannot control how customers load them. You do not get to tell Google Tag Manager or a third-party payment processor to add `type="module"` to their script tags.

Async IIFEs remain the pragmatic solution for top-level `await` in CommonJS Node.js environments, which represent a significant portion of production infrastructure at most enterprise companies. Many production systems have `package.json` without `"type": "module"` and will not be migrated on any near-term roadmap.

Understanding IIFEs is not optional for any engineer who reads build output, audits third-party scripts, or maintains code older than five years. Every Webpack bundle you open in an incident contains an IIFE. Every minified SDK you audit starts with an IIFE. Saying "we don't write them anymore" is technically true for new code; treating that as a reason to stop understanding them is a gap that shows up in exactly the wrong moments — production incidents at 2 AM reading minified output without source maps.

## Why It's a Trap

Sounds like a principled position about modern practices, but it is a surface-level answer that signals the candidate has never audited third-party scripts or maintained pre-2015 code in production.

## What NOT to Say

"Yeah, I never write IIFEs anymore — we use ES modules." Technically true for their own code, but reveals they have never read a Webpack bundle or audited a payment SDK in production.

## Follow-up

**Q:** Your team is migrating a library from IIFE/UMD to ES modules. How do you manage the transition for downstream consumers who may still be using the script-tag version?

**A:** Ship both simultaneously during a deprecation window. Maintain the IIFE/UMD build for existing consumers — breaking their integration is not acceptable. Add the ESM build as the new primary, pointed to by the `"module"` field in `package.json` (which bundlers like Webpack and Rollup understand). Announce a deprecation timeline, update documentation, and monitor download stats on the old format. Hard cutover only after the old build's download curve has flattened. This is exactly what Lodash, date-fns, and most major OSS libraries did through the 2018–2022 period.
