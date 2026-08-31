# When would you NOT use React?

> **Interview priority:** GOOD TO KNOW

## Question

When would you NOT use React?

## Beginner Lens

Before memorizing the interview answer, follow the scenario and notice three things: the problem React is solving, the state or browser work that changes, and the rule that keeps the UI correct. Read the code blocks slowly and predict the next result before reading the explanation.

## Detailed Explanation

**WEAK answer:** *"React is great for everything, I'd always use it."*

**STRONG answer (what to say):**

> "This is a question I genuinely think about at the start of a project.
> React is the right default for most web apps, but not all. Here are the
> cases where I'd reach for something else:
>
> A pure content/marketing site — Astro. Zero JavaScript by default,
> ships HTML, great Core Web Vitals out of the box. I've seen teams
> spend weeks optimizing a React marketing site's LCP that would have
> been fast by default in Astro.
>
> A real-time collaborative tool — Figma-style — where hundreds of updates
> per second come through WebSockets. React's virtual DOM diffing adds
> overhead on every update. SolidJS with fine-grained reactivity would
> be better there — updates bypass the virtual DOM entirely.
>
> A small embeddable widget that gets dropped into non-React host pages —
> Web Components. No framework coupling, works in Angular, Vue, plain HTML.
>
> React is still my default for dashboards, SPAs, server-rendered apps,
> e-commerce, anything with complex interactive UI."

---
