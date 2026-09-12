# How Java Works — JVM, JRE, JDK, and the Write-Once-Run-Anywhere Pipeline

## What is this? (Plain English)

Think of it like ordering food through a universal translator at an international food court. You write your order in one language (Java source code). A translator (the compiler, `javac`) converts it into a universal "menu code" (bytecode) that every food stall in the court can read, no matter what language the stall's cooks actually speak. Each stall has its own cook (a JVM) who understands the local kitchen equipment (the actual OS/hardware) but can still read the universal menu code and turn it into food (native machine instructions) using that specific kitchen's tools.

That's Java's core idea: you write code once, compile it into a universal format (bytecode), and any machine with a JVM installed for its own platform can run that exact same bytecode. This is "Write Once, Run Anywhere" (WORA), and it's the reason Java is called a platform-independent language even though the JVM itself is not.

Java is a platform-independent, popular object-oriented programming (OOP) language, and its biggest advantage is portability (WORA) — a program written on one machine (say, a laptop) can run unmodified on any other machine (a different OS, a mobile device, etc.) as long as that machine has a compatible JVM.

## The Problem It Solves

Without an intermediate step, a compiled program is tied to one specific operating system and CPU architecture — you'd need to recompile (or rewrite) your program for every platform you want it to run on.

Java solves this by never compiling directly to machine code. Instead:
- The Java compiler (`javac`) turns your `.java` source into `.class` bytecode — a format that isn't tied to any specific OS.
- Every platform (Windows, macOS, Linux, mobile, etc.) gets its own platform-specific JVM.
- Any JVM, on any platform, can read the exact same bytecode file and translate it into that platform's native machine code at runtime.

So the Java program (as bytecode) is platform-independent, but the JVM that runs it is platform-dependent — you need the correct JVM for the OS you're running on. This split is what gives Java its portability.

## Diagram

**ASCII fallback:**

```
 .java source file
        |
        |  javac (compiler)
        v
 .class file = BYTECODE  (platform-independent — same file works everywhere)
        |
        v
 +-------------------------------------------------------------+
 | JDK  =  JRE  +  Compiler (javac)  +  Debugger                |
 |                                                               |
 |   +-------------------------------------------------------+ |
 |   | JRE  =  JVM  +  Class Libraries                        | |
 |   |                                                         | |
 |   |   Class Libraries (java.lang, java.util, ...) ---.      | |
 |   |                                                    \     | |
 |   |   +---------------------------------------------+  \    | |
 |   |   | JVM (abstract machine, platform-dependent)   |<--'    | |
 |   |   |                                               |       | |
 |   |   |  Class Loader -> Bytecode Verifier            |       | |
 |   |   |      -> Execution Engine                      |       | |
 |   |   |          -> JIT Compiler (interpreter + JIT)  |       | |
 |   |   +---------------------------------------------+       | |
 |   +-------------------------------------------------------+ |
 +-------------------------------------------------------------+
        |
        v
 Native Machine Code -> CPU executes -> Output

 Same .class bytecode file, unchanged, can be handed to:
   JVM on macOS   |   JVM on Windows   |   JVM on Linux   |   JVM on Mobile
 => Write Once, Run Anywhere (WORA)
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## Key Concepts (from the transcript)

- **JVM (Java Virtual Machine)**: An abstract machine — it doesn't exist physically, it's software. Its job: take bytecode as input and produce machine code as output (using its JIT — Just-In-Time — compiler), which the CPU can then execute. The JVM is platform-dependent: a Mac needs a Mac-compatible JVM, Windows needs a Windows-compatible JVM, etc. Because any JVM (regardless of OS) can read the same bytecode, the bytecode itself is portable — this is what makes Java "write once, run anywhere."
- **JRE (Java Runtime Environment)**: JVM + class libraries. Class libraries are the pre-built code Java ships with, e.g. `Math.abs()` from `java.lang`, or `Arrays.sort()` from `java.util`. When your bytecode calls a library method, that call has to be resolved/linked at runtime — the JVM needs the actual library code to run it, and the JRE supplies those class libraries. With only a JRE installed, you can **run** any compiled Java bytecode, but you **cannot write or compile** Java code (JRE has no compiler).
- **JDK (Java Development Kit)**: JRE + the programming language tooling + compiler (`javac`) + debugger. Downloading the JDK gives you everything: the compiler to turn `.java` into `.class`, a debugger, and the JRE (which itself includes the JVM and class libraries).
- All three — JVM, JRE, JDK — are platform-dependent (you download/install the version matching your OS). Only the compiled bytecode (`.class` files) is platform-independent.
- **JSE (Java Standard Edition)**: Core Java — classes, objects, multithreading, and the fundamentals a developer normally works with day to day.
- **JEE (Java Enterprise Edition)**: JSE + additional APIs aimed at large-scale applications (e.g. e-commerce systems) — including the transactional API (commit/rollback), persistence APIs (for managing relational databases), and web technologies like Servlets and JSP.
- **JME (Java Micro/Mobile Edition)**: APIs targeted at resource-constrained environments like mobile devices. (Its naming has since changed — it's now referred to as Jakarta EE.)
- **Main method (`public static void main(String[] args)`)**: The entry point of every Java program — the JVM specifically looks for and calls this method to start execution.
  - `void`: no return value expected.
  - `public`: must be callable from outside the class/package, because the JVM (an external caller) needs to invoke it.
  - `static`: means it belongs to the class itself, not to an object — the JVM can call it directly via the class name without first creating an object instance.
- **File/class naming rule**: The `.java` file name must match its public class name exactly, and a single `.java` file can contain only one public class.
- **Recompilation matters**: The JVM only ever reads `.class` (bytecode) files, never `.java` source files directly. If you edit the `.java` source but don't recompile it, running the program again still executes the *old* bytecode — your changes have no effect until you recompile.

## Key Code / Config

**Basic class structure and the first program (from the transcript's `Employee` example):**

```java
// Employee.java — file name must match the public class name exactly
public class Employee {

