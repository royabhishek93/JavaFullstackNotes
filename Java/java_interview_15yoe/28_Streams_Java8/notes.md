# Java 8 Streams — Pipeline Processing, Laziness, and Parallelism

## What is this? (Plain English)

Think of a stream as a **conveyor-belt pipeline**: your data (a list, an array) enters at one end, and along the belt there are stations that each do one job — filter out some items, sort them, transform them, and so on. The data flows through station after station, and at the very end there's a final station that collects or computes the result. The original pile of data you started with never gets touched — the pipeline only ever produces a **new** result.

A stream has exactly three parts:
1. **Create the stream** from a data source (a list, an array, etc.).
2. **Zero or more intermediate operations** (filter, map, sorted, etc.) — each one takes a stream in and hands back a (transformed) stream.
3. **Exactly one terminal operation** (count, collect, reduce, etc.) — this is what actually triggers the whole pipeline to run, produces the final result, and closes the stream so it can't be reused.

Streams matter most for **bulk processing**. For a collection of 10–15 items, a plain `for`/`if-else` loop and a stream will feel about the same. The real benefit shows up with large collections, because streams can also be run in **parallel** across CPU cores.

## The Problem It Solves

Without streams, processing a collection means writing an explicit loop with `if` checks, temporary counters, and manual accumulation — for example, iterating a list of salaries with a `for` loop and an `if (salary > 3000) count++` to count how many salaries exceed a threshold. This works, but:

- It mixes "what to do" with "how to loop," making it harder to read and compose multiple transformations (filter, then sort, then count) in sequence.
- It doesn't give you an easy way to run the same logic in parallel across CPU cores for large datasets.

Streams solve this by turning the same logic into a **declarative pipeline**: open a stream from the collection, chain intermediate operations like `filter`, and finish with a terminal operation like `count`. The source collection is never modified — every operation produces a new stream (and the terminal operation produces a new result), which also makes the pipeline safe to reason about.

## Stream Pipeline (with Lazy Evaluation)

```
 (Data Source: List / Array)
        │  .stream() or .parallelStream()
        v
 [ Stream Created ]  (step 1: open stream)
        │
        v
 ┌─── Intermediate Operations (step 2: zero or more, chainable) ────────────────────────────┐
 │  filter(Predicate)          keep matching elements                                 │
 │        │                                                                           │
 │        v                                                                           │
 │  map / flatMap(Function)    transform / flatten                                    │
 │        │                                                                           │
 │        v                                                                           │
 │  distinct()                 remove duplicates                                      │
 │        │                                                                           │
 │        v                                                                           │
 │  sorted() / sorted(Comparator)   needs ALL elements first                          │
 │        │                                                                           │
 │        v                                                                           │
 │  peek / limit / skip / mapToInt/Long/Double                                        │
 └───────────────────────────────────────────────────────────────────────────┬───────────────────────────┘
                                          v
                          << Terminal Operation >> (step 3: exactly one)
                     forEach, collect, reduce, count, min/max, anyMatch,
                     findFirst, findAny, toArray
                                          │
                                          v
                     Result: new list/array/value (original source untouched)

 NOTE (applies to both the intermediate pipeline and the terminal op):
 Lazy evaluation — filter/map/sorted etc. do NOT run until a terminal op is invoked.
 Then each element flows through the whole pipeline one at a time, except ops like
 sorted() that must wait for the full stream first.
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

- **Intermediate operations are lazy.** Calling `.filter()`, `.map()`, `.peek()`, etc. does not process anything by itself — it just builds up the recipe. Nothing actually runs until a **terminal operation** is invoked.
- **Once closed, a stream can't be reused.** As soon as a terminal operation runs, the stream is consumed/closed. Calling another operation on the same stream reference throws `IllegalStateException: stream has already been operated upon or closed`.
- **Processing is element-by-element, not stage-by-stage** — for most operations. A single element is pushed as far down the pipeline as possible before the next element is picked up, rather than the whole collection finishing `filter` before any element starts `map`. The exception is an operation like `sorted()`, which needs the **entire** stream to be available before it can produce anything, so it forces the pipeline to wait until all elements have reached that point.

## Key Code / Config

### 1. Same logic with a loop vs. a stream

```java
import java.util.List;
import java.util.Arrays;

public class StreamVsLoop {
    public static void main(String[] args) {
        List<Integer> salaries = Arrays.asList(3000, 4100, 9000, 1000, 3500);

        // Without streams: manual loop + counter
        int count = 0;
        for (int salary : salaries) {
            if (salary > 3000) {
                count++;
            }
        }
        System.out.println("Loop count: " + count); // 3

        // With streams: create -> filter (intermediate) -> count (terminal)
        long streamCount = salaries.stream()
                .filter(salary -> salary > 3000)
                .count();
        System.out.println("Stream count: " + streamCount); // 3
    }
}
```

### 2. Different ways to create a stream

```java
import java.util.*;
import java.util.stream.Stream;

