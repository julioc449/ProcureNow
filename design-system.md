# ProcureNow Design System
> Extracted from Complicheck screenshots. Every component must reference this file.

---

## 1. Color Palette

### Primary Colors
| Token | Hex | Role |
|---|---|---|
| `--color-forest` | `#1A3C34` | Primary brand, nav text, dark buttons, headings |
| `--color-lime` | `#96D01C` | Hero/accent backgrounds, bold section fills |
| `--color-amber` | `#E8A020` | Decorative accent only (image backdrops, highlights) |

### Surface & Background Colors
| Token | Hex | Role |
|---|---|---|
| `--color-bg-page` | `#EDECEA` | Main page/app background (warm off-white) |
| `--color-bg-card` | `#FFFFFF` | Card surfaces, modals, panels |
| `--color-bg-muted` | `#F5F4F0` | Subtle section fills, hover states |

### Text Colors
| Token | Hex | Role |
|---|---|---|
| `--color-text-primary` | `#1A3C34` | Headings, bold copy (uses forest green, not black) |
| `--color-text-body` | `#4A5A54` | Body paragraphs, descriptions |
| `--color-text-muted` | `#8A9E98` | Captions, secondary labels, nav sub-items |
| `--color-text-inverse` | `#FFFFFF` | Text on dark green or lime backgrounds |

### Border Colors
| Token | Hex | Role |
|---|---|---|
| `--color-border` | `#DDD9D3` | Default 1px card/container borders |
| `--color-border-strong` | `#1A3C34` | Outline buttons, focused inputs |

---

## 2. Typography

**Font Family:** `Inter` (Google Fonts). Fallback: `system-ui, -apple-system, sans-serif`.

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

font-family: 'Inter', system-ui, -apple-system, sans-serif;
```

### Type Scale
| Role | Size | Weight | Line Height | Usage |
|---|---|---|---|---|
| Display / Hero | `52px` | `800` | `1.1` | Main hero headlines ("Statutory compliance…") |
| Heading 1 | `40px` | `700` | `1.2` | Section titles ("Core Compliance") |
| Heading 2 | `28px` | `700` | `1.3` | Card titles, sub-section heads |
| Heading 3 | `20px` | `600` | `1.4` | Feature list items, sidebar headers |
| Body | `16px` | `400` | `1.6` | Paragraphs, descriptions |
| Body Small | `14px` | `400` | `1.5` | Nav links, footer links, table rows |
| Label / Overline | `11px` | `600` | `1.4` | ALL CAPS labels ("THE NEW COMPLICHECK BRAND IS OUT NOW!"), tracking: `0.08em` |
| Caption | `12px` | `400` | `1.4` | Attribution lines ("– Ajay Singh, Pataylam Partners") |

### Rules
- **Never use `#000000` black for text** — use `--color-text-primary` (`#1A3C34`) for emphasis.
- Overline labels are ALWAYS uppercase + letter-spaced.
- Hero display copy is tight (`line-height: 1.1`) and heavy (`font-weight: 800`).

---

## 3. Spacing & Layout

| Token | Value | Usage |
|---|---|---|
| `--space-xs` | `4px` | Icon gaps, tight inline spacing |
| `--space-sm` | `8px` | Label-to-value gaps |
| `--space-md` | `16px` | Internal card padding (small) |
| `--space-lg` | `24px` | Card padding standard |
| `--space-xl` | `40px` | Section inner padding |
| `--space-2xl` | `64px` | Top/bottom section gaps |
| `--space-3xl` | `96px` | Page-level vertical rhythm |

- **Max content width:** `1200px`, centered.
- **Grid:** 12-column, 24px gutters.
- **Layout splits:** 50/50 or 55/45 two-column layouts are the primary pattern (hero left copy + right product screenshot).

---

## 4. Border Radius

| Token | Value | Usage |
|---|---|---|
| `--radius-sm` | `6px` | Tags, small inline chips |
| `--radius-md` | `12px` | Input fields, small cards |
| `--radius-lg` | `16px` | Standard cards, containers, product panels |
| `--radius-xl` | `24px` | Large feature blocks (the big lime/footer card) |
| `--radius-pill` | `9999px` | ALL buttons (primary, ghost, outline), filter tags |

> **Rule:** Buttons are ALWAYS pill-shaped (`border-radius: 9999px`). No square or slightly-rounded buttons exist in this system.

---

## 5. Borders

