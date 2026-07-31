# Compatibility package for the legacy GitHub Pages project

Status: `PREPARED_NOT_DEPLOYED`.

This directory is not part of the target Pages root. Copy its redirect HTML
files to the old repository only after the new target returns HTTP 200 and a
typed external Pages receipt exists.

Required order:

1. Create `m72692591-collab/praxelta-services`.
2. Deploy and verify `https://m72692591-collab.github.io/praxelta-services/`.
3. Run `validate_praxelta_pages_migration.ps1 -Mode Deploy -TargetPagesReceipt <path>`.
4. Only then deploy this directory's HTML files to the legacy repository.

Never delete the old repository before redirects and inbound-link monitoring
have completed.
