# How do you make a modal accessible with keyboard and screen readers?

> **Interview priority:** SHOULD KNOW

## Question

How do you make a modal accessible with keyboard and screen readers?

## Beginner Lens

Watch the focus: when a modal opens, keyboard users can still Tab to elements behind it (trapped outside modal), screen readers don't announce it's a dialog, and pressing Escape doesn't close it. Making it accessible means: trap focus inside modal, announce to screen readers, allow Escape to close, and restore focus when closed.

## Detailed Explanation

**HOW TO SAY IT (spoken to interviewer):**

> "Modals are one of the most common accessibility failures in React apps. The visible overlay tricks sighted users into thinking the page behind is inert, but keyboard and screen reader users can still interact with it. I've tested apps where you can't close the modal with keyboard, or Tab takes you to hidden elements. The WCAG standard requires focus management, ARIA roles, and keyboard controls. Let me show exactly what breaks..."

```
REAL APP: Confirmation Modal — Accessibility Bugs
─────────────────────────────────────────────────────────────────

INACCESSIBLE CODE:
────────────────────────────────────────────────────────────────

function Modal({ isOpen, onClose, children }) {
  if (!isOpen) return null;
  
  return (
    <div className="modal-overlay">  {/* ← NO ARIA */}
      <div className="modal-content">  {/* ← NO ROLE */}
        {children}
        <button onClick={onClose}>Close</button>
      </div>
    </div>
  );
}

// Usage
function App() {
  const [isOpen, setIsOpen] = useState(false);
  
  return (
    <div>
      <button onClick={() => setIsOpen(true)}>Delete Account</button>
      <input placeholder="Email" />
      <input placeholder="Password" />
      
      <Modal isOpen={isOpen} onClose={() => setIsOpen(false)}>
        <h2>Are you sure?</h2>
        <button onClick={handleDelete}>Confirm</button>
        <button onClick={() => setIsOpen(false)}>Cancel</button>
      </Modal>
    </div>
  );
}

ACCESSIBILITY BUGS:
─────────────────────────────────────────────────────────────────

1. NO FOCUS TRAP
   User opens modal → presses Tab
   ├─ Focus moves to "Confirm" button ✅
   ├─ Tab again → moves to "Cancel" button ✅
   ├─ Tab again → moves to "Close" button ✅
   ├─ Tab again → ESCAPES modal ❌
   └─ Now focused on hidden "Email" input behind overlay ❌
      User can type in hidden field (confusing)

2. NO SCREEN READER ANNOUNCEMENT
   Screen reader user clicks "Delete Account"
   ├─ Modal opens (visually)
   ├─ Screen reader says: "button clicked" (the trigger)
   ├─ Does NOT announce modal opened ❌
   ├─ Does NOT read modal heading ❌
   └─ User doesn't know a dialog appeared

3. NO ESCAPE KEY HANDLER
   User presses Escape → nothing happens ❌
   Expected: modal closes ✅

4. NO FOCUS MANAGEMENT
   Modal opens:
   ├─ Focus stays on "Delete Account" button (trigger) ❌
   └─ Should move to first element in modal ✅
   
   Modal closes:
   ├─ Focus lost (goes to <body>) ❌
   └─ Should return to trigger button ✅

5. NO ARIA LABELING
   Screen reader announces modal content as generic <div>
   Should announce: "Dialog: Are you sure?" ✅
```

```
VISUAL DIAGRAM — FOCUS TRAP FAILURE:
─────────────────────────────────────────────────────────────────

WITHOUT FOCUS TRAP:

Page:
  [Delete Account] ← trigger button
  [Email input]    ← visible but behind overlay
  [Password input] ← visible but behind overlay
  
  MODAL (on top):
  ┌────────────────────────────────────┐
  │ Are you sure?                      │
  │ [Confirm]  [Cancel]  [Close]       │
  └────────────────────────────────────┘

Tab order (broken):
  1. Confirm button ← in modal ✅
  2. Cancel button  ← in modal ✅
  3. Close button   ← in modal ✅
  4. Email input    ← BEHIND MODAL ❌ (focus escapes)
  5. Password input ← BEHIND MODAL ❌
  6. Delete Account ← trigger ❌
  7. Confirm button ← back in modal ❌ (confusing loop)

User is confused: why am I interacting with hidden elements?


WITH FOCUS TRAP:

Tab order (correct):
  1. Confirm button ← in modal ✅
  2. Cancel button  ← in modal ✅
  3. Close button   ← in modal ✅
  4. Confirm button ← LOOPS BACK to first ✅ (trapped)

Shift+Tab order:
  1. Close button   ← in modal ✅
  2. Cancel button  ← in modal ✅
  3. Confirm button ← in modal ✅
  4. Close button   ← LOOPS BACK to last ✅ (trapped)

Focus cannot escape modal ✅
```

