from copy import copy
import matplotlib.pyplot as plt


def atlas(data, title=None, cmap="Greens"):
    cm = getattr(plt.cm, cmap, None)
    if cm is None:
        raise KeyError(cmap)
    palette = copy(cm)
    palette.set_over("r", 1.0)
    palette.set_under("y", 1.0)
    palette.set_bad("k", 1.0)

    h, w = data.shape
    r = w * 1.0 / h
    _ = plt.figure(
        figsize=(6.0, 6.0 / r),
        dpi=196,
        tight_layout={"w_pad": 0.0, "h_pad": 0.0, "pad": 0.0},
    )
    ax = plt.axes(frameon=False)
    ax.axes.get_yaxis().set_visible(False)
    ax.axes.get_xaxis().set_visible(False)
    _ = plt.imshow(data, cmap=palette)
    if title:
        _ = plt.text(
            0.5,
            0.1,
            title,
            ha="center",
            va="center",
            color="y",
            fontsize=24,
            transform=ax.transAxes,
        )
    plt.show()
    return
