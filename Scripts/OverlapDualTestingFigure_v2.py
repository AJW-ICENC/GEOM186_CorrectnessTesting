"""
Overlap Assessment Service Dual Testing script
Takes collated output of main.py and creates figures for the overlap service within the DCAT service
"""

## Author: Alex Wallage

## Version: 4

## Date: 18/08/2026

### Enhanced with AI

from datetime import date
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.stats import linregress

## colour palette

COLOUR_RECORDS = "#1B4F72"
COLOUR_ATTRIBUTES = "#117A65"
COLOUR_GEOMETRY = "#6C3483"

## Load and manipulate data

df = pd.read_csv("data/OverlapAssessmentDualTesting.csv")

## Convert YYWK format

df["Week"] = df["Week"].astype(str)
df["Year"] = "20" + df["Week"].str[:2]
df["ISO_Week"] = df["Week"].str[2:].astype(int)

df["Date"] = pd.to_datetime(
    df.apply(
        lambda row: date.fromisocalendar(
            int(row["Year"]),
            int(row["ISO_Week"]),
            1,
        ),
        axis=1,
    )
)

df = df.sort_values("Date")

## Calculate comparison metrics

df["StatusMatchPct"] = (
    df["Overlaps classified successfully"] * 100
)

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

## Create figure

fig, (ax_a, ax_b) = plt.subplots(
    2,
    1,
    figsize=(12, 9),
    sharex=True,
)

## Sprint development periods

sprint_dates = pd.read_csv("static/dates.csv")

sprint_dates = sprint_dates[
    sprint_dates["Title"].isin(
        [
            "Sprint 1 Development",
            "Sprint 2 Development",
            "Sprint 3 Development",
        ]
    )
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
            color=sprint_colours[row["Title"]],
            alpha=0.4,
        )
        
        for _, row in sprint_dates.iterrows():

            midpoint = row["start_date"] + (
                row["end_date"] - row["start_date"]
            ) / 2
        
            ax_a.text(
                midpoint,
                18,
                row["Title"].replace(" Development", ""),
                ha="center",
                va="bottom",
                fontsize=8,
                color="dimgray",
                bbox=dict(
                    facecolor="white",
                    edgecolor="none",
                    alpha=0.8,
                ),
            )

## Plot A - correspondence metrics

ax_a.plot(
    df["Date"],
    df["RecordMatchPct"],
    color=COLOUR_RECORDS,
    linewidth=2.2,
    marker="o",
    label="Record agreement",
)

ax_a.plot(
    df["Date"],
    df["AttributeMatchPct"],
    color=COLOUR_ATTRIBUTES,
    linewidth=2.2,
    marker="o",
    label="Attribute agreement",
)

ax_a.plot(
    df["Date"],
    df["GeometryMatchPct"],
    color=COLOUR_GEOMETRY,
    linewidth=2.2,
    marker="o",
    label="Geometry agreement",
)

ax_a.set_ylabel("Baseline Agreement (%)")

ax_a.set_ylim(5, 102)

ax_a.grid(
    True,
    linestyle="--",
    alpha=0.3,
)

ax_a.legend(
    loc="right",
)

ax_a.text(
    -0.04,
    1.03,
    "A",
    transform=ax_a.transAxes,
    fontsize=16,
    fontweight="bold",
)



periods = [
    {
        "label": "Pre Sprint 1",
        "start": df["Date"].min(),
        "end": sprint_dates.iloc[0]["end_date"],
    },
    {
        "label": "After Sprint 1",
        "start": sprint_dates.iloc[0]["end_date"],
        "end": sprint_dates.iloc[1]["end_date"],
    },
    {
        "label": "After Sprint 2",
        "start": sprint_dates.iloc[1]["end_date"],
        "end": sprint_dates.iloc[2]["end_date"],
    },
    {
        "label": "After Sprint 3",
        "start": sprint_dates.iloc[2]["end_date"],
        "end": df["Date"].max(),
    },
]

