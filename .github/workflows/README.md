# GitHub Actions

- `site-data.yml` collects validated SC and HC data twice daily, updates the
  split datasets, captures monthly/final snapshots, and updates the history
  manifest. It can also be started manually. It uses Python 3.12.
- `daily-qords-ranking.yml` updates the separately generated ranking pages.
- `static.yml` publishes the default branch on normal pushes, manual dispatch,
  and successful completion of either data workflow. The `workflow_run`
  trigger is needed because pushes made using `GITHUB_TOKEN` do not normally
  trigger a push workflow.

The two data-writing workflows share a concurrency group to avoid pushing from
the same old commit simultaneously. GitHub may delay or skip scheduled runs;
monitor workflow failures. Site behavior is configured in `site_config.json`;
see the repository README for freeze and archive semantics.
