# Q16: Shortest Word Distance I

**Study Time:** 6-8 minutes | **Frequency:** 65% in interviews | **Difficulty:** ⭐⭐⭐

---

## 🤔 Scenario

Given an array of words and two target words, return the minimum index distance between them.

**Input:**
```text
words = ["practice", "makes", "perfect", "coding", "makes"]
word1 = "coding"
word2 = "practice"
```

**Output:**
```text
3
```

**Why:** `coding` is at index `3`, `practice` is at index `0`, so distance is `|3 - 0| = 3`.

---

## 🧠 Key Principle

Track the latest index of each target word while scanning once from left to right.
Whenever both indices are known, update the minimum distance.

---

## ✅ Java Solution (O(n))

```java
public static int shortestDistance(String[] words, String word1, String word2) {
    int idx1 = -1;
    int idx2 = -1;
    int minDist = Integer.MAX_VALUE;

    for (int i = 0; i < words.length; i++) {
        if (words[i].equals(word1)) {
            idx1 = i;
        }
        if (words[i].equals(word2)) {
            idx2 = i;
        }

        if (idx1 != -1 && idx2 != -1) {
            minDist = Math.min(minDist, Math.abs(idx1 - idx2));
        }
    }

    return minDist;
}
```

---

## 📊 Dry Run

For `words = [practice, makes, perfect, coding, makes]`, `word1 = coding`, `word2 = practice`:

- i=0 → `practice`: idx2=0
- i=3 → `coding`: idx1=3 → minDist = `|3-0| = 3`
- i=4 → `makes`: no change

Final answer: `3`

---

## 🎯 Interview Q&A

### Q1: Time and space complexity?

- Time: `O(n)` (single scan)
- Space: `O(1)`

### Q2: Why not nested loops?

Nested loops become `O(n^2)`. This one-pass approach is optimal for this variant.

### Q3: What if one word is missing?

LeetCode 243 guarantees both exist. In production code, you can return `-1` when either index never gets assigned.
