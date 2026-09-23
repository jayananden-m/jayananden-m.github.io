#!/usr/bin/env python3
"""
build.py — turns Markdown posts into styled HTML for the portfolio blog.

Workflow
--------
1. Write a post as Markdown in  posts/<slug>.md  (see posts/ for an example).
2. Drop any images / GIFs in     assets/posts/  and reference them in the post.
3. Run:  python build.py
4. Commit and push. GitHub Pages serves the generated .html files.

What it produces
----------------
- writing-<slug>.html   one styled article page per post
- writing.html          the index that lists every (non-draft) post

The design (fonts, colours, layout, reading-progress bar) is defined once in
this file, so every post looks consistent and you never touch HTML by hand.

You only ever edit files in  posts/  and  assets/posts/ .
Nothing here touches index.html or support.js.
"""

from __future__ import annotations

import html
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import markdown
import yaml
from pygments.formatters import HtmlFormatter

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
POSTS_DIR = ROOT / "posts"
WORDS_PER_MIN = 220  # for auto read-time estimates

# --------------------------------------------------------------------------
# Design system — the single source of truth for how the blog looks.
# These are lifted straight from your existing pages.
# --------------------------------------------------------------------------
TOKENS = (
    "--paper:#faf6f1;--rose:#b8574a;--rose-dark:#9c4438;"
    "--ink:#3a3446;--slate:#6f6880;--hair:#e6ddd3;--code-bg:#f3ece3;"
)

FONTS_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    "family=JetBrains+Mono:wght@400;500;600&"
    "family=Newsreader:opsz,wght@6..72,400;6..72,500&"
    "family=Space+Grotesk:wght@400;500;600&display=swap\">"
)

# Custom tuned dark syntax highlighting CSS for code blocks
_PYGMENTS_CSS = """
  /* Code container & syntax highlighting */
  .post-body .codehilite {
    position: relative;
    margin: 28px 0;
    background: #181520;
    border: 1px solid #2d2838;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 12px 28px -8px rgba(24, 21, 32, 0.28), 0 2px 6px -1px rgba(24, 21, 32, 0.15);
  }
  .post-body .codehilite pre {
    margin: 0;
    padding: 16px 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13.5px;
    line-height: 1.65;
    color: #e8e3f0;
    background: transparent;
    overflow-x: auto;
    -webkit-font-smoothing: antialiased;
    tab-size: 4;
  }
  .post-body .codehilite pre code {
    font-family: inherit;
    font-size: inherit;
    color: inherit;
    background: transparent;
    padding: 0;
    border: none;
  }
  .post-body .codehilite pre::-webkit-scrollbar { height: 7px; }
  .post-body .codehilite pre::-webkit-scrollbar-track { background: #131019; }
  .post-body .codehilite pre::-webkit-scrollbar-thumb { background: #352e42; border-radius: 4px; }
  .post-body .codehilite pre::-webkit-scrollbar-thumb:hover { background: #4e4460; }

  /* Code header bar */
  .code-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 9px 14px;
    background: #120f18;
    border-bottom: 1px solid #252030;
    user-select: none;
  }
  .code-dots {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .code-dots span {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    display: inline-block;
  }
  .code-dots span:nth-child(1) { background: #ff5f56; opacity: 0.85; }
  .code-dots span:nth-child(2) { background: #ffbd2e; opacity: 0.85; }
  .code-dots span:nth-child(3) { background: #27c93f; opacity: 0.85; }

  .copy-btn {
    all: unset;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    cursor: pointer;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #9d94b0;
    padding: 3px 8px;
    border-radius: 5px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    transition: all 0.2s ease;
  }
  .copy-btn:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.12);
    border-color: rgba(255, 255, 255, 0.2);
  }
  .copy-btn.copied {
    color: #5af78e;
    border-color: rgba(90, 247, 142, 0.4);
    background: rgba(90, 247, 142, 0.1);
  }

  /* Token highlighting */
  .post-body .codehilite .c,
  .post-body .codehilite .ch,
  .post-body .codehilite .cm,
  .post-body .codehilite .c1,
  .post-body .codehilite .cs { color: #7f7791; font-style: italic; }

  .post-body .codehilite .k,
  .post-body .codehilite .kd,
  .post-body .codehilite .kn,
  .post-body .codehilite .kp,
  .post-body .codehilite .kr,
  .post-body .codehilite .kt { color: #f2777a; font-weight: 500; }

  .post-body .codehilite .s,
  .post-body .codehilite .sa,
  .post-body .codehilite .sb,
  .post-body .codehilite .sc,
  .post-body .codehilite .dl,
  .post-body .codehilite .sd,
  .post-body .codehilite .s2,
  .post-body .codehilite .se,
  .post-body .codehilite .sh,
  .post-body .codehilite .si,
  .post-body .codehilite .sx,
  .post-body .codehilite .sr,
  .post-body .codehilite .s1,
  .post-body .codehilite .ss { color: #a6e22e; }

  .post-body .codehilite .na,
  .post-body .codehilite .nf,
  .post-body .codehilite .fm { color: #67b0e8; font-weight: 500; }

  .post-body .codehilite .m,
  .post-body .codehilite .mb,
  .post-body .codehilite .mf,
  .post-body .codehilite .mh,
  .post-body .codehilite .mi,
  .post-body .codehilite .il,
  .post-body .codehilite .mo { color: #e5c07b; }

  .post-body .codehilite .nb,
  .post-body .codehilite .nc,
  .post-body .codehilite .no,
  .post-body .codehilite .nd { color: #e59866; }

  .post-body .codehilite .o,
  .post-body .codehilite .ow,
  .post-body .codehilite .p { color: #c4bdcf; }

  .post-body .codehilite .ge { font-style: italic; }
  .post-body .codehilite .gs { font-weight: bold; }
  .post-body .codehilite .gp { color: #7f7791; user-select: none; }
  .post-body .codehilite .go { color: #b0a8bd; }
  .post-body .codehilite .gt { color: #f2777a; }
  .post-body .codehilite .err { color: #f2777a; }
"""