public class CreatingStreams {
    public static void main(String[] args) {

        // From a collection
        List<Integer> salaryList = Arrays.asList(1000, 2000, 3000);
        Stream<Integer> fromCollection = salaryList.stream();

        // From an array
        Integer[] salaryArray = {1000, 2000, 3000};
        Stream<Integer> fromArray = Arrays.stream(salaryArray);

        // From a static factory method (varargs)
        Stream<Integer> fromOf = Stream.of(1000, 2000, 3000);

        // From a Stream.Builder
        Stream.Builder<Integer> builder = Stream.builder();
        builder.add(1000).add(2000).add(3000);
        Stream<Integer> fromBuilder = builder.build();

        // From Stream.iterate — infinite unless bounded with .limit()
        Stream<Integer> fromIterate = Stream.iterate(1000, n -> n + 5000)
                .limit(5); // 1000, 6000, 11000, 16000, 21000

        fromIterate.forEach(System.out::println);
    }
}
```

### 3. `filter` — keep elements matching a predicate

```java
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.Stream;

public class FilterExample {
    public static void main(String[] args) {
        List<String> result = Stream.of("hello", "everybody", "how", "are", "you", "doing")
                .filter(name -> name.length() <= 3) // keep short words
                .collect(Collectors.toList());

        System.out.println(result); // [how, are, you]
    }
}
```

### 4. `map` — transform each element

```java
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.Stream;

public class MapExample {
    public static void main(String[] args) {
        List<String> result = Stream.of("HELLO", "EVERYBODY", "HOW", "ARE", "YOU", "DOING")
                .map(String::toLowerCase) // transform each element
                .collect(Collectors.toList());

        System.out.println(result); // [hello, everybody, how, are, you, doing]
    }
}
```

### 5. `flatMap` — flatten a nested collection into a single stream

```java
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

public class FlatMapExample {
    public static void main(String[] args) {
        List<List<String>> sentences = Arrays.asList(
                Arrays.asList("I", "love", "Java"),
                Arrays.asList("Concepts", "are", "clear"),
                Arrays.asList("It's", "very", "easy")
        );

        // Flatten list-of-lists into one stream of words
        List<String> flatWords = sentences.stream()
                .flatMap(List::stream)
                .collect(Collectors.toList());
        System.out.println(flatWords); // [I, love, Java, Concepts, are, clear, It's, very, easy]

        // flatMap can also chain more intermediate operations on the flattened stream
        List<String> flatLowerWords = sentences.stream()
                .flatMap(sentence -> sentence.stream().map(String::toLowerCase))
                .collect(Collectors.toList());
        System.out.println(flatLowerWords); // [i, love, java, concepts, are, clear, it's, very, easy]
    }
}
```

### 6. `distinct` and `sorted` (natural order and comparator)

```java
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

public class DistinctSortedExample {
    public static void main(String[] args) {
        int[] withDuplicates = {5, 2, 9, 2, 4, 0, 4, 7};

        List<Integer> distinctValues = Arrays.stream(withDuplicates)
                .boxed()
                .distinct()
                .collect(Collectors.toList());
        System.out.println(distinctValues); // [5, 2, 9, 4, 0, 7]

        List<Integer> ascending = distinctValues.stream()
                .sorted() // natural order
                .collect(Collectors.toList());
        System.out.println(ascending); // [0, 2, 4, 5, 7, 9]

        List<Integer> descending = distinctValues.stream()
                .sorted((v1, v2) -> v2 - v1) // custom comparator
                .collect(Collectors.toList());
        System.out.println(descending); // [9, 7, 5, 4, 2, 0]
    }
}
```

### 7. `peek`, `limit`, `skip`

```java
import java.util.Arrays;
import java.util.List;

public class PeekLimitSkipExample {
    public static void main(String[] args) {
        List<Integer> numbers = Arrays.asList(2, 1, 4, 7, 3, 6);

        // peek: run a side-effect (e.g. print) on each element, doesn't change the stream
        numbers.stream()
                .filter(v -> v > 2)
                .peek(v -> System.out.println("after filter: " + v))
                .forEach(v -> {}); // terminal operation needed to trigger execution

        // limit: truncate the stream to at most n elements
        List<Integer> firstThree = numbers.stream()
                .limit(3)
                .collect(java.util.stream.Collectors.toList());
        System.out.println(firstThree); // [2, 1, 4]

        // skip: skip the first n elements
        List<Integer> afterSkip = numbers.stream()
                .skip(3)
                .collect(java.util.stream.Collectors.toList());
        System.out.println(afterSkip); // [7, 3, 6]
    }
}
```

### 8. Primitive streams — `mapToInt` / `mapToLong` / `mapToDouble`

```java
import java.util.Arrays;
import java.util.List;
import java.util.stream.IntStream;

