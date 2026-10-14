# Contributions

1. Use your own exact-version APK; regenerate targets locally. Never commit APKs, game assets, binaries, generated target assembly or bulk decompiler output.
2. Pick one named function or tool defect. Describe its inputs, completion checks and unresolved boundaries before expanding scope. Use a branch and pull request; disclose AI assistance and review every proposed change.
3. Compile/diff after changes. Include the manifest identity, candidate source hash, profile, byte comparison and reproduction command. An objdiff percentage alone is not acceptance.
4. Re-run all previous exact matches after shared-header changes. No inline assembly, embedded original instructions, copied binary fallback, fake expected values or adjusted reference addresses to obtain a match.
5. State whether evidence proves native bytes, inferred semantics or observed device behavior. A local match does not close runtime, dependency or broader recovery gaps.

Public CI uses synthetic ARM64 fixtures and does not have an APK. Real-APK checks run only after maintainer review of changes, in a compiler environment without account credentials. Build-script or target-manifest changes require explicit review; do not automatically run untrusted PR scripts on the research server. All merges remain manual.

MIT applies to newly authored tooling and synthetic tests. Recovered game material and third-party components are distinguished and are not relicensed by that tooling license.
