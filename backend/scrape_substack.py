#!/usr/bin/env python3
"""
Scrape Lewis Lin's Substack articles (free content only) and ingest into the knowledge base.
Processes articles in daily batches of 15 to spread the workload.

Usage:
    # Scrape the next batch of unprocessed articles
    python scrape_substack.py

    # Check progress
    python scrape_substack.py --status
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(__file__))
from ingest_knowledge import ingest_text_content, check_already_ingested, configure_genai

SUBSTACK_BASE = "https://lewislin.substack.com"
BATCH_SIZE = int(os.getenv('SCRAPE_BATCH_SIZE', '15'))
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), '.substack_progress.json')
COOKIE_FILE = os.path.join(os.path.dirname(__file__), '.substack_cookie')

def get_substack_cookie():
    """Load Substack session cookie from file or env var."""
    # Try env var first
    cookie = os.getenv('SUBSTACK_SID', '')
    if cookie:
        return cookie
    # Try cookie file
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, 'r') as f:
            return f.read().strip()
    return ''

# Full article list from sitemap (285 articles)
# Excluding obvious promotional/coaching-spots posts
ARTICLE_SLUGS = [
    "g7-design-an-elevator-for-a-skyscraper",
    "o15-metrics-for-ai-coding-agents",
    "m33n-measuring-success-for-meta-ads",
    "o16-design-an-ai-powered-voice-text",
    "m6-design-a-gardening-app-for-meta",
    "o14-how-agentic-tool-use-actually",
    "m54-design-a-neighborhood-borrowing",
    "m37n-measuring-success-for-instagrams",
    "m34-success-metrics-for-facebook",
    "d8-improve-the-etsy-discovery-experience",
    "m39-goals-and-success-metrics-for",
    "g28-hidden-signal-youtube-shorts",
    "how-do-ai-evals-work",
    "g4-design-youtube-for-kids",
    "o4-candidate-generation-without-neural",
    "m30-success-metrics-for-facebook",
    "o10-design-a-perplexity-like-search",
    "g3-design-a-product-to-improve-the",
    "o2-metrics-binary-tradeoffs-and-hidden",
    "o9-building-ai-for-humananimal-communication",
    "m19-design-a-neighborhood-connection",
    "m21-design-a-marketplace-connecting",
    "d4-grow-craigslist-revenue-by-3x",
    "m28-measuring-success-for-facebook",
    "o6-measuring-search-success-in-slack",
    "m14-design-an-emergency-response",
    "o5-binary-tradeoff-should-notions",
    "m17-create-a-fitness-tracking-feature",
    "o6-binary-tradeoff-should-3rd-party",
    "d1-fix-the-worst-airline-postbooking",
    "m52-measuring-success-for-facebooks",
    "o4-design-a-structured-data-extraction",
    "d7-root-cause-analysis-for-incorrect",
    "o3-design-a-video-recommendation",
    "m51-design-a-product-for-farmers",
    "m47-biggest-failure",
    "m11-design-a-product-to-learn-musical",
    "m29-metrics-binary-tradeoffs-and",
    "o1-design-claude-code-feature-to",
    "g21-market-size-for-language-learning",
    "m8-design-a-product-for-homework",
    "m27-metrics-for-facebook-live",
    "m27-improve-the-dmv-experience-with",
    "m7-health-product-for-meta",
    "m42-metrics-and-goals-for-whatsapp",
    "g22-how-google-docs-real-time-collaboration",
    "m5-design-a-contractor-marketplace",
    "g24-leadership-pressuring-to-deliver",
    "g17-launch-and-price-a-teleportation",
    "g13-youtubes-gen-ai-strategy",
    "g14-chatgpt-thumbs-down-feedback",
    "g1-favorite-product",
    "m31-goals-and-metrics-for-fb-notifications",
    "m10-build-an-art-platform",
    "m35-meta-ai-chatbot-goals-metrics",
    "m9-design-olympics-product",
    "m26-netflix-podcast",
    "m3-design-a-group-travel-planning",
    "m24-zoom-metrics",
    "m3-create-a-volunteering-platform",
    "m25-measuring-success-for-instagram",
    "m2-design-a-rideshare-app-for-seniors",
    "meta-23-measuring-success-for-meta",
    "ep-1-add-a-parking-spot-finder-to",
    "master-product-strategy-in-15-minutes",
    "metas-binary-tradeoff-questions-why",
    "decoding-pm-interviews-in-2024-trends",
    "o10-design-an-ai-first-data-analysis",
    "m37h-close-friends-stories-are-up",
    "m37b-should-we-optimize-for-smaller",
    # "Dear Lewis" advice columns (PM career/leadership guidance)
    "dear-lewis-how-do-i-influence-without-f68",
    "dear-lewis-im-the-fighter-in-the",
    "dear-lewis-is-ai-making-my-product",
    "dear-lewis-my-predecessor-made-promises",
    "dear-lewis-the-ceos-turned-my-peers",
    "dear-lewis-my-transparency-backfired",
    "dear-lewis-how-can-i-resolve-performance",
    "dear-lewis-are-companies-hiring-fewer-64f",
    "dear-lewis-i-think-my-star-performer",
    "dear-lewis-how-do-i-set-the-emotional",
    "dear-lewis-how-do-i-handle-a-leader",
    "dear-lewis-how-can-i-protect-myself",
    "dear-lewis-how-do-i-get-my-manager",
    "dear-lewis-is-it-too-soon-to-ask",
    "dear-lewis-how-do-i-say-no-when-my",
    "dear-lewis-why-am-i-working-so-hard",
    "dear-lewis-how-do-i-handle-someone",
    "dear-lewis-how-do-i-handle-competitive",
    "dear-lewis-how-do-i-handle-subtle",
    "dear-lewis-why-does-my-boss-not-respond",
    "dear-lewis-why-does-my-team-always",
    "dear-lewis-i-just-got-reorganized",
    "dear-lewis-is-my-instinct-to-deflect",
    "dear-lewis-how-do-i-break-the-cycle",
    "dear-lewis-how-do-i-survive-a-vibe",
    "dear-lewis-why-did-decode-and-conquer",
    "dear-lewis-i-plan-to-avoid-failure",
    "dear-lewis-i-jump-to-solutions-too",
    "dear-lewis-i-trained-my-replacement",
    "dear-lewis-my-snap-reactions-are",
    "dear-lewis-how-do-i-influence-without",
    "dear-lewis-the-ceo-wants-me-to-snitch",
    "dear-lewis-my-boss-is-sabotaging",
    "dear-lewis-what-is-the-gen-z-stare",
    "dear-lewis-how-do-i-handle-interview",
    "dear-lewis-what-did-377-leaders-reveal",
    "dear-lewis-how-will-llms-reshape",
    "dear-lewis-our-calibration-meetings",
    "dear-lewis-how-do-i-teach-my-team",
    "dear-lewis-how-do-i-transition-from",
    "dear-lewis-my-team-member-delegates",
    "dear-lewis-my-colleague-is-stealing",
    "dear-lewis-can-people-tell-when-im",
    "dear-lewis-my-brilliance-is-being",
    "dear-lewis-how-do-i-answer-the-weakness",
    "dear-lewis-how-do-i-pivot-from-traditional",
    "dear-lewis-my-poor-performer-says",
    "dear-lewis-what-do-i-do-when-the",
    "dear-lewis-why-is-my-team-leaving",
    "dear-lewis-how-do-i-demonstrate-value",
    "dear-lewis-why-do-i-keep-failing",
    "dear-lewis-my-team-wants-warmth-but",
    "dear-lewis-how-do-i-get-a-director",
    "dear-lewis-how-do-i-get-the-courage",
    "dear-lewis-how-do-i-deal-with-a-narcissist",
    "dear-lewis-i-get-emotionally-flooded",
    "dear-lewis-why-is-my-resume-getting",
    "dear-lewis-im-killing-myself-at-work",
    "dear-lewis-these-bizarre-new-interview",
    "dear-lewis-can-i-use-notes-or-ai",
    "dear-lewis-ai-is-reshaping-product",
    "dear-lewis-my-boss-is-threatened",
    "dear-lewis-my-ceo-wants-ai-to-do",
    "dear-lewis-engineers-are-making-magic",
    "dear-lewis-my-critical-performer",
    "dear-lewis-i-hate-overcommunicating",
    "dear-lewis-im-afraid-of-rejection",
    "dear-lewis-my-team-member-is-paralyzed",
    "dear-lewis-my-boss-plays-power-games",
    "dear-lewis-how-do-i-build-ai-products",
    "dear-lewis-my-team-has-ai-brain-fog",
    "dear-lewis-i-inherited-a-struggling",
    "dear-lewis-im-overly-deferential",
    "dear-lewis-im-stuck-in-neutral-how",
    "dear-lewis-i-feel-like-a-fraud-how",
    "dear-lewis-my-company-is-toxic-how",
    "dear-lewis-ive-optimized-my-lifeso",
    "dear-lewis-my-retreat-taught-me-to",
    "dear-lewis-how-do-i-get-my-team-to",
    "dear-lewis-how-do-i-fix-it-when-an",
    "dear-lewis-how-do-i-handle-false",
    "dear-lewis-how-not-to-take-things",
    "dear-lewis-how-can-i-network-effectively",
    "dear-lewis-how-can-i-respond-to-my",
    "dear-lewis-how-can-i-explain-a-small",
    "dear-lewis-how-to-handle-an-employees",
    "dear-lewis-how-to-handle-a-hire-who",
    "dear-lewis-how-can-i-become-more",
    "dear-lewis-is-my-boss-micromanaging",
    "dear-lewis-how-much-small-talk-is",
    "dear-lewis-how-to-balance-self-promotion",
    "dear-lewis-am-i-to-blame-for-hiring",
    "dear-lewis-what-mindset-do-leaders",
    "dear-lewis-are-companies-hiring-fewer",
    "dear-lewis-whats-the-best-approach",
    "dear-lewis-how-to-deal-with-a-suffocating",
    "dear-lewis-is-it-okay-to-tell-white",
    "dear-lewis-can-a-manager-ask-about",
    "dear-lewis-how-do-i-talk-to-my-senior",
    "dear-lewis-how-can-i-devise-a-compelling",
    "dear-lewis-can-hrtechs-x-ray-vision",
    "dear-lewis-how-often-should-i-ask",
    "dear-lewis-how-do-i-overcome-my-own",
    "dear-lewis-how-do-i-demonstrate-executive",
    "dear-lewis-should-i-sue-or-settle",
    # General PM content
    "the-narcissist-boss-survival-guide",
    "the-corporate-drone-trap-why-your",
    "fighting-off-workplace-predators",
    "ai-made-me-ordinary",
    "the-self-confidence-paradox-when",
    "how-to-plan-your-career-for-the-ai",
    "what-did-a-377-leader-survey-reveal",
    "helping-a-manager-who-is-unsure-about",
    "my-coworker-sighs-and-argues-when",
    # ML/AI deep dives (useful for technical PM questions)
    "part-9-what-breaks-at-scale",
    "part-8-batch-size-learning-rate-and",
    "part-7-the-interconnect-bottleneck",
    "part-6-tensor-parallelism-splitting",
    "part-5-when-one-chip-isnt-enough",
    "part-4-the-memory-hierarchy-mountain",
    "part-3-meet-the-hardware-gpu-vs-tpu",
    "part-2-why-training-is-a-memory-game",
    "part-1-what-happens-when-you-train",
    "part-22-navigate-the-ai-workforce",
    "part-12-navigate-the-ai-workforce",
]


class ArticleHTMLParser(HTMLParser):
    """Extract article text content from Substack HTML."""

    def __init__(self):
        super().__init__()
        self.in_article = False
        self.article_depth = 0
        self.in_paywall = False
        self.in_skip_tag = False
        self.skip_depth = 0
        self.text_parts = []
        self.title = ""
        self.in_title = False

    SKIP_TAGS = {'script', 'style', 'noscript', 'svg'}
    VOID_TAGS = {'br', 'hr', 'img', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'source', 'track', 'wbr'}

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get('class', '')

        if tag in self.SKIP_TAGS:
            self.in_skip_tag = True
            self.skip_depth += 1
            return

        if 'body' in classes and 'markup' in classes:
            self.in_article = True
            self.article_depth = 1
        elif self.in_article and tag not in self.VOID_TAGS:
            self.article_depth += 1

        if 'paywall' in classes or 'subscription-widget' in classes:
            self.in_paywall = True
            self.in_article = False

        if tag == 'h1' and 'post-title' in classes:
            self.in_title = True

        if self.in_article and not self.in_paywall and not self.in_skip_tag:
            if tag in ('h1', 'h2', 'h3', 'h4'):
                self.text_parts.append('\n\n## ')
            elif tag == 'p':
                self.text_parts.append('\n\n')
            elif tag == 'li':
                self.text_parts.append('\n- ')
            elif tag == 'blockquote':
                self.text_parts.append('\n\n> ')

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self.in_skip_tag:
            self.skip_depth -= 1
            if self.skip_depth <= 0:
                self.in_skip_tag = False
                self.skip_depth = 0
            return

        if self.in_title and tag == 'h1':
            self.in_title = False

        if self.in_article and tag not in self.VOID_TAGS:
            self.article_depth -= 1
            if self.article_depth <= 0:
                self.in_article = False

    def handle_data(self, data):
        if self.in_skip_tag:
            return
        if self.in_title:
            self.title = data.strip()
        elif self.in_article and not self.in_paywall:
            self.text_parts.append(data)

    def get_text(self):
        return ''.join(self.text_parts).strip()


def fetch_page(url):
    """Fetch a URL with optional authentication cookie."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    cookie = get_substack_cookie()
    if cookie:
        headers['Cookie'] = f'substack.sid={cookie}'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"    Error fetching {url}: {e}")
        return None


