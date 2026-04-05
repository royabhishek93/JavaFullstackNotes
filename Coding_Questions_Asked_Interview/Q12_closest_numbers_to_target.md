# Q12: Closest Number(s) to Target (Interview Variant)

**Type:** Array | **Pattern:** Minimum absolute difference | **Difficulty:** Easy

---

## Problem Statement

Given an integer array and a target value, print or return all numbers whose absolute difference from the target is minimum.

### Example

```text
Input:  arr = [10, 120, 45, 175, 98, 180, 200, 102], target = 100
Output: [98, 102]
Explanation:
|98 - 100| = 2 and |102 - 100| = 2 (minimum difference)
```

---

## Approach

Use 2 passes:

1. Find the minimum absolute difference from target.
2. Collect all values whose difference equals that minimum.

This keeps the code simple and still runs in linear time.

---

## Java Solution (as requested)

```java
import java.util.*;

public class ClosestNumbers {
    public static void main(String[] args) {
        List<Integer> arr = Arrays.asList(10, 120, 45, 175, 98, 180, 200, 102);
        int target = 100;

        int minDiff = Integer.MAX_VALUE;

        // Step 1: Find minimum difference
        for (int num : arr) {
            minDiff = Math.min(minDiff, Math.abs(num - target));
        }

        // Step 2: Print all matching values
        System.out.print("Closest numbers: ");
        for (int num : arr) {
            if (Math.abs(num - target) == minDiff) {
                System.out.print(num + " ");
            }
        }
    }
}
```

---

## Reusable Method Version

```java
import java.util.*;

public class ClosestNumbersUtil {

    public static List<Integer> closestNumbers(List<Integer> arr, int target) {
        int minDiff = Integer.MAX_VALUE;

        for (int num : arr) {
            minDiff = Math.min(minDiff, Math.abs(num - target));
        }

        List<Integer> result = new ArrayList<>();
        for (int num : arr) {
            if (Math.abs(num - target) == minDiff) {
                result.add(num);
            }
        }

        return result;
    }

    public static void main(String[] args) {
        List<Integer> arr = Arrays.asList(10, 120, 45, 175, 98, 180, 200, 102);
        int target = 100;
        System.out.println(closestNumbers(arr, target)); // [98, 102]
    }
}
```

---

## Complexity

- Time: O(n)
- Space: O(1) extra space for print-only version, O(k) for returned result list

---

## LeetCode Mapping

This exact wording is typically used as an interview variant, not a standard standalone LeetCode title.

Closest related LeetCode problems:
- 658. Find K Closest Elements
- 16. 3Sum Closest