# One stylesheet, shared shape for both templates. {extra} lets the article page
# add the reading-progress rules without duplicating everything.
BASE_CSS = """
  *{box-sizing:border-box;}
  body{margin:0;background:var(--paper);color:var(--ink);
       font-family:'Space Grotesk',sans-serif;
       -webkit-font-smoothing:antialiased;}
  a{color:var(--rose);text-decoration:none;transition:color .2s ease;}
  a:hover{color:var(--rose-dark);}
  .wrap{min-height:100vh;background:var(--paper);}

  /* sticky header */
  header{position:sticky;top:0;z-index:5;display:flex;align-items:center;
    justify-content:space-between;gap:16px;padding:14px 28px;
    background:color-mix(in srgb,var(--paper) 86%,transparent);
    backdrop-filter:blur(10px);border-bottom:1px solid var(--hair);}
  header .back{display:inline-flex;align-items:center;gap:9px;
    font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.03em;
    color:var(--slate);}
  header .back:hover{color:var(--rose);}
  header .back .arrow{display:inline-block;color:var(--rose);
    transition:transform .25s cubic-bezier(.2,.7,.2,1);}
  header .back:hover .arrow{transform:translateX(-3px);}
  header .who{font-family:'JetBrains Mono',monospace;font-size:11px;
    letter-spacing:.14em;text-transform:uppercase;color:var(--slate);}

  main{margin:0 auto;padding:72px 28px 110px;}
  .kicker{margin:0 0 18px;font-family:'JetBrains Mono',monospace;
    font-size:11px;letter-spacing:.06em;color:var(--slate);}
  .kicker .sep{color:var(--rose);}

  /* tags */
  .tag-pill{display:inline-flex;align-items:center;font-family:'JetBrains Mono',monospace;
    font-size:11px;letter-spacing:.02em;padding:3px 8px;border-radius:6px;
    border:1px solid var(--hair);color:var(--slate);background:var(--code-bg);
    text-decoration:none;transition:all .2s ease;line-height:1.4;white-space:nowrap;}
  .tag-pill::before{content:"#";color:var(--rose);margin-right:2px;opacity:.7;}
  .tag-pill:hover{border-color:var(--rose);color:var(--rose-dark);
    background:color-mix(in srgb,var(--rose) 6%,var(--paper));}
"""