public class PrimitiveStreamExample {
    public static void main(String[] args) {
        // Directly from a primitive int[] array -> IntStream
        int[] primitiveInts = {2, 5, 8};
        int[] filtered = Arrays.stream(primitiveInts)
                .filter(v -> v > 3)
                .toArray();
        System.out.println(Arrays.toString(filtered)); // [5, 8]

        // From a List<String> of numbers -> convert to IntStream with mapToInt
        List<String> stringNumbers = Arrays.asList("2", "1", "4", "7");
        int[] parsedInts = stringNumbers.stream()
                .mapToInt(Integer::parseInt)
                .toArray();
        System.out.println(Arrays.toString(parsedInts)); // [2, 1, 4, 7]
    }
}
```

### 9. Laziness proof — nothing runs without a terminal operation

```java
import java.util.Arrays;
import java.util.List;

public class LazyEvaluationExample {
    public static void main(String[] args) {
        List<Integer> numbers = Arrays.asList(2, 1, 4, 7, 10);

        // Only intermediate operations chained -- nothing is printed, nothing executes.
        numbers.stream()
                .filter(n -> n >= 3)
                .peek(val -> System.out.println("val: " + val));

        System.out.println("--- nothing printed above, stream never ran ---");

        // Adding a terminal operation (count) triggers the whole pipeline to execute.
        long total = numbers.stream()
                .filter(n -> n >= 3)
                .peek(val -> System.out.println("val: " + val)) // now prints 4, 7, 10
                .count();
        System.out.println("count = " + total); // 3
    }
}
```

### 10. Element-by-element processing order (why `sorted()` behaves differently)

```java
import java.util.Arrays;
import java.util.List;

public class ProcessingOrderExample {
    public static void main(String[] args) {
        List<Integer> numbers = Arrays.asList(2, 1, 4, 7, 10);

        numbers.stream()
                .filter(n -> n >= 3)
                .peek(n -> System.out.println("after filter: " + n))
                .map(n -> -n)
                .peek(n -> System.out.println("after negating: " + n))
                .sorted() // needs the FULL stream before it can produce anything
                .peek(n -> System.out.println("after sorted: " + n))
                .forEach(n -> {});

        // Actual output shows each element (4, then 7, then 10) running through
        // filter -> peek -> map -> peek BEFORE the next element starts.
        // Only sorted() waits until all elements (-4, -7, -10) have arrived,
        // then sorts them (-10, -7, -4) and pushes them through the final peek.
    }
}
```

### 11. Terminal operations

```java
import java.util.*;
import java.util.stream.Collectors;

public class TerminalOperationsExample {
    public static void main(String[] args) {
        List<Integer> numbers = Arrays.asList(2, 1, 4, 7, 10);

        // forEach: perform an action per element, returns nothing
        numbers.stream().filter(n -> n >= 3).forEach(System.out::println); // 4, 7, 10

        // toArray: collect into an Object[] or a typed array
        Object[] objArray = numbers.stream().filter(n -> n >= 3).toArray();
        Integer[] intArray = numbers.stream().filter(n -> n >= 3).toArray(Integer[]::new);

        // reduce: associative aggregation, returns Optional
        Optional<Integer> sum = numbers.stream().reduce((v1, v2) -> v1 + v2);
        System.out.println(sum.get()); // 24  (2+1+4+7+10)

        // collect: gather into a List
        List<Integer> filtered = numbers.stream()
                .filter(n -> n >= 3)
                .collect(Collectors.toList());

        // min / max with a comparator
        Optional<Integer> min = numbers.stream().filter(n -> n >= 3)
                .min((v1, v2) -> v1 - v2); // natural order -> smallest first
        Optional<Integer> max = numbers.stream().filter(n -> n >= 3)
                .max((v1, v2) -> v1 - v2);
        System.out.println(min.get() + " " + max.get()); // 4 10

        // count
        long count = numbers.stream().filter(n -> n >= 3).count(); // 3

        // anyMatch / allMatch / noneMatch
        boolean anyGreaterThanThree = numbers.stream().anyMatch(n -> n > 3); // true

        // findFirst / findAny
        Optional<Integer> first = numbers.stream().filter(n -> n >= 3).findFirst(); // 4
        Optional<Integer> any = numbers.stream().filter(n -> n >= 3).findAny(); // any matching value
    }
}
```

### 12. A stream can only be consumed once

```java
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

