# Q18: Shortest Word Distance III

**Study Time:** 7-9 minutes | **Frequency:** 55% in interviews | **Difficulty:** ⭐⭐⭐⭐

---

## 🤔 Scenario

Same as Word Distance, but now `word1` and `word2` can be equal.

**Input:**
```text
words = ["practice", "makes", "perfect", "coding", "makes"]
word1 = "makes"
word2 = "makes"
```

**Output:**
```text
3
```

Because `makes` appears at indices `1` and `4`, distance is `4 - 1 = 3`.

---

## 🧠 Key Principle

Two cases:
- `word1 != word2`: same approach as LC 243.
- `word1 == word2`: distance is between consecutive occurrences of that word.

---

## ✅ Java Solution

```java
public static int shortestWordDistance(String[] words, String word1, String word2) {
    int minDist = Integer.MAX_VALUE;

    if (word1.equals(word2)) {
        int prev = -1;
        for (int i = 0; i < words.length; i++) {
            if (words[i].equals(word1)) {
                if (prev != -1) {
                    minDist = Math.min(minDist, i - prev);
                }
                prev = i;
            }
        }
        return minDist;
    }

    int idx1 = -1;
    int idx2 = -1;

    for (int i = 0; i < words.length; i++) {
        if (words[i].equals(word1)) {
            idx1 = i;
        } else if (words[i].equals(word2)) {
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

## 📊 Dry Run (same word)

`words = [practice, makes, perfect, coding, makes]`, `word1 = word2 = makes`

- i=1 -> first `makes`, `prev = 1`
- i=4 -> second `makes`, dist = `4 - 1 = 3`, `minDist = 3`

Answer: `3`

---

## 🎯 Interview Q&A

### Q1: Why does LC 243 logic fail when words are same?

Because the same index could be used for both words, incorrectly giving distance `0`.

### Q2: Complexity?

- Time: `O(n)`
- Space: `O(1)`

### Q3: Common bug?

For `word1 == word2`, using two separate pointers without special handling often gives wrong answers.
