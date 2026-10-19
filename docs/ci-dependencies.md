# CI action verification

Checked against official GitHub releases on 2026-10-19. Actions are pinned to full commits rather than mutable major tags; hosted runners supply Node 24 for these versions. Checkout does not persist its token in Git configuration, and the workflow has read-only repository contents permission. No `pull_request_target` execution is used.

| Action | Reviewed release | Pinned commit |
| --- | --- | --- |
| actions/checkout | [v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1) | [3d3c42e5aac5ba805825da76410c181273ba90b1](https://github.com/actions/checkout/commit/3d3c42e5aac5ba805825da76410c181273ba90b1) |
| actions/setup-python | [v7.0.0](https://github.com/actions/setup-python/releases/tag/v7.0.0) | [5fda3b95a4ea91299a34e894583c3862153e4b97](https://github.com/actions/setup-python/commit/5fda3b95a4ea91299a34e894583c3862153e4b97) |
| actions/upload-artifact | [v7.0.2](https://github.com/actions/upload-artifact/releases/tag/v7.0.2) | [cf430e030ddbb5b0abf93d22962f4752f3646cd9](https://github.com/actions/upload-artifact/commit/cf430e030ddbb5b0abf93d22962f4752f3646cd9) |

The versions were reviewed from primary upstream action manifests and release commit links. This record verifies dependency identity, not successful execution of the matrix; run evidence remains separate. Public Release tooling requires all 12 actual matrix jobs for the exact pushed source commit to succeed.
