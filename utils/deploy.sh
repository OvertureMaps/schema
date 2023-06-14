# The deploy script that prepares the schema-wg/main repository to publish at schema/main

# 1. Create a new branch for publishing
git branch -D "release-schema"
git checkout -b "release-schema"

# 2. Remove extra github workflows
git rm .github/workflows/github-actions-copy-latest-docs-to-staging.yaml
git rm .github/workflows/github-actions-copy-pr-docs-to-staging.yaml

# 3. Remove ISSUE_TEMPLATE
git rm .github/ISSUE_TEMPLATE/*

# 4. Remove other irrelevant files
git rm submission_process.svg

# 5. Temporary: empty the repository
git rm GLOSSARY.md
git rm LICENSE
git rm README.md
git rm SCHEMA_CONVENTIONS.md

git rm -r utils/*
git rm -r docusaurus/*
git rm -r examples/*
git rm -r counterexamples/*
git rm -r schema/*
git rm -r task-force-docs/*

git status
git commit -am "Ready for publication to schema/main"

git remote add public git@github.com:overturemaps/schema.git
git push --set-upstream public
