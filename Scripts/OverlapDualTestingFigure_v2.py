"""
Overlap Assessment Service Dual Testing script

Takes collated output of main.py and creates figures for the overlap service within the DCAT service

"""

# Author: Alex Wallage
# Version: 3
# Date: 14/07/2026

## Enhanced with AI

from datetime import date

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.stats import linregress



# colour palette

COLOUR_RECORDS = "#1B4F72"
COLOUR_ATTRIBUTES = "#117A65"
COLOUR_GEOMETRY = "#6C3483"


# Load and manipulate data

df = pd.read_csv("data/OverlapAssessmentDualTesting.csv")

# Convert YYWK format
df["Week"] = df["Week"].astype(str)

df["Year"] = "20" + df["Week"].str[:2]
df["ISO_Week"] = df["Week"].str[2:].astype(int)

df["Date"] = df.apply(
    lambda row: date.fromisocalendar(
        int(row["Year"]),
        int(row["ISO_Week"]),
        1,
    ),
    axis=1,
)

df = df.sort_values("Date")


# Calculate comparison metrics

df["StatusMatchPct"] = df["Overlaps classified successfully"] * 100

df["RecordMatchPct"] = (
    df["Overlaps Joined between databases"]
    / df["Number of  Overlaps in QGIS"]
) * 100

df["AttributeMatchPct"] = (
    (
        df["Overlaps Joined between databases"]
        - df["Cells with Differences in attribution"]
    )
    / df["Overlaps Joined between databases"]
) * 100

df["GeometryMatchPct"] = (
    (
        df["Overlaps Joined between databases"]
        - df["Cells with Differences in geometry"]
    )
    / df["Overlaps Joined between databases"]
) * 100

# Linear regression for status classification success

x = mdates.date2num(df["Date"])
y = df["StatusMatchPct"]

slope, intercept, r_value, p_value, std_err = linregress(x, y)

y_pred = intercept + (slope * x)

r_squared = r_value**2


# Create figure

fig, (ax_a, ax_b) = plt.subplots(
    2,
    1,
    figsize=(12, 9),
    sharex=True,
)


# Sprint development periods

sprint_dates = pd.read_csv("static/dates.csv")

sprint_dates = sprint_dates[
    sprint_dates["Title"].isin([
        "Sprint 1 Development",
        "Sprint 2 Development",
        "Sprint 3 Development",
    ])
].copy()

sprint_dates["start_date"] = pd.to_datetime(
    sprint_dates["start_date"],
    dayfirst=True,
)

sprint_dates["end_date"] = pd.to_datetime(
    sprint_dates["end_date"],
    dayfirst=True,
)

sprint_colours = {
    "Sprint 1 Development": "#d9edf7",
    "Sprint 2 Development": "#dff0d8",
    "Sprint 3 Development": "#fcf8e3",
}

for ax in [ax_a, ax_b]:

    for _, row in sprint_dates.iterrows():

        ax.axvspan(
            row["start_date"],
            row["end_date"],
            alpha=0.5,
            color=sprint_colours.get(row["Title"], "lightgrey"),
            zorder=0,
        )

    for sprint in sorted(df["Sprint"].unique()):

        sprint_data = df[df["Sprint"] == sprint]

        ax.axvline(
            sprint_data["Date"].min(),
            color="lightgrey",
            linestyle=":",
            linewidth=1,
        )


# Plot A - correspondence metrics

ax_a.plot(
    df["Date"],
    df["RecordMatchPct"],
    color=COLOUR_RECORDS,
    linewidth=2.2,
    marker="o",
    label="Record correspondence",
)

ax_a.plot(
    df["Date"],
    df["AttributeMatchPct"],
    color=COLOUR_ATTRIBUTES,
    linewidth=2.2,
    marker="o",
    label="Attribute correspondence",
)

ax_a.plot(
    df["Date"],
    df["GeometryMatchPct"],
    color=COLOUR_GEOMETRY,
    linewidth=2.2,
    marker="o",
    label="Geometry correspondence",
)

ax_a.set_ylabel("Correspondence (%)")

ax_a.set_ylim(5, 102)

ax_a.grid(
    True,
    linestyle="--",
    alpha=0.3,
)

ax_a.legend(
    loc="lower right",
)

ax_a.text(
    -0.04,
    1.03,
    "A",
    transform=ax_a.transAxes,
    fontsize=16,
    fontweight="bold",
)

for _, row in sprint_dates.iterrows():

    midpoint = row["start_date"] + (
        row["end_date"] - row["start_date"]
    ) / 2

    ax_a.text(
        midpoint,
        101,
        row["Title"].replace(" Development", ""),
        ha="center",
        va="top",
        fontsize=8,
        fontweight="semibold",
        color="dimgray",
        bbox=dict(
            facecolor="white",
            edgecolor="none",
            alpha=0.8,
        ),
    )


# Plot B status classification success

ax_b.plot(
    df["Date"],
    df["StatusMatchPct"],
    color="steelblue",
    linewidth=2.5,
    marker="o",
)

ax_b.scatter(
    df["Date"],
    df["StatusMatchPct"],
    color="royalblue",
    s=80,
    label="Status classification success",
    zorder=3,
)

ax_b.plot(
    df["Date"],
    y_pred,
    color="black",
    linestyle="--",
    linewidth=2,
    label="Linear trend",
    zorder=2,
)

ax_b.set_xlabel("Date")

ax_b.set_ylabel(
    "Overlap Classification Success (%)"
)

ax_b.set_ylim(50, 100)

ax_b.grid(
    True,
    linestyle="--",
    alpha=0.3,
)

ax_b.legend(
    loc="lower right",
)

ax_b.text(
    -0.04,
    1.03,
    "B",
    transform=ax_b.transAxes,
    fontsize=16,
    fontweight="bold",
)

for _, row in sprint_dates.iterrows():

    midpoint = row["start_date"] + (
        row["end_date"] - row["start_date"]
    ) / 2

    ax_b.text(
        midpoint,
        99,
        row["Title"].replace(" Development", ""),
        ha="center",
        va="top",
        fontsize=8,
        fontweight="semibold",
        color="dimgray",
        bbox=dict(
            facecolor="white",
            edgecolor="none",
            alpha=0.8,
        ),
    )


# Regression statistics

stats_text = (
    f"R² = {r_squared:.3f}\n"
    f"p = {p_value:.3f}"
)

ax_b.text(
    0.02,
    0.95,
    stats_text,
    transform=ax_b.transAxes,
    fontsize=10,
    verticalalignment="top",
    bbox=dict(
        boxstyle="round",
        facecolor="white",
        edgecolor="grey",
        alpha=0.9,
    ),
)


# Date axis formatting

ax_b.xaxis.set_major_locator(
    mdates.MonthLocator()
)

ax_b.xaxis.set_major_formatter(
    mdates.DateFormatter("%b %Y")
)

plt.xticks(rotation=45)

plt.tight_layout()


# Save

plt.savefig(
    "plots/OverlapAssessmentSuccessTrend.png",
    dpi=300,
    bbox_inches="tight",
)

plt.close()