public class StreamReuseExample {
    public static void main(String[] args) {
        List<Integer> numbers = Arrays.asList(2, 1, 4, 7, 10);
        var filteredNumberStream = numbers.stream().filter(n -> n >= 3);

        filteredNumberStream.forEach(System.out::println); // terminal op #1 -- OK, closes the stream

        // Reusing the same stream reference after a terminal operation throws:
        // java.lang.IllegalStateException: stream has already been operated upon or closed
        filteredNumberStream.collect(Collectors.toList()); // terminal op #2 -- throws!
    }
}
```

### 13. Parallel streams (Fork/Join under the hood)

```java
import java.util.Arrays;
import java.util.List;

public class ParallelStreamExample {
    public static void main(String[] args) {
        List<Integer> numbers = Arrays.asList(11, 22, 33, 44, 55, 66, 77, 88, 99, 110);

        long sequentialStart = System.currentTimeMillis();
        numbers.stream()
                .map(n -> n * n)
                .forEach(n -> {});
        System.out.println("Sequential time: " + (System.currentTimeMillis() - sequentialStart) + "ms");

        long parallelStart = System.currentTimeMillis();
        numbers.parallelStream() // only difference: .stream() -> .parallelStream()
                .map(n -> n * n)
                .forEach(n -> {});
        System.out.println("Parallel time: " + (System.currentTimeMillis() - parallelStart) + "ms");
    }
}
```

Internally, `parallelStream()` hands the source collection to a `Spliterator`, whose `trySplit()` method recursively finds the midpoint and splits the data into smaller and smaller chunks. Those chunks are then handed to the **Fork/Join pool**: "fork" divides a task into subtasks that run concurrently (one per CPU core), and "join" combines the subtask results back together once they finish.

## Interview Q&A

**Q1: Why are intermediate operations described as "lazy," and how did the transcript demonstrate it?**
A: Intermediate operations like `filter`, `map`, and `peek` don't execute anything by themselves — they just describe a transformation to apply later. In the demo, chaining `.filter()` and `.peek()` with no terminal operation printed nothing at all. Only after adding a terminal operation like `.count()` did the pipeline actually run and the `peek` print statements appear. This is why intermediate operations are said to "execute only when a terminal operation is invoked."

**Q2: What's the difference between `map` and `flatMap`?**
A: `map` transforms each element and returns one output per input element, keeping the same "shape" (e.g., a stream of strings stays a stream of strings, just modified). `flatMap` is for flattening nested/complex collections — for example, a `List<List<String>>` — into a single flat stream, by having its function return a stream for each element and merging all of those streams together into one.

**Q3: Does a stream process one operation across the whole collection before moving to the next operation?**
A: No — for most operations, a single element is pushed through the entire pipeline (filter → peek → map → peek, etc.) before the next element is even picked up. The exception is an operation like `sorted()`, which cannot produce any output until it has seen every element in the stream, so the pipeline is forced to collect the whole stream before `sorted()` (and anything after it) can run. This same element-by-element behavior is also why short-circuiting operations like `anyMatch` can stop processing as soon as a match is found, without touching every element.

**Q4: Can you reuse a stream after calling a terminal operation on it?**
A: No. Once a terminal operation runs, the stream is considered closed/consumed. Calling another operation (intermediate or terminal) on that same stream reference throws `IllegalStateException: stream has already been operated upon or closed`. To run the pipeline again, you need to create a brand-new stream from the original data source.

**Q5: How does `reduce` differ from `collect`?**
A: `reduce` performs an associative aggregation across the stream's elements using a binary operation (e.g., summing pairs of values two at a time: 2+1=3, 3+4=7, 7+7=14, 14+10=24) and returns a single `Optional` value. `collect` instead gathers the stream's elements into a new collection, such as a `List`, via `Collectors.toList()`.

**Q6: How does `parallelStream()` actually split work across CPU cores, and is it commonly used in practice?**
A: Calling `parallelStream()` (instead of `stream()`) hands the source collection to a `Spliterator`. Its `trySplit()` method recursively finds the midpoint of the data and splits it into progressively smaller chunks, each becoming its own `Spliterator`. Those chunks are then handed to the **Fork/Join pool** technique, which runs the sub-tasks concurrently across available CPU cores and joins the results back together. That said, it's called out as a pattern that's good to know for interviews but was rarely used day-to-day in practice — most real-world stream usage is sequential.
