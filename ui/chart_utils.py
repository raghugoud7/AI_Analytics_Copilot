def apply_chart_style(fig, height: int = 500):
    fig.update_layout(
        height=height,
        template="plotly_white",
        title_x=0.02,
        font=dict(size=13),
        margin=dict(l=20, r=20, t=60, b=20),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="#E5E7EB",
        zeroline=False,
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="#E5E7EB",
        zeroline=False,
    )

    return fig
