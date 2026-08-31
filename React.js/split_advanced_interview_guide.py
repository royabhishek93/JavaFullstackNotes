#!/usr/bin/env python3
"""Split the advanced React guide into one beginner-friendly question per file."""

from pathlib import Path
import re


SOURCE = Path(__file__).with_name("advanced-interview-guide_bySangamMukherjee.md")
OUTPUT = Path(__file__).with_name("advanced-interview-questions")

TOPICS = [
    ("react-fiber-architecture", "React Fiber Architecture", "MUST KNOW"),
    ("concurrent-mode-start-transition", "Concurrent Rendering and startTransition", "MUST KNOW"),
    ("react-server-components", "React Server Components", "MUST KNOW"),
    ("state-management-at-scale", "State Management at Scale", "MUST KNOW"),
    ("performance-optimization", "Performance Optimization", "MUST KNOW"),
    ("stale-closure-problem", "The Stale Closure Problem", "MUST KNOW"),
    ("react-design-patterns", "React Design Patterns", "SHOULD KNOW"),
    ("error-boundaries", "Error Boundaries", "SHOULD KNOW"),
    ("code-splitting-bundle-optimization", "Code Splitting and Bundle Optimization", "SHOULD KNOW"),
    ("testing-strategy", "Testing Strategy", "SHOULD KNOW"),
    ("react-query-advanced", "React Query Caching and Optimistic Updates", "SHOULD KNOW"),
    ("typescript-generic-components", "TypeScript Generic Components", "GOOD TO KNOW"),
    ("react-security", "Security in React", "GOOD TO KNOW"),
    ("react-19", "React 19", "GOOD TO KNOW"),
    ("when-not-to-use-react", "When Not to Use React", "GOOD TO KNOW"),
]


def beginner_intro(priority: str, question: str) -> str:
    return f"""# {question}

> **Interview priority:** {priority}

## Question

{question}

## Beginner Lens

Before memorizing the interview answer, follow the scenario and notice three things: the problem React is solving, the state or browser work that changes, and the rule that keeps the UI correct. Read the code blocks slowly and predict the next result before reading the explanation.

## Detailed Explanation

"""


def question_from_section(section: str) -> str:
    match = re.search(r'\*\*Q:\s*"([^"]+)"\*\*', section)
    if not match:
        raise ValueError("Could not find a question in section")
    return match.group(1)


def explanation_from_section(section: str) -> str:
    """Remove the source heading and question so a generated note asks it once."""
    lines = section.splitlines()
    if lines and lines[0].startswith("## "):
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and lines[0].startswith("**Q:"):
        lines.pop(0)
    return "\n".join(lines).lstrip("-\n")


def write_question(number: int, slug: str, priority: str, question: str, body: str) -> None:
    content = beginner_intro(priority, question) + explanation_from_section(body).strip() + "\n"
    path = OUTPUT / f"{number:02d}-{slug}.md"
    path.write_text(content, encoding="utf-8")


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    OUTPUT.mkdir(exist_ok=True)
    for generated_file in OUTPUT.glob("[0-9][0-9]-*.md"):
        generated_file.unlink()

    sections = re.split(r'(?=^## \d+\. )', source, flags=re.MULTILINE)
    numbered_sections = [section for section in sections if re.match(r'^## \d+\. ', section)]
    primary_sections = numbered_sections[:-1]
    senior_section = numbered_sections[-1]

    if len(primary_sections) != 13:
        raise ValueError(f"Expected 13 primary sections, found {len(primary_sections)}")

    for index, section in enumerate(primary_sections, start=1):
        topic_index = index - 1 if index <= 5 else index
        slug, _, priority = TOPICS[topic_index]
        output_number = index if index <= 5 else index + 1
        write_question(output_number, slug, priority, question_from_section(section), section)

    senior_questions = re.split(r'(?=^\*\*Q: )', senior_section, flags=re.MULTILINE)
    senior_questions = [part for part in senior_questions if part.startswith("**Q:")]
    if len(senior_questions) != 2:
        raise ValueError(f"Expected 2 senior questions, found {len(senior_questions)}")

    senior_question = senior_questions[0]
    slug, _, priority = TOPICS[14]
    write_question(15, slug, priority, question_from_section(senior_question), senior_question)

    stale_closure = senior_questions[1]
    slug, _, priority = TOPICS[5]
    write_question(6, slug, priority, question_from_section(stale_closure), stale_closure)

    index_lines = [
        "# React Advanced Interview Questions",
        "",
        "The filename number is the recommended interview-study order: lower number means higher priority. Each file contains one question and a detailed beginner-oriented explanation.",
        "",
        "## Study Order",
        "",
        "| Priority | Question |",
        "| --- | --- |",
    ]
    for number, (slug, title, priority) in enumerate(TOPICS, start=1):
        index_lines.append(f"| {number:02d} - {priority} | [{title}]({number:02d}-{slug}.md) |")
    (OUTPUT / "README.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()