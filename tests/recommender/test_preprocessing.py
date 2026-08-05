from recommender.preprocessing import (
    clean_text,
    preprocess_incoming_email,
    remove_signature_and_disclaimers,
    strip_html,
    strip_quoted_history,
)


def test_strip_html_removes_tags_and_decodes_entities():
    raw = "<p>Hello &amp; welcome</p><br><div>Second line</div>"
    result = strip_html(raw)
    assert "<" not in result
    assert "Hello & welcome" in result
    assert "Second line" in result


def test_strip_html_is_noop_on_plain_text():
    raw = "Just a plain email with no markup at all, spanning enough characters."
    assert strip_html(raw) == raw


def test_remove_signature_cuts_at_signoff():
    raw = (
        "Hi team, following up on the claim denial from last week, any updates "
        "on the resubmission status would be appreciated.\n"
        "Best regards,\nJane Doe\nBilling Manager"
    )
    result = remove_signature_and_disclaimers(raw)
    assert "Jane Doe" not in result
    assert "following up on the claim denial" in result


def test_remove_signature_does_not_cut_short_email_starting_with_signoff_word():
    raw = "Thanks - go ahead and process the adjustment as discussed."
    result = remove_signature_and_disclaimers(raw)
    assert "process the adjustment" in result


def test_clean_text_normalizes_whitespace():
    raw = "Line one\n\n\n\nLine two   with    extra   spaces"
    result = clean_text(raw)
    assert "\n\n\n" not in result
    assert "   " not in result


def test_preprocess_incoming_email_builds_embedding_text():
    email = preprocess_incoming_email(
        subject="RE: Claim denied - timely filing",
        body="Any update on this?",
        sender_email="Billing@ExampleClinic.COM",
    )
    assert email.sender_email == "billing@exampleclinic.com"
    assert "Claim denied - timely filing" in email.embedding_text
    assert "Any update on this?" in email.embedding_text


def test_embedding_text_includes_subject_even_with_re_prefix():
    email = preprocess_incoming_email(
        subject="Re: Modifier 25 denial",
        body="Any update?",
        sender_email="ar@metrocardiologypartners.com",
    )
    assert email.embedding_text == "Re: Modifier 25 denial\n\nAny update?"


def test_embedding_text_omits_blank_subject():
    email = preprocess_incoming_email(subject="   ", body="Any update?", sender_email="a@b.com")
    assert email.embedding_text == "Any update?"


def test_strip_html_skips_blockquote_content():
    raw = (
        "<div>New message about claim 81044, please advise on status.</div>"
        "<blockquote>Old thread: previous unrelated claim 55555 details here.</blockquote>"
    )
    result = strip_html(raw)
    assert "claim 81044" in result
    assert "55555" not in result


def test_strip_html_skips_gmail_quote_class_div():
    raw = (
        "<div>Any update on the appeal for Jane Smith?</div>"
        '<div class="gmail_quote">On Mon, Jul 28, 2026, Bob wrote: original appeal details</div>'
    )
    result = strip_html(raw)
    assert "Any update on the appeal" in result
    assert "original appeal details" not in result


def test_strip_html_separates_adjacent_table_cells():
    raw = "<table><tr><td>Claim #</td><td>81044</td></tr></table>"
    result = strip_html(raw)
    assert "Claim #81044" not in result


def test_strip_quoted_history_removes_plain_text_quote_block():
    raw = (
        "Hi, just checking in on claim #81044, any update on the resubmission?\n\n"
        "> On Jul 20, 2026, Support wrote:\n"
        "> We are still reviewing claim #81044 for timely filing.\n"
        "> Please allow 5-7 business days.\n"
    )
    result = strip_quoted_history(raw)
    assert "checking in on claim #81044" in result
    assert "still reviewing" not in result


def test_strip_quoted_history_removes_on_wrote_preamble():
    raw = (
        "Attaching the physical therapy notes you requested for the MRI appeal.\n\n"
        "On Mon, Jul 28, 2026 at 3:04 PM, Support <support@rcmsupport.internal> wrote:\n"
        "Please send the PT notes to proceed with the appeal.\n"
    )
    result = strip_quoted_history(raw)
    assert "Attaching the physical therapy notes" in result
    assert "Please send the PT notes" not in result


def test_strip_quoted_history_removes_original_message_banner():
    raw = (
        "Please add this to the batch you are already correcting for modifier 25.\n\n"
        "-----Original Message-----\n"
        "From: Support\nSent: Monday\nSubject: Modifier 25 denial\n"
        "We found the missing modifier issue on claim 12345.\n"
    )
    result = strip_quoted_history(raw)
    assert "add this to the batch" in result
    assert "missing modifier issue" not in result


def test_strip_quoted_history_removes_forwarded_message_banner():
    raw = (
        "FYI, forwarding this from our front desk regarding claim 99887.\n\n"
        "---------- Forwarded message ---------\n"
        "From: Front Desk <frontdesk@example.com>\n"
        "Date: Mon, Jul 20, 2026\n"
        "Subject: Claim denied\n"
        "The claim was denied for missing documentation.\n"
    )
    result = strip_quoted_history(raw)
    assert "forwarding this from our front desk" in result
    assert "missing documentation" not in result


def test_strip_quoted_history_removes_pasted_header_block():
    raw = (
        "See below for the original request, can you check on this again please.\n\n"
        "From: Jane Doe <jane@clinic.com>\n"
        "Sent: Monday, July 20, 2026 3:04 PM\n"
        "To: RCM Support <support@rcmsupport.internal>\n"
        "Subject: RE: Claim denied - timely filing\n\n"
        "Any update on claim #81044?\n"
    )
    result = strip_quoted_history(raw)
    assert "check on this again" in result
    assert "Any update on claim #81044" not in result


def test_strip_quoted_history_is_noop_without_quote_markers():
    raw = "This is a brand new issue about eligibility verification for a new patient."
    assert strip_quoted_history(raw) == raw


def test_clean_text_preserves_identifiers_through_full_pipeline():
    raw = (
        "<div>Hi team, following up on Claim #81044 for Patient ID: 456789, "
        "reference CLM-100 as discussed.</div>"
        "<blockquote>Old unrelated thread about claim 22222</blockquote>"
        "<div>Best regards,</div><div>Jane Doe</div>"
    )
    result = clean_text(raw)
    assert "Claim #81044" in result
    assert "Patient ID: 456789" in result
    assert "CLM-100" in result
    assert "22222" not in result
    assert "Jane Doe" not in result
