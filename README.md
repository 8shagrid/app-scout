# App Scout

App Scout is a market intelligence tool designed for Google Play Store developers and researchers. It helps identify market gaps (Blue Ocean) and analyze competitors using data scraping and automated analysis.

## Features

### Market Gap Hunter
*   **Keyword Analysis**: Bulk search and analyze statistics for specific keywords.
*   **Opportunity Detection**: Automatically identifies "Lite Targets" (heavy apps with high installs) and "Low Quality" competitors (high installs, low ratings).
*   **ASO Difficulty Score**: Estimates the effort required to rank based on competitor metadata.
*   **Decision Support**: Provides "Go/No-Go" recommendations based on market saturation and demand.

### Competitor Spy
*   **Deep Analysis**: Fetches detailed app information, including installs, ratings, and update history.
*   **Sentiment Trends**: Visualizes rating changes over time to detect declining app quality.
*   **Review Analysis**: Uses N-grams and Topic Clustering to categorize user complaints (e.g., Bugs, Ads, UI/UX).
*   **Strategic Insights**: Generates actionable advice on how to outperform specific competitors.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/8shagrid/app-scout.git
    cd app-scout
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the application using Streamlit:

```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`.

## Technologies

*   Python
*   Streamlit
*   Pandas & Plotly
*   Google Play Scraper
*   TextBlob & NLTK
