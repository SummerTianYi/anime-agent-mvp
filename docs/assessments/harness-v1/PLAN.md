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

## Progress

- [x] Read actual source/overlay and V0 REVIEW; baseline tests.
- [ ] Calibrate grader/offline regrade.
- [ ] Mainline implementation and regression gates.
- [ ] Four interaction fixes and tests.
- [ ] Dual-model frozen core trials.
- [ ] Adversarial review and recorded retests.
- [ ] Authorized desktop activation and immediate owner notice.
- [ ] Owner feedback, report, commit/push/remote verification.