for period in periods:

    if period["label"] == "Pre Sprint 1":

        period_df = df[
            (df["Date"] >= period["start"])
            & (df["Date"] <= period["end"])
        ]

    else:

        period_df = df[
            (df["Date"] > period["start"])
            & (df["Date"] <= period["end"])
        ]

    if len(period_df) == 0:
        continue

    record_mean = period_df[
        "RecordMatchPct"
    ].mean()

    attribute_mean = period_df[
        "AttributeMatchPct"
    ].mean()

    geometry_mean = period_df[
        "GeometryMatchPct"
    ].mean()

    overall_mean = (
        record_mean
        + attribute_mean
        + geometry_mean
    ) / 3

    overlap_count = period_df[
        "Number of  Overlaps in GaOs db"
    ].sum()

    midpoint = (
        period["start"]
        + (period["end"] - period["start"]) / 2
    )
    
    if period["label"] == "Pre Sprint 1":
        x_pos = midpoint - pd.Timedelta(days=10)
    else:
        x_pos = midpoint

    ax_a.text(
        x_pos,
        8,
        (
            f"{period['label']}\n"
            f"Mean = {overall_mean:.1f}%\n"
            f"n = {overlap_count:,}"
        ),
        ha="center",
        va="bottom",
        fontsize=9,
    )


## Plot B status classification success

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


ax_b.set_xlabel("Date")

ax_b.set_ylabel(
    "Overlap Classification Baseline Agreement (%)"
)

ax_b.set_ylim(50, 100)

ax_b.grid(
    True,
    linestyle="--",
    alpha=0.3,
)


ax_b.text(
    -0.04,
    1.03,
    "B",
    transform=ax_b.transAxes,
    fontsize=16,
    fontweight="bold",
)

## Mean success before and after sprint deployments

sprint_dates = sprint_dates.sort_values(
    "end_date"
).reset_index(drop=True)

periods = [
    {
        "label": "Pre Sprint 1",
        "start": df["Date"].min(),
        "end": sprint_dates.iloc[0]["end_date"],
    },
    {
        "label": "After Sprint 1",
        "start": sprint_dates.iloc[0]["end_date"],
        "end": sprint_dates.iloc[1]["end_date"],
    },
    {
        "label": "After Sprint 2",
        "start": sprint_dates.iloc[1]["end_date"],
        "end": sprint_dates.iloc[2]["end_date"],
    },
    {
        "label": "After Sprint 3",
        "start": sprint_dates.iloc[2]["end_date"],
        "end": df["Date"].max(),
    },
]

for period in periods:

    if period["label"] == "Pre Sprint 1":

        period_df = df[
            (df["Date"] >= period["start"])
            & (df["Date"] <= period["end"])
        ]

    else:

        period_df = df[
            (df["Date"] > period["start"])
            & (df["Date"] <= period["end"])
        ]

    if len(period_df) == 0:
        continue

    mean_pct = period_df[
        "StatusMatchPct"
    ].mean()

    overlap_count = period_df[
        "Number of  Overlaps in GaOs db"
    ].sum()

    midpoint = (
        period["start"]
        + (period["end"] - period["start"]) / 2
    )

    ax_b.text(
        midpoint,
        52,
        (
            f"{period['label']}\n"
            f"Mean = {mean_pct:.2f}%\n"
            f"n = {overlap_count:,}"
        ),
        ha="center",
        va="bottom",
        fontsize=9,
    )


## Date axis formatting

ax_b.xaxis.set_major_locator(
    mdates.MonthLocator()
)

ax_b.xaxis.set_major_formatter(
    mdates.DateFormatter("%b %Y")
)

plt.xticks(rotation=45)

plt.tight_layout()

## Save

plt.savefig(
    "plots/OverlapAssessmentSuccessTrend.png",
    dpi=300,
    bbox_inches="tight",
)

plt.close()