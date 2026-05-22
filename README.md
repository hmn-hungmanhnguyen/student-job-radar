# Student Job Radar

Student Job Radar is an automated public job-monitoring tool for student assistant positions at the University of Duisburg-Essen.

The project reads the official UDE SHK RSS feed, downloads attached PDF job descriptions, extracts useful information such as deadlines and contact emails, and publishes the result into a public Google Sheet that updates automatically through GitHub Actions.

## Public Sheet

[Open the public Google Sheet](https://docs.google.com/spreadsheets/d/12DHXo1gfbXLHJl6y_2v1AzLuqhfd1qFVlCPZk9XtjJ0/edit?usp=sharing)

## Motivation

Student job postings are often scattered across university pages and PDF files. Checking them manually is slow, easy to forget, and inconvenient for students who want to monitor new SHK opportunities.

This project turns that process into a small automated pipeline.

## What It Does

The pipeline performs the following steps:

```text
RSS feed
→ PDF download
→ PDF text extraction
→ structured job table
→ Google Sheets publishing
→ scheduled GitHub Actions update
```
