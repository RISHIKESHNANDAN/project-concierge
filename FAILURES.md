# FAILURES.md - Failure and Recovery Log

Log every break, surprise, or abandoned approach: **what happened / what I believed / what I tried / what I learned.**
Only write real entries from your own runs. Nothing below is pre-filled on purpose.

## Template
### YYYY-MM-DD - short title
- What happened:
- What I believed:
- What I tried:
- What I learned:

## Things worth checking early (hypotheses, not results)
- Does ABSTAIN_DISTANCE separate unanswerable from answerable questions, or do they overlap?
- Does the refund-time conflict (refund_policy 5-7 days vs help_center_faq 3-5 days) resolve correctly?
- Does the regex guard have false positives on normal customer messages?
- Does the emotional-keyword escalation over-trigger?




### Q48 wrong eval label
- What happened: Q48 failed even though the system answered correctly.
- What I believed: ORD-1003 would be "not cancellable".
- What I tried: read the mock order data; ORD-1003 is "processing", so it is cancellable.
- What I learned: the eval set can be wrong too. Check the label before blaming the system.

### Q27 vague question answered
- What happened: "How long does it take?" was answered instead of abstained (top-1 distance 0.454, under the gate).
- What I believed: the distance gate would catch low-information questions.
- What I tried: added a prompt rule for questions too vague to identify a topic.
- What I learned: a retrieval distance can't detect vagueness, because a vague query still resembles some document.