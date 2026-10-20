# Archive: what no requirement names

Not linked to any requirement; kept out of the published design since v4.0.

Since v4.0 the design (`design/`) holds only what serves a requirement or an acceptance criterion of `requirements/`,
and every design page names the requirements it serves under its title. What the review for v4.0 found serving none
of them is kept here, as Markdown, so that nothing is lost and a human can turn any of it back into a requirement:

- whole pages keep their file name: `7.1-implementation-project-and-acceptance-testing.md` (the build tenant, the
  phases, the security reviews, the company's firewall options and the connection readiness gate),
  `7.4-outlook-2030-and-the-options-kept-open.md` (the bets, the trends, the rule for adding a feature, the options
  kept open and the roadmap watch list) and `7.5-other-clouds-and-exit.md` (what replaces the Azure specifics in
  another cloud, sovereignty and exit, adding a cloud; its data services moved to design section 1.3, which R16 needs);
- the decision log and the open questions, `7.2-decisions.md` (decisions D01-D84 with their options, the capability
  and verification matrix V03-V32, the human sign-offs H01-H15) and `7.3-open-questions.md` (the features still to weigh, Q01 onwards), left the
  design in v4.0: the design states only what is chosen, so these are kept for history only;
- sections moved out of a page that stays are in `<page-number>-<slug>-sections.md`, one heading per section.

The folder is excluded from the site (`_config.yml`) and from the PDFs, and `scripts/check.sh` fails when a published
page links into it. Its own links may point anywhere and are not checked; they were rewritten to `../design/` when
the pages moved, so most still resolve on GitHub. Content comes back only through a requirement: a human changes
`requirements/` first, and the design follows it in its own pull request ([0.1 How we work](../requirements/0.1-how-we-work.md)).
