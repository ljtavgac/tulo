# Tulo Page Templates — Build Spec for Claude Code

Every template below includes a **Competitive Gap** note — a specific,
verified weakness on major competitor sites (Allrecipes, Serious Eats,
Food Network) that this template is designed to directly counter.

---

## 1. Recipe Page
**What it is:** A single dish's recipe — the core content unit of the site, mapped from `page_purpose: seo_target`, template_type: `recipe_or_dish` rows.

**Competitive gap addressed:** Competitor sites bury the actual recipe under long personal-story preambles — a pain point so widespread that third-party tools (RecipeStripper and similar) exist solely to strip competitor pages down to just the recipe. Sites are also called out repeatedly for heavy ad load and autoplay video sidebars hurting the cooking experience.

**Recommended content sections:**
- Recipe title + hero photo
- **Ingredients and instructions visible immediately — no scrolling past a story to reach them.** A short "why this recipe works" blurb can sit ABOVE the recipe card in 2-3 sentences max, with any longer narrative content collapsed below the recipe, never between the user and the instructions.
- Recipe schema markup (Recipe, AggregateRating, NutritionInformation) for rich snippets
- Prep time / cook time / total time / servings
- **Native serving-size scaler** — adjust servings, ingredient quantities recalculate live (a feature competitor sites lack natively, per the research)
- **Native unit toggle** (US customary ↔ metric) on the ingredient list — ties directly into the Conversion Calculator tool
- Step-by-step instructions, numbered, one action per step
- "Ingredients used" module — links out to each Ingredient Hub page
- "Recipes using this technique" module — links to relevant How-To page if applicable
- Related recipes / category roundup links
- Clean print/PDF view button (default, not hidden)
- Optional: longer story/background content, positioned after the recipe
- **Depth, below the recipe card, never above it or between the user and the instructions** -- this is how to compete on content depth without reintroducing the "buried under a story" problem this template exists to counter. Structured reference content, not narrative:
  - Tips & variations (substitutions, make-ahead notes, common adjustments specific to this recipe -- not generic ingredient info that belongs on the Ingredient Hub page)
  - Storage & reheating instructions
  - Nutrition note (brief, estimate-labeled -- not a certified nutrition panel)
  - FAQ section (3-5 real questions, e.g. "can I freeze X," "why did my X turn out dense/gummy/dry") marked up with FAQPage schema -- these map directly to real "People Also Ask" search intent and are worth more for SEO than the same word count as prose

---

## 2. Ingredient Hub Page
**What it is:** A reference page for a single ingredient — substitutes, storage, uses. Covers both `seo_target` ingredient rows (fuller content, real SEO target) and `internal_infrastructure` rows (thinner content, exists mainly to send/receive internal links).

**Competitive gap addressed:** This is the core structural gap this entire project's research was built around — major competitor sites have thin or nonexistent dedicated pages for many ingredients (the "garlic confit," "cajeta," "pecorino" pattern found repeatedly). Building genuinely useful, complete ingredient pages at scale is a direct, evidenced opportunity.

