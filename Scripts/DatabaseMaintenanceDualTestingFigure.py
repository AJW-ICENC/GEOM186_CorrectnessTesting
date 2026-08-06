"""
Database Management Service Dual Testing Figure Creation Script

Takes collated output of main.py and creates figures for the Database
Management service within the DCAT service.

"""

# Author: Alex Wallage
# Version: 2
# Date: 29/07/2026

## Enhanced with AI



from datetime import date

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


## Load and manipulate data

df = pd.read_csv(
    "data/DatabaseMaintenanceDualTesting.csv",
    sep="\t",
    )

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



## Corrected success metric


## Attribution differences are deliberately excluded.
"""
Testing identified that the vast majority of these
differences were caused by:
- UTF / ASCII encoding differences
- CellTitle formatting differences
- APPROACHES usage-band implementation differences

and therefore do not represent substantive failures
of the database management service.

"""

# Define Success Percentage
df["SuccessPct"] = (
    (
        df["Number of  ENCs in ALLRELEASED QGIS"]
        - df["Number of Missing ENCs"]
        - df["Number of Additional ENCs"]
        - df["ENCs with Differences in geometry"]
    )
    /
    df["Number of  ENCs in ALLRELEASED QGIS"]
) * 100


## Create figure

fig, ax = plt.subplots(
    figsize=(12, 6)
)

# Correctness line

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
    label="Corrected success",
    zorder=3,
)


# Sprint development periods

sprint_dates = pd.read_csv(
    "static/dates.csv"
)

sprint_dates = sprint_dates[
    sprint_dates["Title"].isin([
        "Sprint 1 Development",
        "Sprint 2 Development",
        "Sprint 3 Development"
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

for _, row in sprint_dates.iterrows():

    ax.axvspan(
        row["start_date"],
        row["end_date"],
        alpha=0.5,
        color=sprint_colours.get(
            row["Title"],
            "lightgrey",
        ),
        zorder=0,
    )

    midpoint = row["start_date"] + (
        row["end_date"]
        - row["start_date"]
    ) / 2

    ax.text(
        midpoint,
        100.05,
        row["Title"].replace(
            " Development",
            ""
        ),
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


# Date axis formatting

ax.xaxis.set_major_locator(
    mdates.MonthLocator()
)

ax.xaxis.set_major_formatter(
    mdates.DateFormatter("%b %Y")
)

plt.xticks(rotation=45)


# Formatting

ax.set_xlabel("Date")

ax.set_ylabel(
    "Database Management Success (%)"
)


ax.set_ylim(
    df["SuccessPct"].min() - 0.4,
    100.1,
)

ax.grid(
    True,
    linestyle="--",
    alpha=0.3,
)

plt.tight_layout()


## Save

plt.savefig(
    "plots/DatabaseManagementSuccessTrend.png",
    dpi=300,
    bbox_inches="tight",
)

plt.close()