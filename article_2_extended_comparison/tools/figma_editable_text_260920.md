# Making the Article 2 panel text editable in Figma — runbook, 2026-09-20

The Figma half of `../figma_editable_text_plan_260920.md`. Run
`split_panel_text_260920.py` first; this document only moves its output into the file.

**File** `t8bFgusleBEwB9ht7rORCH`, **Page 2** (`1013:2`). Every `use_figma` script starts with
`await figma.setCurrentPageAsync(figma.root.children.find(p => p.name === 'Page 2'))` — page
context resets to the first page on every call. Never call `get_metadata` on the page root or on
a whole figure frame (Extended Figure 1 alone returns ~3.5 M characters), and address nodes by id.

Executed on 2026-09-20. Result: 21 panels, **1,966 editable `TEXT` nodes**, 0 geometry changes.

---

## What the pass produces

Each of the 21 panel rectangles becomes a **panel `FRAME`** of the identical box, holding

| child | what it is |
|---|---|
| `artwork` | the original `RECTANGLE`, keeping its node id, now filled with the **text-free** 300 dpi render and **locked** so a click selects the label above it |
| `labels` | the overlay `FRAME` imported from `<panel>_text.svg`, holding one Inter `TEXT` node per label, tick and annotation |

`Figure 6 - Recipe` is not touched: it was already fully vector with 21 `TEXT` nodes.

---

## Step F0 — snapshot

Read Page 2's top-level children plus a child listing of the seven Article 2 frames, and save as
`figures/figma_snapshots/page2_before_editable_260920.json`. This is both the rollback reference
and the baseline for the acceptance diff.

```js
const p2 = figma.root.children.find(p => p.name === 'Page 2');
await figma.setCurrentPageAsync(p2);
const pageChildren = p2.children.map(n => ({
  id: n.id, name: n.name, type: n.type,
  x: Math.round(n.x), y: Math.round(n.y),
  w: Math.round(n.width), h: Math.round(n.height),
  kids: ('children' in n) ? n.children.length : 0
}));
const re = /^(Figure 4|Figure 5|Figure 6|Supplementary Figure 1[1-4])/;
const a2 = {};
for (const f of p2.children.filter(n => re.test(n.name) && 'children' in n)) {
  a2[f.id] = { name: f.name, x: f.x, y: f.y, w: f.width, h: f.height,
    children: f.children.map(c => ({
      id: c.id, name: c.name, type: c.type,
      x: c.x, y: c.y, w: c.width, h: c.height, locked: c.locked,
      fill: ('fills' in c && Array.isArray(c.fills) && c.fills.length) ? c.fills[0].type : null,
      nSub: ('children' in c) ? c.children.length : 0 })) };
}
return { page: p2.name, pageId: p2.id, pageChildren, article2Frames: a2 };
```

---

## Step F1 — replace the 21 artwork fills

**`upload_assets` with `nodeIds` stores the images but does not attach them.** Measured on
2026-09-20: all 21 POSTs returned `{"success": true, "imageHash": ...}` and every target node still
carried its previous hash. The fills must be set explicitly in a second call. Budget two calls for
this step, not one.

1. `upload_assets(fileKey, count: 21, scaleMode: "FILL", nodeIds: [...])` — the `nodeIds` array is
   parallel to the returned `uploads` array.
2. POST each `<panel>_artwork_300dpi.png` to its `submitUrl` as `multipart/form-data`, field `file`,
   type `image/png`. **Use `curl -4`**: this machine's resolver returns an IPv6-only answer for
   some hosts and the request hangs otherwise. Keep each response — it holds the `imageHash`.
3. Set the fills from those hashes:

```js
const p2 = figma.root.children.find(p => p.name === 'Page 2');
await figma.setCurrentPageAsync(p2);
const pairs = [["1256:2","<hash>"], /* ... 21 entries, rect id -> imageHash ... */];
const changed = [];
for (const [id, hash] of pairs) {
  const n = await figma.getNodeByIdAsync(id);
  const before = n.fills[0] && n.fills[0].imageHash;
  n.fills = [{ type: 'IMAGE', imageHash: hash, scaleMode: 'FILL' }];
  changed.push({ id, name: n.name, before, after: n.fills[0].imageHash });
}
return { mutatedNodeIds: changed.map(c => c.id), n: changed.length };
```

`FILL` is safe because `split_panel_text_260920.py` resizes every artwork PNG to the placed box's
exact aspect ratio. Left at the drawing's own aspect it would differ by up to 0.7 %, and `FILL`
would crop that away and slide the artwork out from under the text.

Then screenshot one frame and confirm the artwork is blank where the labels were.

---

## Step F2 — wrap each rectangle in a panel frame

Six panels per call, four calls. The rectangle's `x`/`y` must be read **before** reparenting,
because they are parent-relative.

