# BlockReel distribution

The four Agent Skills, local renderer, GitHub Actions, and gallery are maintained on `main`. Use the [installation guide](../README.md#quick-start), [skills.sh listing](https://www.skills.sh/viniciusnoetzold/mine-blockreel-skill), or [film gallery](https://viniciusnoetzold.github.io/mine-blockreel-skill/) when sharing BlockReel.

## Claude directory source

The directory checks the archive of the selected Git ref, including files outside the plugin folder. Its 50 MiB archive limit calls for a separate package because the gallery videos are stored in the project repository. The tag `claude-directory-v0.7.1` points to a lightweight snapshot containing the four skills and their renderer. [Directory checklist](https://claude.com/docs/plugins/pre-submission-checklist#repository-and-folder-layout) · [Source tag](https://github.com/ViniciusNoetzold/mine-blockreel-skill/tree/claude-directory-v0.7.1)

In the [Claude developer portal](https://claude.ai/directory/manage), choose **Plugin bundle**, enter `ViniciusNoetzold/mine-blockreel-skill` as the repository, select `claude-directory-v0.7.1` in **Branch or tag**, and leave **Plugin path** blank. The manifest is at the root of the snapshot. [Submission instructions](https://claude.com/docs/plugins/submit)

For a future version, run the packaging tool after committing the source.

```bash
python tools/package_claude_directory.py --ref HEAD --out work/claude-directory.zip
```

The command prints the snapshot commit and writes a ZIP. It builds the snapshot with a temporary Git index. Validate the extracted plugin using `claude plugin validate`, then tag the printed commit and select the new tag in the portal.
