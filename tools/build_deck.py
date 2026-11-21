"""Build the 5-slide business deck on a copy of the 2025 Databricks corporate template (P14). Rerun = rebuild in place."""
import sys, json, uuid
sys.path.insert(0, "/Users/sophia.masse/.claude/plugins/cache/fe-vibe/fe-google-tools/1.2.9/skills/google-slides/resources")
import gslides_builder as g

PID = "1vVHQvhakpZE94rTSKyphTQd5FXsDzOe3BAKDFVts0bA"   # copy of the 2025 Databricks corporate template
L = {"title": "g324ba092b07_3_208", "basic": "g324ba092b07_3_45", "two": "g324ba092b07_3_50", "cards": "g324ba092b07_3_92"}

SLIDES = [
    ("title", {
        ("CENTERED_TITLE", 0): "Test every rebalance rule change in minutes, before you announce it",
        ("SUBTITLE", 0): "NextDAQ-100 Rebalance Simulator\nFor the Head of the Index Business and the Head of Index Methodology",
        ("SUBTITLE", 1): "NextDAQ · November 2026",
    }, "Open with the outcome. Today every rule change or rebalance is tested in spreadsheets over days, while billions of dollars of ETF trading depend on getting it right. In the next 20 minutes I'll show how the methodology team can test a change in minutes, keep pre-announcement data locked down, and record every decision. Ask: what would you most like to see covered today? Pause and adapt."),
    ("cards", {
        ("TITLE", 0): "Every rebalance moves billions, yet runs on spreadsheets",
        ("BODY", 3): "Why now: more special rebalances, faster competitors, tougher benchmark oversight",
        ("SUBTITLE", 0): "Days per scenario",
        ("BODY", 0): "2-3 analyst-days to rebuild one scenario\nOnly 3-4 options reach the index committee\nLate surprises cost trust with ETF issuers",
        ("SUBTITLE", 1): "No audit trail",
        ("BODY", 1): "No record of who changed which rule, or why\nApprovals live in minutes and email\nErrors lead to corrections and restatements",
        ("SUBTITLE", 2): "MNPI at risk",
        ("BODY", 2): "Pre-announcement changes sit in shared files\nAnyone with the file sees the decision\nRegulators expect controlled access",
    }, "Recap what we heard in discovery. Each December reconstitution and every cap breach is rebuilt in spreadsheets, two to three analyst-days per scenario, so only a handful of options reach the committee. There is no audit trail, and pre-announcement numbers sit in files. Why now: a few megacaps now drive so much of the index that special rebalances are more frequent, competitors launch custom indexes in weeks, and benchmark regulation expects a documented process. Question to the room: which of these hurts most today?"),
    ("cards", {
        ("TITLE", 0): "What you're about to see: three stops, three KPIs",
        ("BODY", 3): "Watch for: KPIs moving live, the AI draft, what a non-cleared user can't see",
        ("SUBTITLE", 0): "1 · Scenario Lab",
        ("BODY", 0): "Change caps, liquidity floor and bands; stress-test a megacap\nKPI: time per scenario, days to minutes\nKPI: scenarios per cycle, 3-4 to 20+",
        ("SUBTITLE", 1): "2 · Compare & Approve",
        ("BODY", 1): "Scenario A vs B, AI impact summary, templated client notice\nSubmit and approve, recorded in Lakebase\nKPI: proposal-to-approval time",
        ("SUBTITLE", 2): "3 · Ask Genie",
        ("BODY", 2): "Plain-English questions on the same governed data\n\"Which removals have the highest ETF trading impact?\"\nKPI: analyst productivity, no SQL",
    }, "TELL before the demo. Stop 1: change the rules and watch who joins or leaves; the liquidity floor removes a name that would take about 769 days to trade. Stop 2: compare two scenarios, get the AI summary and a templated client notice, then submit and approve. Stop 3: ask Genie in plain English. Watch the KPIs move, and remember that a user who isn't cleared for MNPI sees the forecast masked by the platform. Then switch to the app."),
    ("two", {
        ("TITLE", 0): "~$0.75-1.0M a year, on a platform you can trust",
        ("BODY", 2): "Value is illustrative (discovery assumptions); trust points are measured",
        ("SUBTITLE", 0): "The value (illustrative)",
        ("BODY", 0): "Analyst time: ~$190-240k (4 analysts x 30% of time; scenario work cut ~80%)\nFewer corrections: ~$250-500k (from 2 to 1 or fewer a year, ~$250k each)\nFaster custom indexes: ~$300k pulled forward (3 launches a year, 2 months sooner)",
        ("SUBTITLE", 1): "Why you can trust it (measured)",
        ("BODY", 1): "Scenario recomputed in under 30 ms across 1,015 securities\n54 bad rows quarantined and 1 broken vendor file caught, out of 1.33M rows\n0 of 1,015 forecast probabilities visible to non-cleared users\nEvery scenario, approval and change recorded; AI drafts reviewed by a person",
    }, "TELL after the demo: land what it means for each leader. For the Head of Methodology: scenarios in minutes, more options per cycle, approvals with an audit trail. For the Head of the Index Business: fewer surprises for ETF issuers and faster custom index launches. Every value number shows its assumption, and I'm happy to replace them with your figures. Be honest about limits: the forecast is a watchlist, not a verdict, and every AI draft is reviewed by a person."),
    ("basic", {
        ("TITLE", 0): "Next step: run the December reconstitution through it",
        ("BODY", 1): "A 6-week pilot that shadows the 21 December 2026 reconstitution",
        ("BODY", 0): "Weeks 1-2: connect your security master, market data and index history; set entitlements\nWeeks 3-4: run the reconstitution scenarios in parallel with today's process\nWeeks 5-6: approvals live; compare results and timings with the spreadsheets\nSuccess: a scenario in under 5 minutes end to end · 20+ scenarios per cycle · zero MNPI exposure · Head of Methodology sign-off\nWe need: data access, two methodology analysts, an executive sponsor. Decision by 5 December.",
    }, "Close with a direct ask. Recap value per persona in one line each. Propose the bounded pilot that shadows the December reconstitution, with four measurable success criteria. Ask for a decision by 5 December so the pilot can run alongside the reconstitution. If the session ends early: headline result, value, the pilot, the ask."),
]