INDEX_CSS = """
  main{max-width:840px;}
  .kicker.big{font-size:12px;letter-spacing:.04em;}
  h1.title{margin:0 0 16px;font-family:'Newsreader',serif;font-weight:400;
    font-size:60px;line-height:1.02;letter-spacing:-.02em;color:var(--ink);}
  p.intro{margin:0 0 40px;max-width:52ch;font-family:'Newsreader',serif;
    font-size:20px;line-height:1.6;color:var(--slate);text-wrap:pretty;}

  /* tag filter buttons */
  .tag-filters{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 44px;align-items:center;}
  .filter-btn{all:unset;display:inline-flex;align-items:center;gap:6px;
    padding:5px 12px;border-radius:20px;border:1px solid var(--hair);
    background:transparent;color:var(--slate);font-family:'JetBrains Mono',monospace;
    font-size:11.5px;letter-spacing:.03em;cursor:pointer;
    transition:all .2s cubic-bezier(.2,.7,.2,1);}
  .filter-btn::before{content:"#";color:var(--rose);opacity:.7;}
  .filter-btn[data-tag="all"]::before{content:"";display:none;}
  .filter-btn .count{font-size:10px;opacity:.75;}
  .filter-btn:hover{border-color:var(--rose);color:var(--rose);
    background:color-mix(in srgb,var(--rose) 5%,var(--paper));}
  .filter-btn.active{background:var(--rose);color:#fff;border-color:var(--rose);}
  .filter-btn.active::before{color:#fff;opacity:1;}
  .filter-btn.active .count{color:#fff;opacity:.9;}

  .list{display:flex;flex-direction:column;}
  a.row{display:block;padding:28px 0;border-top:1px solid var(--hair);
    color:inherit;transition:background-color .3s ease,padding-left .3s cubic-bezier(.2,.7,.2,1);}
  a.row:last-child{border-bottom:1px solid var(--hair);}
  a.row:hover{padding-left:10px;background:color-mix(in srgb,var(--rose) 4%,transparent);}
  a.row .meta-row{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 10px;flex-wrap:wrap;}
  a.row .meta{margin:0;font-family:'JetBrains Mono',monospace;
    font-size:11px;letter-spacing:.06em;color:var(--slate);}
  a.row .row-tags{display:inline-flex;flex-wrap:wrap;gap:6px;}
  a.row h2{margin:0 0 8px;font-family:'Newsreader',serif;font-weight:400;
    font-size:30px;line-height:1.2;color:var(--ink);transition:color .25s ease;}
  a.row:hover h2{color:var(--rose);}
  a.row .dek{margin:0;max-width:56ch;font-size:15px;line-height:1.65;
    color:var(--slate);text-wrap:pretty;}

  .no-posts{display:none;padding:48px 0;text-align:center;font-family:'Space Grotesk',sans-serif;color:var(--slate);font-size:15px;}
  .no-posts .clear-filter{display:inline-block;margin-top:12px;color:var(--rose);font-family:'JetBrains Mono',monospace;font-size:12px;cursor:pointer;}

  @media (prefers-reduced-motion:reduce){
    a.row,a.row h2,header .back .arrow,.filter-btn,.tag-pill{transition:none!important;}
  }
  @media (max-width:640px){
    h1.title{font-size:42px;} main{padding:48px 22px 90px;}
    .tag-filters{margin-bottom:32px;}
    p.intro{margin-bottom:32px;}
  }
"""

