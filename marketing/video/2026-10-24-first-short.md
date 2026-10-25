# MAESTRO: video pilot — 2026-10-24

## Goal
Create original faceless educational Shorts to attract paid implementation inquiries for MAESTRO. No paid ads. No fake client results, fabricated integrations, client data, or copied videos.

## First video (production request submitted)
- Topic: Your Telegram bot is matching the wrong customers? Here is the fix.
- Audience: English-speaking SMB owners / automation buyers.
- Format: 9:16, 30–60 sec, English narration, animated conceptual demo.
- Status as of 2026-10-24: Motion rendering **queued**, not yet published.
- Production session: https://motion.so/agent?chat=c1e3ee1e-79b3-42de-baa4-494a7843436e
- Do not claim the video is published until an actual public URL and platform ID are verified.

## Technical accuracy review
1. chat_id is a Telegram conversation identifier, NOT an Airtable record identifier.
2. Do not pair by name, handle, email without validation.
3. Generate random, single-use, short-lived pairing codes, store only hashes where practicable, enforce expiry + anti-brute-force limits.
4. Verify code server-side, atomically associate Airtable contact/internal ID with the intended Telegram chat_id.
5. Add duplicate protection and revocation/re-binding flows.
6. Synthetic examples only; illustrative animation is not proof of a deployed integration.

## 45-second original English narration draft
**0:00–0:06** — “Is your Telegram bot sending messages to the wrong customer?”
**0:06–0:13** — “A common mistake is treating a Telegram chat ID like an Airtable record ID, or matching on a display name.”
**0:13–0:23** — “Instead, issue a unique, short-lived, one-time pairing code for each customer.”
**0:23–0:31** — “The user enters it in Telegram. Your backend verifies the code and stores the verified customer-to-chat mapping.”
**0:31–0:39** — “Now future notifications use that validated mapping. Add expiry, retry limits and an easy way to revoke.”
**0:39–0:45** — “Need a reliable Airtable–Telegram workflow? MAESTRO builds careful business automation.”

## Upload metadata
**Short title:** Telegram Bot Sending Messages to the Wrong Person? Fix the Matching
**Description:**
A reliable Airtable ↔ Telegram integration must correctly bind each customer to their Telegram chat, not rely on matching names or mixing IDs. This video explains one-time-code verification using a conceptual (synthetic) example. Need help with automations? Visit MAESTRO: https://m72692591-collab.github.io/praxelta-services/
**Tags:** #TelegramBot #Airtable #Automation #SmallBusiness #MAESTRO

## Acceptance / publication gates
- [ ] Watch finished render for factual errors, subtitles, licensing and legibility.
- [ ] Remove/repair misleading elements before distribution.
- [ ] Connect channel through permitted OAuth / platform access; do not share passwords.
- [ ] Confirm publishing API access and platform restrictions for this account.
- [ ] Upload with disclosure if platform rules require it.
- [ ] Log exact platform URL, ID, date, unique click/lead source, inquiries, and paid orders.

## Initial measurement
Track weekly: published clips, impressions, average view duration, profile views, site referrals, qualified inquiries, and **confirmed paid orders**. No positive ROI claims before measured evidence.

## Budget
No paid ads or credit purchases authorized. Stop if a service requests payment. Existing account credits, if any, must be monitored separately. Avoid running idle GitHub Actions or uncontrolled recurring jobs.
