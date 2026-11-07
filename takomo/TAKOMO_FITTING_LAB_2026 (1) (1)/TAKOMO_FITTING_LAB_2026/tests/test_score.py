import pandas as pd
import pytest
from takomo_fit import score as S

LAB = pd.DataFrame([dict(golfer_id="G1", ref_head="201-mkii", ref_head_2="101-mkii", ref_flex="regular",
                         ref_material="steel", ref_shaft_model="KBS Tour", ref_shaft="kbs-tour-regular",
                         ref_length_in=0.5, ref_lie_deg=1, ref_grip="midsize", ref_purchase="custom",
                         ref_handedness="right", close_call_head=False, close_call_flex=False,
                         close_call_length=True, close_call_lie=False, close_call_grip=False)])


def P(**kw):
    d = dict(golfer_id="G1", head="201-mkii", shaft="kbs-tour-regular", length_in=0.5, lie_deg=1,
             grip="midsize", purchase="custom", handedness="right")
    d.update(kw)
    return pd.DataFrame([d])


def test_perfect_is_100():
    assert S.summary(P(), LAB)["spec_agreement_score"] == 100


def test_close_call_adjacent_gets_full_credit_and_others_do_not():
    assert S.score_frame(P(length_in=0.0), LAB)["length"].iloc[0] == 1.0
    assert S.score_frame(P(lie_deg=0), LAB)["lie"].iloc[0] == 0.0


def test_runner_up_head_half_credit():
    assert S.score_frame(P(head="101-mkii"), LAB)["head"].iloc[0] == 0.5


def test_missing_prediction_scores_zero():
    empty = pd.DataFrame(columns=["golfer_id", "head", "shaft", "length_in", "lie_deg", "grip", "purchase", "handedness"])
    assert S.summary(empty, LAB)["spec_agreement_score"] == 0


def test_unbuildable_spec_scores_zero():
    # KBS C-Taper is only offered on the 301 heads
    assert S.summary(P(shaft="kbs-c-taper-regular"), LAB)["spec_agreement_score"] == 0
    assert S.summary(P(shaft="no-such-shaft"), LAB)["spec_agreement_score"] == 0
    assert S.summary(P(lie_deg=4), LAB)["spec_agreement_score"] == 0


def test_spelling_and_units_are_normalised():
    assert S.summary(P(head="201-MKII", handedness="Right", length_in='0.5"'), LAB)["spec_agreement_score"] == 100


def test_missing_column_is_a_clear_error():
    with pytest.raises(ValueError, match="missing columns"):
        S.summary(P().drop(columns=["purchase"]), LAB)


def test_flex_close_call_accepts_the_whole_alternative_shaft():
    lab = LAB.copy()
    lab["close_call_flex"] = True
    lab["ref_shaft_alt"] = "kbs-tour-stiff"
    f = S.score_frame(P(shaft="kbs-tour-stiff"), lab).iloc[0]
    assert f.flex == 1 and f.material == 1 and f.shaft_model == 1
    f = S.score_frame(P(shaft="kbs-tour-lite-stiff"), lab).iloc[0]     # neighbouring flex, other model
    assert f.flex == 1 and f.shaft_model == 0


def test_duplicates_rejected_in_python_api():
    with pytest.raises(ValueError, match="duplicate"):
        S.summary(pd.concat([P(), P()]), LAB)


def test_purchase_must_follow_from_the_spec():
    lab = LAB.copy()
    lab["ref_purchase"] = "stock"; lab["ref_lie_deg"] = 0; lab["ref_length_in"] = 0.0; lab["ref_grip"] = "midsize"
    ok = S.score_frame(P(lie_deg=0, length_in=0.0, grip="midsize", purchase="stock"), lab).iloc[0]
    assert ok.purchase == 1                                    # midsize grip is stock
    bad = S.score_frame(P(lie_deg=0, length_in=0.0, grip="oversize", purchase="stock"), lab).iloc[0]
    assert bad.purchase == 0                                   # oversize cannot be stock