```js
async function wrap(id) {
  const rect = await figma.getNodeByIdAsync(id);
  const parent = rect.parent;
  const idx = parent.children.indexOf(rect);
  const rx = rect.x, ry = rect.y, rw = rect.width, rh = rect.height;
  const f = figma.createFrame();
  f.name = rect.name;
  f.resize(rw, rh);
  f.fills = [];              // createFrame defaults to an opaque white fill
  f.clipsContent = true;
  parent.insertChild(idx, f);   // the frame takes the rect's slot, so z-order holds
  f.x = rx; f.y = ry;
  f.appendChild(rect);          // removes the rect from parent, leaving f at idx
  rect.x = 0; rect.y = 0;
  rect.name = 'artwork';
  rect.locked = true;
  return { frameId: f.id, artworkId: rect.id, name: f.name,
           x: f.x, y: f.y, w: f.width, h: f.height,
           index: parent.children.indexOf(f) };
}
```

No auto-layout: these are absolutely-positioned artwork boxes on a poster canvas, the case Rule 12a
of the figma-use skill exempts.

---

## Step F3 — import the overlays

**Upload the overlay SVGs; do not inline them.** The four expression-scatter overlays are ~34 KB
each and the `use_figma` `code` parameter caps at 50,000 characters, so inlining them is fragile and
costs a great deal of context for nothing. `upload_assets` imports an SVG as an editable vector node
tree and reports where it landed:

1. Pin the current page to Page 2 in a one-line `use_figma` call. Uploads land on the file's
   current page, which is *sticky between calls* — the recipe assets landed on Page 1 in the
   original assembly because nothing had pinned it.
2. `upload_assets(fileKey, count: 21)` — **no `nodeIds`**, which do not apply to SVGs.
3. POST each `<panel>_text.svg` with type `image/svg+xml`. The response carries
   `placedOnNodeId`; the layer takes the filename, so the mapping is unambiguous either way.
4. Reparent, in two calls of ~11 panels:

```js
await figma.loadFontAsync({ family: 'Inter', style: 'Regular' });
// [overlay node, panel frame, expected TEXT count from overlay_manifest.json]
for (const [ovId, frId, want] of jobs) {
  const ov = await figma.getNodeByIdAsync(ovId);
  const fr = await figma.getNodeByIdAsync(frId);
  if (Math.abs(ov.width - fr.width) > 1 || Math.abs(ov.height - fr.height) > 1) {
    throw new Error(`${frId}: overlay ${ov.width}x${ov.height} != panel ${fr.width}x${fr.height}`);
  }
  const texts = ov.findAll(c => c.type === 'TEXT');
  if (texts.length !== want) throw new Error(`${frId}: ${texts.length} TEXT, expected ${want}`);
  const bad = texts.filter(t => !t.characters.trim()
    || t.fontName === figma.mixed || t.fontName.family !== 'Inter');
  if (bad.length) throw new Error(`${frId}: ${bad.length} bad TEXT nodes`);
  ov.name = 'labels';
  ov.fills = [];
  ov.clipsContent = false;
  fr.appendChild(ov);
  ov.x = 0; ov.y = 0;
}
```

The overlay frame arrives at exactly the placed pixel box because its `viewBox` is that box — no
`rescale()`, no repositioning, no font-size correction.

---

## Step F4 — acceptance

Screenshot all six frames and compare against `figures/panels_260917/<panel>.png`, then run the
read-only acceptance script of the plan's verification section. Note that filtering a figure frame's
children on `type === 'FRAME'` also catches Figure 6's twelve recipe assets, which have no
`artwork`/`labels` children by design; read the totals per panel, not across all frames.

Finally write `page2_after_editable_260920.json` and diff it against the before-snapshot. The
2026-09-20 run: **0 geometry differences, 0 name differences, 21 rectangles converted, 54 children
untouched** (Figure 6's 33 plus the 21 panel letters).

---

## Two facts about Figma's SVG reader, measured here

1. **`font-size` inside a `style=` attribute is ignored** and the label imports at Figma's 10 px
   default. matplotlib writes typography only into `style=`, so a raw panel SVG imports with every
   label the wrong size. Presentation attributes (`font-size="7.5"`) are honoured exactly — which is
   what `write_overlay_svg()` emits.
2. **Only `Inter` is available in this file.** `Arial`, `Helvetica`, `DejaVu Sans` and
   `Liberation Sans` all return `no` from `listAvailableFontsAsync()`.

---

## Rollback

Delete the 21 `labels` frames, unwrap the 21 panel frames (move each `artwork` rectangle back to its
figure frame at the box recorded in the before-snapshot, unlock it, restore its name), and re-upload
the original `figures/panels_260917/<panel>.png` artwork to the same rectangle ids. Nothing outside
the seven Article 2 frames is touched, so rollback cannot reach the Extended Figures.
