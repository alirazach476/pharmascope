"""Plotly chart builders for the PharmaScope dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from pharmascope.dashboard.theme import COLORS, PLOTLY_LAYOUT


def _style(fig: go.Figure, *, height: int = 380) -> go.Figure:
    fig.update_layout(**PLOTLY_LAYOUT, height=height)
    return fig


def line_trend(
    df: pd.DataFrame,
    x: str,
    y: str,
    *,
    color: str | None = None,
    title: str = "",
    height: int = 380,
) -> go.Figure:
    fig = px.line(df, x=x, y=y, color=color, markers=True, title=title)
    fig.update_traces(line={"width": 2.5})
    return _style(fig, height=height)


def bar_rank(
    df: pd.DataFrame,
    x: str,
    y: str,
    *,
    title: str = "",
    orientation: str = "h",
    height: int = 420,
) -> go.Figure:
    if orientation == "h":
        fig = px.bar(df, x=x, y=y, orientation="h", title=title, text=x)
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
    else:
        fig = px.bar(df, x=x, y=y, title=title, text=y)
    fig.update_traces(marker_color=COLORS["accent"], textposition="outside", cliponaxis=False)
    return _style(fig, height=height)


def donut(
    df: pd.DataFrame,
    names: str,
    values: str,
    *,
    title: str = "",
    height: int = 360,
) -> go.Figure:
    fig = px.pie(df, names=names, values=values, hole=0.62, title=title)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return _style(fig, height=height)


def area_trend(
    df: pd.DataFrame,
    x: str,
    y: str,
    *,
    title: str = "",
    height: int = 380,
) -> go.Figure:
    fig = px.area(df, x=x, y=y, title=title)
    fig.update_traces(line_color=COLORS["accent_2"], fillcolor="rgba(61,139,253,0.25)")
    return _style(fig, height=height)


def heatmap(
    matrix: pd.DataFrame,
    *,
    title: str = "",
    height: int = 420,
) -> go.Figure:
    fig = px.imshow(
        matrix,
        aspect="auto",
        color_continuous_scale=["#0b1220", "#1aa6a0", "#f0c14a"],
        title=title,
    )
    return _style(fig, height=height)


def scatter_bubble(
    df: pd.DataFrame,
    x: str,
    y: str,
    size: str,
    hover: str,
    *,
    title: str = "",
    height: int = 420,
) -> go.Figure:
    fig = px.scatter(
        df,
        x=x,
        y=y,
        size=size,
        hover_name=hover,
        title=title,
        size_max=48,
    )
    fig.update_traces(marker={"color": COLORS["accent"], "line": {"width": 0}})
    return _style(fig, height=height)


def treemap(
    df: pd.DataFrame,
    path: list[str],
    values: str,
    *,
    title: str = "",
    height: int = 420,
) -> go.Figure:
    fig = px.treemap(df, path=path, values=values, title=title, color=values,
                     color_continuous_scale=["#182338", "#1aa6a0", "#f0c14a"])
    return _style(fig, height=height)


def funnel(
    labels: list[str],
    values: list[int | float],
    *,
    title: str = "",
    height: int = 360,
) -> go.Figure:
    fig = go.Figure(
        go.Funnel(
            y=labels,
            x=values,
            textinfo="value+percent initial",
            marker={"color": COLORS["series"][: len(labels)]},
        )
    )
    fig.update_layout(title=title)
    return _style(fig, height=height)
