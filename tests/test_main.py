from main import dedupe, generate


def test_labels_do_not_drive_dedupe_or_ranking():
    rows = generate()
    first = [a["id"] for a in dedupe(rows)]
    for row in rows:
        row["true_positive"] = not row["true_positive"]
        row["incident"] = "ignored"
    assert [a["id"] for a in dedupe(rows)] == first


def test_high_severity_representative_and_collision_are_explicit():
    selected = dedupe(generate())
    collision = [a for a in selected if a["asset"] == "SYN-COLLISION"]
    assert len(collision) == 1 and collision[0]["severity"] == 9
    assert selected[0]["severity"] >= selected[-1]["severity"]