**Recommended content sections:**
- Ingredient name + photo
- What it is / brief description
- Substitutes section (ranked, with ratios where relevant)
- Storage / shelf-life section
- How to use / prep tips
- Nutrition basics (brief, not the main focus)
- **"Recipes using this ingredient" module — this is the critical reverse-link that makes the whole site's internal linking graph work.** Every ingredient page should surface every recipe that uses it.
- Related ingredients (e.g., other cheeses, other chiles)
- FAQ section (2-4 real questions specific to this ingredient -- identification/lookalikes, "can I substitute X for Y," how it's grown/stored long-term), marked up with FAQPage schema. Same rationale as the Recipe page's FAQ section: real search intent, not padding.
- For `internal_infrastructure` rows: same template, lighter content — description + substitutes + recipe links is enough; doesn't need the full depth of an `seo_target` ingredient page.

---

## 3. How-To/Technique Page
**What it is:** A cooking technique or method (not tied to one dish) — e.g. "how to season a wok," "how to broil steak." Maps from `howto_technique` rows.

**Competitive gap addressed:** Same "buried under a story" problem as recipes, plus these pages benefit from clear step visuals that many competitor technique articles skip.

**Recommended content sections:**
- Technique name + hero image or short video/GIF if available
- Numbered steps (not paragraph-form)
- Common mistakes / troubleshooting section
- Tools/equipment needed
- "Recipes using this technique" module
- Related techniques

---

## 4. Definition Page ("What Is X")
**What it is:** A short, direct answer to "what is X" for an ingredient, dish, or term. Can share most of its structure with the Ingredient Hub template as a lighter variant.

**Competitive gap addressed:** Competitor "what is X" pages often over-explain with long intros before answering the actual question — direct answer first wins featured snippets and respects the user's time.

**Recommended content sections:**
- Direct 1-2 sentence answer at the very top (featured-snippet optimized)
- Expanded explanation
- How it's used / where it comes from
- Substitutes (if applicable) — link to full Substitute page if one exists
- Related recipes

---

## 5. Comparison Page ("X vs Y")
**What it is:** A side-by-side comparison of two related items/techniques. Maps from `comparison` rows.

**Competitive gap addressed:** Comparison content on competitor sites is often locked by global consumer brands (per this project's research — cappuccino vs. latte, for example, is dominated by Starbucks/Nescafé). Where genuinely open, a clean structured comparison beats a wall of prose.

**Recommended content sections:**
- Side-by-side comparison table (key differences at a glance)
- Verdict/summary — when to use which
- Individual sections expanding on each item
- Links to recipes/hub pages for each item being compared

---

## 6. Substitute Page
**What it is:** "Best Substitutes for X" — dedicated to substitution options for one ingredient. Can be a standalone page or a section within an Ingredient Hub for lower-volume items.

**Competitive gap addressed:** Same thin-coverage gap as Ingredient Hubs — many substitute pages on competitor sites cover only the most common ingredients, leaving specific/niche substitutions (verified repeatedly in this project's research) uncovered.

**Recommended content sections:**
- Ranked list of substitutes with ratios/conversion notes
- Best-for-baking vs. best-for-cooking distinctions where relevant
- Link back to the main Ingredient Hub page
- Recipes that work well with each substitute

---

## 7. Category/Cuisine Roundup Page
**What it is:** A curated collection linking out to many Recipe pages within a category (cuisine, occasion, equipment type). Maps from `category_roundup` rows. Low page count, high structural importance — this is the internal-linking hub layer.

**Competitive gap addressed:** Competitor roundup pages are often auto-generated tag-archive pages with weak curation and thin intro text — a genuinely curated roundup with real selection criteria outperforms both for users and for SEO (avoids thin-content signals).

**Recommended content sections:**
- Short curatorial intro (why these recipes, what ties them together)
- Grid/list of recipes with photos, linking to each Recipe page
- Sub-category filters if the roundup is large (e.g., "Italian Recipes" → appetizers/mains/desserts)
- Link to related roundups

---

## 8. Tool Pages (3 distinct builds — not a shared template)
**What they are:** Interactive utility pages, each absorbing a long tail of specific queries under one URL — the "one tool, many keywords" pattern validated earlier in this project.

**Competitive gap addressed:** Directly fills a gap third-party tools exist to solve — native unit conversion and serving-scaling tools are not offered natively by major competitor sites, per the research above.

- **Kitchen Measurement Conversion Calculator:** interactive input/output converter (cups↔grams, tbsp↔tsp, oven temps), covering the fraction-heavy long tail found in research. Should also be embeddable as a widget on Recipe pages (double use of the same build).
- **Cooking Time & Temperature Guide:** searchable/filterable reference table by protein and method (oven, air fryer, grill), covering both the doneness/safety angle and the time-by-method angle as clearly labeled sections.
- **Custom Recipe Generator:** input form (ingredients on hand / meal type) → generated recipe output. Lower SEO priority (per prior research, more competitive, more of a retention/differentiation feature); build last.

---

## 9. Homepage
**Recommended content sections:**
- Featured/trending recipes module
- Direct links into the major Category Roundup hubs
- Prominent placement for the 3 Tool pages (P0 priority per launch plan)
- Search bar
- Brief site positioning (what makes Tulo different — worth reflecting the "no clutter, no story-before-recipe, no cross-vertical dilution" differentiators established above)

---

## Brand Assets

Two logo files are provided in `/brand/`:
- **`tulo-light.png`** — dark wordmark, for light-background contexts (default site theme, most pages)
- **`tulo_dark.png`** — light/cream wordmark on a dark backdrop, for dark-background contexts (dark mode, footer if dark-themed, or any dark section)

Both include the orange-red accent underline as part of the brand mark — Claude Code should sample the exact accent color from these files directly (visually reads as a warm orange-red, roughly in the `#e8402c`–`#ea3f24` range) and use it consistently as the site's primary accent color for buttons, links, and highlights, rather than approximating a different shade.

---

## Stock Photo Sourcing (Free Image APIs)

**Correction from last round: this was already built.** `fetch_stock_images.py` (included in this package) is a working script using the official **Unsplash** and **Pexels** APIs — both free, both return verified license/attribution info, pulling from the real APIs rather than scraping search results (avoids licensing guesswork). It searches both sources per title, downloads the top matches, and writes an attribution log (`image_results.csv`) that must be kept alongside published content per each API's license terms.

**To use it:** get free API keys from https://unsplash.com/developers and https://www.pexels.com/api/, fill them into the script, and feed it the titles from `CONTENT_QUEUE.csv`. For niche ingredients where these APIs return thin/no results (a real risk given how specific this catalogue gets — cajeta, huacatay, etc.), fall back to a generic category image rather than leaving the page blank, and flag those pages for eventual real photography.

## Instacart Integration (Affiliate Revenue)

**Correction from last round: this was already built too.** `instacart_recipe_links.py` (included in this package) uses the real **Instacart Developer Platform API** (`connect.instacart.com/idp/v1/products/recipe`) to generate a shoppable link per recipe — submitting title, image URL, structured ingredients (name + quantity + unit), and instructions, and getting back a `products_link_url` to embed as a "Shop Ingredients" button.

**Requirements before this goes live:** Instacart API access (application/approval required — flagged as a pending business task) and full structured ingredient data per recipe (name, quantity, unit — not just a text ingredient list), since the API needs that structure to match products correctly. Build the Recipe page template with the "Shop Ingredients" button slot now, wire it to real links once API access is approved and recipes have structured ingredient data.

## Ad Unit Recommendations

**Note: the revenue modeling earlier in this project used $15-20 RPM, not $30 — flagging this discrepancy rather than silently assuming $30 is the agreed target. The guidance below is built to support the higher end of realistic outcomes rather than locked to one specific number.**

Food content sites can realistically reach into the $20-40 RPM range, but almost always by joining a premium ad management network rather than running generic display ads directly — this is standard practice across the top independent food blogs (the ones this whole project has been benchmarking against). Two names worth investigating for the account/business side of this (not something to build into templates directly, but worth knowing before finalizing ad-unit placement): **Mediavine** and **Raptive** (formerly AdThrive) — both are well-known ad management networks specifically built for content publishers, requiring a minimum traffic threshold to join (worth checking current requirements once traffic is established), and both are widely cited as the mechanism independent food sites use to reach RPMs in that higher range rather than a generic ad network.

**Template-level ad placement recommendations, regardless of which network is used:**
- **In-content ad unit** between the recipe intro and the ingredients list — high-visibility without interrupting the ingredients/instructions themselves
- **In-content ad unit** after the instructions, before any "related recipes" module
- **Sticky sidebar unit** on desktop (not mobile, where sidebar ads perform poorly and hurt UX)
- **Native/in-feed ad units** on Category Roundup pages, blended into the recipe grid
- Avoid stacking multiple ad units directly above the fold on mobile — this is one of the specific complaints documented against competitor sites (heavy ad load hurting the cooking experience) and directly undermines the clean-UX differentiation this whole template set is built around