    // main is the entry point: the JVM calls this method to start the program
    // public  -> callable from outside the package (JVM calls it externally)
    // static  -> callable via the class name, no object needed
    // void    -> returns nothing
    public static void main(String[] args) {

        // This is a single-line comment (ignored by the compiler)

        /* This is a
           multi-line comment */

        int a = -10;
        System.out.println("This is my first program and output of a is " + a);
        // Output: This is my first program and output of a is -10
    }
}
```

**Compiling and running from the command line:**

```bash
# Compile: .java source -> .class bytecode
javac Employee.java
# Produces Employee.class (the bytecode file)

# Run: JVM reads the .class bytecode and executes it
java Employee
# Output: This is my first program and output of a is -10
```

**Why recompiling matters (demonstrated in the transcript):**

```bash
# 1. Change int a = -10; to int a = -11; in Employee.java and save it
# 2. Run WITHOUT recompiling:
java Employee
# Output is still: ... output of a is -10   (JVM only reads the stale .class file)

# 3. Recompile, THEN run:
javac Employee.java
java Employee
# Output is now: ... output of a is -11   (bytecode has been updated)
```

**Using built-in class libraries (part of the JRE, resolved at runtime):**

```java
// Math.abs comes from java.lang (implicitly available)
int result = Math.abs(-25);

// Arrays.sort comes from java.util
import java.util.Arrays;

int[] numbers = {5, 3, 1, 4};
Arrays.sort(numbers);
```

**Verifying your JDK installation:**

```bash
java -version
# Prints the installed Java version (e.g. Java 8, Java 15, Java 17, ...),
# confirming the JDK/JRE/JVM were installed correctly.
```

> Download JDK versions from the official Oracle downloads page (choose the installer matching your OS — e.g. Windows 64-bit, macOS 64-bit).

## Interview Q&A

**Q1: Is Java itself platform-independent, or is the JVM platform-independent?**
A: The Java *program* (its compiled bytecode) is platform-independent — the same `.class` file can be handed to any machine. The JVM itself is **not** platform-independent; it's platform-dependent, meaning you need a JVM build that matches your specific OS (Windows, macOS, Linux, etc.). The JVM's job is to read that same universal bytecode and translate it into the native machine code for its own platform.

**Q2: What's the actual relationship between JDK, JRE, and JVM?**
A: JVM is the innermost piece — the abstract machine that executes bytecode. JRE = JVM + class libraries (the pre-built code like `java.lang`, `java.util` that your bytecode may call into at runtime). JDK = JRE + the compiler (`javac`) + a debugger + other development tooling. So JDK is a superset of JRE, and JRE is a superset of JVM — downloading the JDK gives you everything needed to both write and run Java code.

**Q3: If I only have a JRE installed (no JDK), can I run Java programs? Can I write and compile them?**
A: You can run any existing compiled bytecode (`.class` files), because JRE includes the JVM (to execute) and the class libraries (to resolve any library calls the bytecode makes). But you cannot write or compile Java source code, because JRE does not include a compiler (`javac`) — that only comes with the JDK.

**Q4: What actually happens between compiling a `.java` file and getting output on screen?**
A: `javac` compiles the `.java` source into a `.class` bytecode file. That bytecode is handed to the JVM. Any library calls in the bytecode (e.g. `Arrays.sort`) get resolved/linked against the class libraries that are part of the JRE. The JVM's JIT (Just-In-Time) compiler then converts the bytecode into native machine code, which the CPU executes to produce the program's output.

**Q5: Why does `public static void main(String[] args)` need to be exactly `public static void`?**
A: `public` because the JVM — an external caller outside your class/package — needs to be able to invoke it. `static` because the JVM must call it without first creating an object of your class; being static means it belongs to the class itself and can be invoked directly as `ClassName.main(...)`. `void` because this method isn't expected to return any value back to its caller.

**Q6: I edited my `.java` file and saved it, but running the program still shows the old output. Why?**
A: The JVM never reads `.java` source files directly — it only ever executes `.class` bytecode. If you don't recompile (`javac`) after editing the source, the `.class` file on disk is unchanged (stale), so running it again just re-executes the old logic. You must recompile before your changes take effect.

**Q7: What's the difference between JSE, JEE, and JME?**
A: JSE (Java Standard Edition) is core Java — classes, objects, multithreading, and the fundamentals most developers work with daily. JEE (Java Enterprise Edition) builds on JSE by adding APIs for large-scale applications, such as the transactional API (commit/rollback) and persistence APIs for relational databases, plus web technologies like Servlets and JSP — commonly used for systems like e-commerce platforms. JME (Java Micro/Mobile Edition) provides APIs suited to resource-constrained environments like mobile devices (its branding has since evolved into what's now called Jakarta EE).
