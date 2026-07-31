"""
Overlap Assessment Service Dual Testing script

Takes collated output of main.py and creates figures for the overlap service within the DCAT service
"""

# Author: Alex Wallage
# Version: 1
# Date: 14/07/2026

## Enhanced with AI

from datetime import date

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from scipy.stats import linregress, t


# ------------------------------------------------------------------
# Load and manipulate data
# ------------------------------------------------------------------

df = pd.read_csv("data/OverlapAssessmentDualTesting.csv")

# Convert YYWK format (e.g. 2543 -> 2025 week 43)
df["Week"] = df["Week"].astype(str)

df["Year"] = "20" + df["Week"].str[:2]
df["ISO_Week"] = df["Week"].str[2:].astype(int)

df["Date"] = df.apply(
    lambda row: date.fromisocalendar(
        int(row["Year"]),
        int(row["ISO_Week"]),
        1,  # Monday of ISO week
    ),
    axis=1,
)

df["SuccessPct"] = df["Overlaps classified successfully"] * 100

df = df.sort_values("Date")


# ------------------------------------------------------------------
# Linear regression
# ------------------------------------------------------------------

x = mdates.date2num(df["Date"])
y = df["SuccessPct"]

slope, intercept, r_value, p_value, std_err = linregress(x, y)

y_pred = intercept + (slope * x)

r_squared = r_value**2


# ------------------------------------------------------------------
# 95% Prediction Interval
# ------------------------------------------------------------------

n = len(x)

residuals = y - y_pred

s_err = np.sqrt(
    np.sum(residuals**2) / (n - 2)
)

x_mean = np.mean(x)

t_value = t.ppf(0.975, n - 2)

prediction_band = (
    t_value
    * s_err
    * np.sqrt(
        1
        + (1 / n)
        + ((x - x_mean) ** 2)
        / np.sum((x - x_mean) ** 2)
    )
)

lower = y_pred - prediction_band
upper = y_pred + prediction_band

lower = np.clip(lower, 0, 100)
upper = np.clip(upper, 0, 100)


# ------------------------------------------------------------------
# Create figure
# ------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(12, 6))

# Main trend line
ax.plot(
    df["Date"],
    df["SuccessPct"],
    color="steelblue",
    linewidth=2.5,
    marker="o",
)

ax.scatter(
    df["Date"],
    df["SuccessPct"],
    color="royalblue",
    s=80,
    zorder=3,
)

## Prediction interval
#ax.fill_between(
#    df["Date"],
#    lower,
#    upper,
#    color="grey",
#    alpha=0.2,
#    label="95% Prediction Interval",
#    zorder=1,
#)

# Linear regression line
ax.plot(
    df["Date"],
    y_pred,
    color="black",
    linestyle="--",
    linewidth=2,
    label="Linear Trend",
    zorder=2,
)

# Sprint boundaries
for sprint in sorted(df["Sprint"].unique()):

    sprint_data = df[df["Sprint"] == sprint]

    start_date = sprint_data["Date"].min()

    ax.axvline(
        start_date,
        color="lightgrey",
        linestyle=":",
        linewidth=1,
    )

# ------------------------------------------------------------------
# Date axis formatting
# ------------------------------------------------------------------

ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

plt.xticks(rotation=45)

# ------------------------------------------------------------------
# Formatting
# ------------------------------------------------------------------

ax.set_xlabel("Date")
ax.set_ylabel("Overlap Classification Success (%)")

ax.set_ylim(50, 100)

ax.grid(
    True,
    linestyle="--",
    alpha=0.3,
)

# ------------------------------------------------------------------
# Sprint development periods
# ------------------------------------------------------------------

sprint_dates = pd.read_csv("static/dates.csv")

sprint_dates = sprint_dates[
    sprint_dates["Title"].isin([
        "Sprint 1 Development",
        "Sprint 2 Development",
        "Sprint 3 Development"
    ])
].copy()

sprint_dates["start_date"] = pd.to_datetime(
    sprint_dates["start_date"],
    dayfirst=True
)

sprint_dates["end_date"] = pd.to_datetime(
    sprint_dates["end_date"],
    dayfirst=True
)

sprint_colours = {
    "Sprint 1 Development": "#d9edf7",
    "Sprint 2 Development": "#dff0d8",
    "Sprint 3 Development": "#fcf8e3",
}

for _, row in sprint_dates.iterrows():

    start = row["start_date"]
    end = row["end_date"]
    title = row["Title"]

    ax.axvspan(
        start,
        end,
        alpha=0.5,
        color=sprint_colours.get(title, "lightgrey"),
        zorder=0,
    )

    midpoint = start + (end - start) / 2

    ax.text(
        midpoint,
        ax.get_ylim()[1] - 2,
        title.replace(" Development", ""),
        ha="center",
        va="top",
        fontsize=9,
        fontweight="bold",
        bbox=dict(
            facecolor="white",
            edgecolor="none",
            alpha=0.8,
        ),
    )

# ------------------------------------------------------------------
# Regression statistics
# ------------------------------------------------------------------


p_label = f"p = {p_value:.3f}"

stats_text = (
    f"R² = {r_squared:.3f}\n"
    f"{p_label}"
)

ax.text(
    0.02,
    0.95,
    stats_text,
    transform=ax.transAxes,
    fontsize=10,
    verticalalignment="top",
    bbox=dict(
        boxstyle="round",
        facecolor="white",
        edgecolor="grey",
        alpha=0.9,
    ),
)

ax.legend()

plt.tight_layout()

# ------------------------------------------------------------------
# Save / Show
# ------------------------------------------------------------------

plt.savefig(
    "plots/OverlapAssessmentSuccessTrend.png",
    dpi=300,
    bbox_inches="tight",
)

plt.close()