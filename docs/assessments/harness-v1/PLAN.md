# Harness V1 implementation — Codex

Manager instruction: implement the shared Harness and four interaction repairs; candidate only, independent branch, no main merge.

## Scope and gates

- V0 `559404f29ca255448f490615f5e52cb27dc58d3e` evidence/cases/results/scripts are immutable.
- Production HEAD `d3ed6d68f2509ad51bea15cf8224c5f3a165d957` has local connection fixes. Preserve production files; carry main/provider_http and their tests, start-mvp and example config into this branch before V1 changes. Runtime hashes must match the V0 overlay before implementation.
- Baseline: isolated Core 307 tests passed, 22.834 seconds, 2026-10-04. No production service/DB/window touched.
- First calibrate facts, confirmation/receipt association, contradictory success and timeout classification using V0 evidence. Write regrades only under V1.
- Implement authorization/receipt/queue, result continuation/resource content, recall/task context and shared persona; then manual-only STT with stale-result guards, simplified input, 600-second idle episodes, and effort budgets.
- Freeze core cases and grading before live model runs. Same scenarios and initial fixtures; three repetitions per model. Preserve first failures and separately label repair retests.
- After basic regression and execution-safety gates pass, normal official-entry desktop restart is authorized. Notify owner immediately with active version; request real voice, tier and real 10-minute idle feedback.
- Candidate frozen adversarial verification: independent reviewer if available, otherwise explicitly self-review. No real email send or remote business writes.
- Commit/push independent branch and verify remote SHA; Manager decides final acceptance.

## API registration (before any V1 real request)

Expected 600–850 HTTP requests; **hard cap 1,100** across probes, formal trials and explicitly labelled repair/adversarial tests. Reserve before wire; adapter retries count. Per trial at most 20 HTTP, 6 user/confirmation turns, 240 seconds; bounded task budgets remain equal across models. Stop on auth/rate limit and on three consecutive external failures. No automatic replacement of failing samples.

Read exact IDs and gateway from current sanitized configuration: Deepseek-v4-flash and GLM-5.2 via OpenAI-compatible WeChat gateway. No unverified reasoning parameter will be sent. Current gateway reasoning control is not certified; effort initially controls shared bounded execution budgets, with model controls explicitly reported unsupported/unverified, not simulated by forced sentence style.

## Protected surfaces

Production private configuration/data and uncommitted work are preserved. No model, animation, voice asset, TTS implementation, historical chat or memory deletion. Synthetic fixtures only. V0 bytes never rewritten. Real service connectivity is separate from controlled MCP results.

## Repair batch registration (before any repair batch API request)

`repair-01`: F02,F03,F04,F05,F07,M02,M03,M04,M05,G02,G03,G05,P01,P02, both models three times (84 runs). This covers the execution/authorization/receipt surface changed by independent review and F04 follow-up, plus shared JSON display recovery for literal newlines observed in P01/P02. Persona cases were added before any repair-batch request, because raw model identity content existed but was discarded by parsing. Includes the known first-batch failures, all three task types, rejection, cancellation, parameter edits, multiple actions and connector failure. Same frozen cases/criteria/fixtures and per-trial budgets. The other 12 cases are not resampled just for a better score; their core-01 results retain that source version. Estimated additional 300–400 HTTP, still inside the original global cap 1,100; no counter reset. One model worker at a time, only after core-01 ends. Any interruption or remaining gap is reported, not silently replaced.

Final idle delivery follow-up is self-reviewed (not attributed to the closed independent reviewer): a new regression first reproduced rejection of the second part of one idle utterance. The fix leases the reminder by utterance and idle episode, preserves same-ID playback recovery, and clears speaking state after local cancellation. TTS implementation is untouched. This local-only follow-up sends zero model requests.

Owner follow-up (2026-10-04): change quiet hours to 01:00–07:00. Apply through production .env (`ANIME_AGENT_QUIET_START/END`) and normal official-entry restart; do not disable DND or change the 600-second episode rule. This configuration-only change does not alter frozen model cases or runtime source.

## Progress

- [x] Read actual source/overlay and V0 REVIEW; baseline tests.
- [x] Calibrate grader/offline regrade (21 legacy + 7 native receipt calibration controls).
- [x] Mainline implementation and regression gates (350 isolated unit tests).
- [x] Four interaction fixes and automated tests (human checks remain separate).
- [ ] Dual-model frozen core trials.
- [x] Independent adversarial review and recorded retests (five P1 findings, 11 regression scenarios).
- [ ] Authorized desktop activation and immediate owner notice.
- [ ] Owner feedback, report, commit/push/remote verification.
