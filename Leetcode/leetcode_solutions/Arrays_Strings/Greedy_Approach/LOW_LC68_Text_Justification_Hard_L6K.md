# LC 68: Text Justification

**Link**: [leetcode.com/problems/text-justification](https://leetcode.com/problems/text-justification/)

## Problem
Given a list of words and a max width `maxWidth`, format the text such that each line has exactly `maxWidth` characters and is fully (left) justified.

## Approach: Greedy Line Packing

```java
public List<String> fullJustify(String[] words, int maxWidth) {
    List<String> result = new ArrayList<>();
    int i = 0, n = words.length;

    while (i < n) {
        // Determine words that fit on this line
        int lineLen = words[i].length();
        int j = i + 1;
        while (j < n && lineLen + 1 + words[j].length() <= maxWidth) {
            lineLen += 1 + words[j].length();
            j++;
        }

        // Build line from words[i..j-1]
        int numWords = j - i;
        int numSpaces = maxWidth - lineLen + (numWords - 1); // extra spaces to distribute

        StringBuilder sb = new StringBuilder(words[i]);

        if (j == n || numWords == 1) {
            // Last line or single word: left-justify, pad right
            for (int k = i + 1; k < j; k++) {
                sb.append(' ').append(words[k]);
            }
            while (sb.length() < maxWidth) sb.append(' ');
        } else {
            int gaps = numWords - 1;
            int spacePerGap = numSpaces / gaps;
            int extraSpaces = numSpaces % gaps;

            for (int k = i + 1; k < j; k++) {
                int spaces = spacePerGap + (k - i <= extraSpaces ? 1 : 0);
                for (int s = 0; s < spaces; s++) sb.append(' ');
                sb.append(words[k]);
            }
        }

        result.add(sb.toString());
        i = j;
    }

    return result;
}
```

**Time Complexity**: O(total characters across all words)  
**Space Complexity**: O(maxWidth) per line

## Key Insight: Space Calculation
```
Total characters in words[i..j-1] = lineLen - (numWords-1)
Minimum spaces needed (1 between each) = numWords-1
Spaces to distribute = maxWidth - (total word chars)
                      = maxWidth - (lineLen - (numWords-1))
                      = maxWidth - lineLen + numWords - 1
```

## Edge Cases Handled
- **Last line**: left-justify with single spaces, right-pad
- **Single word on line**: left-justify, right-pad
- **Uneven space distribution**: extra spaces go to leftmost gaps first

## Trace Example
```
words = ["What","must","be","acknowledged"]
maxWidth = 16

Line 1: "What must be   " → 3+1+4+1+2+7=  wait...
words[0..2]="What must be": 4+1+4+1+2=12 chars, 3 words, 2 gaps
spaces=16-(4+4+2)=6, 6/2=3 per gap, 0 extra
→ "What   must   be" ✓ (16 chars)
```

## Tips and Tricks
- State the core invariant before coding so the implementation follows the idea directly.
- Test the smallest edge cases first because they expose most off-by-one bugs.
- When explaining in interviews, lead with the optimized idea and then justify complexity clearly.

## Related Problems
- LC 6 Zigzag Conversion
