from creatorsignal.dna.formats import (
    EXTENDED,
    LONG_FORM,
    NON_REEL,
    SHORT_FORM,
    STANDARD,
    TUTORIAL_STYLE,
    UNKNOWN_DURATION,
    tag_format,
)


def test_tag_format_non_reel_media_type():
    assert tag_format(media_product_type="IMAGE", duration_seconds=20, caption=None) == NON_REEL


def test_tag_format_tutorial_marker_takes_priority():
    result = tag_format(
        media_product_type="REELS", duration_seconds=45, caption="Tutorial: how to do X"
    )
    assert result == TUTORIAL_STYLE


def test_tag_format_unknown_duration():
    result = tag_format(media_product_type="REELS", duration_seconds=None, caption="hi")
    assert result == UNKNOWN_DURATION


def test_tag_format_duration_buckets():
    assert tag_format(media_product_type="REELS", duration_seconds=10, caption=None) == SHORT_FORM
    assert tag_format(media_product_type="REELS", duration_seconds=25, caption=None) == STANDARD
    assert tag_format(media_product_type="REELS", duration_seconds=45, caption=None) == EXTENDED
    assert tag_format(media_product_type="REELS", duration_seconds=90, caption=None) == LONG_FORM