ARTICLE_CSS = """
  main{max-width:840px;}
  .article-meta{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 18px;flex-wrap:wrap;}
  .article-meta .kicker{margin:0;}
  .article-tags{display:inline-flex;flex-wrap:wrap;gap:6px;}
  h1.title{margin:0 0 24px;font-family:'Newsreader',serif;font-weight:400;
    font-size:46px;line-height:1.1;letter-spacing:-.02em;color:var(--ink);}
  p.lede{margin:0 0 48px;font-family:'Newsreader',serif;font-size:20px;
    line-height:1.6;color:var(--slate);text-wrap:pretty;}

  /* reading-progress bar — pure CSS, degrades to a harmless empty strip */
  #read-progress{position:fixed;top:0;left:0;height:3px;width:100%;
    transform-origin:0 50%;transform:scaleX(0);background:var(--rose);
    box-shadow:0 0 8px 0 rgba(184,87,74,.55);z-index:20;}
  @supports (animation-timeline:scroll()){
    #read-progress{animation:read-fill linear;animation-timeline:scroll(root);}
  }
  @keyframes read-fill{from{transform:scaleX(0);}to{transform:scaleX(1);}}

  /* ---- article body: markdown maps onto these ---- */
  .post-body{font-size:16.5px;line-height:1.75;color:var(--ink);}
  .post-body > *:first-child{margin-top:0;}
  .post-body p{margin:0 0 24px;}
  .post-body h2{margin:44px 0 18px;font-family:'Newsreader',serif;
    font-weight:500;font-size:28px;line-height:1.25;color:var(--ink);}
  .post-body h3{margin:36px 0 14px;font-family:'Newsreader',serif;
    font-weight:500;font-size:22px;line-height:1.3;color:var(--ink);}
  .post-body ul,.post-body ol{margin:0 0 24px;padding-left:1.3em;}
  .post-body li{margin:0 0 8px;}
  .post-body li::marker{color:var(--rose);}
  .post-body strong{font-weight:600;color:var(--ink);}
  .post-body blockquote{margin:0 0 24px;padding:4px 0 4px 20px;
    border-left:3px solid var(--rose);color:var(--slate);font-style:italic;}
  .post-body blockquote p{margin:0 0 10px;}
  .post-body hr{border:none;border-top:1px solid var(--hair);margin:40px 0;}

  /* small-print / caveat paragraph: write  {: .note}  under it in markdown */
  .post-body .note{color:var(--slate);font-size:15px;line-height:1.65;}

  /* images & diagrams (tldraw / Excalidraw exports, GIFs) */
  .post-body figure{margin:36px 0;}
  .post-body figure img,.post-body p img{display:block;max-width:100%;
    height:auto;margin:0 auto;border:1px solid var(--hair);border-radius:10px;
    background:#fff;}
  .post-body figcaption{margin-top:12px;text-align:center;
    font-family:'JetBrains Mono',monospace;font-size:11.5px;letter-spacing:.02em;
    color:var(--slate);}

  /* inline code */
  .post-body code{font-family:'JetBrains Mono',monospace;font-size:.88em;}
  .post-body :not(pre) > code{background:color-mix(in srgb,var(--rose) 8%,var(--paper));
    border:1px solid color-mix(in srgb,var(--rose) 20%,var(--hair));border-radius:5px;padding:.15em .42em;
    color:var(--rose-dark);font-weight:500;}

  /* tables */
  .post-body table{width:100%;border-collapse:collapse;margin:0 0 28px;
    font-size:14.5px;}
  .post-body th,.post-body td{padding:9px 12px;border-bottom:1px solid var(--hair);
    text-align:left;}
  .post-body th{font-family:'JetBrains Mono',monospace;font-size:11px;
    letter-spacing:.04em;text-transform:uppercase;color:var(--slate);
    border-bottom:1.5px solid var(--hair);}

  .post-footer{margin-top:56px;padding-top:28px;border-top:1px solid var(--hair);
    display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;}
  .post-footer a.back-link{font-family:'JetBrains Mono',monospace;font-size:12px;
    letter-spacing:.03em;color:var(--rose);}
  .post-footer .footer-tags{display:inline-flex;align-items:center;gap:8px;flex-wrap:wrap;}
  .post-footer .footer-tags-label{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--slate);letter-spacing:.04em;}
  @media (max-width:640px){
    h1.title{font-size:34px;} main{padding:48px 22px 90px;}
  }
""" + "\n" + _PYGMENTS_CSS