```
SOLUTION 1: FULLY ACCESSIBLE MODAL
─────────────────────────────────────────────────────────────────

import { useEffect, useRef } from 'react';

function Modal({ isOpen, onClose, title, children }) {
  const modalRef = useRef(null);
  const previousFocusRef = useRef(null);

  // Focus management
  useEffect(() => {
    if (isOpen) {
      // Save currently focused element
      previousFocusRef.current = document.activeElement;
      
      // Move focus to modal
      const firstFocusable = modalRef.current?.querySelector(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      firstFocusable?.focus();
    } else {
      // Restore focus to trigger element
      previousFocusRef.current?.focus();
    }
  }, [isOpen]);

  // Escape key handler
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Focus trap
  useEffect(() => {
    if (!isOpen) return;

    const handleTab = (e) => {
      if (e.key !== 'Tab') return;

      const focusableElements = modalRef.current?.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (e.shiftKey) {  // Shift+Tab
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();  // loop to end
        }
      } else {  // Tab
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();  // loop to start
        }
      }
    };

    document.addEventListener('keydown', handleTab);
    return () => document.removeEventListener('keydown', handleTab);
  }, [isOpen]);

  // Prevent body scroll when modal open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="modal-overlay"
      onClick={onClose}  // click overlay to close
      aria-hidden="true"  // hide overlay from screen readers
    >
      <div
        ref={modalRef}
        className="modal-content"
        role="dialog"  // ← ARIA role
        aria-modal="true"  // ← tells screen readers it's modal
        aria-labelledby="modal-title"  // ← links to heading
        onClick={(e) => e.stopPropagation()}  // don't close when clicking modal
      >
        <h2 id="modal-title">{title}</h2>  {/* ← labeled element */}
        
        {children}
        
        <button
          onClick={onClose}
          aria-label="Close dialog"  // ← descriptive label
        >
          ×
        </button>
      </div>
    </div>
  );
}

// Usage
function App() {
  const [isOpen, setIsOpen] = useState(false);
  
  return (
    <div>
      <button onClick={() => setIsOpen(true)}>
        Delete Account
      </button>
      
      <Modal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Are you sure?"
      >
        <p>This action cannot be undone.</p>
        <button onClick={handleDelete}>Confirm</button>
        <button onClick={() => setIsOpen(false)}>Cancel</button>
      </Modal>
    </div>
  );
}

WHAT THIS ACHIEVES:
─────────────────────────────────────────────────────────────────

✅ Screen reader announces: "Dialog: Are you sure?"
✅ Focus moves to first button when modal opens
✅ Tab cycles through modal elements only (trapped)
✅ Shift+Tab cycles backward (trapped)
✅ Escape key closes modal
✅ Focus returns to "Delete Account" button when closed
✅ Body scroll locked when modal open
✅ Click overlay to close
✅ Semantic HTML with ARIA roles
```

```
SOLUTION 2: USE LIBRARY (focus-trap-react)
─────────────────────────────────────────────────────────────────

// Handles all focus management for you

import FocusTrap from 'focus-trap-react';

function Modal({ isOpen, onClose, title, children }) {
  const previousFocusRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      previousFocusRef.current = document.activeElement;
    } else {
      previousFocusRef.current?.focus();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <FocusTrap>  {/* ← auto focus trap */}
        <div
          className="modal-content"
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
          onClick={(e) => e.stopPropagation()}
        >
          <h2 id="modal-title">{title}</h2>
          {children}
          <button onClick={onClose}>Close</button>
        </div>
      </FocusTrap>
    </div>
  );
}

// OR: Use @headlessui/react Dialog component
import { Dialog } from '@headlessui/react';

function Modal({ isOpen, onClose, title, children }) {
  return (
    <Dialog open={isOpen} onClose={onClose}>
      <Dialog.Overlay className="modal-overlay" />
      <Dialog.Title>{title}</Dialog.Title>
      <Dialog.Description>
        {children}
      </Dialog.Description>
      <button onClick={onClose}>Close</button>
    </Dialog>
  );
}

// Headless UI handles:
// ✅ Focus management
// ✅ ARIA attributes
// ✅ Escape key
// ✅ Click outside
// ✅ Scroll locking
```