- **Default card border:** `1px solid #DDD9D3` — always present, never omitted.
- **Outline button border:** `1px solid #1A3C34`
- **Dividers (horizontal rules):** `1px solid #DDD9D3`, full width, used between list items (see "Automated Checks / Comprehensive Reporting" feature list).
- **No double borders.** If a card is on a page background, one border is sufficient.

---

## 6. Elevation & Shadows

This system is **flat-first**. Shadows are minimal and used sparingly.

| Level | Value | Usage |
|---|---|---|
| Flat | `none` | All standard cards and containers |
| Whisper | `0 1px 4px rgba(0,0,0,0.06)` | Floating dropdowns, hover states |
| Lifted | `0 4px 16px rgba(0,0,0,0.08)` | Modals, sticky nav on scroll |

> **Rule:** Default cards use `box-shadow: none`. Depth is implied by the `1px border` + the `--color-bg-page` background contrast, not shadows.

---

## 7. Button System

### Primary Button (Dark Green)
```css
background: #1A3C34;
color: #FFFFFF;
border-radius: 9999px;
padding: 10px 20px;
font-size: 14px;
font-weight: 600;
border: none;
```

### Ghost / Outline Button
```css
background: transparent;
color: #1A3C34;
border: 1px solid #1A3C34;
border-radius: 9999px;
padding: 10px 20px;
font-size: 14px;
font-weight: 600;
```

### CTA Button on Lime Background
```css
background: #1A3C34;
color: #FFFFFF;
border-radius: 12px; /* slightly less pill on hero — more of a rounded rectangle */
padding: 16px 32px;
font-size: 16px;
font-weight: 600;
```

### Hover States
- Primary: lighten background slightly → `#234D42`
- Ghost: fill background with `#1A3C34`, text becomes white

---

## 8. Cards & Containers

```css
/* Standard Card */
background: #FFFFFF;
border: 1px solid #DDD9D3;
border-radius: 16px;
padding: 32px;
box-shadow: none;
```

```css
/* Accent Section (Lime) */
background: #96D01C;
border: 1px solid rgba(0,0,0,0.06);
border-radius: 24px;
padding: 40px;
```

```css
/* App Screenshot Panel (Forest Green) */
background: #1A3C34;
border-radius: 16px;
overflow: hidden;
```

---

## 9. Navigation Bar

```css
background: #FFFFFF;
border-bottom: 1px solid #DDD9D3;
height: 60px;
padding: 0 40px;
display: flex;
align-items: center;
justify-content: space-between;
```

- **Logo:** `font-weight: 700`, `font-size: 18px`, color `#1A3C34`
- **Nav links:** `font-size: 14px`, `font-weight: 400`, color `#1A3C34`
- **CTA button:** Primary pill button (dark green), right-aligned

---

## 10. Feature List Pattern

Used for numbered feature rows ("Automated Checks 01"):

```css
/* Each row */
display: flex;
justify-content: space-between;
align-items: center;
padding: 16px 0;
border-bottom: 1px solid #DDD9D3;
font-weight: 600;
font-size: 16px;
color: #1A3C34;

/* Number label */
color: #8A9E98;
font-size: 14px;
font-weight: 400;
```

---

## 11. Anti-Patterns (Do NOT Use)

- ❌ No dark mode backgrounds (`#0D0D0D`, `#1E1E2E`, etc.)
- ❌ No neon or saturated accent colors other than lime (`#96D01C`) and amber (`#E8A020`)
- ❌ No heavy drop shadows (`box-shadow: 0 20px 40px …`)
- ❌ No square buttons (`border-radius: 4px`)
- ❌ No pure black text (`#000000`) — always use `#1A3C34`
- ❌ No generic blue links or accents
- ❌ No gradient backgrounds on hero sections — use flat lime or off-white

---

## CSS Custom Properties (Root)

```css
:root {
  /* Colors */
  --color-forest: #1A3C34;
  --color-lime: #96D01C;
  --color-amber: #E8A020;
  --color-bg-page: #EDECEA;
  --color-bg-card: #FFFFFF;
  --color-bg-muted: #F5F4F0;
  --color-text-primary: #1A3C34;
  --color-text-body: #4A5A54;
  --color-text-muted: #8A9E98;
  --color-text-inverse: #FFFFFF;
  --color-border: #DDD9D3;
  --color-border-strong: #1A3C34;

  /* Typography */
  --font-family: 'Inter', system-ui, -apple-system, sans-serif;

  /* Radius */
  --radius-sm: 6px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-pill: 9999px;

  /* Spacing */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 40px;
  --space-2xl: 64px;
  --space-3xl: 96px;
}
```
