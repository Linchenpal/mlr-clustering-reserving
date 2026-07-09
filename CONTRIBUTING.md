# Contributing — Git basics for this project

You don't need to know Git deeply to contribute. Here's the minimum loop.

## One-time setup

1. Install Git: https://git-scm.com/downloads
2. Get access to the repo on GitHub (ask Lina/Sarah to add you as a collaborator,
   or fork it if it's public).
3. **Clone it** — this downloads a full copy to your computer:
   ```bash
   git clone https://github.com/<org-or-user>/mlr-clustering-reserving.git
   cd mlr-clustering-reserving
   ```

## Everyday workflow

1. **Pull the latest changes** before you start working, so you're not out of date:
   ```bash
   git pull
   ```
2. **Create a branch** for whatever you're working on (keeps your changes separate
   until they're ready):
   ```bash
   git checkout -b your-name/short-description
   # e.g. git checkout -b luca/kmeans-first-pass
   ```
3. Make your changes (edit notebooks, add code, etc).
4. **Stage and commit** — this saves a snapshot with a message explaining what changed:
   ```bash
   git add .
   git commit -m "Add first K-means pass on SPLICE data"
   ```
5. **Push** your branch to GitHub:
   ```bash
   git push -u origin your-name/short-description
   ```
6. On GitHub, open a **Pull Request** (PR) from your branch into `main`. This is
   where others can review and comment before it's merged in.

## Quick glossary

| Term | Meaning |
|---|---|
| Clone | Download a copy of the repo to your machine |
| Pull | Fetch and merge the latest changes from GitHub |
| Branch | A separate line of work so you don't affect `main` directly |
| Commit | A saved snapshot of your changes, with a message |
| Push | Upload your commits to GitHub |
| Pull Request (PR) | A request to merge your branch into `main`, open for review |

## A few habits worth keeping

- Commit often, with clear messages — small commits are easier to review and undo.
- Don't commit raw data files or credentials — see `.gitignore`.
- If you're unsure, open a PR early (even unfinished) and ask for input rather
  than sitting on changes locally.
- If Git ever gets confusing, GitHub Desktop (https://desktop.github.com/) gives
  a visual interface for all of the above instead of the command line.
