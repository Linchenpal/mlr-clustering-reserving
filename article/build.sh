#!/usr/bin/env bash
# Build the article with citations resolved (pdflatex -> biber -> pdflatex x2).
set -e
cd "$(dirname "$0")"
pdflatex -interaction=nonstopmode main.tex
biber main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