ARTICLE_SCRIPT = """  <script>
  (function() {
    document.querySelectorAll('.post-body .codehilite, .post-body pre').forEach(function(block) {
      if (block.tagName === 'PRE' && block.closest('.codehilite')) return;
      
      var isHilite = block.classList.contains('codehilite');
      var pre = isHilite ? block.querySelector('pre') : block;
      if (!pre) return;

      var header = document.createElement('div');
      header.className = 'code-header';
      header.innerHTML = '<div class="code-dots"><span></span><span></span><span></span></div>' +
        '<button class="copy-btn" type="button" aria-label="Copy code">' +
        '<svg class="copy-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>' +
        '<span class="copy-text">Copy</span>' +
        '</button>';

      if (isHilite) {
        block.insertBefore(header, pre);
      } else {
        var wrapper = document.createElement('div');
        wrapper.className = 'codehilite';
        block.parentNode.insertBefore(wrapper, block);
        wrapper.appendChild(header);
        wrapper.appendChild(block);
      }

      var btn = header.querySelector('.copy-btn');
      btn.addEventListener('click', async function() {
        var codeEl = pre.querySelector('code') || pre;
        var text = codeEl.innerText.replace(/\\n$/, '');
        try {
          await navigator.clipboard.writeText(text);
          btn.classList.add('copied');
          btn.querySelector('.copy-text').textContent = 'Copied!';
          btn.querySelector('.copy-icon').outerHTML = '<svg class="copy-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
          setTimeout(function() {
            btn.classList.remove('copied');
            btn.querySelector('.copy-text').textContent = 'Copy';
            btn.querySelector('.copy-icon').outerHTML = '<svg class="copy-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';
          }, 2000);
        } catch (err) {}
      });
    });
  })();
  </script>"""


