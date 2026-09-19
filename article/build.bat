@echo off
REM Build the article with citations resolved (pdflatex -> biber -> pdflatex x2).
REM Double-click, or run from a terminal:  build.bat
REM The references use biblatex with the Biber backend, so a single
REM pdflatex pass leaves every citation as "(?)" until Biber has run.
cd /d "%~dp0"
pdflatex -interaction=nonstopmode main.tex
biber main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
pause