```
WCAG 2.1 REQUIREMENTS FOR MODALS:
─────────────────────────────────────────────────────────────────

1. KEYBOARD ACCESSIBLE (2.1.1)
   ✅ All functions available via keyboard
   ✅ Tab, Shift+Tab, Escape work as expected

2. FOCUS VISIBLE (2.4.7)
   ✅ Focused element has visible outline
   ✅ User can see where they are

3. FOCUS ORDER (2.4.3)
   ✅ Tab order is logical (left to right, top to bottom)
   ✅ Trapped within modal

4. NAME, ROLE, VALUE (4.1.2)
   ✅ role="dialog" or role="alertdialog"
   ✅ aria-modal="true"
   ✅ aria-labelledby or aria-label for title

5. ON FOCUS (3.2.1)
   ✅ Opening modal doesn't cause unexpected behavior
   ✅ Focus moves predictably

6. STATUS MESSAGES (4.1.3)
   ✅ Screen readers announce modal opened
   ✅ aria-live for dynamic content
```

```
COMMON MISTAKES:
─────────────────────────────────────────────────────────────────

1. MISSING aria-modal="true"
   → Screen readers don't know content behind is inert

2. WRONG ROLE (role="dialog" vs role="alertdialog")
   - dialog: user must interact (has controls)
   - alertdialog: urgent message (error, confirmation)
   → Use alertdialog for destructive actions

3. FOCUS NOT RESTORED
   Modal closes → focus lost → keyboard user disoriented

4. TABINDEX ON NON-INTERACTIVE ELEMENTS
   <div tabindex="0"> makes div focusable (confusing)
   → Use semantic elements (<button>, <a>)

5. NO VISIBLE FOCUS INDICATOR
   outline: none; in CSS → keyboard users can't see focus
   → Keep outline or provide custom focus styles

6. NESTED MODALS (stacking)
   Modal A opens → Modal B opens on top
   → Focus trap breaks, very hard to do accessibly
   → Avoid or use dedicated library
```

```
DEBUGGING CHECKLIST — "Modal fails accessibility audit"
─────────────────────────────────────────────────────────────────

✅ Test with keyboard only (unplug mouse)
   - Can you open modal? ✅
   - Can you focus all buttons? ✅
   - Tab stays inside modal? ✅
   - Escape closes it? ✅
   - Focus returns to trigger? ✅

✅ Test with screen reader (VoiceOver on Mac, NVDA on Windows)
   - Announces "dialog" or "alert dialog"? ✅
   - Reads modal title? ✅
   - Announces modal closed? ✅

✅ Run axe DevTools (Chrome extension)
   - Check for ARIA violations
   - Look for missing labels

✅ Check focus trap
   - Tab from last element → goes to first ✅
   - Shift+Tab from first → goes to last ✅

✅ Check ARIA attributes
   - role="dialog" or "alertdialog"? ✅
   - aria-modal="true"? ✅
   - aria-labelledby or aria-label? ✅

✅ Check color contrast (WCAG AA: 4.5:1)
   - Modal text vs background
   - Button text vs button background
```

> "The mental model: sighted mouse users see an overlay and understand the page behind is unavailable. But the DOM still contains all those elements, and assistive tech can access them unless you explicitly mark the modal as modal. aria-modal='true' tells screen readers 'everything outside this is inert.' Focus trap enforces it for keyboard. Escape key is the universal 'cancel' gesture. Always test with Tab and screen reader."

**INTERVIEW FOLLOW-UP QUESTIONS:**

**Q: "What's the difference between `role='dialog'` and `role='alertdialog'`?"**

> "`alertdialog` is for urgent interruptions requiring immediate action — error messages, destructive confirmations. `dialog` is for less urgent interactions — forms, settings, info panels. `alertdialog` has higher priority in screen reader announcement queue."

**Q: "How do you handle long modal content?"**

> "Make modal content scrollable, not the page behind it. Lock body scroll. If modal is taller than viewport, ensure scroll is within modal container with `overflow-y: auto`. Focus trap should include scrollable area."

**Q: "What about mobile accessibility?"**

> "Same principles apply: focus management (iOS VoiceOver rotor), Escape equivalent (swipe gestures), semantic HTML. Test with VoiceOver on iOS, TalkBack on Android. Modals should be full-screen on mobile for better UX."