def main():
    p = g.get_presentation(PID)
    old = [s["objectId"] for s in p["slides"]]
    reqs, ids = [], []
    for i, (kind, ph, _) in enumerate(SLIDES):
        sid = f"nd_s{i}_{uuid.uuid4().hex[:6]}"
        ids.append(sid)
        maps = [{"layoutPlaceholder": {"type": t, "index": idx}, "objectId": f"{sid}_{t.lower()}_{idx}"} for (t, idx) in ph]
        reqs.append({"createSlide": {"objectId": sid, "insertionIndex": i, "slideLayoutReference": {"layoutId": L[kind]},
                                     "placeholderIdMappings": maps}})
    g.batch_update(PID, reqs)
    reqs = []
    for sid, (kind, ph, _) in zip(ids, SLIDES):
        for (t, idx), text in ph.items():
            reqs.append({"insertText": {"objectId": f"{sid}_{t.lower()}_{idx}", "text": text}})
    g.batch_update(PID, reqs)
    SIZE = {("CENTERED_TITLE", 0): 40, ("TITLE", 0): 28}
    reqs = []
    for sid, (kind, ph, _) in zip(ids, SLIDES):
        for (t, idx) in ph:
            if (t, idx) in SIZE:
                pt = SIZE[(t, idx)]
            elif kind == "title":
                pt = 18 if idx == 0 else 12
            elif (t == "BODY" and ((kind == "cards" and idx == 3) or (kind == "two" and idx == 2) or (kind == "basic" and idx == 1))):
                pt = 16
            elif t == "SUBTITLE":
                pt = 18
            else:
                pt = 15
            oid = f"{sid}_{t.lower()}_{idx}"
            reqs.append({"updateTextStyle": {"objectId": oid, "style": {"fontSize": {"magnitude": pt, "unit": "PT"}},
                                             "textRange": {"type": "ALL"}, "fields": "fontSize"}})
            if t == "BODY" and pt == 15:
                reqs.append({"updateParagraphStyle": {"objectId": oid, "textRange": {"type": "ALL"},
                                                      "style": {"spaceBelow": {"magnitude": 12, "unit": "PT"}, "lineSpacing": 110},
                                                      "fields": "spaceBelow,lineSpacing"}})
    g.batch_update(PID, reqs)
    g.batch_update(PID, [{"deleteObject": {"objectId": o}} for o in old])
    # speaker notes
    p = g.get_presentation(PID)
    reqs = []
    for s, (_, _, notes) in zip(p["slides"], SLIDES):
        nid = s["slideProperties"]["notesPage"]["notesProperties"]["speakerNotesObjectId"]
        reqs.append({"insertText": {"objectId": nid, "text": notes}})
    g.batch_update(PID, reqs)
    print(json.dumps({"presentation": PID, "slides": len(p["slides"]),
                      "url": f"https://docs.google.com/presentation/d/{PID}/edit"}))


if __name__ == "__main__":
    main()