# --------------------------------------------------------------------------
# Page templates
# --------------------------------------------------------------------------
def _page(title, css, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
{FONTS_LINK}
<style>{BASE_CSS}{css}</style>
</head>
<body>
<div class="wrap" style="{TOKENS}">
{body}
</div>
</body>
</html>
"""


def render_article(post):
    tags = post.get("tags") or []
    tags_header_html = ""
    footer_tags_html = ""
    if tags:
        tag_pills = "".join(
            f'<a class="tag-pill" href="writing.html?tag={html.escape(t)}">{html.escape(t)}</a>'
            for t in tags
        )
        tags_header_html = f'<div class="article-tags">{tag_pills}</div>'
        footer_tags_html = f'<div class="footer-tags"><span class="footer-tags-label">Tags:</span>{tag_pills}</div>'

    meta_content = f"""    <div class="article-meta">
      <p class="kicker">{html.escape(post['meta_line'])}</p>
      {tags_header_html}
    </div>"""

    body = f"""  <div id="read-progress" aria-hidden="true"></div>
  <header>
    <a class="back" href="writing.html"><span class="arrow">&larr;</span> all writing</a>
    <span class="who">Jayananden M</span>
  </header>
  <main>
{meta_content}
    <h1 class="title">{html.escape(post['title'])}</h1>
    {f'<p class="lede">{html.escape(post["subtitle"])}</p>' if post.get("subtitle") else ''}
    <article class="post-body">
{post['html']}
    </article>
    <div class="post-footer">
      <a class="back-link" href="writing.html">&larr; all writing</a>
      {footer_tags_html}
    </div>
  </main>
{ARTICLE_SCRIPT}"""
    return _page(post["title"], ARTICLE_CSS, body)


def render_index(posts):
    tag_counts = {}
    for p in posts:
        for t in p.get("tags", []):
            tag_counts[t] = tag_counts.get(t, 0) + 1

    tag_filter_html = ""
    if tag_counts:
        filter_buttons = [
            f'<button class="filter-btn active" data-tag="all">all <span class="count">({len(posts)})</span></button>'
        ]
        for tag, count in sorted(tag_counts.items(), key=lambda x: (-x[1], x[0])):
            filter_buttons.append(
                f'<button class="filter-btn" data-tag="{html.escape(tag)}">{html.escape(tag)} <span class="count">({count})</span></button>'
            )
        tag_filter_html = f"""    <div class="tag-filters" id="tag-filters" aria-label="Filter posts by tag">
      {''.join(filter_buttons)}
    </div>"""

    rows = []
    for p in posts:
        tags = p.get("tags", [])
        tags_attr = html.escape(",".join(tags))
        tags_html = ""
        if tags:
            tag_spans = "".join(
                f'<span class="tag-pill" data-tag="{html.escape(t)}">{html.escape(t)}</span>'
                for t in tags
            )
            tags_html = f'<div class="row-tags">{tag_spans}</div>'

        rows.append(f"""      <a class="row" href="{p['out_name']}" data-tags="{tags_attr}">
        <div class="meta-row">
          <p class="meta">{html.escape(p['meta_line'])}</p>
          {tags_html}
        </div>
        <h2>{html.escape(p['title'])}</h2>
        <p class="dek">{html.escape(p['summary'])}</p>
      </a>""")

    script = """  <script>
  (function() {
    const filterBtns = document.querySelectorAll('.filter-btn');
    const rows = document.querySelectorAll('.list a.row');
    const emptyState = document.getElementById('no-posts');

    function applyFilter(selectedTag) {
      let visibleCount = 0;
      rows.forEach(row => {
        const rawTags = row.getAttribute('data-tags') || '';
        const tags = rawTags.split(',').filter(Boolean);
        const match = (selectedTag === 'all' || tags.includes(selectedTag));
        row.style.display = match ? 'block' : 'none';
        if (match) visibleCount++;
      });

      filterBtns.forEach(btn => {
        const btnTag = btn.getAttribute('data-tag');
        btn.classList.toggle('active', btnTag === selectedTag);
      });

      if (emptyState) {
        emptyState.style.display = visibleCount === 0 ? 'block' : 'none';
      }

      const newUrl = selectedTag === 'all'
        ? window.location.pathname
        : window.location.pathname + '?tag=' + encodeURIComponent(selectedTag);
      history.replaceState(null, '', newUrl);
    }

    filterBtns.forEach(btn => {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        applyFilter(this.getAttribute('data-tag'));
      });
    });

    document.querySelectorAll('.row-tags .tag-pill').forEach(tagEl => {
      tagEl.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        const tag = this.getAttribute('data-tag');
        if (tag) applyFilter(tag);
      });
    });

    const clearBtn = document.querySelector('.clear-filter');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => applyFilter('all'));
    }

    const params = new URLSearchParams(window.location.search);
    const initialTag = params.get('tag') || (window.location.hash ? window.location.hash.slice(1) : null);
    if (initialTag && Array.from(filterBtns).some(b => b.getAttribute('data-tag') === initialTag)) {
      applyFilter(initialTag);
    }
  })();
  </script>"""

    body = f"""  <header>
    <a class="back" href="index.html"><span class="arrow">&larr;</span> back to the road</a>
    <span class="who">Jayananden M &middot; Writing</span>
  </header>
  <main>
    <p class="kicker big"><span class="sep">//</span> writing</p>
    <h1 class="title">Notes from the platform</h1>
    <p class="intro">Notes on machine learning systems and the infrastructure around them.</p>
{tag_filter_html}
    <div class="list">
{chr(10).join(rows)}
    </div>
    <div class="no-posts" id="no-posts">
      <p>No posts tagged with this topic yet.</p>
      <span class="clear-filter">&larr; Show all posts</span>
    </div>
  </main>
{script if tag_counts else ''}"""
    return _page("Jayananden M · Writing", INDEX_CSS, body)


# --------------------------------------------------------------------------
# Markdown → HTML
# --------------------------------------------------------------------------
_FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# Turn a paragraph that is just an image into a <figure> with a caption.
_IMG_P_RE = re.compile(
    r'<p>\s*(<img\b[^>]*?alt="(?P<alt>[^"]*)"[^>]*>)\s*</p>', re.DOTALL
)


def _img_to_figure(m):
    alt = m.group("alt").strip()
    cap = f"<figcaption>{alt}</figcaption>" if alt else ""
    return f"<figure>{m.group(1)}{cap}</figure>"


def make_md():
    return markdown.Markdown(
        extensions=[
            "extra",        # tables, fenced code, attr_list, footnotes, def lists
            "codehilite",   # pygments highlighting
            "sane_lists",
            "smarty",       # curly quotes and em/en dashes automatically
        ],
        extension_configs={
            "codehilite": {"css_class": "codehilite", "guess_lang": False},
        },
    )


def read_time(text):
    words = len(re.findall(r"\w+", text))
    return f"{max(1, round(words / WORDS_PER_MIN))} min"


def first_paragraph_text(md_body):
    for block in md_body.strip().split("\n\n"):
        b = block.strip()
        if b and not b.startswith(("#", "!", "```", "|", ">", "-", "*")):
            b = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", b)  # [text](url) -> text
            return re.sub(r"[*_`\[\]]", "", b).replace("\n", " ").strip()
    return ""


def parse_post(path: Path):
    raw = path.read_text(encoding="utf-8")
    m = _FRONT_RE.match(raw)
    front, body = ({}, raw)
    if m:
        front = yaml.safe_load(m.group(1)) or {}
        body = raw[m.end():]

    if front.get("draft"):
        return None

    title = front.get("title") or path.stem.replace("-", " ").title()
    slug = str(front.get("slug") or path.stem)

    md = make_md()
    html_body = md.convert(body)
    html_body = _IMG_P_RE.sub(_img_to_figure, html_body)
    # indent article html so the source is readable
    html_body = "\n".join("      " + ln if ln else ln for ln in html_body.split("\n"))

    date_str = str(front.get("date") or "")
    rt = str(front.get("read") or read_time(body))
    if rt and not rt.endswith("min") and rt.isdigit():
        rt = f"{rt} min"
    meta_line = " · ".join(x for x in (date_str, rt) if x)

    raw_tags = front.get("tags")
    tags = []
    if isinstance(raw_tags, list):
        tags = [str(t).strip() for t in raw_tags if str(t).strip()]
    elif isinstance(raw_tags, str):
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()]

    summary = (front.get("summary") or front.get("subtitle")
               or first_paragraph_text(body))
    summary = re.sub(r"\s+", " ", str(summary)).strip()
    if len(summary) > 240:
        summary = summary[:237].rstrip() + "…"

    # sort key: explicit `sort:` date wins, else file mtime (newest first).
    # Always produce a timezone-aware datetime so the list is always sortable —
    # YAML turns an unquoted 2026-08-29 into a naive date/datetime, and the
    # mtime fallback is aware, so the two must be reconciled here.
    raw_sort = front.get("sort")
    sort_key = None
    if raw_sort is not None:
        if isinstance(raw_sort, datetime):
            sort_key = raw_sort
        elif isinstance(raw_sort, date):
            sort_key = datetime(raw_sort.year, raw_sort.month, raw_sort.day)
        else:
            try:
                sort_key = datetime.fromisoformat(str(raw_sort))
            except ValueError:
                sort_key = None
        if sort_key is not None and sort_key.tzinfo is None:
            sort_key = sort_key.replace(tzinfo=timezone.utc)
    if sort_key is None:
        sort_key = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

    return {
        "title": title,
        "slug": slug,
        "out_name": f"writing-{slug}.html",
        "subtitle": front.get("subtitle"),
        "summary": summary,
        "meta_line": meta_line or rt,
        "tags": tags,
        "html": html_body,
        "sort_key": sort_key,
    }


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
def build():
    if not POSTS_DIR.exists():
        sys.exit("No posts/ directory found. Create posts/ and add a .md file.")

    posts = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        # posts/ can hold non-post markdown too: README, or drafts named with a
        # leading _ or . — skip those rather than publishing them.
        if path.name.lower() == "readme.md" or path.name[0] in "_.":
            continue
        post = parse_post(path)
        if post is None:
            print(f"  skip (draft)  {path.name}")
            continue
        (ROOT / post["out_name"]).write_text(render_article(post), encoding="utf-8")
        print(f"  article       {path.name}  ->  {post['out_name']}")
        posts.append(post)

    posts.sort(key=lambda p: p["sort_key"], reverse=True)  # newest first
    (ROOT / "writing.html").write_text(render_index(posts), encoding="utf-8")
    print(f"  index         writing.html  ({len(posts)} post"
          f"{'' if len(posts) == 1 else 's'})")
    print("Done.")


if __name__ == "__main__":
    build()