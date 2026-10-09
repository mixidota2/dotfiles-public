---
name: eli5
description: Create a dead-simple visual HTML explainer for a topic. Use when the user writes $eli5 <topic> or asks for a picture-first explanation for someone with no prior knowledge. Do not use for ordinary explanations, detailed technical documentation, or non-HTML deliverables.
---

# eli5

Create a self-contained HTML artifact that explains the requested topic to a complete beginner.

## Invoke explicitly

Write `$eli5 <topic>` in Codex. `/skills` opens the skill picker; `/eli5` is not a custom slash command.

## Outcome

- Put the main idea first in one short sentence.
- Use a small sequence of large, clear visual panels to show what happens. Prefer labelled CSS or SVG diagrams; use generated imagery only when it materially improves understanding.
- Use familiar comparisons and everyday language. Define an unavoidable technical word in place.
- Keep each panel to one idea and very few words. Do not trade clarity for completeness.
- Include a final one-sentence recap.

## Process

1. Identify the single beginner question behind the topic. If the topic is ambiguous enough to change the explanation, ask one concise question; otherwise make the smallest reasonable assumption and name it.
2. Build the explanation as a standalone `.html` file with responsive layout, readable large type, high contrast, and descriptive text alternatives for visuals.
3. Check that a reader can understand the sequence without prior knowledge, and remove jargon, dense paragraphs, and unnecessary detail.
4. Return the artifact path and a one-line summary. Do not paste the full HTML into chat unless the user asks.

## Boundaries

- Preserve important safety, uncertainty, and factual caveats in plain language.
- For facts that may have changed, verify them before placing them in the artifact.
- Use the user's requested language; otherwise match the language of the request.