def parse_article(html):
    """Parse article HTML and extract title + text content."""
    parser = ArticleHTMLParser()
    parser.feed(html)
    return parser.title, parser.get_text()


def load_progress():
    """Load scraping progress from file."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'last_index': 0, 'scraped': [], 'skipped': [], 'failed': []}


def save_progress(progress):
    """Save scraping progress to file."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def show_status():
    """Show current scraping status."""
    progress = load_progress()
    total = len(ARTICLE_SLUGS)
    scraped = len(progress.get('scraped', []))
    skipped = len(progress.get('skipped', []))
    failed = len(progress.get('failed', []))
    remaining = total - progress.get('last_index', 0)
    days_left = (remaining + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"Substack Scraping Progress:")
    print(f"  Total articles: {total}")
    print(f"  Scraped:        {scraped}")
    print(f"  Skipped (short):{skipped}")
    print(f"  Failed:         {failed}")
    print(f"  Remaining:      {remaining}")
    print(f"  Days to finish: {days_left} (at {BATCH_SIZE}/day)")


def scrape_batch():
    """Scrape the next batch of articles."""
    progress = load_progress()
    start_idx = progress.get('last_index', 0)

    if start_idx >= len(ARTICLE_SLUGS):
        print("All articles have been processed!")
        show_status()
        return 0

    end_idx = min(start_idx + BATCH_SIZE, len(ARTICLE_SLUGS))
    batch = ARTICLE_SLUGS[start_idx:end_idx]

    print(f"[{datetime.now().isoformat()}] Scraping batch: articles {start_idx+1}-{end_idx} of {len(ARTICLE_SLUGS)}")

    ingested_count = 0
    for i, slug in enumerate(batch):
        url = f"{SUBSTACK_BASE}/p/{slug}"
        source_name = f"Substack: {slug}"

        # Skip if already in DB
        if check_already_ingested(source_name):
            print(f"  [{start_idx+i+1}] {slug} — already ingested, skipping")
            progress.setdefault('skipped', []).append(slug)
            continue

        print(f"  [{start_idx+i+1}] Fetching: {slug}")
        html = fetch_page(url)
        if not html:
            progress.setdefault('failed', []).append(slug)
            continue

        title, text = parse_article(html)
        if not text or len(text) < 200:
            print(f"    Skipped — too little free content ({len(text)} chars)")
            progress.setdefault('skipped', []).append(slug)
            continue

        display_name = f"Substack: {title}" if title else source_name
        try:
            count = ingest_text_content(text, display_name, source_type='article')
            if count > 0:
                ingested_count += count
                progress.setdefault('scraped', []).append(slug)
                print(f"    Ingested ({count} chunks)")
        except Exception as e:
            print(f"    Error ingesting: {e}")
            progress.setdefault('failed', []).append(slug)

        time.sleep(1.5)  # Rate limiting

    progress['last_index'] = end_idx
    save_progress(progress)

    print(f"\nBatch complete! Ingested {ingested_count} chunks from this batch.")
    remaining = len(ARTICLE_SLUGS) - end_idx
    if remaining > 0:
        print(f"  {remaining} articles remaining (~{(remaining + BATCH_SIZE - 1) // BATCH_SIZE} more days)")
    else:
        print("  All articles processed!")

    return ingested_count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape Lewis Lin Substack articles')
    parser.add_argument('--status', action='store_true', help='Show scraping progress')
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        scrape_batch()
