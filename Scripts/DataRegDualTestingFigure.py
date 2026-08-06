"""
Data Registration Service Dual Testing script

Takes collated output of main.py and creates figures for the Data Registration service within the DCAT service


"""

# Author: Alex Wallage
# Version: 2
# Date: 14/07/2026

## Enhanced with AI


from datetime import date

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


## Load and manipulate data

df = pd.read_csv("data/DataRegistrationDualTesting.csv")


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


df["SuccessPct"] = df["% Registered successfully"] * 100

df = df.sort_values("Date")

df = df[~df["Week"].isin(["2607"])]



## Create figure

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
    label="Pass",
    zorder=3,
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


# Date axis formatting

ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

plt.xticks(rotation=45)


# Formatting

ax.set_xlabel("Date")
ax.set_ylabel("Registration Success (%) (Record, Attributes, Geometry)")

ax.set_ylim(94, 101)

ax.grid(
    True,
    linestyle="--",
    alpha=0.3,
)



# Sprint development periods

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

plt.tight_layout()


# Save / Show

plt.savefig(
    "plots/DataRegistrationSuccessTrend.png",
    dpi=300,
    bbox_inches="tight",
)

#plt.show()
plt.close()