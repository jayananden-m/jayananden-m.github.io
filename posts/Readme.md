# Writing posts

You write Markdown here. `build.py` (in the repo root) turns each `.md` file
into a styled HTML page and rebuilds `writing.html`. You never edit HTML.

## To publish a new post

1. Copy `attention-negative-result.md` to `posts/my-new-post.md`.
2. Edit the front matter (the block between the `---` lines) and write the body.
3. From the repo root, run:

   ```
   python build.py
   ```

   (First time only: `pip install markdown pyyaml pygments`.)

4. Commit and push. That's it.

   If you enabled the GitHub Action (`.github/workflows/build-blog.yml`),
   skip step 3 — just commit the `.md` and the Action builds and deploys.

## Front matter

```yaml
---
title: Your post title # required
slug: my-new-post # optional; becomes writing-<slug>.html
date: Sep 2026 # shown on the page, any format you like
read: 6 min # optional; auto-estimated if omitted
sort: 2026-09-14 # optional ISO date; controls index order
subtitle: > # optional; the big lede under the title
  One or two sentences that set up the piece.
summary: > # optional; the blurb on the index card
  Falls back to the subtitle, then the first paragraph, if omitted.
draft: true # optional; excludes the post from the build
tags: ["ml", "systems", "builder-series"] # optional; renders topic badges & enables filter on writing.html
---
```

## Writing the body

Plain Markdown. A few things worth knowing:

- **Headings** — use `##` for sections (`###` for sub-sections). Don't use `#`;
  the title comes from the front matter.
- **Images / GIFs** — put the file in `assets/posts/` and reference it:

  ```
  ![Caption text becomes the caption under the image.](assets/posts/my-diagram.png)
  ```

  A GIF works exactly the same way. Export tldraw/Excalidraw as PNG (or SVG)
  into `assets/posts/`. An image on its own line becomes a centred figure with
  the alt text as its caption.

- **Code** — fenced blocks with a language get syntax highlighting:

  ````
  ```python
  print("hello")
  ```
  ````

- **Tables, blockquotes, lists, bold/italic, links** — all standard Markdown.

- **Small-print / caveat paragraph** (the muted note style) — write the
  paragraph, then put this on the line directly under it:

  ```
  {: .note}
  ```

That's the whole system. Everything about how posts _look_ lives in `build.py`,
so if you ever want to tweak the design it's one file, one place.
