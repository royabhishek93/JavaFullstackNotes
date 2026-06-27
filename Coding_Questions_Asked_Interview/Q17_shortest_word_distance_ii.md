# Q17: Shortest Word Distance II

**Study Time:** 8-10 minutes | **Frequency:** 60% in interviews | **Difficulty:** ⭐⭐⭐⭐

---

## 🤔 Scenario

You are given a dictionary once, then asked many shortest-distance queries between two words.

**Input:**
```text
words = ["practice", "makes", "perfect", "coding", "makes"]

Queries:
shortest("coding", "practice")
shortest("makes", "coding")
```

**Output:**
```text
3
1
```

---

## 🧠 Key Principle

Preprocess word -> list of indices.
For each query, compute minimum distance between two sorted index lists using two pointers.

This makes repeated queries efficient.

---

## ✅ Java Solution

```java
import java.util.*;

public class WordDistance {
    private final Map<String, List<Integer>> positions = new HashMap<>();

    public WordDistance(String[] wordsDict) {
        for (int i = 0; i < wordsDict.length; i++) {
            positions.computeIfAbsent(wordsDict[i], k -> new ArrayList<>()).add(i);
        }
    }

    public int shortest(String word1, String word2) {
        List<Integer> list1 = positions.get(word1);
        List<Integer> list2 = positions.get(word2);

        int i = 0;
        int j = 0;
        int minDist = Integer.MAX_VALUE;

        while (i < list1.size() && j < list2.size()) {
            int idx1 = list1.get(i);
            int idx2 = list2.get(j);

            minDist = Math.min(minDist, Math.abs(idx1 - idx2));

            if (idx1 < idx2) {
                i++;
            } else {
                j++;
            }
        }

        return minDist;
    }
}
```

---

## 📊 Why Two Pointers Work

Index lists are sorted because we inserted in scanning order.

Example:
- `makes` -> `[1, 4]`
- `coding` -> `[3]`

Compare `1` vs `3` -> dist `2`, move smaller pointer (`1` side)
Compare `4` vs `3` -> dist `1`, move smaller pointer (`3` side ends)

Answer = `1`

---

## 🎯 Interview Q&A

### Q1: Complexity with many queries?

- Constructor: `O(n)`
- Each query: `O(k + m)` where `k` and `m` are occurrences of the two words
- Space: `O(n)`

### Q2: Why better than rescanning array per query?

Rescanning per query is `O(n)`. With preprocessing, hot words can be answered from compact index lists.

### Q3: Can we binary-search instead of two pointers?

Yes. For each index in smaller list, binary-search in larger list (`O(min(k,m) * log(max(k,m)))`). Two pointers are often simpler and fast.
