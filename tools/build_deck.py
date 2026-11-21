"""Build the 5-slide executive deck (P14) in NextDAQ branding on the 2025 Databricks template's blank layout.
Rebuilds the slides in place (same presentation and link). The NextDAQ logo is drawn with native shapes.
Usage: python3 tools/build_deck.py
"""
import sys
import uuid

sys.path.insert(0, "/Users/sophia.masse/.claude/plugins/cache/fe-vibe/fe-google-tools/1.2.9/skills/google-slides/resources")
import gslides_builder as g  # noqa: E402

PID = "1vVHQvhakpZE94rTSKyphTQd5FXsDzOe3BAKDFVts0bA"   # copy of the 2025 Databricks corporate template
BLANK = "g3413a4b56ae_5_32"                              # "Content E - Blank" on the Databricks master
NAVY, TEAL, CYAN, AMBER, MIST, SLATE, WHITE, LINE = "#0B1F3A", "#00A6A0", "#3DD9D0", "#F2A93B", "#F3F6FA", "#51627A", "#FFFFFF", "#DCE3EC"
FONT = "DM Sans"
EMU = 914400


def rgb(h):
    h = h.lstrip("#")
    return {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255, "blue": int(h[4:6], 16) / 255}


class Slide:
    def __init__(self, sid):
        self.sid, self.reqs = sid, []

    def _id(self):
        return f"{self.sid}_{uuid.uuid4().hex[:8]}"

    def shape(self, x, y, w, h, fill=None, kind="RECTANGLE", line=None, weight=1.0):
        oid = self._id()
        self.reqs.append({"createShape": {"objectId": oid, "shapeType": kind, "elementProperties": {
            "pageObjectId": self.sid, "size": {"width": {"magnitude": w * EMU, "unit": "EMU"}, "height": {"magnitude": h * EMU, "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": x * EMU, "translateY": y * EMU, "unit": "EMU"}}}})
        props, fields = {}, []
        if fill:
            props["shapeBackgroundFill"] = {"solidFill": {"color": {"rgbColor": rgb(fill)}}}
            fields.append("shapeBackgroundFill.solidFill.color")
        else:
            props["shapeBackgroundFill"] = {"propertyState": "NOT_RENDERED"}
            fields.append("shapeBackgroundFill.propertyState")
        if line:
            props["outline"] = {"outlineFill": {"solidFill": {"color": {"rgbColor": rgb(line)}}}, "weight": {"magnitude": weight, "unit": "PT"}}
            fields += ["outline.outlineFill.solidFill.color", "outline.weight"]
        else:
            props["outline"] = {"propertyState": "NOT_RENDERED"}
            fields.append("outline.propertyState")
        self.reqs.append({"updateShapeProperties": {"objectId": oid, "shapeProperties": props, "fields": ",".join(fields)}})
        return oid

    def text(self, x, y, w, h, runs, size=14, color=NAVY, bold=False, align="START", valign="TOP", fill=None,
             kind="RECTANGLE", line=None, spacing=None):
        """runs: str or list of (text, {style overrides}). Lines separated by \\n."""
        oid = self.shape(x, y, w, h, fill, kind, line)
        runs = [(runs, {})] if isinstance(runs, str) else runs
        full = "".join(t for t, _ in runs)
        self.reqs.append({"insertText": {"objectId": oid, "text": full}})
        self.reqs.append({"updateTextStyle": {"objectId": oid, "textRange": {"type": "ALL"}, "style": {
            "fontFamily": FONT, "fontSize": {"magnitude": size, "unit": "PT"}, "bold": bold,
            "foregroundColor": {"opaqueColor": {"rgbColor": rgb(color)}}}, "fields": "fontFamily,fontSize,bold,foregroundColor"}})
        pos = 0
        for t, st in runs:
            if st:
                style, fields = {}, []
                if "color" in st:
                    style["foregroundColor"] = {"opaqueColor": {"rgbColor": rgb(st["color"])}}
                    fields.append("foregroundColor")
                if "size" in st:
                    style["fontSize"] = {"magnitude": st["size"], "unit": "PT"}
                    fields.append("fontSize")
                if "bold" in st:
                    style["bold"] = st["bold"]
                    fields.append("bold")
                self.reqs.append({"updateTextStyle": {"objectId": oid, "textRange": {"type": "FIXED_RANGE", "startIndex": pos,
                                                                                     "endIndex": pos + len(t)}, "style": style, "fields": ",".join(fields)}})
            pos += len(t)
        para = {"alignment": align}
        fields = "alignment"
        if spacing:
            para["spaceBelow"] = {"magnitude": spacing, "unit": "PT"}
            fields += ",spaceBelow"
        self.reqs.append({"updateParagraphStyle": {"objectId": oid, "textRange": {"type": "ALL"}, "style": para, "fields": fields}})
        self.reqs.append({"updateShapeProperties": {"objectId": oid, "shapeProperties": {
            "contentAlignment": valign, "autofit": {"autofitType": "NONE"}}, "fields": "contentAlignment,autofit.autofitType"}})
        return oid

    def logo(self, x, y, scale=1.0, dark=False):
        """NextDAQ mark (three rising bars + forward chevron) and wordmark, drawn natively."""
        s = scale
        self.shape(x, y + 0.36 * s, 0.13 * s, 0.26 * s, WHITE if dark else NAVY, "ROUND_RECTANGLE")
        self.shape(x + 0.18 * s, y + 0.22 * s, 0.13 * s, 0.40 * s, TEAL, "ROUND_RECTANGLE")
        self.shape(x + 0.36 * s, y + 0.06 * s, 0.13 * s, 0.56 * s, CYAN, "ROUND_RECTANGLE")
        self.shape(x + 0.55 * s, y + 0.14 * s, 0.17 * s, 0.38 * s, AMBER, "CHEVRON")
        self.text(x + 0.82 * s, y - 0.02 * s, 2.6 * s, 0.7 * s, [("Next", {"color": WHITE if dark else NAVY}), ("DAQ", {"color": CYAN if dark else TEAL})],
                  size=round(26 * s), bold=True, valign="MIDDLE")

    def header(self, title, kicker):
        self.logo(0.55, 0.32, 0.55)
        self.text(0.55, 0.95, 12.2, 0.75, title, size=28, bold=True, color=NAVY, valign="MIDDLE")
        self.shape(0.58, 1.72, 0.9, 0.06, TEAL)
        if kicker:
            self.text(1.6, 1.58, 11.2, 0.34, kicker, size=14, color=SLATE, valign="MIDDLE")
        self.text(0.95, 7.05, 9.0, 0.3, "NextDAQ-100 Rebalance Simulator  ·  Confidential  ·  Powered by Databricks",
                  size=9, color=SLATE, valign="MIDDLE")


def slide_title(s):
    s.shape(0, 0, 13.34, 7.5, NAVY)
    s.shape(8.9, 4.3, 0.75, 2.4, "#14305A", "ROUND_RECTANGLE")
    s.shape(9.85, 3.2, 0.75, 3.5, TEAL, "ROUND_RECTANGLE")
    s.shape(10.8, 1.9, 0.75, 4.8, CYAN, "ROUND_RECTANGLE")
    s.shape(11.8, 2.6, 1.0, 2.2, AMBER, "CHEVRON")
    s.logo(0.7, 0.6, 1.0, dark=True)
    s.text(0.7, 2.0, 8.0, 2.4, "Test every rebalance rule change in minutes, before you announce it", size=40, bold=True, color=WHITE, valign="MIDDLE")
    s.shape(0.72, 4.55, 1.2, 0.07, AMBER)
    s.text(0.7, 4.75, 8.0, 0.5, "NextDAQ-100 Rebalance Simulator", size=20, bold=True, color=CYAN)
    s.text(0.7, 5.3, 8.0, 0.8, "For the Head of the Index Business and the Head of Index Methodology", size=16, color="#C9D4E3")
    s.text(0.7, 6.75, 8.0, 0.35, "November 2026  ·  Powered by Databricks", size=11, color="#9FB0C7")


def slide_problem(s):
    s.header("Every rebalance moves billions, yet it runs on spreadsheets", "What it costs the methodology team today")
    tiles = [("2-3 days", "to rebuild one scenario", "So only 3-4 options ever reach the index committee"),
             ("No record", "of who changed which rule, or why", "Approvals live in email and committee minutes"),
             ("At risk", "pre-announcement changes in shared files", "Anyone with the file sees the decision early")]
    for i, (big, label, note) in enumerate(tiles):
        x = 0.55 + i * 4.15
        s.shape(x, 2.25, 3.9, 2.75, WHITE, "RECTANGLE", LINE)
        s.shape(x, 2.25, 3.9, 0.1, [TEAL, NAVY, AMBER][i])
        s.text(x + 0.3, 2.55, 3.4, 0.85, big, size=34, bold=True, color=[TEAL, NAVY, AMBER][i], valign="MIDDLE")
        s.text(x + 0.3, 3.4, 3.4, 0.6, label, size=15, bold=True, color=NAVY)
        s.text(x + 0.3, 4.05, 3.4, 0.8, note, size=13, color=SLATE)
    s.shape(0.55, 5.3, 12.35, 1.5, MIST, "ROUND_RECTANGLE")
    s.text(0.85, 5.42, 2.0, 0.4, "Why now", size=15, bold=True, color=TEAL)
    chips = ["More special rebalances as a few megacaps carry more of the index",
             "Competitors launch custom indexes in weeks", "Regulators expect a documented, controlled methodology"]
    for i, c in enumerate(chips):
        s.text(0.85 + i * 4.0, 5.85, 3.75, 0.8, c, size=13, color=NAVY, fill=WHITE, kind="ROUND_RECTANGLE", valign="MIDDLE", align="CENTER")


def slide_demo(s):
    s.header("What you're about to see: three stops, three KPIs", "Watch the KPIs move live, and what a non-cleared user can't see")
    stops = [("Scenario Lab", "Change the rules and stress-test a megacap", "Days to minutes per scenario"),
             ("Compare & Approve", "AI impact summary, client notice, approval on record", "Faster proposal-to-approval"),
             ("Ask Genie", "Plain-English answers on the same governed data", "Analysts self-serve, no SQL")]
    for i, (name, what, kpi) in enumerate(stops):
        x = 0.55 + i * 4.15
        s.shape(x, 2.3, 3.9, 4.35, WHITE, "ROUND_RECTANGLE", LINE)
        s.text(x + 0.3, 2.6, 0.8, 0.8, str(i + 1), size=26, bold=True, color=WHITE, fill=TEAL, kind="ELLIPSE", align="CENTER", valign="MIDDLE")
        s.text(x + 1.25, 2.6, 2.6, 0.8, name, size=19 if len(name) > 14 else 20, bold=True, color=NAVY, valign="MIDDLE")
        s.text(x + 0.3, 3.65, 3.3, 1.4, what, size=16, color=NAVY)
        s.text(x + 0.3, 5.35, 3.3, 0.95, [("KPI  ", {"color": AMBER, "bold": True}), (kpi, {})], size=14, color=NAVY,
               fill="#FDF4E4", kind="ROUND_RECTANGLE", valign="MIDDLE", align="CENTER")
        if i < 2:
            s.shape(x + 3.93, 4.25, 0.2, 0.45, AMBER, "CHEVRON")


def slide_value(s):
    s.header("About $0.75-1.0M a year in value, on a platform you can trust", "Value is illustrative, from your discovery numbers; trust points were measured")
    s.text(0.55, 2.2, 6.0, 1.0, "$0.75-1.0M", size=48, bold=True, color=TEAL, valign="MIDDLE")
    s.text(0.58, 3.15, 6.0, 0.4, "per year, illustrative", size=14, color=SLATE)
    bars = [("Analyst time", "$190-240k", 0.57, "4 analysts x 30% of time; work cut ~80%"),
            ("Fewer corrections", "$250-500k", 1.0, "From 2 to 1 or fewer a year, ~$250k each"),
            ("Faster custom indexes", "~$300k", 0.8, "3 launches a year, 2 months sooner")]
    for i, (name, val, frac, note) in enumerate(bars):
        y = 3.75 + i * 1.05
        s.text(0.55, y, 2.6, 0.4, name, size=14, bold=True, color=NAVY, valign="MIDDLE")
        s.shape(3.2, y + 0.05, 3.2, 0.32, MIST, "ROUND_RECTANGLE")
        s.shape(3.2, y + 0.05, 3.2 * frac, 0.32, [CYAN, TEAL, NAVY][i], "ROUND_RECTANGLE")
        s.text(3.2, y + 0.42, 3.4, 0.4, note, size=11, color=SLATE)
        s.text(6.45, y, 1.3, 0.4, val, size=14, bold=True, color=NAVY, valign="MIDDLE")
    s.text(8.15, 2.2, 4.8, 0.45, "Measured in the build", size=16, bold=True, color=NAVY)
    proofs = [("< 30 ms", "to recompute a scenario across 1,015 securities"),
              ("54 of 1.33M", "bad rows stopped before they reach weights"),
              ("0 of 1,015", "forecast values visible to non-cleared users"),
              ("14 of 14", "Genie answers matched the ground truth")]
    for i, (big, note) in enumerate(proofs):
        x, y = 8.15 + (i % 2) * 2.45, 2.75 + (i // 2) * 2.05
        s.shape(x, y, 2.3, 1.85, MIST, "ROUND_RECTANGLE")
        s.text(x + 0.15, y + 0.15, 2.0, 0.7, big, size=22, bold=True, color=TEAL, valign="MIDDLE")
        s.text(x + 0.15, y + 0.85, 2.0, 0.9, note, size=12, color=NAVY)


def slide_next(s):
    s.header("Next step: run the December reconstitution through it", "A 6-week pilot that shadows the 21 December 2026 reconstitution, with no risk to today's process")
    phases = [("Weeks 1-2", "Connect", "Your security master, market data and index history; set access"),
              ("Weeks 3-4", "Shadow", "Run the December scenarios in parallel with today's spreadsheets"),
              ("Weeks 5-6", "Decide", "Approvals live; compare results and timings")]
    for i, (when, name, what) in enumerate(phases):
        x = 0.55 + i * 4.15
        s.text(x, 2.25, 3.95, 0.55, [(when + "   ", {"color": CYAN if i == 0 else "#E6FBF9"}), (name, {})], size=16, bold=True, color=WHITE,
               fill=[NAVY, TEAL, "#0A7F7B"][i], kind="HOME_PLATE" if i < 2 else "RECTANGLE", valign="MIDDLE")
        s.text(x + 0.1, 2.95, 3.7, 0.95, what, size=14, color=NAVY)
    s.text(0.55, 4.05, 6.0, 0.4, "Success criteria", size=16, bold=True, color=NAVY)
    crit = ["A scenario end to end in under 5 minutes", "20+ scenarios per rebalance cycle", "Zero MNPI exposure",
            "Sign-off by the Head of Methodology"]
    for i, c in enumerate(crit):
        x = 0.55 + i * 3.1
        s.text(x, 4.5, 2.95, 1.0, [("✓  ", {"color": TEAL, "bold": True}), (c, {})], size=14, color=NAVY, fill=MIST,
               kind="ROUND_RECTANGLE", valign="MIDDLE")
    s.text(0.55, 5.75, 12.35, 1.05, [("The ask:  ", {"color": AMBER, "bold": True}),
                                    ("a decision by 5 December, two methodology analysts and an executive sponsor", {})],
           size=18, bold=True, color=WHITE, fill=NAVY, kind="ROUND_RECTANGLE", valign="MIDDLE", align="CENTER")


NOTES = [
    "Open with the outcome. Every rule change or rebalance moves billions of dollars of ETF trading, and today it's tested in spreadsheets over days. In the next 20 minutes I'll show how your methodology team can test a change in minutes, keep pre-announcement data locked down, and record every decision. Ask: what would make this most useful for each of you? Pause and adapt.",
    "Recap discovery. Two to three analyst-days per scenario, so only three or four options reach the committee; no record of who changed what; pre-announcement changes in shared files. Why now: a few megacaps carry more of the index, so special rebalances are more frequent; competitors launch custom indexes in weeks; regulators expect a documented process. Ask: which of these costs you the most today?",
    "TELL before the demo. Stop 1: change the rules; the liquidity floor removes a name that would take about 769 days to trade. Stop 2: compare two scenarios, get the AI summary and a templated client notice, then submit and approve. Stop 3: ask Genie in plain English. Watch the KPIs move, and note that a user who isn't cleared for MNPI sees the forecast masked by the platform. Then switch to the app.",
    "TELL after the demo. For the Head of Methodology: scenarios in minutes, more options per cycle, approvals with an audit trail. For the Head of the Index Business: fewer surprises for ETF issuers and faster custom index launches. The value uses your discovery numbers; I'd rather use yours. Everything on the right was measured in the build. Be honest about limits: the forecast is a watchlist, not a verdict, and a person reviews every AI draft.",
    "Close with the ask. Recap value per persona in one line each. The pilot shadows the December reconstitution, so there's no risk to today's process. Four measurable success criteria. Ask for a decision by 5 December. If time runs short: headline result, value, the pilot, the ask.",
]


def main():
    p = g.get_presentation(PID)
    old = [x["objectId"] for x in p["slides"]]
    builders = [slide_title, slide_problem, slide_demo, slide_value, slide_next]
    ids = [f"nx{i}_{uuid.uuid4().hex[:6]}" for i in range(len(builders))]
    g.batch_update(PID, [{"createSlide": {"objectId": sid, "insertionIndex": len(old) + i, "slideLayoutReference": {"layoutId": BLANK}}}
                         for i, sid in enumerate(ids)])
    for sid, b in zip(ids, builders):
        s = Slide(sid)
        b(s)
        for i in range(0, len(s.reqs), 400):
            g.batch_update(PID, s.reqs[i:i + 400])
    g.batch_update(PID, [{"deleteObject": {"objectId": o}} for o in old])
    p = g.get_presentation(PID)
    reqs = []
    for sl, note in zip(p["slides"], NOTES):
        nid = sl["slideProperties"]["notesPage"]["notesProperties"]["speakerNotesObjectId"]
        reqs.append({"insertText": {"objectId": nid, "text": note}})
    g.batch_update(PID, reqs)
    print(f"https://docs.google.com/presentation/d/{PID}/edit  ({len(p['slides'])} slides)")


if __name__ == "__main__":
    main()
