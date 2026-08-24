"""
Data Registration Service Dual Testing script
Takes collated output of main.py and creates figures for the Data Registration service within the DCAT service
"""

# Author: Alex Wallage

# Version: 4

# Date: 19/08/2026

## Enhanced with AI

from datetime import date
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

### Load and manipulate data

df = pd.read_csv("data/DataRegistrationDualTesting.csv")

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

df["SuccessPct"] = (
    df["% Registered successfully"] * 100
)

df = df.sort_values("Date")

df = df[
    ~df["Week"].isin(["2607"])
]

### Create figure

fig, ax = plt.subplots(figsize=(12, 6))

## Main trend line

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
    label="Pass",
    zorder=3,
)

## Sprint boundaries

for sprint in sorted(df["Sprint"].unique()):
    pass

## Date axis formatting

ax.xaxis.set_major_locator(
    mdates.MonthLocator()
)

ax.xaxis.set_major_formatter(
    mdates.DateFormatter("%b %Y")
)

plt.xticks(rotation=45)

## Formatting

ax.set_xlabel("Date")

ax.set_ylabel(
    "Baseline Agreement (%) (Record, Attributes, Geometry)"
)

ax.set_ylim(94, 101)

ax.grid(
    True,
    linestyle="--",
    alpha=0.3,
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

for _, row in sprint_dates.iterrows():

    ax.axvspan(
        row["start_date"],
        row["end_date"],
        color=sprint_colours[row["Title"]],
        alpha=0.4,
    )

    ax.text(
        row["start_date"]
        + (row["end_date"] - row["start_date"]) / 2,
        100.7,
        row["Title"].replace(" Development", ""),
        ha="center",
        va="top",
        fontsize=9,
    )

## Mean success after each sprint deployment

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

    period_df = df[
        (df["Date"] > period["start"])
        & (df["Date"] <= period["end"])
    ]

    if len(period_df) == 0:
        continue

    mean_pct = period_df["SuccessPct"].mean()

    total_encs = period_df[
        "CWIs registered in GaOs db"
    ].sum()

    midpoint = (
        period["start"]
        + (period["end"] - period["start"]) / 2
    )

    ax.text(
        midpoint,
        94.4,
        (
            f"{period['label']}\n"
            f"Mean = {mean_pct:.2f}%\n"
            f"ENCs = {total_encs:,}"
        ),
        ha="center",
        va="bottom",
        fontsize=9,
    )

plt.tight_layout()

## Save / Show

plt.savefig(
    "plots/DataRegistrationSuccessTrend.png",
    dpi=300,
    bbox_inches="tight",
)

#plt.show()
plt.close()